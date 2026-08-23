from typing import List, Optional
from pydantic import BaseModel
from src.models.schemas import PolicyDecisionEnum, PolicyDecisionResult


class PolicyRuleConfig(BaseModel):
    action_pattern: str
    decision: PolicyDecisionEnum
    policy_section: str
    policy_rule: str
    reason: str
    required_authority: str


class DefaultPolicyConfig(BaseModel):
    decision: PolicyDecisionEnum
    policy_section: str
    policy_rule: str
    reason: str
    required_authority: str


class PolicyFileConfig(BaseModel):
    policy_reference: str
    in_force_from: str
    department: str
    rules: List[PolicyRuleConfig]
    default_rule: DefaultPolicyConfig
