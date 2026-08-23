# File Dependency & Data Flow Map

This document illustrates the import dependencies and data flow between all project files in the repository.

---

## 1. Architectural Module Dependency Diagram

```text
                               ┌──────────────────────────┐
                               │   referral-queue.json    │
                               └────────────┬─────────────┘
                                            │
                                            v
                               ┌──────────────────────────┐
                               │       app/main.py        │
                               └────────────┬─────────────┘
                                            │
                                            v
                               ┌──────────────────────────┐
                               │       app/graph.py       │
                               └──────┬─────┬──────┬──────┘
                                      │     │      │
           ┌──────────────────────────┘     │      └──────────────────────────┐
           │                                │                                 │
           v                                v                                 v
┌────────────────────┐            ┌───────────────────┐            ┌────────────────────┐
│   app/history.py   │            │   app/agent.py    │            │   app/policy.py    │
└──────────┬─────────┘            └─────────┬─────────┘            └──────────┬─────────┘
           │                                │                                 │
           v                                v                                 v
┌────────────────────┐            ┌───────────────────┐            ┌────────────────────┐
│ history_service.py │            │     Groq API      │            │ config/policy.json │
└────────────────────┘            └───────────────────┘            └────────────────────┘
```

---

## 2. Python File Import Hierarchy

```text
app/main.py
  ├── imports app.history (get_resident_history, HistoryServiceError)
  └── imports app.graph (build_workflow_graph, WorkflowState)

app/graph.py
  ├── imports app.models (Referral, ResidentHistory, TriageNote, PolicyDecision, etc.)
  ├── imports app.policy (PolicyEngine)
  ├── imports app.history (get_resident_history, HistoryServiceError)
  └── imports app.agent (analyze_and_triage)

app/agent.py
  ├── imports app.models (Referral, ResidentHistory, LLMAnalysis, TriageNote)
  └── imports groq (Groq client)

app/policy.py
  ├── imports app.models (PolicyDecision, PolicyDecisionEnum)
  └── reads config/policy.json

app/history.py
  ├── imports app.models (ResidentHistory, HouseholdMember, CaseEvent)
  └── imports urllib.request, urllib.error
```

---

## 3. Data Output Flow Map

```text
[Input Payload]
referral-queue.json ──> app/main.py ──> app/graph.py (load_queue_node)
                                              │
[HTTP Fetch]                                  │
services/_history_data.json <── services/history_service.py <── app/history.py
                                              │
[Groq LLM Reasoning]                          │
Groq Llama 3.3 70B <─────────────────── app/agent.py
                                              │
[Deterministic Authority Check]               │
config/policy.json ───────────────────> app/policy.py
                                              │
[Execution & Output Tracing]                  │
                                ┌─────────────┴─────────────┐
                                ↓                           ↓
                    artifacts/escalations/           artifacts/runs/
                     (Escalation JSON)               (Run Summary JSON)
```

---

## Related Documentation
* For complete file inventory table, see [FILE_INVENTORY.md](FILE_INVENTORY.md).
