# 06 — LangGraph Workflow (`app/graph.py`)

This document provides a line-by-line explanation of the **LangGraph StateGraph** workflow in `app/graph.py`.

---

## Source File Overview: `app/graph.py`

### `WorkflowState` — Lines 24–51
```python
24: class WorkflowState(TypedDict, total=False):
25:     run_id: str
26:     queue_file: str
27:     history_api_url: str
28:     auto_approve: bool
29:     secret_key: str
30:     
31:     referrals: List[Dict[str, Any]]
32:     current_index: int
33:     total_count: int
...
```
* **Explanation**: Defines the TypedDict state object that flows through graph nodes.

---

## 1. Graph Node Handlers Breakdown

### `load_queue_node` — Lines 81–100
* **Input State**: `queue_file` path.
* **Operation**: Opens JSON file, reads array of 12 referrals, initializes summary counters.
* **Output State**: `referrals`, `current_index=0`, `total_count=12`, `completed_referrals=[]`, `is_finished=False`.

### `select_referral_node` — Lines 103–124
* **Input State**: `current_index`, `referrals`.
* **Operation**: Checks if `current_index >= total_count`. If finished, returns `is_finished=True`. Otherwise extracts referral at index.
* **State Reset**: Clears transient item state (`approval_token`, `policy_decision`, `execution_result`, `escalation_file`).

### `fetch_history_node` — Lines 127–140
* **Input State**: `current_referral`, `history_api_url`.
* **Operation**: Calls `get_resident_history(ref.resident_ref)`.
* **Error Boundary**: If `HistoryServiceError` is caught, records error in `errors` and `failed_referrals` without crashing.

### `generate_triage_node` — Lines 143–150
* **Input State**: `current_referral`, `resident_history`.
* **Operation**: Calls `analyze_and_triage(...)` in `app/agent.py`.
* **Output State**: `triage_note`.

### `check_policy_node` — Lines 153–164
* **Input State**: `current_referral.requested_action`.
* **Operation**: Calls `PolicyEngine().evaluate(...)` in `app/policy.py`.
* **Output State**: `policy_decision`. Updates `triage_note["policy_status"]`.

### `human_approval_gate_node` — Lines 167–205
* **Input State**: `current_referral`, `triage_note`, `policy_decision`, `auto_approve`.
* **Operation**: Displays case details, prints `*** NO ACTION HAS BEEN EXECUTED. ***`, prompts `[y/N]`.
* **Output State**: On `y`, generates signed `approval_token` and `approval_granted=True`. On `n`, `approval_granted=False`.

### `execute_action_node` — Lines 207–238
* **Input State**: `current_referral`, `policy_decision`, `approval_token`.
* **Operation**: **Hard Guardrail**. If decision is `APPROVAL_REQUIRED`, verifies HMAC token. Raises `PermissionError` if token is invalid.
* **Output State**: `execution_result`, appends to `completed_referrals`.

### `escalate_node` — Lines 241–276
* **Input State**: `current_referral`, `policy_decision`, `triage_note`.
* **Operation**: Writes escalation report to `artifacts/escalations/<referral_id>.json`.
* **Output State**: `escalation_file`, appends to `escalated_referrals`.

### `next_referral_node` — Lines 279–281
* **Operation**: Increments `current_index += 1`. Loops back to `select_referral`.

---

## 2. Graph Composition (`build_workflow_graph()`) — Lines 284–347

```python
284: def build_workflow_graph():
285:     builder = StateGraph(WorkflowState)
286: 
287:     builder.add_node("load_queue", load_queue_node)
288:     builder.add_node("select_referral", select_referral_node)
...
```

### Conditional Routing Edges — Lines 300–345

1. **Queue Exhaustion Routing** (`L300–L305`):
   ```python
   def route_exhaustion(state: WorkflowState) -> str:
       if state.get("is_finished"):
           return END
       return "fetch_history"
   ```
2. **History Retrieval Routing** (`L307–L312`):
   ```python
   def route_history(state: WorkflowState) -> str:
       if not state.get("resident_history"):
           return "next_referral"
       return "generate_triage"
   ```
3. **Policy Decision Routing** (`L316–L334`):
   ```python
   def route_policy(state: WorkflowState) -> str:
       pol = state.get("policy_decision", {})
       decision = pol.get("decision")
       if decision == PolicyDecisionEnum.ALLOWED.value:
           return "execute_action"
       elif decision == PolicyDecisionEnum.APPROVAL_REQUIRED.value:
           return "human_approval_gate"
       else:
           return "escalate"
   ```
4. **Approval Gate Routing** (`L336–L341`):
   ```python
   def route_approval(state: WorkflowState) -> str:
       if state.get("approval_granted") is True:
           return "execute_action"
       return "escalate"
   ```

---

## Related Documentation
* For execution guardrail security, see [09_EXECUTION_GUARDRAIL.md](09_EXECUTION_GUARDRAIL.md).
