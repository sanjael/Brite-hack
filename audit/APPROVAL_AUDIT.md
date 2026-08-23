# Human Approval Audit (`audit/APPROVAL_AUDIT.md`)

**Audit Status:** **PASS**

---

## 1. Overview
This audit inspects `human_approval_gate_node` in `app/graph.py` and the `--demo` / `--auto-approve` flag in `app/main.py`.

---

## 2. Interactive CLI Gate Code Inspection

In [app/graph.py](file:///e:/5/05-caseworkers-morning/app/graph.py#L167-L205):

```python
167: def human_approval_gate_node(state: WorkflowState) -> Dict[str, Any]:
175:     print("\n" + "=" * 50)
176:     print(" HUMAN APPROVAL REQUIRED ")
...
185:     print(" *** NO ACTION HAS BEEN EXECUTED. ***")
186:     print("=" * 50)

188:     if auto_approve:
189:         print("[AUTO-APPROVE] Supervisor decision: APPROVED")
190:         token = generate_approval_token(ref.referral_id, ref.requested_action, run_id, secret_key)
191:         return {"approval_granted": True, "approval_token": token.model_dump()}

193:     try:
194:         ans = input("Approve? [y/N]: ").strip().lower()
195:     except EOFError:
196:         ans = "n"

198:     if ans == "y":
200:         token = generate_approval_token(ref.referral_id, ref.requested_action, run_id, secret_key)
201:         return {"approval_granted": True, "approval_token": token.model_dump()}
202:     else:
204:         return {"approval_granted": False, "approval_token": None}
```

---

## 3. Human Approval Audit Checklist

| Approval Requirement | Implemented Behavior | Audit Verdict |
|:---|:---|:---|
| **Pause before execution** | `human_approval_gate_node` executes prior to `execute_action_node`. Printed notice asserts no action executed. | **PASS** |
| **Capture decision** | Keyboard input `y` sets `approval_granted=True`; `n` or Enter sets `approval_granted=False`. | **PASS** |
| **Rejection handling** | `route_approval` edge routes `approval_granted=False` directly to `escalate_node`. Execution node is skipped. | **PASS** |
| **Scoped token generation** | Calls `generate_approval_token(...)` tied specifically to `(referral_id, action, run_id)`. | **PASS** |
| **`--demo` mode behavior** | Automatically issues valid HMAC `ApprovalToken` inside the gate node to simulate supervisor consent for non-interactive evaluation. Does **not** bypass `execute_action_node` token verification. | **PASS** |

---

## 4. Audit Conclusion
The human approval gate provides explicit non-execution notices, captures supervisor input cleanly, issues cryptographically scoped approval tokens, and correctly routes rejected actions to escalation.
