import json
import os
import hmac
import hashlib
import uuid
import datetime
from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END

from app.models import (
    Referral,
    ResidentHistory,
    TriageNote,
    PolicyDecision,
    PolicyDecisionEnum,
    ApprovalToken,
    ExecutionResult,
)
from app.policy import PolicyEngine
from app.history import get_resident_history, HistoryServiceError
from app.agent import analyze_and_triage


class WorkflowState(TypedDict, total=False):
    run_id: str
    queue_file: str
    history_api_url: str
    auto_approve: bool
    secret_key: str

    referrals: List[Dict[str, Any]]
    current_index: int
    total_count: int

    current_referral: Optional[Dict[str, Any]]
    resident_history: Optional[Dict[str, Any]]
    triage_note: Optional[Dict[str, Any]]
    policy_decision: Optional[Dict[str, Any]]

    approval_token: Optional[Dict[str, Any]]
    execution_result: Optional[Dict[str, Any]]
    escalation_file: Optional[str]
    handoff_file: Optional[str]

    completed_referrals: List[str]
    approved_referrals: List[str]
    rejected_referrals: List[str]
    escalated_referrals: List[str]
    handoff_referrals: List[str]
    failed_referrals: List[str]
    errors: List[Dict[str, Any]]
    is_finished: bool


def generate_approval_token(referral_id: str, action: str, run_id: str, secret_key: str) -> ApprovalToken:
    token_id = f"TOK-{uuid.uuid4().hex[:8]}"
    approved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = f"{token_id}:{referral_id}:{action}:{run_id}:{approved_at}"
    sig = hmac.new(secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return ApprovalToken(
        token_id=token_id,
        referral_id=referral_id,
        action=action,
        run_id=run_id,
        approved_at=approved_at,
        signature=sig,
    )


def verify_approval_token(token: Optional[ApprovalToken], referral_id: str, action: str, run_id: str, secret_key: str) -> bool:
    if not token or token.referral_id != referral_id or token.action.strip().lower() != action.strip().lower():
        return False
    if run_id and token.run_id != run_id:
        return False
    payload = f"{token.token_id}:{token.referral_id}:{token.action}:{token.run_id}:{token.approved_at}"
    expected_sig = hmac.new(secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, token.signature)


def load_queue_node(state: WorkflowState) -> Dict[str, Any]:
    queue_file = state.get("queue_file", "referral-queue.json")
    with open(queue_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] RUN STARTED")
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Loaded {len(data)} referrals from {queue_file}\n")
    return {
        "referrals": data,
        "current_index": 0,
        "total_count": len(data),
        "completed_referrals": [],
        "approved_referrals": [],
        "rejected_referrals": [],
        "escalated_referrals": [],
        "handoff_referrals": [],
        "failed_referrals": [],
        "errors": [],
        "is_finished": False,
    }


def select_referral_node(state: WorkflowState) -> Dict[str, Any]:
    idx = state.get("current_index", 0)
    referrals = state.get("referrals", [])
    if idx >= len(referrals):
        return {"is_finished": True, "current_referral": None}
    ref = Referral(**referrals[idx])
    print("-" * 50)
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [{idx + 1}/{len(referrals)}] Processing {ref.referral_id} ({ref.resident_ref}) - {ref.requested_action}")
    return {
        "current_referral": ref.model_dump(),
        "resident_history": None,
        "triage_note": None,
        "policy_decision": None,
        "approval_token": None,
        "execution_result": None,
        "escalation_file": None,
        "handoff_file": None,
    }


def fetch_history_node(state: WorkflowState) -> Dict[str, Any]:
    ref = Referral(**state["current_referral"])
    api_url = state.get("history_api_url", "http://127.0.0.1:8083")
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Fetching resident history for {ref.resident_ref}...")
    try:
        history = get_resident_history(ref.resident_ref, base_url=api_url)
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] History received ({history.status}, £{history.award_monthly:.2f}/mo)")
        return {"resident_history": history.model_dump()}
    except HistoryServiceError as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ⚠ History API error: {e}")
        return {
            "resident_history": None,
            "errors": state.get("errors", []) + [{"referral_id": ref.referral_id, "error": str(e)}],
            "failed_referrals": state.get("failed_referrals", []) + [ref.referral_id],
        }


def check_household_policy_node(state: WorkflowState) -> Dict[str, Any]:
    ref = Referral(**state["current_referral"])
    res_hist = state.get("resident_history")
    household = res_hist.get("household") if res_hist else None

    decision, evidence = PolicyEngine().evaluate_household(household)
    if decision and decision.decision == PolicyDecisionEnum.HANDOFF_REQUIRED:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Policy decision: {decision.decision.value} (Section {decision.policy_section})")
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {decision.reason}")
        return {"policy_decision": decision.model_dump(), "triage_note": None}

    return {"policy_decision": None}


