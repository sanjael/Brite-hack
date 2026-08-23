import re
from typing import Optional
from src.models.schemas import PolicyDecisionEnum, PolicyDecisionResult
from src.policy.loader import load_policy_config
from src.policy.models import PolicyFileConfig


class PolicyEngine:
    """
    Deterministic policy authorization engine.
    
    Evaluates requested or proposed actions against ACA-2026/1 policy rules.
    Under policy rule 6.1, any ambiguous or unknown action MUST default to
    APPROVAL_REQUIRED / ESCALATE.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config: PolicyFileConfig = load_policy_config(config_path)

    def reload_policy(self, config_path: Optional[str] = None) -> None:
        """Reload policy configuration dynamically without restarting workflow."""
        self.config = load_policy_config(config_path)

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
