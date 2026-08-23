# 10 — Escalation and Audit Artifacts (`artifacts/`)

This document explains how unauthorized or human-rejected referrals are escalated and how structured audit execution traces are generated.

---

## 1. Escalation Generator — `escalate_node` (`app/graph.py` Lines 241–276)

```python
241: def escalate_node(state: WorkflowState) -> Dict[str, Any]:
242:     ref = Referral(**state["current_referral"])
243:     policy = PolicyDecision(**state["policy_decision"])
244:     triage = TriageNote(**state["triage_note"]) if state.get("triage_note") else None
245:     run_id = state.get("run_id", "")
246: 
247:     esc_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "escalations")
248:     os.makedirs(esc_dir, exist_ok=True)
249: 
250:     file_path = os.path.join(esc_dir, f"{ref.referral_id}.json")
251:     esc_data = {
252:         "referral_id": ref.referral_id,
253:         "resident_ref": ref.resident_ref,
254:         "requested_action": ref.requested_action,
255:         "policy_section": policy.policy_section,
256:         "policy_rule": policy.policy_rule,
257:         "reason": policy.reason,
258:         "triage_summary": triage.situation_summary if triage else ref.summary,
259:         "status": "ESCALATED",
260:         "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
261:         "run_id": run_id,
262:     }
263: 
264:     with open(file_path, "w", encoding="utf-8") as f:
265:         json.dump(esc_data, f, indent=2)
```

### When Escalation Triggered:
1. Action is explicitly `DENIED` by Policy Engine (e.g. `RF-2026-0415` requesting award suspension).
2. Supervisor selects `[N]` (Reject) at `human_approval_gate_node`.

### Escalation Artifact Example (`artifacts/escalations/RF-2026-0415.json`):
```json
{
  "referral_id": "RF-2026-0415",
  "resident_ref": "R-20521",
  "requested_action": "Suspend assistance pending investigation",
  "policy_section": "3.2 / 3.7 / 4.1",
  "policy_rule": "Forbidden & Requires Escalation — Award suspension and fraud assertion",
  "reason": "Section 3.2 prohibits award suspension and Section 3.7 prohibits fraud findings without supervisor authority. Section 4.1 mandates immediate escalation.",
  "status": "ESCALATED",
  "timestamp": "2026-08-22T21:59:48.123456+00:00",
  "run_id": "20260822-215948"
}
```

---

## 2. Audit Trace Generation — `app/main.py` (Lines 70–85)

```python
70:     runs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "runs")
71:     os.makedirs(runs_dir, exist_ok=True)
72:     audit_file = os.path.join(runs_dir, f"RUN_{run_id}.json")
73: 
74:     run_summary = {
75:         "run_id": run_id,
76:         "total": final_state.get("total_count", 0),
77:         "completed": len(final_state.get("completed_referrals", [])),
78:         "approved": len(final_state.get("approved_referrals", [])),
79:         "rejected": len(final_state.get("rejected_referrals", [])),
80:         "escalated": len(final_state.get("escalated_referrals", [])),
81:         "failed": len(final_state.get("failed_referrals", [])),
82:         "errors": final_state.get("errors", []),
83:         "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
84:     }
85:     with open(audit_file, "w", encoding="utf-8") as f:
86:         json.dump(run_summary, f, indent=2)
```

### Traceability Guarantee:
Satisfies Policy Section 5 traceability requirements by writing a machine-readable JSON log of every run with referral counters and error arrays to `artifacts/runs/`.

---

## Related Documentation
* For runtime invocation, see [11_MAIN_RUNTIME_FLOW.md](11_MAIN_RUNTIME_FLOW.md).