def create_handoff_node(state: WorkflowState) -> Dict[str, Any]:
    ref = Referral(**state["current_referral"])
    policy_dict = state.get("policy_decision")
    policy = PolicyDecision(**policy_dict) if policy_dict else None
    res_hist = state.get("resident_history", {})
    household = res_hist.get("household", []) if res_hist else []

    handoff_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "handoffs")
    os.makedirs(handoff_dir, exist_ok=True)
    file_path = os.path.join(handoff_dir, f"{ref.referral_id}.json")

    handoff_data = {
        "referral_id": ref.referral_id,
        "resident_ref": ref.resident_ref,
        "status": "HANDOFF_REQUIRED",
        "policy": "ACA-2026/2",
        "policy_rule": "3.9",
        "reason": policy.reason if policy else "Household contains person under 18.",
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

    print("\n*** TRIAGE NOTE NOT GENERATED ***")
    print(f"✓ HANDOFF CREATED:\n{file_path}\n")

    return {
        "handoff_file": file_path,
        "handoff_referrals": state.get("handoff_referrals", []) + [ref.referral_id],
    }


def generate_triage_node(state: WorkflowState) -> Dict[str, Any]:
    ref = Referral(**state["current_referral"])
    history = ResidentHistory(**state["resident_history"])
    analysis, triage_note = analyze_and_triage(ref, history)
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Triage note generated.")
    return {"triage_note": triage_note.model_dump()}


def check_policy_node(state: WorkflowState) -> Dict[str, Any]:
    ref = Referral(**state["current_referral"])
    decision = PolicyEngine().evaluate(ref.requested_action)
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Policy decision: {decision.decision.value} (Section {decision.policy_section})")
    if "triage_note" in state and state["triage_note"]:
        state["triage_note"]["policy_status"] = f"{decision.decision.value} (Section {decision.policy_section})"
    return {"policy_decision": decision.model_dump()}


def human_approval_gate_node(state: WorkflowState) -> Dict[str, Any]:
    ref = Referral(**state["current_referral"])
    triage = TriageNote(**state["triage_note"])
    policy = PolicyDecision(**state["policy_decision"])
    auto_approve = state.get("auto_approve", False)
    run_id = state.get("run_id", "")
    secret_key = state.get("secret_key", "caseworker-guardrails-secret-key-2026")

    print("\n" + "=" * 50)
    print(" HUMAN APPROVAL REQUIRED ")
    print("=" * 50)
    print(f"Referral:         {ref.referral_id}")
    print(f"Resident:         {ref.resident_ref}")
    print(f"Requested Action: {ref.requested_action}")
    print(f"Policy Section:   {policy.policy_section} ({policy.policy_rule})")
    print(f"Policy Reason:    {policy.reason}")
    print(f"Summary:          {triage.situation_summary}")
    print("=" * 50)
    print(" *** NO ACTION HAS BEEN EXECUTED. ***")
    print("=" * 50)

    if auto_approve:
        print("[AUTO-APPROVE] Supervisor decision: APPROVED")
        token = generate_approval_token(ref.referral_id, ref.requested_action, run_id, secret_key)
        return {"approval_token": token.model_dump()}

    try:
        ans = input("Approve? [y/N]: ").strip().lower()
    except EOFError:
        ans = "n"

    if ans == "y":
        print("HUMAN APPROVAL GRANTED. Executing protected action...\n")
        token = generate_approval_token(ref.referral_id, ref.requested_action, run_id, secret_key)
        return {"approval_token": token.model_dump()}

    print("HUMAN APPROVAL REJECTED. Action NOT executed.\n")
    return {"approval_token": None}


def execute_action_node(state: WorkflowState) -> Dict[str, Any]:
    """Hard Security Execution Boundary."""
    ref = Referral(**state["current_referral"])
    policy = PolicyDecision(**state["policy_decision"])
    run_id = state.get("run_id", "")
    secret_key = state.get("secret_key", "caseworker-guardrails-secret-key-2026")

    if policy.decision == PolicyDecisionEnum.APPROVAL_REQUIRED:
        token_dict = state.get("approval_token")
        token = ApprovalToken(**token_dict) if token_dict else None
        if not verify_approval_token(token, ref.referral_id, ref.requested_action, run_id, secret_key):
            raise PermissionError(f"HARD BLOCKED: Action '{ref.requested_action}' requires valid supervisor HMAC approval token.")

    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✓ ACTION EXECUTED: '{ref.requested_action}'")
    exec_res = ExecutionResult(
        referral_id=ref.referral_id,
        action=ref.requested_action,
        executed=True,
        execution_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        details={"policy_section": policy.policy_section, "mode": "SIMULATED_MOCK_EXECUTION"},
    )
    return {
        "execution_result": exec_res.model_dump(),
        "completed_referrals": state.get("completed_referrals", []) + [ref.referral_id],
        "approved_referrals": state.get("approved_referrals", []) + ([ref.referral_id] if state.get("approval_token") else []),
    }


def escalate_node(state: WorkflowState) -> Dict[str, Any]:
    ref = Referral(**state["current_referral"])
    policy = PolicyDecision(**state["policy_decision"])
    triage = TriageNote(**state["triage_note"]) if state.get("triage_note") else None
    run_id = state.get("run_id", "")

    esc_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "escalations")
    os.makedirs(esc_dir, exist_ok=True)
    file_path = os.path.join(esc_dir, f"{ref.referral_id}.json")

    esc_data = {
        "referral_id": ref.referral_id,
        "resident_ref": ref.resident_ref,
        "requested_action": ref.requested_action,
        "policy_section": policy.policy_section,
        "policy_rule": policy.policy_rule,
        "reason": policy.reason,
        "triage_summary": triage.situation_summary if triage else ref.summary,
        "status": "ESCALATED",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "run_id": run_id,
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(esc_data, f, indent=2)

    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✖ ESCALATED: Referral {ref.referral_id} saved to {file_path}")
    return {
        "escalation_file": file_path,
        "escalated_referrals": state.get("escalated_referrals", []) + [ref.referral_id],
        "rejected_referrals": state.get("rejected_referrals", []) + ([ref.referral_id] if policy.decision == PolicyDecisionEnum.APPROVAL_REQUIRED and not state.get("approval_token") else []),
    }


def next_referral_node(state: WorkflowState) -> Dict[str, Any]:
    return {"current_index": state.get("current_index", 0) + 1}


def build_workflow_graph():
    builder = StateGraph(WorkflowState)
    builder.add_node("load_queue", load_queue_node)
    builder.add_node("select_referral", select_referral_node)
    builder.add_node("fetch_history", fetch_history_node)
    builder.add_node("check_household_policy", check_household_policy_node)
    builder.add_node("create_handoff", create_handoff_node)
    builder.add_node("generate_triage", generate_triage_node)
    builder.add_node("check_policy", check_policy_node)
    builder.add_node("human_approval_gate", human_approval_gate_node)
    builder.add_node("execute_action", execute_action_node)
    builder.add_node("escalate", escalate_node)
    builder.add_node("next_referral", next_referral_node)

    builder.set_entry_point("load_queue")
    builder.add_edge("load_queue", "select_referral")

    builder.add_conditional_edges("select_referral", lambda s: END if s.get("is_finished") else "fetch_history", {END: END, "fetch_history": "fetch_history"})
    builder.add_conditional_edges("fetch_history", lambda s: "next_referral" if not s.get("resident_history") else "check_household_policy", {"next_referral": "next_referral", "check_household_policy": "check_household_policy"})

    def route_household_policy(s: WorkflowState) -> str:
        p = s.get("policy_decision")
        if p and p.get("decision") == PolicyDecisionEnum.HANDOFF_REQUIRED.value:
            return "create_handoff"
        return "generate_triage"

    builder.add_conditional_edges("check_household_policy", route_household_policy, {"create_handoff": "create_handoff", "generate_triage": "generate_triage"})
    builder.add_edge("create_handoff", "next_referral")

    builder.add_edge("generate_triage", "check_policy")

    def route_policy(s: WorkflowState) -> str:
        d = s.get("policy_decision", {}).get("decision")
        if d == PolicyDecisionEnum.ALLOWED.value:
            return "execute_action"
        elif d == PolicyDecisionEnum.APPROVAL_REQUIRED.value:
            return "human_approval_gate"
        return "escalate"

    builder.add_conditional_edges("check_policy", route_policy, {"execute_action": "execute_action", "human_approval_gate": "human_approval_gate", "escalate": "escalate"})
    builder.add_conditional_edges("human_approval_gate", lambda s: "execute_action" if s.get("approval_token") else "escalate", {"execute_action": "execute_action", "escalate": "escalate"})

    builder.add_edge("execute_action", "next_referral")
    builder.add_edge("escalate", "next_referral")
    builder.add_edge("next_referral", "select_referral")

    return builder.compile()

