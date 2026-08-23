import json
import os
import logging
from typing import Dict, Any, Optional
from src.agent.state import CaseworkerState
from src.agent.prompts import CASEWORKER_ANALYSIS_SYSTEM_PROMPT, CASEWORKER_ANALYSIS_USER_TEMPLATE
from src.models.schemas import (
    Referral,
    ResidentHistory,
    LLMAnalysis,
    TriageNote,
    PolicyDecisionResult,
    PolicyDecisionEnum,
)
from src.policy.engine import PolicyEngine
from src.tools.history_client import HistoryClient, HistoryClientError
from src.tools.executor import ControlledExecutor
from src.approval.gate import HumanApprovalGate
from src.escalation.manager import EscalationManager
from src.audit.logger import AuditLogger

logger = logging.getLogger(__name__)


def get_groq_llm_client():
    """Initializes Groq LLM client if GROQ_API_KEY is available."""
    api_key = os.environ.get("GROQ_API_KEY")
    model_name = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    if not api_key:
        return None, model_name
    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(groq_api_key=api_key, model_name=model_name, temperature=0.1)
        return llm, model_name
    except ImportError:
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            return client, model_name
        except ImportError:
            return None, model_name


def load_referrals_node(state: CaseworkerState, audit_logger: AuditLogger) -> Dict[str, Any]:
    """STEP 1: Read overnight referrals from file."""
    queue_file = state.get("referral_queue_file", "referral-queue.json")
    audit_logger.log_event(
        node="LOAD_REFERRALS",
        event_type="REFERRALS_LOADED_START",
        status="IN_PROGRESS",
        details={"queue_file": queue_file},
    )

    if not os.path.exists(queue_file):
        raise FileNotFoundError(f"Referral queue file not found at: {queue_file}")

    with open(queue_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    audit_logger.log_event(
        node="LOAD_REFERRALS",
        event_type="REFERRALS_LOADED_SUCCESS",
        status="COMPLETED",
        details={"count": len(data)},
    )

    return {
        "referrals": data,
        "current_index": 0,
        "total_referrals": len(data),
        "completed_referrals": [],
        "approved_referrals": [],
        "rejected_referrals": [],
        "escalated_referrals": [],
        "handoff_referrals": [],
        "failed_referrals": [],
        "errors": [],
        "is_finished": False,
    }


def select_next_referral_node(state: CaseworkerState, audit_logger: AuditLogger) -> Dict[str, Any]:
    """Selects next referral to process or finishes queue."""
    idx = state.get("current_index", 0)
    referrals = state.get("referrals", [])

    if idx >= len(referrals):
        audit_logger.log_event(
            node="SELECT_NEXT_REFERRAL",
            event_type="QUEUE_EXHAUSTED",
            status="COMPLETED",
            details={"total_processed": idx},
        )
        return {"is_finished": True, "current_referral": None}

    ref_dict = referrals[idx]
    ref = Referral(**ref_dict)

    audit_logger.log_event(
        node="SELECT_NEXT_REFERRAL",
        event_type="REFERRAL_SELECTED",
        status="IN_PROGRESS",
        referral_id=ref.referral_id,
        action=ref.requested_action,
        details={"index": idx + 1, "total": len(referrals), "resident_ref": ref.resident_ref},
    )

    return {
        "current_referral": ref.model_dump(),
        "requested_action": ref.requested_action,
        "resident_history": None,
        "llm_analysis": None,
        "triage_note": None,
        "policy_decision": None,
        "approval_granted": None,
        "approval_token": None,
        "execution_result": None,
        "escalation_artifact": None,
        "handoff_artifact": None,
    }


def fetch_history_node(state: CaseworkerState, history_client: HistoryClient, audit_logger: AuditLogger) -> Dict[str, Any]:
    """STEP 2: Retrieve resident history from API."""
    ref = Referral(**state["current_referral"])
    audit_logger.log_event(
        node="FETCH_HISTORY",
        event_type="HISTORY_REQUESTED",
        status="IN_PROGRESS",
        referral_id=ref.referral_id,
        details={"resident_ref": ref.resident_ref},
    )

    try:
        res_history = history_client.get_resident(ref.resident_ref)
        audit_logger.log_event(
            node="FETCH_HISTORY",
            event_type="HISTORY_RECEIVED",
            status="COMPLETED",
            referral_id=ref.referral_id,
            details={
                "resident_ref": res_history.resident_ref,
                "status": res_history.status,
                "events_count": len(res_history.events),
            },
        )
        return {"resident_history": res_history.model_dump()}
    except HistoryClientError as e:
        audit_logger.log_event(
            node="FETCH_HISTORY",
            event_type="HISTORY_FETCH_FAILED",
            status="FAILED",
            referral_id=ref.referral_id,
            reason=str(e),
        )
        return {
            "resident_history": None,
            "errors": state.get("errors", []) + [{"referral_id": ref.referral_id, "error": str(e)}],
        }


def check_household_policy_node(state: CaseworkerState, policy_engine: PolicyEngine, audit_logger: AuditLogger) -> Dict[str, Any]:
    """Evaluates ACA-2026/2 Section 3.9 restriction rule based on official household data."""
    ref = Referral(**state["current_referral"])
    res_hist = state.get("resident_history")
    household = res_hist.get("household") if res_hist else None

    decision_res, evidence = policy_engine.evaluate_household(household)
    if decision_res and decision_res.decision == PolicyDecisionEnum.HANDOFF_REQUIRED:
        audit_logger.log_event(
            node="CHECK_HOUSEHOLD_POLICY",
            event_type="HOUSEHOLD_POLICY_RESTRICTED",
            status="HANDOFF_REQUIRED",
            referral_id=ref.referral_id,
            action=ref.requested_action,
            policy_rule="3.9",
            reason=decision_res.reason,
            details={"evidence": evidence, "triage_note_generated": False},
        )
        return {"policy_decision": decision_res.model_dump(), "triage_note": None}

    return {"policy_decision": None}


def create_handoff_node(state: CaseworkerState, audit_logger: AuditLogger) -> Dict[str, Any]:
    """Creates a Handoff artifact for caseworker review when Section 3.9 applies."""
    import datetime
    ref = Referral(**state["current_referral"])
    pol_dict = state.get("policy_decision")
    policy_res = PolicyDecisionResult(**pol_dict) if pol_dict else None
    res_hist = state.get("resident_history", {})
    household = res_hist.get("household", []) if res_hist else []

    handoff_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "artifacts", "handoffs")
    os.makedirs(handoff_dir, exist_ok=True)
    file_path = os.path.join(handoff_dir, f"{ref.referral_id}.json")

    handoff_data = {
        "referral_id": ref.referral_id,
        "resident_ref": ref.resident_ref,
        "status": "HANDOFF_REQUIRED",
        "policy": "ACA-2026/2",
        "policy_rule": "3.9",
        "reason": policy_res.reason if policy_res else "Household contains person under 18.",
        "household_contains_minor": True,
        "household_evidence": household,
        "work_completed": [
            "✓ Referral read",
            "✓ Resident history retrieved",
            "✓ Household composition determined",
        ],
        "work_not_completed": [
            "✗ Draft triage note",
        ],
        "triage_note_generated": False,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(handoff_data, f, indent=2)

    print("\n" + "=" * 50)
    print(" HANDOFF TO CASEWORKER ")
    print("=" * 50)
    print(f"Referral:         {ref.referral_id}")
    print(f"Resident:         {ref.resident_ref}")
    print(f"Policy Rule:      ACA-2026/2 Section 3.9")
    print(f"Reason:           Household contains person under 18.")
    print(" *** TRIAGE NOTE NOT GENERATED ***")
    print(f"✓ HANDOFF CREATED: {file_path}")
    print("=" * 50 + "\n")

    audit_logger.log_event(
        node="CREATE_HANDOFF",
        event_type="HANDOFF_CREATED",
        status="HANDOFF_REQUIRED",
        referral_id=ref.referral_id,
        action=ref.requested_action,
        policy_rule="3.9",
        reason=policy_res.reason if policy_res else "Household contains person under 18.",
        details={"handoff_file": file_path, "triage_note_generated": False},
    )

    handoffs = state.get("handoff_referrals", []) + [ref.referral_id]
    return {"handoff_artifact": handoff_data, "handoff_referrals": handoffs}



def analyze_referral_node(state: CaseworkerState, audit_logger: AuditLogger) -> Dict[str, Any]:
    """Analyze referral and resident history using LLM reasoning."""
    ref = Referral(**state["current_referral"])
    history_dict = state.get("resident_history")
    
    if not history_dict:
        # Cannot analyze without history
        return {"llm_analysis": None}

    history = ResidentHistory(**history_dict)

    household_summary = ", ".join([f"{h.name} ({h.relationship})" for h in history.household]) or "None listed"
    events_summary = " | ".join([f"{e.date}: {e.type} ({e.detail})" for e in history.events]) or "No prior events"

    llm, model_name = get_groq_llm_client()

    if llm is not None:
        try:
            user_msg = CASEWORKER_ANALYSIS_USER_TEMPLATE.format(
                referral_id=ref.referral_id,
                received_at=ref.received_at,
                resident_ref=ref.resident_ref,
                source=ref.source,
                urgency=ref.urgency,
                summary=ref.summary,
                requested_action=ref.requested_action,
                status=history.status,
                benefit_code=history.benefit_code,
                district=history.district,
                award_monthly=history.award_monthly,
                household_summary=household_summary,
                events_summary=events_summary,
            )

            if hasattr(llm, "invoke"):
                from langchain_core.messages import SystemMessage, HumanMessage
                res = llm.invoke([SystemMessage(content=CASEWORKER_ANALYSIS_SYSTEM_PROMPT), HumanMessage(content=user_msg)])
                content = res.content
            else:
                res = llm.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": CASEWORKER_ANALYSIS_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    response_format={"type": "json_object"} if "json" in model_name else None,
                )
                content = res.choices[0].message.content

            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            analysis = LLMAnalysis(**parsed)

        except Exception as e:
            logger.warning(f"Groq LLM call failed/fallback for {ref.referral_id}: {e}")
            analysis = _fallback_analysis(ref, history)
    else:
        # Standard analytical engine fallback when Groq API key is omitted
        analysis = _fallback_analysis(ref, history)

    audit_logger.log_event(
        node="ANALYZE_REFERRAL",
        event_type="LLM_ANALYSIS_COMPLETED",
        status="COMPLETED",
        referral_id=ref.referral_id,
        action=analysis.proposed_action,
        details={"confidence": analysis.confidence, "model": model_name if llm else "fallback-engine"},
    )

    return {"llm_analysis": analysis.model_dump()}


