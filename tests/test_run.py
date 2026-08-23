import json
import os
from unittest.mock import patch
from app.graph import build_workflow_graph, WorkflowState
from app.models import ResidentHistory, HouseholdMember, CaseEvent


def test_full_queue_run(tmp_path):
    queue_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "referral-queue.json")
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services", "_history_data.json")

    with open(data_path, "r", encoding="utf-8") as f:
        history_db = json.load(f)

    def mock_get_history(ref_id, base_url="http://127.0.0.1:8083"):
        data = history_db.get(ref_id)
        if not data:
            from app.history import ResidentNotFoundError
            raise ResidentNotFoundError(f"Not found {ref_id}")
        return ResidentHistory(
            resident_ref=data["resident_ref"],
            status=data.get("status", "Active"),
            benefit_code=data.get("benefit_code", "UNKNOWN"),
            district=data.get("district", "UNKNOWN"),
            award_monthly=float(data.get("award_monthly", 0.0)),
            household=[HouseholdMember(**h) for h in data.get("household", [])],
            events=[CaseEvent(**e) for e in data.get("events", [])],
        )

    graph = build_workflow_graph()
    state: WorkflowState = {
        "run_id": "RUN-TEST-FULL",
        "queue_file": queue_path,
        "history_api_url": "http://127.0.0.1:8083",
        "auto_approve": True,
        "secret_key": "test-key",
    }

    with patch("app.graph.get_resident_history", side_effect=mock_get_history):
        final_state = graph.invoke(state)

    assert final_state.get("is_finished") is True
    assert final_state.get("total_count") == 12
    assert "RF-2026-0415" in final_state.get("escalated_referrals", [])
    assert len(final_state.get("completed_referrals", [])) + len(final_state.get("escalated_referrals", [])) == 12
