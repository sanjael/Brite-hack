# File Inventory & Responsibility Matrix

This table inventories every source, configuration, documentation, and test file in the repository.

---

## 1. Application Source Files (`app/`)

| File Path | Type | Primary Purpose | Called / Used By | Core Documentation |
|:---|:---|:---|:---|:---|
| `app/__init__.py` | Python | Package initialization file. | System | [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) |
| `app/models.py` | Python | Pydantic schemas (`Referral`, `ResidentHistory`, `TriageNote`, `PolicyDecision`, `ApprovalToken`, `ExecutionResult`, `AuditEvent`). | Entire application | [03_DATA_MODELS.md](03_DATA_MODELS.md) |
| `app/policy.py` | Python | Deterministic Policy Engine evaluating Policy ACA-2026/1 rules. | `app/graph.py` | [07_POLICY_ENGINE.md](07_POLICY_ENGINE.md) |
| `app/history.py` | Python | HTTP client issuing GET queries to `http://127.0.0.1:8083`. | `app/graph.py` | [04_HISTORY_SERVICE.md](04_HISTORY_SERVICE.md) |
| `app/agent.py` | Python | Groq LLM reasoning & prompt injection defense. | `app/graph.py` | [05_GROQ_AGENT.md](05_GROQ_AGENT.md) |
| `app/graph.py` | Python | LangGraph StateGraph, security node, human CLI gate, HMAC token guardrail. | `app/main.py` | [06_LANGGRAPH_WORKFLOW.md](06_LANGGRAPH_WORKFLOW.md) |
| `app/main.py` | Python | Application CLI entrypoint script. | User / CLI | [11_MAIN_RUNTIME_FLOW.md](11_MAIN_RUNTIME_FLOW.md) |

---

## 2. Hackathon Data & Services (`services/`, root)

| File Path | Type | Primary Purpose | Called / Used By | Core Documentation |
|:---|:---|:---|:---|:---|
| `referral-queue.json` | JSON | 12 overnight referrals received 17 March 2026. | `app/graph.py` | [01_SOURCE_FILES.md](01_SOURCE_FILES.md) |
| `authority-policy.md` | Markdown | Legal policy ACA-2026/1 text (Source of truth). | Policy Reference | [02_POLICY_AND_AUTHORITY.md](02_POLICY_AND_AUTHORITY.md) |
| `services/history_service.py` | Python | HTTP REST API server on port 8083. | `app/history.py` | [04_HISTORY_SERVICE.md](04_HISTORY_SERVICE.md) |
| `services/_history_data.json` | JSON | Resident database for `R-20500` through `R-20577`. | `history_service.py` | [04_HISTORY_SERVICE.md](04_HISTORY_SERVICE.md) |
| `config/policy.json` | JSON | Machine-readable policy mapping derived from ACA-2026/1. | `app/policy.py` | [07_POLICY_ENGINE.md](07_POLICY_ENGINE.md) |

---

## 3. Test Suite (`tests/`)

| File Path | Type | Primary Purpose | Targets | Core Documentation |
|:---|:---|:---|:---|:---|
| `tests/__init__.py` | Python | Test package marker. | Pytest | [12_TESTING.md](12_TESTING.md) |
| `tests/test_policy.py` | Python | Unit tests for `PolicyEngine`. | `app/policy.py` | [12_TESTING.md](12_TESTING.md) |
| `tests/test_guardrail.py` | Python | Unit tests for HMAC token execution boundary. | `app/graph.py` | [12_TESTING.md](12_TESTING.md) |
| `tests/test_run.py` | Python | End-to-end queue processing integration tests. | `app/graph.py` | [12_TESTING.md](12_TESTING.md) |

---

## 4. Root Configuration & Project Documentation

| File Path | Type | Primary Purpose |
|:---|:---|:---|
| `README.md` | Markdown | High-level quickstart & project guide. |
| `DECISIONS.md` | Markdown | 12 architectural decisions & guardrail explanations. |
| `AI-USAGE.md` | Markdown | AI tool disclosure report. |
| `requirements.txt` | Text | Python dependencies (`langgraph`, `langchain-groq`, `pydantic`, `pytest`). |
| `.env.example` | Config | Template for environment variables. |
| `.env` | Config | Active environment variables file. |
| `.gitignore` | Config | Git ignore rules. |
