# LangGraph Implementation Audit (`audit/LANGGRAPH_AUDIT.md`)

**Audit Status:** **PASS**

---

## 1. Overview
This audit inspects `app/graph.py` to verify that LangGraph (`langgraph.graph.StateGraph`) is genuinely used to orchestrate the workflow, manage state transitions, handle conditional routing, enforce security interrupts, and cycle across the referral queue.

---

## 2. State Model Audit (`WorkflowState`)
In [app/graph.py](file:///e:/5/05-caseworkers-morning/app/graph.py#L24-L51), `WorkflowState` is defined as a typed dictionary (`TypedDict, total=False`):

```python
class WorkflowState(TypedDict, total=False):
    run_id: str
    queue_file: str
    history_api_url: str
    auto_approve: bool
    secret_key: str
    
    referrals: List[Dict[str, Any]]
    current_index: int
    total_count: int
    
    current_referral: Optional[Dict[str, Any]]
    resident_history: Optional[Dict[str, Any]]
    triage_note: Optional[Dict[str, Any]]
    policy_decision: Optional[Dict[str, Any]]
    
    approval_granted: Optional[bool]
    approval_token: Optional[Dict[str, Any]]
    execution_result: Optional[Dict[str, Any]]
    escalation_file: Optional[str]
    
    completed_referrals: List[str]
    approved_referrals: List[str]
    rejected_referrals: List[str]
    escalated_referrals: List[str]
    failed_referrals: List[str]
    errors: List[Dict[str, Any]]
    is_finished: bool
```

* **Audit Finding**: State contains all required fields to isolate transient referral items while maintaining cumulative summary counters and run metadata.

---

## 3. Node Inventory & Responsibilities

| Node Name | Handler Function | State Mutations | Audit Verdict |
|:---|:---|:---|:---|
| `load_queue` | `load_queue_node` | Populates `referrals`, `total_count`, resets counters. | **PASS** |
| `select_referral` | `select_referral_node` | Sets `current_referral`, resets item state. Sets `is_finished=True` when queue exhausted. | **PASS** |
| `fetch_history` | `fetch_history_node` | Sets `resident_history`. On API failure, appends to `errors` & `failed_referrals`. | **PASS** |
| `generate_triage` | `generate_triage_node` | Sets `triage_note` using `app/agent.py`. | **PASS** |
| `check_policy` | `check_policy_node` | Sets `policy_decision` using `app/policy.py`. Updates `triage_note["policy_status"]`. | **PASS** |
| `human_approval_gate` | `human_approval_gate_node` | Prompts `[y/N]`. Sets `approval_granted` and generates HMAC `approval_token`. | **PASS** |
| `execute_action` | `execute_action_node` | Verifies `approval_token`. Appends to `completed_referrals` & `approved_referrals`. | **PASS** |
| `escalate` | `escalate_node` | Writes JSON artifact to `artifacts/escalations/`. Appends to `escalated_referrals`. | **PASS** |
| `next_referral` | `next_referral_node` | Increments `current_index += 1`. | **PASS** |

---

## 4. Conditional Edge Routing Audit

### Routing Edge 1: Queue Exhaustion (`route_exhaustion`)
```python
def route_exhaustion(state: WorkflowState) -> str:
    if state.get("is_finished"):
        return END
    return "fetch_history"
```
* **Verdict**: **PASS**. Safely terminates graph execution at `END` when all referrals are processed.

### Routing Edge 2: History Error Boundary (`route_history`)
```python
def route_history(state: WorkflowState) -> str:
    if not state.get("resident_history"):
        return "next_referral"
    return "generate_triage"
```
* **Verdict**: **PASS**. If history API fails, skips triage/execution and advances to `next_referral`.

### Routing Edge 3: Policy Decision Routing (`route_policy`)
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
* **Verdict**: **PASS**. Deterministically routes `ALLOWED` actions to execution, `APPROVAL_REQUIRED` to human gate, and `DENIED` directly to escalation.

### Routing Edge 4: Approval Decision Routing (`route_approval`)
```python
def route_approval(state: WorkflowState) -> str:
    if state.get("approval_granted") is True:
        return "execute_action"
    return "escalate"
```
* **Verdict**: **PASS**. Human approval (`[y]`) routes to execution node; rejection (`[n]`) routes to escalation node.

---

## 5. Audit Conclusion
LangGraph is used cleanly, correctly, and effectively as the central orchestration workflow. Per-referral isolation, error handling, policy routing, and approval interrupts are fully implemented in code.
