import json
import os
import datetime
from typing import Dict, Any, Optional
from src.models.schemas import Referral, PolicyDecisionResult, TriageNote


class EscalationManager:
    """
    Escalation Manager.
    
    Generates detailed, supervisor-ready escalation artifacts (JSON & Markdown)
    for forbidden, out-of-authority, or human-rejected actions.
    Artifacts are stored in `artifacts/escalations/`.
    """

    def __init__(self, output_dir: Optional[str] = None):
        if output_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, "artifacts", "escalations")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def create_escalation(
        self,
        referral: Referral,
        policy_decision: PolicyDecisionResult,
        triage_note: Optional[TriageNote] = None,
        escalation_reason: str = "Out-of-authority action requested",
        run_id: str = "",
        actions_completed: Optional[list] = None,
        actions_not_performed: Optional[list] = None,
    ) -> Dict[str, str]:
        """
        Creates structured JSON and Markdown escalation reports.
        Returns paths to created files.
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        file_prefix = f"ESCALATION_{referral.referral_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        json_path = os.path.join(self.output_dir, f"{file_prefix}.json")
        md_path = os.path.join(self.output_dir, f"{file_prefix}.md")

        completed = actions_completed or ["Read referral", "Fetched resident history", "Evaluated policy ACA-2026/1"]
        not_performed = actions_not_performed or [
            f"EXECUTION REFUSED: {referral.requested_action} (Forbidden under Section {policy_decision.policy_section})"
        ]

        escalation_data = {
            "timestamp": timestamp,
            "run_id": run_id,
            "referral_id": referral.referral_id,
            "resident_ref": referral.resident_ref,
            "source": referral.source,
            "urgency": referral.urgency,
            "requested_action": referral.requested_action,
            "triage_summary": triage_note.situation_summary if triage_note else referral.summary,
            "policy_section": policy_decision.policy_section,
            "policy_rule": policy_decision.policy_rule,
            "policy_reason": policy_decision.reason,
            "required_authority": policy_decision.required_authority,
            "escalation_reason": escalation_reason,
            "actions_completed": completed,
            "actions_not_performed": not_performed,
        }

        # Write JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(escalation_data, f, indent=2)

        # Write Markdown
        md_content = f"""# CASE ESCALATION REPORT — {referral.referral_id}

**Timestamp:** {timestamp}  
**Run ID:** `{run_id}`  
**Referral ID:** `{referral.referral_id}`  
**Resident Reference:** `{referral.resident_ref}`  
**Source:** {referral.source}  
**Assessed Urgency:** {referral.urgency}  

---

## 1. Executive Summary & Reason for Escalation
> **ESCALATION REASON:** {escalation_reason}

The referral requests the action **"{referral.requested_action}"**, which violates Authority Policy **ACA-2026/1**. Under Policy Section {policy_decision.policy_section}, the automated assistant is strictly prohibited from executing this action without supervisor authority.

---

## 2. Policy Enforcement Breakdown
* **Policy Section:** Section {policy_decision.policy_section}
* **Policy Rule:** {policy_decision.policy_rule}
* **Policy Reason:** {policy_decision.reason}
* **Required Authority:** {policy_decision.required_authority}

---

## 3. Case Context & Triage Summary
**Summary:**  
{triage_note.situation_summary if triage_note else referral.summary}

**Proposed Next Step:**  
{triage_note.proposed_next_step if triage_note else 'Escalate to human supervisor for case review.'}

---

## 4. Execution Boundary Status
### Actions Completed Autonomously:
{"".join([f"- {a}\n" for a in completed])}

### Actions Deliberately NOT Performed:
{"".join([f"- **[REFUSED]** {a}\n" for a in not_performed])}

---
*Generated automatically by Calder County Automated Casework Assistant (Policy ACA-2026/1).*
"""
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return {"json": json_path, "markdown": md_path}