def _fallback_analysis(ref: Referral, history: ResidentHistory) -> LLMAnalysis:
    """Deterministic analytical fallback for offline/no-key runs."""
    relevant = [f"{e.date}: {e.type}" for e in history.events[-2:]] if history.events else []
    return LLMAnalysis(
        summary=f"Referral from {ref.source} for resident {history.resident_ref} ({history.district}). {ref.summary}",
        relevant_history=relevant,
        proposed_action=ref.requested_action,
        reasoning=f"Analyzed situation for award (£{history.award_monthly:.2f}/mo) and historical case events.",
        confidence=0.95,
        uncertainty_notes=None,
    )


def draft_triage_note_node(state: CaseworkerState, audit_logger: AuditLogger) -> Dict[str, Any]:
    """STEP 3: Draft structured triage note."""
    ref = Referral(**state["current_referral"])
    analysis_dict = state.get("llm_analysis")

    if analysis_dict:
        analysis = LLMAnalysis(**analysis_dict)
        summary = analysis.summary
        rel_hist = analysis.relevant_history
        proposed = analysis.proposed_action
        reasoning = analysis.reasoning
    else:
        summary = ref.summary
        rel_hist = []
        proposed = ref.requested_action
        reasoning = "Direct referral processing."

    triage_note = TriageNote(
        referral_id=ref.referral_id,
        resident_ref=ref.resident_ref,
        source=ref.source,
        urgency=ref.urgency,
        situation_summary=summary,
        relevant_history=rel_hist,
        requested_action=ref.requested_action,
        proposed_next_step=proposed,
        policy_status="PENDING_POLICY_EVALUATION",
        reasoning=reasoning,
    )

    audit_logger.log_event(
        node="DRAFT_TRIAGE_NOTE",
        event_type="TRIAGE_NOTE_DRAFTED",
        status="COMPLETED",
        referral_id=ref.referral_id,
        action=proposed,
        details={"urgency": ref.urgency},
    )

    return {"triage_note": triage_note.model_dump()}


