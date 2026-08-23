# 13 — File-by-File Master Reference

Quick-reference summary for every important source file in the repository.

---

## 1. Source Files Index

### `app/models.py`
* **Purpose**: Pydantic data schemas.
* **Main Classes**: `Referral`, `ResidentHistory`, `TriageNote`, `PolicyDecision`, `ApprovalToken`, `ExecutionResult`, `AuditEvent`.
* **Used By**: Entire codebase (`app/graph.py`, `app/policy.py`, `app/agent.py`, `app/history.py`).
* **Documentation**: [03_DATA_MODELS.md](03_DATA_MODELS.md)

### `app/policy.py`
* **Purpose**: Deterministic Policy Engine for ACA-2026/1.
* **Main Classes**: `PolicyEngine`.
* **Inputs**: Action string.
* **Outputs**: `PolicyDecision` (`ALLOWED`, `APPROVAL_REQUIRED`, `DENIED`).
* **Used By**: `check_policy_node` in `app/graph.py`.
* **Documentation**: [07_POLICY_ENGINE.md](07_POLICY_ENGINE.md)

### `app/history.py`
* **Purpose**: HTTP client for Resident History API (`http://127.0.0.1:8083`).
* **Main Functions**: `get_resident_history(resident_ref)`.
* **Inputs**: Resident reference string.
* **Outputs**: `ResidentHistory` model.
* **Used By**: `fetch_history_node` in `app/graph.py`.
* **Documentation**: [04_HISTORY_SERVICE.md](04_HISTORY_SERVICE.md)

### `app/agent.py`
* **Purpose**: Groq LLM reasoning & triage note drafting.
* **Main Functions**: `analyze_and_triage(referral, history)`.
* **Inputs**: `Referral`, `ResidentHistory`.
* **Outputs**: `(LLMAnalysis, TriageNote)`.
* **Used By**: `generate_triage_node` in `app/graph.py`.
* **Documentation**: [05_GROQ_AGENT.md](05_GROQ_AGENT.md)

### `app/graph.py`
* **Purpose**: LangGraph workflow graph, HMAC security guardrail, human CLI gate, and escalation nodes.
* **Main Functions**: `build_workflow_graph()`, `generate_approval_token()`, `verify_approval_token()`, node functions.
* **Inputs**: `WorkflowState`.
* **Outputs**: Final `WorkflowState` dictionary.
* **Used By**: `app/main.py`.
* **Documentation**: [06_LANGGRAPH_WORKFLOW.md](06_LANGGRAPH_WORKFLOW.md), [08_APPROVAL_AND_HUMAN_GATE.md](08_APPROVAL_AND_HUMAN_GATE.md), [09_EXECUTION_GUARDRAIL.md](09_EXECUTION_GUARDRAIL.md)

### `app/main.py`
* **Purpose**: CLI application entrypoint.
* **Main Functions**: `main()`.
* **Inputs**: Command line arguments (`--queue-file`, `--history-url`, `--demo`).
* **Outputs**: Console logs & `artifacts/runs/RUN_<id>.json`.
* **Documentation**: [11_MAIN_RUNTIME_FLOW.md](11_MAIN_RUNTIME_FLOW.md)

### `services/history_service.py`
* **Purpose**: Mock Resident History API HTTP server.
* **Inputs**: Port `--port 8083`.
* **Outputs**: JSON HTTP responses.
* **Documentation**: [04_HISTORY_SERVICE.md](04_HISTORY_SERVICE.md)

---

## 2. Configuration & Test Files Index

* `config/policy.json`: Machine-readable policy mapping $\rightarrow$ [07_POLICY_ENGINE.md](07_POLICY_ENGINE.md)
* `tests/test_policy.py`: Policy engine unit tests $\rightarrow$ [12_TESTING.md](12_TESTING.md)
* `tests/test_guardrail.py`: Hard execution boundary unit tests $\rightarrow$ [12_TESTING.md](12_TESTING.md)
* `tests/test_run.py`: Integration queue tests $\rightarrow$ [12_TESTING.md](12_TESTING.md)
