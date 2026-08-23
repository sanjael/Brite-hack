# 00 — Project Overview

## 1. Problem Statement
Every morning, caseworkers at the **Calder County Department of Household Services** process overnight benefit referrals, retrieve resident history, draft triage notes, and determine appropriate case actions.

The goal of this hackathon submission is to build an automated assistant that performs this morning sequence reliably, securely, and in full compliance with **Authority Policy ACA-2026/1**.

---

## 2. Core Value Proposition: Deterministic Security Boundary
> *The reasoning model (Groq Llama 3.3 70B) can analyze referrals and propose next steps, but it is **structurally incapable** of executing protected side-effects without deterministic policy authorization and explicit human supervisor approval.*

### Key Security Distinction:
* **Probabilistic LLM Reasoning**: Drafts triage summaries, identifies relevant historical case events, and proposes next steps.
* **Deterministic Authority Boundary**: Evaluates proposed actions against policy rules in `config/policy.json` and demands cryptographically signed HMAC-SHA256 `ApprovalToken`s for restricted actions before execution.

---

## 3. High-Level Architecture Diagram

```text
Referral Queue (referral-queue.json)
      ↓
LangGraph Workflow Engine (app/graph.py)
      ↓
Fetch Resident History (HTTP GET http://127.0.0.1:8083/residents/<ref>)
      ↓
Groq LLM Reasoning & Triage Generator (app/agent.py)
      ↓
Deterministic Policy Engine (app/policy.py)
      ↓
 ┌────────────┬───────────────┐
 ↓            ↓               ↓
[ALLOWED] [APPROVAL NEEDED] [DENY/ESCALATE]
 ↓            ↓               ↓
Execute    Human CLI Gate    Escalate Artifact
 (app/graph.py) (app/graph.py) (artifacts/escalations/)
                ↓
             Execute
```

---

## 4. Key Hackathon Floor Requirements & Enforcement

1. **Three-step Agent Run**: `load_queue` $\rightarrow$ `fetch_history` $\rightarrow$ `generate_triage` $\rightarrow$ `check_policy`.
2. **Visible Execution Trace**: Structured JSON log artifacts saved to `artifacts/runs/RUN_<timestamp>.json`.
3. **Hard Approval Gate**: `human_approval_gate_node` displays full context, asserts `NO ACTION HAS BEEN EXECUTED`, and issues scoped HMAC token upon `[y]` approval.
4. **Unauthorized Referral Escalation**: `RF-2026-0415` (fraud suspension) is recognized as forbidden under Policy 3.2 & 3.7, refused, escalated to `artifacts/escalations/RF-2026-0415.json`, and remaining referrals continue without interruption.
5. **Clean Clone Reproducibility**: Runnable via standard Python 3: `python services/history_service.py --port 8083` and `python -m app.main --demo`.

---

## 5. Related Documentation
* For details on supplied hackathon files, see [01_SOURCE_FILES.md](01_SOURCE_FILES.md).
* For policy governance rules, see [02_POLICY_AND_AUTHORITY.md](02_POLICY_AND_AUTHORITY.md).
