import json
import os
import datetime
import logging
from typing import List, Dict, Any, Optional
from src.models.schemas import AuditEvent

logger = logging.getLogger("audit_logger")


class AuditLogger:
    """
    Audit Logger for complete, reconstructible execution traces.
    
    Persists structured events to artifacts/runs/RUN_<timestamp>.json
    and streams clean console traces.
    """

    def __init__(self, run_id: str, output_dir: Optional[str] = None):
        self.run_id = run_id
        if output_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, "artifacts", "runs")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.run_file_path = os.path.join(self.output_dir, f"RUN_{self.run_id}.json")
        self.events: List[AuditEvent] = []

    def log_event(
        self,
        node: str,
        event_type: str,
        status: str,
        referral_id: Optional[str] = None,
        action: Optional[str] = None,
        policy_rule: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """
        Logs a structured audit event.
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        event = AuditEvent(
            timestamp=timestamp,
            run_id=self.run_id,
            referral_id=referral_id,
            node=node,
            event_type=event_type,
            action=action,
            status=status,
            policy_rule=policy_rule,
            reason=reason,
            details=details or {},
        )

        self.events.append(event)
        self._console_print(event)
        self._flush_to_file()
        return event

    def _console_print(self, event: AuditEvent) -> None:
        ref_str = f"[{event.referral_id}] " if event.referral_id else ""
        act_str = f" Action: '{event.action}'" if event.action else ""
        pol_str = f" (Rule: {event.policy_rule})" if event.policy_rule else ""
        print(f"[{event.timestamp[11:19]}] [{event.node}] {event.event_type} - Status: {event.status} | {ref_str}{act_str}{pol_str}")
        if event.reason:
            print(f"         Reason: {event.reason}")

    def _flush_to_file(self) -> None:
        data = [e.model_dump() for e in self.events]
        with open(self.run_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_trace(self) -> List[Dict[str, Any]]:
        return [e.model_dump() for e in self.events]
