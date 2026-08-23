# Architecture Specification (docs/ARCHITECTURE.md)

**Brite Spark 2026 — Problem 5: The Caseworker's Morning**  
**Policy Reference:** ACA-2026/1  

---

## 1. High-Level Data Flow

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

## 2. Responsibility Matrix

| Component | Responsible File | Allowed Actions | Strictly Prohibited Actions |
|:---|:---|:---|:---|
| **LLM Reasoning** | `app/agent.py` | Summarize situation, identify relevant history, propose action, draft triage note. | Authorizing actions, granting permissions, calling execution side-effects directly. |
| **Policy Engine** | `app/policy.py` | Classify requested action against ACA-2026/1 rules (`ALLOWED`, `APPROVAL_REQUIRED`, `DENIED`). | Executing side-effects, generating approval tokens. |
| **Human Approval Gate** | `app/graph.py` | Display case context, assert `NO ACTION HAS BEEN EXECUTED`, issue scoped HMAC `ApprovalToken` on `[y]`. | Executing actions prior to human consent. |
| **Controlled Executor** | `app/graph.py` | Execute side-effect if action is `ALLOWED` or valid HMAC `ApprovalToken` matches `(referral_id, action, run_id)`. | Executing protected actions without valid token. |
| **Escalation Manager** | `app/graph.py` | Write structured JSON escalation report to `artifacts/escalations/`. | Suppressing unauthorized actions or stopping queue loop. |

---

## 3. Defense-in-Depth Security Model

1. **Layer 1: Prompt Isolation**: LLM prompt explicitly delineates instructions from untrusted referral summary text.
2. **Layer 2: Deterministic Policy Engine**: LLM recommendations pass into `PolicyEngine.evaluate()`. The LLM's opinion has zero bearing on policy classification.
3. **Layer 3: Cryptographic Approval Tokens**: Protected actions require an HMAC-SHA256 token generated exclusively by the `HumanApprovalGate`.
4. **Layer 4: Hard Execution Guardrail**: `execute_action_node` checks policy and token signatures. If missing or invalid, it throws `PermissionError`.
