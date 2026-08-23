# 11 — Main Runtime Flow (`app/main.py`)

This document provides a line-by-line code explanation of `app/main.py`, the CLI entrypoint script.

---

## Source Code Analysis: `app/main.py`

### Lines 1–10 — Imports & Environment Loading
```python
1: import argparse
2: import datetime
3: import json
4: import os
5: import sys
6: from dotenv import load_dotenv
7: from app.history import get_resident_history, HistoryServiceError
8: from app.graph import build_workflow_graph, WorkflowState
9: 
10: load_dotenv()
```
* **Explanation**: Loads environment variables from `.env` (e.g. `GROQ_API_KEY`, `GROQ_MODEL`, `HISTORY_API_URL`, `SECRET_KEY`).

---

## 1. CLI Argument Parsing — Lines 13–33

```python
13:     parser = argparse.ArgumentParser(...)
14:     parser.add_argument("--queue-file", default="referral-queue.json", ...)
15:     parser.add_argument("--history-url", default=os.environ.get("HISTORY_API_URL", "http://127.0.0.1:8083"), ...)
16:     parser.add_argument("--auto-approve", action="store_true", ...)
17:     parser.add_argument("--demo", action="store_true", ...)
18:     args = parser.parse_args()
19: 
20:     auto_approve = args.auto_approve or args.demo
21:     run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
22:     secret_key = os.environ.get("SECRET_KEY", "caseworker-guardrails-secret-key-2026")
```
* **Explanation**: Parses CLI flags. `--demo` or `--auto-approve` enables non-interactive mode. Generates a unique timestamped `run_id` (e.g. `"20260822-215948"`).

---

## 2. History API Health Verification — Lines 52–57

```python
52:     try:
53:         get_resident_history("R-20500", base_url=args.history_url)
54:         print("✓ Connected to Resident History API!\n")
55:     except Exception as e:
56:         print(f"⚠ History API health check warning: {e}")
```
* **Explanation**: Issues a lightweight test GET query for `R-20500` against `http://127.0.0.1:8083` to verify that `history_service.py` is running before launching the state graph.

---

## 3. LangGraph Workflow Invocation — Lines 59–67

```python
59:     graph = build_workflow_graph()
60: 
61:     initial_state: WorkflowState = {
62:         "run_id": run_id,
63:         "queue_file": args.queue_file,
64:         "history_api_url": args.history_url,
65:         "auto_approve": auto_approve,
66:         "secret_key": secret_key,
67:     }
68: 
69:     final_state = graph.invoke(initial_state)
```
* **Explanation**: Compiles the graph via `build_workflow_graph()`, sets initial state dictionary, and starts graph processing with `graph.invoke(initial_state)`.

---

## 4. Run Summary & Audit Logging — Lines 70–100

```python
70:     runs_dir = os.path.join(...)
72:     audit_file = os.path.join(runs_dir, f"RUN_{run_id}.json")
74:     run_summary = {
75:         "run_id": run_id,
76:         "total": final_state.get("total_count", 0),
77:         "completed": len(final_state.get("completed_referrals", [])),
78:         "approved": len(final_state.get("approved_referrals", [])),
79:         "rejected": len(final_state.get("rejected_referrals", [])),
80:         "escalated": len(final_state.get("escalated_referrals", [])),
81:         "failed": len(final_state.get("failed_referrals", [])),
...
```
* **Explanation**: Extracts final statistics from graph state, persists summary JSON to `artifacts/runs/RUN_<id>.json`, and prints formatted console output.

---

## Related Documentation
* For graph execution details, see [06_LANGGRAPH_WORKFLOW.md](06_LANGGRAPH_WORKFLOW.md).
