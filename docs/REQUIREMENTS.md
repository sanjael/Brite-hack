# Requirements Map (docs/REQUIREMENTS.md)

**Brite Spark 2026 — Problem 5: The Caseworker's Morning**  
**Policy Reference:** ACA-2026/1  

---

## 1. Mandatory Hackathon Floor Requirements

| Floor Requirement | Implementation Component | Evidence / Artifact |
|:---|:---|:---|
| **A. Three-step Agent Run** | Read referrals → Fetch resident history → Draft triage notes in `app/graph.py` | Console log trace showing explicit sequential execution steps. |
| **B. Visible Execution Trace** | `app/main.py` + `app/graph.py` writing to `artifacts/runs/RUN_<id>.json` | Structured JSON run log containing timestamp, referral ID, policy section, decision, and status. |
| **C. Hard Approval Gate** | `app/graph.py` (`human_approval_gate_node` + `execute_action_node`) | Code check enforcing valid `ApprovalToken` for `APPROVAL_REQUIRED` actions. Returns `PermissionError` without token. |
| **D. Unauthorized Refusal & Escalation** | `app/policy.py` + `app/graph.py` (`escalate_node`) writing to `artifacts/escalations/` | `RF-2026-0415` (fraud suspension) detected, blocked, escalated to `artifacts/escalations/RF-2026-0415.json`, and queue continues. |
| **E. Clean Clone Reproducibility** | `README.md` instructions + `requirements.txt` + `.env.example` | Standalone execution from `python3 services/history_service.py` & `python -m app.main`. |

---

## 2. Security & Policy Rules

| Requirement | Enforcement Mechanism |
|:---|:---|
| **Deterministic Authority Boundary** | `app/policy.py` evaluates requested action against Policy ACA-2026/1 independently of LLM reasoning. |
| **Policy Rule 6.1 Ambiguity Handling** | Any unlisted or ambiguous action string defaults to `APPROVAL_REQUIRED` / `ESCALATION`. |
| **Prompt Injection Defense** | `app/agent.py` system prompt explicitly isolates untrusted referral data from instructions. Enforcement occurs at Policy Engine + Token Executor level. |
| **Per-Referral Error Isolation** | `app/graph.py` wraps history fetching and referral evaluation in per-item exception handling so one failure never terminates the queue. |
