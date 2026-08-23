# Critical Issues Audit (`audit/CRITICAL_ISSUES.md`)

This document identifies potential risks, recommendations, and minor improvements.

---

## 1. P0 Issues — Must Fix Before Submission
> **None.** All 5 Floor requirements and core security guardrails are fully implemented and verified.

---

## 2. P1 Issues — Strongly Recommended

### P1-01: Groq API Key Configuration
* **Problem**: If `.env` is missing or `GROQ_API_KEY` is omitted, the application seamlessly uses the analytical reasoning fallback engine (`app/agent.py`).
* **Evidence**: In `app/agent.py`, `if analysis is None:` populates triage summaries using resident history data.
* **Why it matters**: While the fallback prevents crashes and passes all tests, live hackathon demonstrations should supply a valid Groq API key in `.env` to showcase Llama 3.3 70B inference.
* **Affected File**: [.env](file:///e:/5/05-caseworkers-morning/.env)
* **Suggested Action**: Ensure `GROQ_API_KEY=gsk_...` is set in `.env` prior to live demonstration.

---

## 3. P2 Issues — Optional Improvements

### P2-01: Explicit DENIED Exception Check inside Execution Node
* **Problem**: Currently, `execute_action_node` in `app/graph.py` checks `if policy.decision == PolicyDecisionEnum.APPROVAL_REQUIRED:` to enforce HMAC token validation. Actions classified as `DENIED` are routed to `escalate_node` by the conditional edge `route_policy`.
* **Evidence**: Line 323 of `app/graph.py` routes `DENIED` directly to `escalate`.
* **Why it matters**: Adding an explicit `if policy.decision == PolicyDecisionEnum.DENIED: raise PermissionError("DENIED ACTION")` inside `execute_action_node` itself would provide defense-in-depth in the unlikely event a developer invokes `execute_action_node` directly for a denied action.
* **Affected File**: [app/graph.py](file:///e:/5/05-caseworkers-morning/app/graph.py#L214)
* **Suggested Action**: Add redundant check inside `execute_action_node` if extra defense-in-depth is desired.
