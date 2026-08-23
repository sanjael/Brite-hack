import re
import datetime
from typing import Optional, List, Dict, Any, Tuple
from src.models.schemas import PolicyDecisionEnum, PolicyDecisionResult
from src.policy.loader import load_policy_config
from src.policy.models import PolicyFileConfig


def calculate_age(dob_str: str, ref_date: Optional[datetime.date] = None) -> Optional[int]:
    if not dob_str:
        return None
    try:
        dob = datetime.datetime.strptime(dob_str.strip(), "%Y-%m-%d").date()
        if ref_date is None:
            ref_date = datetime.date(2026, 3, 1)
        age = ref_date.year - dob.year - ((ref_date.month, ref_date.day) < (dob.month, dob.day))
        return age
    except Exception:
        return None


def check_household_minor(household: Optional[List[Any]], ref_date: Optional[datetime.date] = None) -> Tuple[bool, bool, List[Dict[str, Any]]]:
    if household is None:
        return True, True, []

    evidence = []
    has_minor = False
    for member in household:
        if isinstance(member, dict):
            name = member.get("name", "Unknown")
            dob = member.get("date_of_birth", "")
            rel = member.get("relationship", "")
        else:
            name = getattr(member, "name", "Unknown")
            dob = getattr(member, "date_of_birth", "")
            rel = getattr(member, "relationship", "")

        age = calculate_age(dob, ref_date)
        if age is not None:
            is_under_18 = age < 18
            if is_under_18:
                has_minor = True
            evidence.append({
                "name": name,
                "relationship": rel,
                "date_of_birth": dob,
                "age": age,
                "is_minor": is_under_18,
            })
        else:
            evidence.append({
                "name": name,
                "relationship": rel,
                "date_of_birth": dob,
                "age": "UNKNOWN",
                "is_minor": True,
            })
            has_minor = True

    return has_minor, False, evidence


class PolicyEngine:
    """
    Deterministic policy authorization engine.
    
    Evaluates requested or proposed actions against ACA-2026/1 and ACA-2026/2 policy rules.
    Under policy rule 6.1, any ambiguous or unknown action MUST default to
    APPROVAL_REQUIRED / ESCALATE.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config: PolicyFileConfig = load_policy_config(config_path)

    def reload_policy(self, config_path: Optional[str] = None) -> None:
        """Reload policy configuration dynamically without restarting workflow."""
        self.config = load_policy_config(config_path)

    def evaluate_household(self, household: Optional[List[Any]], action: str = "Draft triage note") -> Tuple[Optional[PolicyDecisionResult], List[Dict[str, Any]]]:
        """
        Evaluates ACA-2026/2 Section 3.9 restriction rule.
        Returns (PolicyDecisionResult, evidence_list) if 3.9 applies, else (None, evidence_list).
        """
        has_minor, unknown_state, evidence = check_household_minor(household)
        if has_minor or unknown_state:
            reason = (
                "Household composition unknown or cannot be established. Under Rule 5.2, Section 3.9 is treated as applying."
                if unknown_state
                else "Household contains a person under 18. Under ACA-2026/2 Section 3.9, triage drafting is restricted and requires caseworker involvement from the outset."
            )
            return (
                PolicyDecisionResult(
                    decision=PolicyDecisionEnum.HANDOFF_REQUIRED,
                    action=action,
                    policy_section="3.9",
                    policy_rule="Drafting triage note restricted for households with person under 18",
                    reason=reason,
                    required_authority="Caseworker Handoff",
                ),
                evidence,
            )
        return None, evidence


    def evaluate(self, action: str) -> PolicyDecisionResult:
        """
        Deterministically evaluates an action against the loaded policy rules.
        """
        if not action or not action.strip():
            return PolicyDecisionResult(
                decision=PolicyDecisionEnum.APPROVAL_REQUIRED,
                action=action or "UNSPECIFIED",
                policy_section=self.config.default_rule.policy_section,
                policy_rule=self.config.default_rule.policy_rule,
                reason="No explicit action provided. Defaulting to supervisor approval under Policy 6.1.",
                required_authority=self.config.default_rule.required_authority,
            )

        clean_action = action.strip()

        # Check configured rules
        for rule in self.config.rules:
            # Case-insensitive substring or regex match
            pattern = re.escape(rule.action_pattern)
            if re.search(pattern, clean_action, re.IGNORECASE) or rule.action_pattern.lower() in clean_action.lower():
                return PolicyDecisionResult(
                    decision=rule.decision,
                    action=clean_action,
                    policy_section=rule.policy_section,
                    policy_rule=rule.policy_rule,
                    reason=rule.reason,
                    required_authority=rule.required_authority,
                )

        # Rule 6.1 Fallback: Ambiguous / Unknown actions
        return PolicyDecisionResult(
            decision=self.config.default_rule.decision,
            action=clean_action,
            policy_section=self.config.default_rule.policy_section,
            policy_rule=self.config.default_rule.policy_rule,
            reason=f"Action '{clean_action}' is not explicitly listed as permitted under Section 2. {self.config.default_rule.reason}",
            required_authority=self.config.default_rule.required_authority,
        )
