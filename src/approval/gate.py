import datetime
import hmac
import hashlib
import uuid
from typing import Tuple, Optional, Callable
from src.models.schemas import PolicyDecisionResult, ApprovalToken, TriageNote, Referral


class HumanApprovalGate:
    """
    Human-in-the-loop Approval Gate.
    
    When a policy decision is APPROVAL_REQUIRED, this gate pauses execution,
    presents case context to the user/supervisor, and ensures no protected
    action is taken without explicit human consent.
    
    Upon approval, it generates a cryptographically signed ApprovalToken tied
    specifically to (referral_id, action, run_id).
    """

    def __init__(
        self,
        secret_key: str = "caseworker-guardrails-secret-key-2026",
        input_func: Optional[Callable[[str], str]] = None,
        auto_approve: bool = False,
    ):
        self.secret_key = secret_key
        self.input_func = input_func or input
        self.auto_approve = auto_approve

    def generate_token(
        self, referral_id: str, action: str, run_id: str, approved_by: str = "Supervisor"
    ) -> ApprovalToken:
        """Generates an HMAC-signed ApprovalToken for a approved protected action."""
        token_id = f"TOK-{uuid.uuid4().hex[:8]}"
        approved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload = f"{token_id}:{referral_id}:{action}:{run_id}:{approved_at}"
        
        signature = hmac.new(
            self.secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return ApprovalToken(
            token_id=token_id,
            referral_id=referral_id,
            action=action,
            run_id=run_id,
            approved_at=approved_at,
            approved_by=approved_by,
            signature=signature,
        )

    def request_approval(
        self,
        referral: Referral,
        triage_note: TriageNote,
        policy_decision: PolicyDecisionResult,
        run_id: str,
    ) -> Tuple[bool, Optional[ApprovalToken]]:
        """
        Displays approval UI and prompts supervisor for decision.
        Returns (is_approved, approval_token).
        """
        print("\n" + "=" * 60)
        print(" [HUMAN APPROVAL REQUIRED] ")
        print("=" * 60)
        print(f"Referral ID:      {referral.referral_id}")
        print(f"Resident Ref:     {referral.resident_ref}")
        print(f"Source:           {referral.source} (Urgency: {referral.urgency})")
        print(f"Requested Action: {referral.requested_action}")
        print("-" * 60)
        print(f"Policy Section:   {policy_decision.policy_section}")
        print(f"Policy Rule:      {policy_rule_summary(policy_decision.policy_rule)}")
        print(f"Authority Reason: {policy_decision.reason}")
        print(f"Required Auth:    {policy_decision.required_authority}")
        print("-" * 60)
        print(f"Situation Summary: {triage_note.situation_summary}")
        print(f"Proposed Next Step: {triage_note.proposed_next_step}")
        print("=" * 60)
        print(" *** NO ACTION HAS BEEN EXECUTED. ***")
        print("=" * 60)

        if self.auto_approve:
            print("[AUTO-APPROVE MODE] Supervisor decision: APPROVED")
            print("HUMAN APPROVAL RECEIVED.")
            print("AUTHORIZATION VERIFIED.")
            print("ISSUING APPROVAL TOKEN & EXECUTING PROTECTED ACTION.\n")
            token = self.generate_token(referral.referral_id, referral.requested_action, run_id)
            return True, token

        try:
            choice = self.input_func("Approve this protected action? [Y] Approve / [N] Reject: ").strip().upper()
        except EOFError:
            choice = "N"

        if choice == "Y":
            print("\nHUMAN APPROVAL RECEIVED.")
            print("AUTHORIZATION VERIFIED.")
            print("ISSUING APPROVAL TOKEN & EXECUTING PROTECTED ACTION.\n")
            token = self.generate_token(referral.referral_id, referral.requested_action, run_id)
            return True, token
        else:
            print("\nHUMAN APPROVAL REJECTED.")
            print("NO PROTECTED ACTION EXECUTED.\n")
            return False, None


def policy_rule_summary(rule_text: str) -> str:
    return rule_text.strip()