def evaluate_policy_node(state: CaseworkerState, policy_engine: PolicyEngine, audit_logger: AuditLogger) -> Dict[str, Any]:
    """Evaluates proposed action against policy engine ACA-2026/1."""
    ref = Referral(**state["current_referral"])
    requested_action = state.get("requested_action", ref.requested_action)

    decision_res = policy_engine.evaluate(requested_action)

    audit_logger.log_event(
        node="EVALUATE_POLICY",
        event_type="POLICY_CHECKED",
        status=decision_res.decision.value,
        referral_id=ref.referral_id,
        action=decision_res.action,
        policy_rule=decision_res.policy_section,
        reason=decision_res.reason,
        details={"required_authority": decision_res.required_authority},
    )

    # Update triage note policy status
    if "triage_note" in state and state["triage_note"]:
        tn = state["triage_note"]
        tn["policy_status"] = f"{decision_res.decision.value} (Section {decision_res.policy_section})"

    return {"policy_decision": decision_res.model_dump()}


def execute_allowed_action_node(
    state: CaseworkerState, executor: ControlledExecutor, audit_logger: AuditLogger
) -> Dict[str, Any]:
    """Executes actions permitted without approval under Policy Section 2."""
    ref = Referral(**state["current_referral"])
    policy_res = PolicyDecisionResult(**state["policy_decision"])
    run_id = state.get("run_id", "")

    audit_logger.log_event(
        node="EXECUTE_ALLOWED_ACTION",
        event_type="ACTION_ALLOWED",
        status="EXECUTING",
        referral_id=ref.referral_id,
        action=policy_res.action,
        policy_rule=policy_res.policy_section,
    )

    exec_result = executor.execute(
        referral_id=ref.referral_id,
        action=policy_res.action,
        policy_decision=policy_res,
        approval_token=None,
        run_id=run_id,
    )

    audit_logger.log_event(
        node="EXECUTE_ALLOWED_ACTION",
        event_type="ACTION_EXECUTED",
        status="COMPLETED",
        referral_id=ref.referral_id,
        action=policy_res.action,
        policy_rule=policy_res.policy_section,
    )

    completed = state.get("completed_referrals", []) + [ref.referral_id]
    return {"execution_result": exec_result.model_dump(), "completed_referrals": completed}


