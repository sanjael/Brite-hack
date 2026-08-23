import logging
from typing import Dict, Any, Callable
from langgraph.graph import StateGraph, END
from src.agent.state import CaseworkerState
from src.policy.engine import PolicyEngine
from src.tools.history_client import HistoryClient
from src.tools.executor import ControlledExecutor
from src.approval.gate import HumanApprovalGate
from src.escalation.manager import EscalationManager
from src.audit.logger import AuditLogger
from src.models.schemas import PolicyDecisionEnum

from src.agent.nodes import (
    load_referrals_node,
    select_next_referral_node,
    fetch_history_node,
    analyze_referral_node,
    draft_triage_note_node,
    evaluate_policy_node,
    execute_allowed_action_node,
    request_human_approval_node,
    execute_approved_action_node,
    escalate_node,
    prepare_next_referral_node,
    finalize_run_node,
)

logger = logging.getLogger(__name__)


def build_caseworker_graph(
    policy_engine: PolicyEngine,
    history_client: HistoryClient,
    executor: ControlledExecutor,
    gate: HumanApprovalGate,
    escalation_manager: EscalationManager,
    audit_logger: AuditLogger,
):
    """
    Constructs and compiles the LangGraph StateGraph workflow for Caseworker Morning.
    """
    builder = StateGraph(CaseworkerState)

    # Node definitions wrapping parameters
    builder.add_node("load_referrals", lambda state: load_referrals_node(state, audit_logger))
    builder.add_node("select_next_referral", lambda state: select_next_referral_node(state, audit_logger))
    builder.add_node("fetch_history", lambda state: fetch_history_node(state, history_client, audit_logger))
    builder.add_node("analyze_referral", lambda state: analyze_referral_node(state, audit_logger))
    builder.add_node("draft_triage_note", lambda state: draft_triage_note_node(state, audit_logger))
    builder.add_node("evaluate_policy", lambda state: evaluate_policy_node(state, policy_engine, audit_logger))
    builder.add_node("execute_allowed_action", lambda state: execute_allowed_action_node(state, executor, audit_logger))
    builder.add_node("request_human_approval", lambda state: request_human_approval_node(state, gate, audit_logger))
    builder.add_node("execute_approved_action", lambda state: execute_approved_action_node(state, executor, audit_logger))
    builder.add_node("escalate", lambda state: escalate_node(state, escalation_manager, audit_logger))
    builder.add_node("prepare_next_referral", lambda state: prepare_next_referral_node(state, audit_logger))
    builder.add_node("finalize_run", lambda state: finalize_run_node(state, audit_logger))

    # Entry point
    builder.set_entry_point("load_referrals")
    builder.add_edge("load_referrals", "select_next_referral")

    # Conditional router for queue exhaustion
    def route_queue_exhaustion(state: CaseworkerState) -> str:
        if state.get("is_finished"):
            return "finalize_run"
        return "fetch_history"

    builder.add_conditional_edges(
        "select_next_referral",
        route_queue_exhaustion,
        {
            "finalize_run": "finalize_run",
            "fetch_history": "fetch_history",
        },
    )

    # Conditional router for history fetch success
    def route_history_result(state: CaseworkerState) -> str:
        if state.get("resident_history") is None:
            return "prepare_next_referral"
        return "analyze_referral"

    builder.add_conditional_edges(
        "fetch_history",
        route_history_result,
        {
            "prepare_next_referral": "prepare_next_referral",
            "analyze_referral": "analyze_referral",
        },
    )

    builder.add_edge("analyze_referral", "draft_triage_note")
    builder.add_edge("draft_triage_note", "evaluate_policy")

    # Policy Routing Edge
    def route_by_policy_decision(state: CaseworkerState) -> str:
        pol_dict = state.get("policy_decision")
        if not pol_dict:
            return "escalate"
        decision = pol_dict.get("decision")
        if decision == PolicyDecisionEnum.ALLOWED.value:
            return "execute_allowed_action"
        elif decision == PolicyDecisionEnum.APPROVAL_REQUIRED.value:
            return "request_human_approval"
        else:
            return "escalate"

    builder.add_conditional_edges(
        "evaluate_policy",
        route_by_policy_decision,
        {
            "execute_allowed_action": "execute_allowed_action",
            "request_human_approval": "request_human_approval",
            "escalate": "escalate",
        },
    )

    # Approval Routing Edge
    def route_by_approval(state: CaseworkerState) -> str:
        if state.get("approval_granted") is True:
            return "execute_approved_action"
        return "escalate"

    builder.add_conditional_edges(
        "request_human_approval",
        route_by_approval,
        {
            "execute_approved_action": "execute_approved_action",
            "escalate": "escalate",
        },
    )

    builder.add_edge("execute_allowed_action", "prepare_next_referral")
    builder.add_edge("execute_approved_action", "prepare_next_referral")
    builder.add_edge("escalate", "prepare_next_referral")
    builder.add_edge("prepare_next_referral", "select_next_referral")

    builder.add_edge("finalize_run", END)

    return builder.compile()
