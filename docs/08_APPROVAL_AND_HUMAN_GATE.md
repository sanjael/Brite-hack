# 08 — Approval and Human Gate (`app/graph.py`)

This document explains `human_approval_gate_node` in `app/graph.py`, CLI approval prompts, token generation, and the `--demo` auto-approve flag.

---

## Source Code Analysis: `human_approval_gate_node` (Lines 167–205)

```python
167: def human_approval_gate_node(state: WorkflowState) -> Dict[str, Any]:
168:     ref = Referral(**state["current_referral"])
169:     triage = TriageNote(**state["triage_note"])
170:     policy = PolicyDecision(**state["policy_decision"])
171:     auto_approve = state.get("auto_approve", False)
172:     run_id = state.get("run_id", "")
173:     secret_key = state.get("secret_key", "caseworker-guardrails-secret-key-2026")
```

---

## 1. Explicit Non-Execution Notice — Lines 175–186

```python
175:     print("\n" + "=" * 50)
176:     print(" HUMAN APPROVAL REQUIRED ")
177:     print("=" * 50)
178:     print(f"Referral:         {ref.referral_id}")
179:     print(f"Resident:         {ref.resident_ref}")
180:     print(f"Requested Action: {ref.requested_action}")
181:     print(f"Policy Section:   {policy.policy_section} ({policy.policy_rule})")
182:     print(f"Policy Reason:    {policy.reason}")
183:     print(f"Summary:          {triage.situation_summary}")
184:     print("=" * 50)
185:     print(" *** NO ACTION HAS BEEN EXECUTED. ***")
186:     print("=" * 50)
```
* **User Experience Feature**: The CLI displays case context, situation summary, and policy rule. It explicitly prints `*** NO ACTION HAS BEEN EXECUTED. ***` so the supervisor knows no side-effect has occurred prior to approval.

---

## 2. Interactive Prompt & Token Issuance — Lines 188–205

```python
188:     if auto_approve:
189:         print("[AUTO-APPROVE] Supervisor decision: APPROVED")
190:         token = generate_approval_token(ref.referral_id, ref.requested_action, run_id, secret_key)
191:         return {"approval_granted": True, "approval_token": token.model_dump()}

193:     try:
194:         ans = input("Approve? [y/N]: ").strip().lower()
195:     except EOFError:
196:         ans = "n"

198:     if ans == "y":
199:         print("HUMAN APPROVAL GRANTED. Executing protected action...\n")
200:         token = generate_approval_token(ref.referral_id, ref.requested_action, run_id, secret_key)
201:         return {"approval_granted": True, "approval_token": token.model_dump()}
202:     else:
203:         print("HUMAN APPROVAL REJECTED. Action NOT executed.\n")
204:         return {"approval_granted": False, "approval_token": None}
```

### Key Logic:
1. **Demo Mode (`--demo` / `--auto-approve`)**: Skips keyboard prompt and issues token automatically for non-interactive evaluation.
2. **User Input (`y`)**: Generates an HMAC-signed `ApprovalToken` scoped to `(referral_id, action, run_id)` and sets `approval_granted=True`.
3. **User Input (`n`)**: Returns `approval_granted=False` and `approval_token=None`. The conditional router `route_approval` directs state to `escalate_node`.

---

## Related Documentation
* For execution token validation, see [09_EXECUTION_GUARDRAIL.md](09_EXECUTION_GUARDRAIL.md).
* For escalation of rejected actions, see [10_ESCALATION_AND_AUDIT.md](10_ESCALATION_AND_AUDIT.md).
