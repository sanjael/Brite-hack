from typing import TypedDict, List, Optional, Dict, Any
from src.models.schemas import (
    Referral,
    ResidentHistory,
    LLMAnalysis,
    TriageNote,
    PolicyDecisionResult,
    ApprovalToken,
    ExecutionResult,
)


class CaseworkerState(TypedDict, total=False):
    """
    LangGraph Typed State for Caseworker Morning Workflow.
    """

    run_id: str
    referral_queue_file: str
    history_api_url: str
    
    # Queue management
    referrals: List[Dict[str, Any]]
    current_index: int
    total_referrals: int

    # Current item context
    current_referral: Optional[Dict[str, Any]]
    resident_history: Optional[Dict[str, Any]]
    llm_analysis: Optional[Dict[str, Any]]
    triage_note: Optional[Dict[str, Any]]
    requested_action: Optional[str]
    policy_decision: Optional[Dict[str, Any]]

    # Approval and Execution
    approval_granted: Optional[bool]
    approval_token: Optional[Dict[str, Any]]
    execution_result: Optional[Dict[str, Any]]
    escalation_artifact: Optional[Dict[str, Any]]

    # Results Tracking
    completed_referrals: List[str]
    approved_referrals: List[str]
    rejected_referrals: List[str]
    escalated_referrals: List[str]
    failed_referrals: List[str]
    
    # Audit Trace
    errors: List[Dict[str, Any]]
    is_finished: bool