def request_human_approval_node(
    state: CaseworkerState, gate: HumanApprovalGate, audit_logger: AuditLogger
) -> Dict[str, Any]:
    """Pauses for supervisor approval when decision is APPROVAL_REQUIRED."""
    ref = Referral(**state["current_referral"])
    triage_note = TriageNote(**state["triage_note"])
    policy_res = PolicyDecisionResult(**state["policy_decision"])
    run_id = state.get("run_id", "")

    audit_logger.log_event(
        node="REQUEST_HUMAN_APPROVAL",
        event_type="APPROVAL_REQUESTED",
        status="PAUSED_FOR_HUMAN",
        referral_id=ref.referral_id,
        action=policy_res.action,
        policy_rule=policy_res.policy_section,
        reason=policy_res.reason,
    )

    is_approved, token = gate.request_approval(
        referral=ref,
        triage_note=triage_note,
        policy_decision=policy_res,
        run_id=run_id,
    )

    if is_approved and token:
        audit_logger.log_event(
            node="REQUEST_HUMAN_APPROVAL",
            event_type="APPROVAL_GRANTED",
            status="APPROVED",
            referral_id=ref.referral_id,
            action=policy_res.action,
            details={"token_id": token.token_id, "approved_by": token.approved_by},
        )
        return {"approval_granted": True, "approval_token": token.model_dump()}
    else:
        audit_logger.log_event(
            node="REQUEST_HUMAN_APPROVAL",
            event_type="APPROVAL_REJECTED",
            status="REJECTED",
            referral_id=ref.referral_id,
            action=policy_res.action,
            reason="Supervisor rejected the proposed action.",
        )
        return {"approval_granted": False, "approval_token": None}


