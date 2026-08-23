from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class PolicyDecisionEnum(str, Enum):
    ALLOWED = "ALLOWED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    DENIED = "DENIED"


class Referral(BaseModel):
    referral_id: str
    received_at: str
    resident_ref: str
    source: str
    summary: str
    requested_action: str
    urgency: str


class HouseholdMember(BaseModel):
    name: str
    date_of_birth: str
    relationship: str


class CaseEvent(BaseModel):
    date: str
    type: str
    detail: str


class ResidentHistory(BaseModel):
    resident_ref: str
    status: str
    benefit_code: str
    district: str
    award_monthly: float
    household: List[HouseholdMember] = []
    events: List[CaseEvent] = []


class LLMAnalysis(BaseModel):
    summary: str
    relevant_history: List[str] = Field(default_factory=list)
    proposed_action: str
    reasoning: str
    confidence: float = 1.0
    uncertainty_notes: Optional[str] = None


class TriageNote(BaseModel):
    referral_id: str
    resident_ref: str
    source: str
    urgency: str
    situation_summary: str
    relevant_history: List[str] = Field(default_factory=list)
    requested_action: str
    proposed_next_step: str
    policy_status: str
    reasoning: str


class PolicyDecisionResult(BaseModel):
    decision: PolicyDecisionEnum
    action: str
    policy_section: str
    policy_rule: str
    reason: str
    required_authority: str


class ApprovalToken(BaseModel):
    token_id: str
    referral_id: str
    action: str
    run_id: str
    approved_at: str
    approved_by: str = "Supervisor"
    signature: str


class AuditEvent(BaseModel):
    timestamp: str
    run_id: str
    referral_id: Optional[str] = None
    node: str
    event_type: str
    action: Optional[str] = None
    status: str
    policy_rule: Optional[str] = None
    reason: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    referral_id: str
    action: str
    executed: bool
    execution_timestamp: str
    details: Dict[str, Any] = Field(default_factory=dict)
    approval_token_used: Optional[str] = None
