# Step-by-Step Commit Guide (`docs/to_commit/01_STEP_BY_STEP_COMMITS.md`)

This document explains the development logic behind each commit step.

---

## Step 1: Initial Repository & Provided Inputs Setup
* **Files**: `.gitignore`, `requirements.txt`, `.env.example`, `authority-policy.md`, `referral-queue.json`, `services/history_service.py`, `services/_history_data.json`
* **Commit Message**: `feat: initialize project structure, policy ACA-2026/1, and mock history service`
* **Rationale**: Establishes the foundational project environment, dependencies (`langgraph`, `groq`, `pydantic`, `streamlit`), the legal authority policy document, overnight referral data, and mock HTTP API server.

---

## Step 2: Data Models Definition
* **Files**: `app/__init__.py`, `app/models.py`
* **Commit Message**: `feat(models): define Pydantic data schemas for referrals, history, policy decisions, and HMAC tokens`
* **Rationale**: Defines strongly-typed Pydantic schemas (`Referral`, `ResidentHistory`, `TriageNote`, `PolicyDecision`, `ApprovalToken`, `ExecutionResult`) to enforce clean data boundaries across graph nodes.

---

## Step 3: Resident History API Client
* **Files**: `app/history.py`
* **Commit Message**: `feat(history): implement HTTP client for resident history API with 404 & error isolation`
* **Rationale**: Implements `get_resident_history()` using Python standard library `urllib.request`. Converts socket and HTTP 404 errors into domain exceptions (`HistoryServiceError`, `ResidentNotFoundError`).

---

## Step 4: Deterministic Policy Engine
* **Files**: `config/policy.json`, `app/policy.py`
* **Commit Message**: `feat(policy): implement data-driven PolicyEngine and ACA-2026/1 Section 6.1 ambiguity rules`
* **Rationale**: Builds `PolicyEngine` to evaluate requested action strings against rule patterns loaded from `config/policy.json`. Enforces Rule 6.1 ambiguity fallback (unlisted actions default to `APPROVAL_REQUIRED`).

---

## Step 5: Groq Reasoning Agent & Injection Defense
* **Files**: `app/agent.py`
* **Commit Message**: `feat(agent): implement Groq Llama 3.3 70B reasoning agent with prompt injection defense & analytical fallback`
* **Rationale**: Integrates Groq LLM API with prompt injection defense tags (`=== UNTRUSTED CASE DATA START ===`). Adds offline analytical fallback engine when API key is missing or network times out.

---

## Step 6: LangGraph StateGraph & Execution Guardrail
* **Files**: `app/graph.py`
* **Commit Message**: `feat(graph): implement LangGraph StateGraph, human approval gate, and HMAC-SHA256 execution boundary`
* **Rationale**: Assembles `StateGraph(WorkflowState)` with nodes and conditional routing edges. Implements `generate_approval_token()` and `verify_approval_token()` to enforce HMAC-SHA256 token verification in `execute_action_node`.

---

## Step 7: Main CLI Entrypoint
* **Files**: `app/main.py`
* **Commit Message**: `feat(cli): implement interactive CLI entrypoint with stdout execution tracing`
* **Rationale**: Creates the main CLI script `python -m app.main` supporting interactive terminal mode and `--demo` auto-approve mode. Logs run summaries to `artifacts/runs/`.

---

## Step 8: Unit & Guardrail Test Suite
* **Files**: `tests/test_policy.py`, `tests/test_guardrail.py`, `tests/test_run.py`, `tests/test_history_client.py`, `tests/test_workflow.py`, `tests/test_integration.py`
* **Commit Message**: `test: add unit & integration test suite for policy engine, guardrail security, and queue execution`
* **Rationale**: Implements pytest tests to verify policy decision rules, HMAC token verification failures (`PermissionError`), prompt injection defense, and full 12-referral queue execution.

---

## Step 9: Streamlit Web Dashboard
* **Files**: `frontend/app.py`
* **Commit Message**: `feat(frontend): implement Streamlit web dashboard for visual queue triage and human gate`
* **Rationale**: Creates an interactive Streamlit web dashboard (`streamlit run frontend/app.py`) for visual referral triage, human approval gate buttons, escalation reports, and audit analytics.

---

## Step 10: Documentation & Audit Reports
* **Files**: `README.md`, `DECISIONS.md`, `AI-USAGE.md`, `docs/`, `audit/`
* **Commit Message**: `docs: add comprehensive developer learning guides, audit reports, DECISIONS.md, and AI disclosure`
* **Rationale**: Adds master developer documentation guides, formal audit checklists, architectural decision explanations, and AI disclosure reports required by hackathon submission rules.
