# 04 — Resident History Client (`app/history.py`)

This document explains how resident historical records are retrieved from the supplied Resident History HTTP API.

---

## Source File Overview: `app/history.py`

### Lines 1–5 — Imports
```python
1: import json
2: import logging
3: import urllib.request
4: import urllib.error
5: from typing import Optional, Dict, Any
6: from app.models import ResidentHistory, HouseholdMember, CaseEvent
```
* **Explanation**: Uses standard Python `urllib.request` for HTTP communication, eliminating external network library dependencies.

---

## 1. Custom Exceptions — Lines 8–15
```python
8: class HistoryServiceError(Exception):
9:     """Exception raised when History API communication fails."""
10:     pass

13: class ResidentNotFoundError(HistoryServiceError):
14:     """Exception raised when resident reference is 404."""
15:     pass
```
* **Purpose**: Clear exception hierarchy allowing calling graph nodes to handle 404s and network outages cleanly.

---

## 2. `get_resident_history()` — Lines 18–49

```python
18: def get_resident_history(
19:     resident_ref: str, base_url: str = "http://127.0.0.1:8083", timeout: float = 5.0
20: ) -> ResidentHistory:
```

### Lines 24–27 — Request Execution
```python
24:     url = f"{base_url.rstrip('/')}/residents/{resident_ref}"
25:     try:
26:         req = urllib.request.Request(url, headers={"Accept": "application/json"})
27:         with urllib.request.urlopen(req, timeout=timeout) as resp:
```
* **Explanation**: Constructs the target REST endpoint (`GET /residents/<ref>`), adds JSON headers, and issues an HTTP GET request with a 5-second timeout safeguard.

### Lines 28–39 — Parsing & Serialization
```python
28:             data = json.load(resp) # or json.loads(resp.read().decode("utf-8"))
29: 
30:             household = [HouseholdMember(**h) for h in data.get("household", [])]
31:             events = [CaseEvent(**e) for e in data.get("events", [])]
32: 
33:             return ResidentHistory(
34:                 resident_ref=data["resident_ref"],
35:                 status=data.get("status", "Active"),
36:                 benefit_code=data.get("benefit_code", "UNKNOWN"),
37:                 district=data.get("district", "UNKNOWN"),
38:                 award_monthly=float(data.get("award_monthly", 0.0)),
39:                 household=household,
40:                 events=events,
41:             )
```
* **Explanation**: Parses the JSON response payload and hydrates the `ResidentHistory` Pydantic model with nested `HouseholdMember` and `CaseEvent` lists.

### Lines 41–49 — Error Handling Boundary
```python
41:     except urllib.error.HTTPError as e:
42:         if e.code == 404:
43:             raise ResidentNotFoundError(f"Resident record '{resident_ref}' not found (404).") from e
44:         raise HistoryServiceError(f"HTTP error {e.code} fetching resident '{resident_ref}': {e.reason}") from e
45:     except urllib.error.URLError as e:
46:         raise HistoryServiceError(f"Network error connecting to History API at {base_url}: {e}") from e
```
* **Explanation**: Catches HTTP 404s, general HTTP errors, and connection failures. Converts raw socket/urllib exceptions into domain-specific `HistoryServiceError` exceptions.

---

## Connections to Graph Workflow
* **Called by**: `fetch_history_node` in `app/graph.py` (Line 127).
* **Per-Item Failure Handling**: If `HistoryServiceError` is raised, `fetch_history_node` catches it, records the error in `state["errors"]`, and advances the loop to the next referral without crashing the entire run.

---

## Related Documentation
* For how this function is invoked in the graph, see [06_LANGGRAPH_WORKFLOW.md](06_LANGGRAPH_WORKFLOW.md).
