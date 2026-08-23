# Developer Learning & Documentation Index

Welcome to the comprehensive developer documentation for **Calder County Automated Casework Assistant** (Brite Spark 2026 Hackathon — Problem 5: The Caseworker's Morning).

This documentation layer explains the **actual implementation** currently present in this repository, line by line, module by module.

---

## 📖 Recommended Reading Order

### 1. Fundamentals & Problem Context
* [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) — Problem statement, core value proposition, and architecture summary.
* [01_SOURCE_FILES.md](01_SOURCE_FILES.md) — Analysis of supplied hackathon data files (`authority-policy.md`, `referral-queue.json`, `history_service.py`).
* [02_POLICY_AND_AUTHORITY.md](02_POLICY_AND_AUTHORITY.md) — Deep dive into Policy ACA-2026/1 rules, Section 2 permitted actions, Section 3 restricted actions, and Rule 6.1 ambiguity.

### 2. Architecture & Component Deep Dives
* [03_DATA_MODELS.md](03_DATA_MODELS.md) — Line-by-line explanation of Pydantic models in `app/models.py`.
* [04_HISTORY_SERVICE.md](04_HISTORY_SERVICE.md) — HTTP Client communication in `app/history.py` and mock API in `services/history_service.py`.
* [05_GROQ_AGENT.md](05_GROQ_AGENT.md) — Groq LLM integration, system prompt injection defense, and triage note generation in `app/agent.py`.
* [06_LANGGRAPH_WORKFLOW.md](06_LANGGRAPH_WORKFLOW.md) — LangGraph StateGraph, node state transitions, and state model in `app/graph.py`.
* [07_POLICY_ENGINE.md](07_POLICY_ENGINE.md) — Deterministic evaluation logic in `app/policy.py` and `config/policy.json`.
* [08_APPROVAL_AND_HUMAN_GATE.md](08_APPROVAL_AND_HUMAN_GATE.md) — CLI human approval gate, token issuance, and auto-approve demo mode in `app/graph.py`.
* [09_EXECUTION_GUARDRAIL.md](09_EXECUTION_GUARDRAIL.md) — Hard cryptographic HMAC-SHA256 execution boundary in `app/graph.py`.
* [10_ESCALATION_AND_AUDIT.md](10_ESCALATION_AND_AUDIT.md) — Unauthorized referral escalation generator and audit log artifacts in `artifacts/`.

### 3. Execution, Testing & System Flow
* [11_MAIN_RUNTIME_FLOW.md](11_MAIN_RUNTIME_FLOW.md) — Entrypoint CLI initialization, argument parsing, and loop invocation in `app/main.py`.
* [12_TESTING.md](12_TESTING.md) — Test suite breakdown (`test_policy.py`, `test_guardrail.py`, `test_run.py`).
* [13_FILE_BY_FILE_REFERENCE.md](13_FILE_BY_FILE_REFERENCE.md) — Master quick-reference index of every source file.
* [14_COMPLETE_END_TO_END_FLOW.md](14_COMPLETE_END_TO_END_FLOW.md) — Step-by-step trace of 3 real referrals (Allowed, Approval Required, Denied/Escalated).

### 4. Navigation & Maps
* [FILE_DEPENDENCY_MAP.md](FILE_DEPENDENCY_MAP.md) — Diagram and data dependency flow between modules.
* [FILE_INVENTORY.md](FILE_INVENTORY.md) — Inventory table of all project files and their responsibilities.
