# 14 — Complete End-to-End Runtime Flow

This document traces 3 real referrals from `referral-queue.json` through the runtime state graph, demonstrating how data flows through every file.

---

## 1. Example 1: Allowed Action (`RF-2026-0413`)

### Referral Details:
* **Referral ID**: `RF-2026-0413` | **Resident**: `R-20507`
* **Summary**: *"New address notified. Resident has moved within the county."*
* **Requested Action**: `"Record change of address"`

### Step-by-Step Flow:
1. **`app/main.py`**: Launches run `20260822-215948`, calls `graph.invoke(initial_state)`.
2. **`load_queue_node` (`app/graph.py`)**: Loads `referral-queue.json`.
3. **`select_referral_node` (`app/graph.py`)**: Picks `RF-2026-0413` at index 1.
4. **`fetch_history_node` (`app/graph.py`)**: Issues HTTP GET to `http://127.0.0.1:8083/residents/R-20507`.
   * **`app/history.py`**: Parses response into `ResidentHistory(status="Active", award_monthly=707.90, ...)`.
5. **`generate_triage_node` (`app/graph.py`)**:
   * **`app/agent.py`**: Sends untrusted prompt to Groq API. Returns `LLMAnalysis` and `TriageNote(requested_action="Record change of address")`.
6. **`check_policy_node` (`app/graph.py`)**:
   * **`app/policy.py`**: Matches `"Record change of address"` in `config/policy.json`. Returns `PolicyDecision(decision=PolicyDecisionEnum.ALLOWED, policy_section="2.1 / 2.5")`.
7. **`route_policy` edge (`app/graph.py`)**: Decision is `ALLOWED` $\rightarrow$ routes to `execute_action_node`.
8. **`execute_action_node` (`app/graph.py`)**: No approval token required. Simulates address update, appends `RF-2026-0413` to `completed_referrals`.
9. **`next_referral_node` (`app/graph.py`)**: Increments index to 2.

---

## 2. Example 2: Restricted Action (`RF-2026-0423`)

### Referral Details:
* **Referral ID**: `RF-2026-0423` | **Resident**: `R-20577`
* **Summary**: *"Resident asks to change the account into which payment is made."*
* **Requested Action**: `"Update payment details"`

### Step-by-Step Flow:
1. **`select_referral_node`**: Selects `RF-2026-0423`.
2. **`fetch_history_node`**: Retrieves history for `R-20577`.
3. **`generate_triage_node`**: Groq drafts triage note.
4. **`check_policy_node`**: `PolicyEngine` evaluates `"Update payment details"` against Policy 3.4.
   * **Result**: `PolicyDecision(decision=PolicyDecisionEnum.APPROVAL_REQUIRED, policy_section="3.4")`.
5. **`route_policy` edge**: Decision is `APPROVAL_REQUIRED` $\rightarrow$ routes to `human_approval_gate_node`.
6. **`human_approval_gate_node`**:
   * Displays context, prints `*** NO ACTION HAS BEEN EXECUTED. ***`.
   * User selects `[y]` (or `--demo` auto-approves).
   * Generates `ApprovalToken(token_id="TOK-a1b2c3d4", signature="...")`.
7. **`route_approval` edge**: `approval_granted == True` $\rightarrow$ routes to `execute_action_node`.
8. **`execute_action_node`**: Verifies HMAC token signature. Token valid $\rightarrow$ executes payment detail update. Appends to `approved_referrals` and `completed_referrals`.

---

## 3. Example 3: Forbidden & Escalated Action (`RF-2026-0415`)

### Referral Details:
* **Referral ID**: `RF-2026-0415` | **Resident**: `R-20521`
* **Summary**: *"Anonymous report alleging undeclared employment. Unit requests assistance be suspended pending investigation."*
* **Requested Action**: `"Suspend assistance pending investigation"`

### Step-by-Step Flow:
1. **`select_referral_node`**: Selects `RF-2026-0415`.
2. **`fetch_history_node`**: Retrieves history for `R-20521`.
3. **`generate_triage_node`**: Groq drafts triage note summarizing Counter-Fraud report.
4. **`check_policy_node`**: `PolicyEngine` evaluates requested action.
   * **Result**: `PolicyDecision(decision=PolicyDecisionEnum.DENIED, policy_section="3.2 / 3.7 / 4.1", reason="Section 3.2 prohibits award suspension...")`.
5. **`route_policy` edge**: Decision is `DENIED` $\rightarrow$ routes directly to `escalate_node`.
6. **`escalate_node`**:
   * Execution is **blocked**. No side-effect occurs.
   * Writes JSON report to `artifacts/escalations/RF-2026-0415.json`.
   * Appends `RF-2026-0415` to `escalated_referrals`.
7. **`next_referral_node`**: Increments index to 4. **Queue continues processing remaining referrals!**

---

## Related Documentation
* For execution trace logs, see [10_ESCALATION_AND_AUDIT.md](10_ESCALATION_AND_AUDIT.md).
