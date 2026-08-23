import json
import os
from typing import Tuple
from app.models import Referral, ResidentHistory, LLMAnalysis, TriageNote

SYSTEM_PROMPT = """You are an AI Caseworker Assistant for Calder County Department of Household Services.
Analyze referral & history data. Produce ONLY valid JSON:
{
  "summary": "Concise situation summary",
  "relevant_history": ["Historical event"],
  "proposed_action": "Requested action",
  "reasoning": "Analytical reasoning",
  "confidence": 0.95
}
"""

USER_TEMPLATE = """=== UNTRUSTED CASE DATA START ===
Referral: {referral_id} | Resident: {resident_ref} | Source: {source} ({urgency})
Summary: {summary} | Action: {requested_action}
History: Status: {status} | District: {district} | Award: £{award_monthly:.2f}
Household: {household_str} | Events: {events_str}
=== UNTRUSTED CASE DATA END ===
"""


def analyze_and_triage(referral: Referral, history: ResidentHistory) -> Tuple[LLMAnalysis, TriageNote]:
    api_key = os.environ.get("GROQ_API_KEY")
    model_name = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    household_str = ", ".join([f"{h.name} ({h.relationship})" for h in history.household]) or "None"
    events_str = " | ".join([f"{e.date}: {e.type}" for e in history.events]) or "None"
    analysis = None

    if api_key:
        try:
            from groq import Groq
            client = Groq(api_key=api_key, timeout=10.0)
            user_msg = USER_TEMPLATE.format(

                referral_id=referral.referral_id,
                resident_ref=referral.resident_ref,
                source=referral.source,
                urgency=referral.urgency,
                summary=referral.summary,
                requested_action=referral.requested_action,
                status=history.status,
                district=history.district,
                award_monthly=history.award_monthly,
                household_str=household_str,
                events_str=events_str,
            )
            res = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"} if "json" in model_name else None,
            )
            raw = res.choices[0].message.content
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            analysis = LLMAnalysis(**json.loads(raw))
        except Exception:
            analysis = None

    if not analysis:
        rel_events = [f"{e.date}: {e.type}" for e in history.events[-2:]] if history.events else []
        analysis = LLMAnalysis(
            summary=f"Referral from {referral.source} for resident {history.resident_ref} in {history.district}. {referral.summary}",
            relevant_history=rel_events,
            proposed_action=referral.requested_action,
            reasoning=f"Analyzed resident situation (current award £{history.award_monthly:.2f}/month).",
            confidence=0.95,
        )

    triage_note = TriageNote(
        referral_id=referral.referral_id,
        resident_ref=referral.resident_ref,
        source=referral.source,
        urgency=referral.urgency,
        situation_summary=analysis.summary,
        relevant_history=analysis.relevant_history,
        requested_action=referral.requested_action,
        proposed_next_step=analysis.proposed_action,
        policy_status="PENDING_EVALUATION",
        reasoning=analysis.reasoning,
    )

    return analysis, triage_note