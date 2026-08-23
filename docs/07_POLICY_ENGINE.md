# 07 — Policy Engine (`app/policy.py`)

This document provides a line-by-line technical explanation of `app/policy.py` and `config/policy.json`.

---

## Source File Overview: `app/policy.py`

### Lines 1–5 — Imports
```python
1: import json
2: import os
3: import re
4: from typing import Optional
5: from app.models import PolicyDecision, PolicyDecisionEnum
```

---

## 1. Class Initialization & Rule Loading — Lines 18–32

```python
18:     def __init__(self, config_path: Optional[str] = None):
19:         if config_path is None:
20:             config_path = os.path.join(
21:                 os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
22:                 "config",
23:                 "policy.json",
24:             )
25:         self.config_path = config_path
26:         self.rules = self._load_rules()
```
* **Explanation**: Resolves path to `config/policy.json`. Externalizing rules ensures policy definitions can be modified without altering Python graph logic.

### Lines 28–32 — Data-Driven Rule Loading
```python
28:     def _load_rules(self) -> list:
29:         if os.path.exists(self.config_path):
30:             with open(self.config_path, "r", encoding="utf-8") as f:
31:                 data = json.load(f)
32:                 return data.get("rules", [])
```
* **Explanation**: Loads rules list from `config/policy.json`. (Includes hardcoded fallback on L34–L98 if config file is absent).

---

## 2. Deterministic Action Evaluation — Lines 100–131

```python
100:     def evaluate(self, action: str) -> PolicyDecision:
```

### Lines 102–109 — Unspecified Action Safeguard
```python
102:         if not action or not action.strip():
103:             return PolicyDecision(
104:                 decision=PolicyDecisionEnum.APPROVAL_REQUIRED,
105:                 action=action or "UNSPECIFIED",
106:                 policy_section="6.1",
107:                 policy_rule="Unclear action boundary rule",
108:                 reason="No explicit action provided. Defaulting to supervisor approval under Policy 6.1.",
109:             )
```
* **Explanation**: If an empty or whitespace string is passed, it is caught immediately and assigned `APPROVAL_REQUIRED` under Section 6.1.

### Lines 113–122 — Pattern & Substring Matching
```python
113:         for rule in self.rules:
114:             pattern = re.escape(rule["action_pattern"])
115:             if re.search(pattern, clean_action, re.IGNORECASE) or rule["action_pattern"].lower() in clean_action.lower():
116:                 return PolicyDecision(
117:                     decision=PolicyDecisionEnum(rule["decision"]),
118:                     action=clean_action,
119:                     policy_section=rule["policy_section"],
120:                     policy_rule=rule["policy_rule"],
121:                     reason=rule["reason"],
122:                 )
```
* **Explanation**: Performs case-insensitive regex search and substring comparison against rule action patterns.

### Lines 125–131 — Policy Rule 6.1 Ambiguity Fallback
```python
125:         return PolicyDecision(
126:             decision=PolicyDecisionEnum.APPROVAL_REQUIRED,
127:             action=clean_action,
128:             policy_section="6.1",
129:             policy_rule="Unclear action boundary rule",
130:             reason=f"Action '{clean_action}' is not explicitly listed as permitted under Section 2. Under Rule 6.1, ambiguous actions must be treated as requiring supervisor approval.",
131:         )
```
* **Explanation**: **Crucial Guardrail Feature**. If an action pattern does not match any rule in `config/policy.json` (or contains adversarial prompt injection text), `PolicyEngine` defaults to `APPROVAL_REQUIRED` with Policy Section `"6.1"`.

---

## Machine-Readable Policy Representation (`config/policy.json`)

```json
{
  "policy_reference": "ACA-2026/1",
  "rules": [
    {
      "action_pattern": "Record change of address",
      "decision": "ALLOWED",
      "policy_section": "2.1 / 2.5"
    },
    {
      "action_pattern": "Update payment details",
      "decision": "APPROVAL_REQUIRED",
      "policy_section": "3.4"
    },
    {
      "action_pattern": "Suspend assistance pending investigation",
      "decision": "DENIED",
      "policy_section": "3.2 / 3.7 / 4.1"
    }
  ]
}
```

---

## Related Documentation
* For policy interpretation rules, see [02_POLICY_AND_AUTHORITY.md](02_POLICY_AND_AUTHORITY.md).
* For human approval gate execution, see [08_APPROVAL_AND_HUMAN_GATE.md](08_APPROVAL_AND_HUMAN_GATE.md).
