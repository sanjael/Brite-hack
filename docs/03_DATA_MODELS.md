# 03 — Data Models Reference (`app/models.py`)

This document provides a line-by-line technical reference for `app/models.py`, which defines the Pydantic data schemas used throughout the system.

---

## Source File Overview: `app/models.py`

### Lines 1–3 — Imports
```python
1: from typing import List, Optional, Dict, Any
2: from enum import Enum
3: from pydantic import BaseModel, Field
```
* **Explanation**: Imports standard Python typing primitives, string-backed enumeration base class, and Pydantic `BaseModel` for automatic data validation and serialization.

---

## 1. `PolicyDecisionEnum` — Lines 6–9
```python
6: class PolicyDecisionEnum(str, Enum):
7:     ALLOWED = "ALLOWED"
8:     APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
9:     DENIED = "DENIED"
```
* **Purpose**: Explicit enumeration representing the 3 possible policy authorization decisions.
* **Inheritance**: Inherits from `str` and `Enum` so that value comparisons work seamlessly with JSON data strings.

---

## 2. `Referral` — Lines 12–19
```python
12: class Referral(BaseModel):
13:     referral_id: str
14:     received_at: str
15:     resident_ref: str
16:     source: str
17:     summary: str
18:     requested_action: str
19:     urgency: str
```
* **Purpose**: Represents an overnight referral item parsed from `referral-queue.json`.
* **Fields**:
  * `referral_id`: E.g. `"RF-2026-0412"`
  * `resident_ref`: E.g. `"R-20500"`
  * `requested_action`: E.g. `"Update payment details"`

---

## 3. `HouseholdMember` & `CaseEvent` — Lines 22–31
```python
22: class HouseholdMember(BaseModel):
23:     name: str
24:     date_of_birth: str
25:     relationship: str

28: class CaseEvent(BaseModel):
29:     date: str
30:     type: str
31:     detail: str
```
* **Purpose**: Child schemas embedded inside `ResidentHistory`.

---

## 4. `ResidentHistory` — Lines 34–41
```python
34: class ResidentHistory(BaseModel):
35:     resident_ref: str
36:     status: str = "Active"
37:     benefit_code: str = "UNKNOWN"
38:     district: str = "UNKNOWN"
39:     award_monthly: float = 0.0
40:     household: List[HouseholdMember] = Field(default_factory=list)
41:     events: List[CaseEvent] = Field(default_factory=list)
```
* **Purpose**: Represents full resident context returned by the Resident History API (`app/history.py`).

---

## 5. `LLMAnalysis` & `TriageNote` — Lines 44–62
```python
44: class LLMAnalysis(BaseModel):
45:     summary: str
46:     relevant_history: List[str] = Field(default_factory=list)
47:     proposed_action: str
48:     reasoning: str
49:     confidence: float = 0.95

52: class TriageNote(BaseModel):
53:     referral_id: str
54:     resident_ref: str
55:     source: str
56:     urgency: str
57:     situation_summary: str
58:     relevant_history: List[str] = Field(default_factory=list)
59:     requested_action: str
60:     proposed_next_step: str
61:     policy_status: str
62:     reasoning: str
```
* **Purpose**: Structuring Groq LLM reasoning outputs into human-readable triage assessments.

---

## 6. `PolicyDecision` — Lines 65–70
```python
65: class PolicyDecision(BaseModel):
66:     decision: PolicyDecisionEnum
67:     action: str
68:     policy_section: str
69:     policy_rule: str
70:     reason: str
```
* **Purpose**: Structured output returned by `PolicyEngine.evaluate()`.

---

## 7. `ApprovalToken` — Lines 73–80
```python
73: class ApprovalToken(BaseModel):
74:     token_id: str
75:     referral_id: str
76:     action: str
77:     run_id: str
78:     approved_at: str
79:     signature: str
```
* **Purpose**: HMAC-SHA256 authorization token required by `execute_action_node` for protected actions.

---

## 8. Data Flow Lifecycle

```text
referral-queue.json → Referral
                           ↓
               app/history.py → ResidentHistory
                                       ↓
                           app/agent.py → LLMAnalysis → TriageNote
                                                            ↓
                                             app/policy.py → PolicyDecision
                                                                 ↓
                                           app/graph.py → ApprovalToken → ExecutionResult
```

---

## Related Documentation
* For history fetching using these models, see [04_HISTORY_SERVICE.md](04_HISTORY_SERVICE.md).
* For policy decision generation, see [07_POLICY_ENGINE.md](07_POLICY_ENGINE.md).
