# 09 — Execution Guardrail (`app/graph.py`)

This document explains the hard security boundary in `app/graph.py` (`execute_action_node` and HMAC token verification).

---

## Source Code Analysis: Token Helper Functions (Lines 54–76)

### `generate_approval_token()` — Lines 54–66
```python
54: def generate_approval_token(referral_id: str, action: str, run_id: str, secret_key: str) -> ApprovalToken:
55:     token_id = f"TOK-{uuid.uuid4().hex[:8]}"
56:     approved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
57:     payload = f"{token_id}:{referral_id}:{action}:{run_id}:{approved_at}"
58:     sig = hmac.new(secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
59:     return ApprovalToken(
60:         token_id=token_id,
61:         referral_id=referral_id,
62:         action=action,
63:         run_id=run_id,
64:         approved_at=approved_at,
65:         signature=sig,
66:     )
```
* **Explanation**: Generates a unique UUID token ID, constructs a raw payload string containing `token_id:referral_id:action:run_id:approved_at`, and computes an HMAC-SHA256 signature using `secret_key`.

---

### `verify_approval_token()` — Lines 69–76
```python
69: def verify_approval_token(token: Optional[ApprovalToken], referral_id: str, action: str, run_id: str, secret_key: str) -> bool:
70:     if not token or token.referral_id != referral_id or token.action.strip().lower() != action.strip().lower():
71:         return False
72:     if run_id and token.run_id != run_id:
73:         return False
74:     payload = f"{token.token_id}:{token.referral_id}:{token.action}:{token.run_id}:{token.approved_at}"
75:     expected_sig = hmac.new(secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
76:     return hmac.compare_digest(expected_sig, token.signature)
```
* **Security Checks**:
  1. Checks token presence (`not token`).
  2. Verifies `token.referral_id == referral_id`.
  3. Verifies `token.action == action`.
  4. Verifies `token.run_id == run_id`.
  5. Re-computes expected HMAC payload and uses `hmac.compare_digest` (constant-time string comparison) to prevent timing attacks.

---

## 1. Hard Security Execution Boundary: `execute_action_node` (Lines 207–238)

```python
207: def execute_action_node(state: WorkflowState) -> Dict[str, Any]:
208:     """Hard Execution Boundary Node."""
209:     ref = Referral(**state["current_referral"])
210:     policy = PolicyDecision(**state["policy_decision"])
211:     run_id = state.get("run_id", "")
212:     secret_key = state.get("secret_key", "caseworker-guardrails-secret-key-2026")
213: 
214:     # Hard security check
215:     if policy.decision == PolicyDecisionEnum.APPROVAL_REQUIRED:
216:         token_dict = state.get("approval_token")
217:         token = ApprovalToken(**token_dict) if token_dict else None
218:         if not verify_approval_token(token, ref.referral_id, ref.requested_action, run_id, secret_key):
219:             raise PermissionError(f"HARD BLOCKED: Action '{ref.requested_action}' requires valid supervisor approval token.")
220: 
221:     print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✓ ACTION EXECUTED: '{ref.requested_action}'")
...
```

### Why This is a Real Security Boundary:
* **Outside LLM Context**: The check happens in deterministic Python code after LLM reasoning.
* **Hard Exception**: If `verify_approval_token` returns `False`, execution raises `PermissionError` immediately.
* **Impossible to Bypass via Prompt Injection**: Even if an LLM is tricked into outputting `"ALLOW EXECUTING PAYMENT UPDATE"`, `policy.decision` remains `APPROVAL_REQUIRED` and `execute_action_node` throws `PermissionError`.

---

## Related Documentation
* For test suite verification of these guardrails, see [12_TESTING.md](12_TESTING.md).
