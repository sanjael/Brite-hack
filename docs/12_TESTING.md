# 12 — Test Suite Reference (`tests/`)

This document explains the test suite in `tests/` and the specific behaviors verified by each test.

---

## 1. `tests/test_policy.py` — Policy Engine Unit Tests

### Tests Covered:
1. `test_allowed_action()`:
   * **Target**: `PolicyEngine().evaluate("Record change of address")`
   * **Verifies**: Returns `PolicyDecisionEnum.ALLOWED` and policy section `"2.1 / 2.5"`.
2. `test_approval_required_action()`:
   * **Target**: `PolicyEngine().evaluate("Update payment details")`
   * **Verifies**: Returns `PolicyDecisionEnum.APPROVAL_REQUIRED` and section `"3.4"`.
3. `test_denied_action()`:
   * **Target**: `PolicyEngine().evaluate("Suspend assistance pending investigation")`
   * **Verifies**: Returns `PolicyDecisionEnum.DENIED` and section `"3.2 / 3.7 / 4.1"`.
4. `test_unknown_action_defaults_to_rule_6_1()`:
   * **Target**: `PolicyEngine().evaluate("Unknown custom action request")`
   * **Verifies**: Returns `PolicyDecisionEnum.APPROVAL_REQUIRED` and policy section `"6.1"`.

---

## 2. `tests/test_guardrail.py` — Security Boundary Unit Tests

### Tests Covered:
1. `test_protected_action_without_token_fails()`:
   * **Scenario**: Calls `execute_action_node` for `"Update payment details"` without an `approval_token`.
   * **Verifies**: Raises `PermissionError` containing `"HARD BLOCKED"`.
2. `test_protected_action_with_valid_token_executes()`:
   * **Scenario**: Generates a valid `ApprovalToken` using `generate_approval_token` and calls `execute_action_node`.
   * **Verifies**: Execution completes successfully (`executed=True`).
3. `test_token_verification_rejects_mismatches()`:
   * **Scenario**: Generates token for `RF-2026-0423` / `"Update payment details"` / `RUN-TEST`.
   * **Verifies**:
     * Mismatched referral ID (`RF-2026-9999`) $\rightarrow$ `verify_approval_token(...)` returns `False`.
     * Mismatched action (`"Review award"`) $\rightarrow$ `verify_approval_token(...)` returns `False`.
     * Mismatched run ID (`"RUN-OTHER"`) $\rightarrow$ `verify_approval_token(...)` returns `False`.

---

## 3. `tests/test_run.py` — Integration & Full Queue Tests

### Tests Covered:
1. `test_full_queue_run()`:
   * **Scenario**: Executes `build_workflow_graph()` across all 12 referrals in `referral-queue.json` with mocked history responses.
   * **Verifies**:
     * `total_count == 12`
     * `is_finished == True`
     * `RF-2026-0415` (fraud suspension) is correctly escalated (`"RF-2026-0415" in escalated_referrals`).
     * `completed + escalated == 12`.

---

## Command to Run Tests
```bash
pytest -v
```

---

## Related Documentation
* For execution guardrail code details, see [09_EXECUTION_GUARDRAIL.md](09_EXECUTION_GUARDRAIL.md).
