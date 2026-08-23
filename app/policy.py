import json
import os
import re
from typing import Optional
from app.models import PolicyDecision, PolicyDecisionEnum


class PolicyEngine:
    """Evaluates actions against Calder County Policy ACA-2026/1."""

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
