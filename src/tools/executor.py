import datetime
import hmac
import hashlib
import logging
from typing import Optional, Dict, Any
from src.models.schemas import PolicyDecisionEnum, PolicyDecisionResult, ApprovalToken, ExecutionResult

logger = logging.getLogger(__name__)


class GuardrailSecurityError(PermissionError):
    """Raised when an execution attempt violates the security guardrail boundary."""
    pass


class ControlledExecutor:
    """
    Controlled Execution Layer — The Hard Security Guardrail.
    
    The LLM has NO direct access to execution methods in this class.
    All side-effects must pass through `execute(...)`.
    
    If an action requires supervisor approval (APPROVAL_REQUIRED),
    the executor requires a cryptographically valid, scoped `ApprovalToken`.
    Without a valid token matching the referral_id, action, and run_id,
    the executor raises `GuardrailSecurityError` and refuses execution.
    """

    def __init__(self, secret_key: str = "caseworker-guardrails-secret-key-2026"):
        self.secret_key = secret_key

    def verify_token(
        self, token: Optional[ApprovalToken], referral_id: str, action: str, run_id: str
    ) -> bool:
        """
        Cryptographically validates an ApprovalToken.
        Returns True if token is valid and matches referral, action, and run ID.
        """
        if token is None:
            logger.error("Token verification failed: No approval token provided.")
            return False

        if token.referral_id != referral_id:
            logger.error(
                f"Token verification failed: referral_id mismatch. Expected '{referral_id}', got '{token.referral_id}'."
            )
            return False

        if token.action.strip().lower() != action.strip().lower():
            logger.error(
                f"Token verification failed: action mismatch. Expected '{action}', got '{token.action}'."
            )
            return False

        if run_id and token.run_id != run_id:
            logger.error(
                f"Token verification failed: run_id mismatch. Expected '{run_id}', got '{token.run_id}'."
            )
            return False

        # Re-compute expected signature
        payload = f"{token.token_id}:{token.referral_id}:{token.action}:{token.run_id}:{token.approved_at}"
        expected_sig = hmac.new(
            self.secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, token.signature):
            logger.error("Token verification failed: Cryptographic signature mismatch / token forged.")
            return False

        return True

    def execute(
        self,
        referral_id: str,
        action: str,
        policy_decision: PolicyDecisionResult,
        approval_token: Optional[ApprovalToken] = None,
        run_id: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Executes a requested side-effect if authorized by policy or human approval token.
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Case 1: Action explicitly DENIED by policy
        if policy_decision.decision == PolicyDecisionEnum.DENIED:
            raise GuardrailSecurityError(
                f"EXECUTION DENIED: Action '{action}' on referral '{referral_id}' is explicitly forbidden "
                f"under Policy Section {policy_decision.policy_section}. Escalation required."
            )

        # Case 2: Action requires Supervisor Approval
        if policy_decision.decision == PolicyDecisionEnum.APPROVAL_REQUIRED:
            if not self.verify_token(approval_token, referral_id, action, run_id):
                raise GuardrailSecurityError(
                    f"SECURITY BOUNDARY VIOLATION: Action '{action}' on referral '{referral_id}' requires "
                    f"supervisor approval under Policy Section {policy_decision.policy_section}. "
                    "No valid, matching ApprovalToken was provided. Execution HARD BLOCKED."
                )

        # Case 3: Action ALLOWED or valid token verified
        logger.info(
            f"EXECUTING ACTION: '{action}' on referral '{referral_id}' [Policy: {policy_decision.policy_section}]"
        )

        return ExecutionResult(
            referral_id=referral_id,
            action=action,
            executed=True,
            execution_timestamp=timestamp,
            details={
                "policy_section": policy_decision.policy_section,
                "policy_rule": policy_decision.policy_rule,
                "mode": "SIMULATED_MOCK_EXECUTION",
                "context": context or {},
            },
            approval_token_used=approval_token.token_id if approval_token else None,
        )
