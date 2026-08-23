import pytest
import os
import json
from unittest.mock import patch
from app.graph import build_workflow_graph, WorkflowState
from app.history import HistoryServiceError
from app.models import ResidentHistory


def test_per_referral_isolation_on_history_error(tmp_path):
    queue = [
        {
            "referral_id": "RF-TEST-01",
            "received_at": "2026-03-17T01:00:00",
            "resident_ref": "R-MISSING",
            "source": "Test",
            "summary": "Missing history test",
            "requested_action": "Record change of address",
            "urgency": "Standard",
        },
        {
            "referral_id": "RF-TEST-02",
            "received_at": "2026-03-17T02:00:00",
            "resident_ref": "R-VALID",
            "source": "Test",
            "summary": "Valid referral",
            "requested_action": "Record change of address",
            "urgency": "Standard",
        },
    ]

    q_file = tmp_path / "test_queue.json"
    with open(q_file, "w") as f:
        json.dump(queue, f)

    def mock_get_history(ref_id, base_url="http://127.0.0.1:8083"):
        if ref_id == "R-MISSING":
            raise HistoryServiceError("API connection error")
        return ResidentHistory(
            resident_ref="R-VALID",
            status="Active",
            benefit_code="HSP-A",
            district="Ash Hill",
            award_monthly=500.0,
            household=[],
            events=[],
        )

    graph = build_workflow_graph()
    initial_state: WorkflowState = {
        "run_id": "RUN-TEST-ISOLATION",
        "queue_file": str(q_file),
        "history_api_url": "http://mock",
        "auto_approve": True,
        "secret_key": "test-key",
    }

    with patch("app.graph.get_resident_history", side_effect=mock_get_history):
        final_state = graph.invoke(initial_state)

    assert final_state.get("is_finished") is True
    assert "RF-TEST-02" in final_state.get("completed_referrals", [])
    assert len(final_state.get("errors", [])) >= 1
    assert final_state["errors"][0]["referral_id"] == "RF-TEST-01"
