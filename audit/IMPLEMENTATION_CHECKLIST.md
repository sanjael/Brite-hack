# Implementation Checklist

This checklist audits the actual current implementation in the repository against all floor, security, policy, and workflow requirements.

| ID | Requirement | Status | Evidence | File(s) | Risk |
|:---|:---|:---|:---|:---|:---|
| **H-01** | Three-step agent workflow | **PASS** | Referrals loaded $\rightarrow$ history fetched $\rightarrow$ Groq triage generated $\rightarrow$ policy evaluated in `app/graph.py`. | [app/graph.py](file:///e:/5/05-caseworkers-morning/app/graph.py) | Low |
| **H-02** | Visible stdout execution trace | **PASS** | Timestamps, referral IDs, resident refs, actions, policy sections, and execution status streamed live to stdout. | [app/graph.py](file:///e:/5/05-caseworkers-morning/app/graph.py) | Low |
| **H-03** | Structured audit JSON artifact | **PASS** | Run summary counters (`completed`, `approved`, `rejected`, `escalated`, `failed`, `errors`) persisted to `artifacts/runs/RUN_<id>.json`. | [app/main.py](file:///e:/5/05-caseworkers-morning/app/main.py) | Low |
| **H-04** | Hard approval gate | **PASS** | `execute_action_node` checks `verify_approval_token(...)`. Raises `PermissionError` if HMAC-SHA256 token is missing/invalid. | [app/graph.py](file:///e:/5/05-caseworkers-morning/app/graph.py#L215-L219) | Low |
| **H-05** | Unauthorized referral refusal | **PASS** | `RF-2026-0415` ("Suspend assistance pending investigation") evaluated as `DENIED` under Policy 3.2/3.7/4.1. Execution skipped. | [app/policy.py](file:///e:/5/05-caseworkers-morning/app/policy.py#L93-L97) | Low |
| **H-06** | Unauthorized referral escalation | **PASS** | `escalate_node` writes structured escalation context to `artifacts/escalations/RF-2026-0415.json`. | [app/graph.py](file:///e:/5/05-caseworkers-morning/app/graph.py#L241-L266) | Low |
| **H-07** | Queue continuation after escalation | **PASS** | `escalate_node` routes directly to `next_referral_node`. Referrals 5–12 continue without program termination. | [app/graph.py](file:///e:/5/05-caseworkers-morning/app/graph.py#L344) | Low |
| **H-08** | Policy determines authority | **PASS** | Deterministic `PolicyEngine` evaluates requested actions against `config/policy.json` rules independent of LLM reasoning. | [app/policy.py](file:///e:/5/05-caseworkers-morning/app/policy.py) | Low |
| **H-09** | Policy Section 6.1 Ambiguity Rule | **PASS** | Unlisted or ambiguous action strings default to `APPROVAL_REQUIRED` with policy section `"6.1"`. | [app/policy.py](file:///e:/5/05-caseworkers-morning/app/policy.py#L125-L131) | Low |
| **H-10** | Per-referral error isolation | **PASS** | `fetch_history_node` catches `HistoryServiceError`, logs error in `errors` array, and advances queue without crashing. | [app/graph.py](file:///e:/5/05-caseworkers-morning/app/graph.py#L136-L140) | Low |
| **H-11** | Policy as data (Day-two resilience) | **PASS** | Policy rules loaded from `config/policy.json`. Changing rules alters behavior without modifying graph Python code. | [config/policy.json](file:///e:/5/05-caseworkers-morning/config/policy.json) | Low |
| **H-12** | Clean clone & README instructions | **PASS** | Clear instructions for starting history API (`python services/history_service.py`) and agent (`python -m app.main`). | [README.md](file:///e:/5/05-caseworkers-morning/README.md) | Low |
| **H-13** | Architecture decisions document | **PASS** | Covers 12 core decision points including why LangGraph, Groq, policy engine, and token security were chosen. | [DECISIONS.md](file:///e:/5/05-caseworkers-morning/DECISIONS.md) | Low |
| **H-14** | AI usage disclosure document | **PASS** | Covers AI tools used, human engineering verification, and fallback limitations per participant handbook rules. | [AI-USAGE.md](file:///e:/5/05-caseworkers-morning/AI-USAGE.md) | Low |
| **H-15** | Test suite verification | **PASS** | `pytest -v` verifies policy evaluation (`test_policy.py`), token guardrails (`test_guardrail.py`), and 12-referral queue (`test_run.py`). | [tests/](file:///e:/5/05-caseworkers-morning/tests/) | Low |
