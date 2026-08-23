import json
import pytest
from unittest.mock import patch, MagicMock
from app.history import get_resident_history, ResidentNotFoundError


def test_get_resident_success():
    mock_data = {
        "resident_ref": "R-20500",
        "status": "Active",
        "benefit_code": "HSP-A",
        "district": "Ash Hill",
        "award_monthly": 988.04,
        "household": [{"name": "Elizabeth Whitlock", "date_of_birth": "1964-05-25", "relationship": "Applicant"}],
        "events": [{"date": "2025-03-18", "type": "Address change recorded", "detail": "Referred to support."}],
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = get_resident_history("R-20500", base_url="http://mock-service:8083")
        assert res.resident_ref == "R-20500"
        assert res.award_monthly == 988.04
        assert len(res.household) == 1
        assert res.household[0].name == "Elizabeth Whitlock"


def test_get_resident_not_found():
    with patch("urllib.request.urlopen") as mock_urlopen:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError("http://mock-service/residents/R-99999", 404, "Not Found", {}, None)

        with pytest.raises(ResidentNotFoundError):
            get_resident_history("R-99999", base_url="http://mock-service:8083")