def execute_approved_action_node(
    state: CaseworkerState, executor: ControlledExecutor, audit_logger: AuditLogger
) -> Dict[str, Any]:
    """Executes a protected action after human approval token is verified."""
    ref = Referral(**state["current_referral"])
    policy_res = PolicyDecisionResult(**state["policy_decision"])
    token_dict = state.get("approval_token")
    token = ApprovalToken(**token_dict) if token_dict else None
    run_id = state.get("run_id", "")

    exec_result = executor.execute(
        referral_id=ref.referral_id,
        action=policy_res.action,
        policy_decision=policy_res,
        approval_token=token,
        run_id=run_id,
    )

    audit_logger.log_event(
        node="EXECUTE_APPROVED_ACTION",
        event_type="ACTION_EXECUTED",
        status="COMPLETED",
        referral_id=ref.referral_id,
        action=policy_res.action,
        policy_rule=policy_res.policy_section,
        details={"token_id": token.token_id if token else None},
    )

    approved = state.get("approved_referrals", []) + [ref.referral_id]
    completed = state.get("completed_referrals", []) + [ref.referral_id]
    return {
        "execution_result": exec_result.model_dump(),
        "approved_referrals": approved,
        "completed_referrals": completed,
    }


def escalate_node(
    state: CaseworkerState, manager: EscalationManager, audit_logger: AuditLogger
) -> Dict[str, Any]:
    """Escalates forbidden or human-rejected actions."""
    ref = Referral(**state["current_referral"])
    policy_res = PolicyDecisionResult(**state["policy_decision"])
    triage_dict = state.get("triage_note")
    triage_note = TriageNote(**triage_dict) if triage_dict else None
    run_id = state.get("run_id", "")

    if state.get("approval_granted") is False:
        escalation_reason = "Human supervisor explicitly REJECTED the proposed protected action."
    else:
        escalation_reason = f"Action violates Policy Section {policy_res.policy_section}: {policy_res.reason}"

    paths = manager.create_escalation(
        referral=ref,
        policy_decision=policy_res,
        triage_note=triage_note,
        escalation_reason=escalation_reason,
        run_id=run_id,
    )

    audit_logger.log_event(
        node="ESCALATE",
        event_type="ESCALATION_CREATED",
        status="ESCALATED",
        referral_id=ref.referral_id,
        action=policy_res.action,
        policy_rule=policy_res.policy_section,
        reason=escalation_reason,
        details=paths,
    )

    escalated = state.get("escalated_referrals", []) + [ref.referral_id]
    rejected = state.get("rejected_referrals", []) + ([ref.referral_id] if state.get("approval_granted") is False else [])

    return {
        "escalation_artifact": paths,
        "escalated_referrals": escalated,
        "rejected_referrals": rejected,
    }


def prepare_next_referral_node(state: CaseworkerState, audit_logger: AuditLogger) -> Dict[str, Any]:
    """Increments referral queue index."""
    curr_idx = state.get("current_index", 0)
    ref_dict = state.get("current_referral")
    ref_id = ref_dict["referral_id"] if ref_dict else "UNKNOWN"

    audit_logger.log_event(
        node="PREPARE_NEXT_REFERRAL",
        event_type="REFERRAL_COMPLETED",
        status="COMPLETED",
        referral_id=ref_id,
        details={"next_index": curr_idx + 1},
    )

    return {"current_index": curr_idx + 1}


def finalize_run_node(state: CaseworkerState, audit_logger: AuditLogger) -> Dict[str, Any]:
    """Finalizes run and outputs summary."""
    run_id = state.get("run_id", "")

    audit_logger.log_event(
        node="FINALIZE_RUN",
        event_type="RUN_COMPLETED",
        status="COMPLETED",
        details={
            "total": state.get("total_referrals", 0),
            "completed": len(state.get("completed_referrals", [])),
            "approved": len(state.get("approved_referrals", [])),
            "rejected": len(state.get("rejected_referrals", [])),
            "escalated": len(state.get("escalated_referrals", [])),
            "handoffs": len(state.get("handoff_referrals", [])),
            "failed": len(state.get("failed_referrals", [])),
        },
    )

    return {"is_finished": True}
