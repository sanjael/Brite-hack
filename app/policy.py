import json
import os
import re
import datetime
from typing import Optional, List, Dict, Any, Tuple
from app.models import PolicyDecision, PolicyDecisionEnum


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
    """Evaluates actions against Calder County Policy ACA-2026/1 and ACA-2026/2 Amendment."""

    def __init__(self, config_path: Optional[str] = None):
        if not config_path:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config",
                "policy.json",
            )
        self.rules = []
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self.rules = json.load(f).get("rules", [])

    def evaluate_household(self, household: Optional[List[Any]], action: str = "Draft triage note") -> Tuple[Optional[PolicyDecision], List[Dict[str, Any]]]:
        """
        Evaluates ACA-2026/2 Section 3.9 restriction rule.
        Returns (PolicyDecision, evidence_list) if 3.9 applies, else (None, evidence_list).
        """
        has_minor, unknown_state, evidence = check_household_minor(household)
        if has_minor or unknown_state:
            reason = (
                "Household composition unknown or cannot be established. Under Rule 5.2, Section 3.9 is treated as applying."
                if unknown_state
                else "Household contains a person under 18. Under ACA-2026/2 Section 3.9, triage drafting is restricted and requires caseworker involvement from the outset."
            )
            return (
                PolicyDecision(
                    decision=PolicyDecisionEnum.HANDOFF_REQUIRED,
                    action=action,
                    policy_section="3.9",
                    policy_rule="Drafting triage note restricted for households with person under 18",
                    reason=reason,
                ),
                evidence,
            )
        return None, evidence

    def evaluate(self, action: str) -> PolicyDecision:
        if not action or not action.strip():
            return PolicyDecision(
                decision=PolicyDecisionEnum.APPROVAL_REQUIRED,
                action=action or "UNSPECIFIED",
                policy_section="6.1",
                policy_rule="Unclear action boundary rule",
                reason="No explicit action provided. Defaulting to supervisor approval under Policy 6.1.",
            )

        clean_action = action.strip()
        for rule in self.rules:
            pattern = re.escape(rule["action_pattern"])
            if re.search(pattern, clean_action, re.IGNORECASE) or rule["action_pattern"].lower() in clean_action.lower():
                return PolicyDecision(
                    decision=PolicyDecisionEnum(rule["decision"]),
                    action=clean_action,
                    policy_section=rule["policy_section"],
                    policy_rule=rule["policy_rule"],
                    reason=rule["reason"],
                )

        # Policy Rule 6.1 Fallback: Ambiguous / Unknown actions
        return PolicyDecision(
            decision=PolicyDecisionEnum.APPROVAL_REQUIRED,
            action=clean_action,
            policy_section="6.1",
            policy_rule="Unclear action boundary rule",
            reason=f"Action '{clean_action}' is not explicitly listed as permitted under Section 2. Under Rule 6.1, ambiguous actions must be treated as requiring supervisor approval.",
        )

