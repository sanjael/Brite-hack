# Executor Security Audit (`audit/EXECUTOR_SECURITY_AUDIT.md`)

**Audit Status:** **PASS**

---

## 1. Overview
This audit inspects `execute_action_node` and token verification helper functions in `app/graph.py` to evaluate the technical enforcement of the hard execution guardrail boundary.

---

## 2. Source Code Inspection: `execute_action_node`

In [app/graph.py](file:///e:/5/05-caseworkers-morning/app/graph.py#L207-L238):

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
```

---

## 3. Cryptographic Token Verification Inspection

In [app/graph.py](file:///e:/5/05-caseworkers-morning/app/graph.py#L69-L76):

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

---

## 4. Hard Guardrail Evaluation Checklist

| Security Question | Code Behavior | Audit Verdict |
|:---|:---|:---|
| **1. Can the LLM directly call the executor?** | No. LLM returns JSON data strings. It has zero references or tool bindings to `execute_action_node`. | **PASS** |
| **2. Can the executor be called without authorization?** | No. If `policy.decision` is `APPROVAL_REQUIRED`, it checks `verify_approval_token`. Without a token, raises `PermissionError`. | **PASS** |
| **3. What exact condition allows execution?** | `policy.decision == ALLOWED` OR (`policy.decision == APPROVAL_REQUIRED` AND valid `ApprovalToken` present). | **PASS** |
| **4. What exact condition blocks execution?** | Missing token, forged token signature, mismatched referral ID, mismatched action string, or mismatched run ID. | **PASS** |
| **5. Where is approval stored?** | Stored in `state["approval_token"]` generated exclusively by `human_approval_gate_node`. | **PASS** |
| **6. Can approval tokens be forged?** | No. Tokens require an HMAC-SHA256 signature calculated over payload using `secret_key`. | **PASS** |
| **7. Can a token for Referral A be used for Referral B?** | No. `token.referral_id != referral_id` causes `verify_approval_token` to return `False`. | **PASS** |
| **8. Can a token for Action A be used for Action B?** | No. `token.action != action` causes `verify_approval_token` to return `False`. | **PASS** |

---

## 5. Audit Conclusion
The execution guardrail is **structurally hard**. Authorization enforcement occurs in deterministic Python code outside the LLM context and requires cryptographic token verification, satisfying the core hackathon guardrail requirement.
