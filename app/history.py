import json
import urllib.request
import urllib.error
from app.models import ResidentHistory, HouseholdMember, CaseEvent


class HistoryServiceError(Exception):
    pass


class ResidentNotFoundError(HistoryServiceError):
    pass


def get_resident_history(
    resident_ref: str, base_url: str = "http://127.0.0.1:8083", timeout: float = 5.0
) -> ResidentHistory:
    url = f"{base_url.rstrip('/')}/residents/{resident_ref}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return ResidentHistory(
                resident_ref=data["resident_ref"],
                status=data.get("status", "Active"),
                benefit_code=data.get("benefit_code", "UNKNOWN"),
                district=data.get("district", "UNKNOWN"),
                award_monthly=float(data.get("award_monthly", 0.0)),
                household=[HouseholdMember(**h) for h in data.get("household", [])],
                events=[CaseEvent(**e) for e in data.get("events", [])],
            )
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ResidentNotFoundError(f"Resident '{resident_ref}' not found (404).") from e
        raise HistoryServiceError(f"HTTP error {e.code} fetching resident '{resident_ref}': {e.reason}") from e
    except urllib.error.URLError as e:
        raise HistoryServiceError(f"Network error connecting to History API at {base_url}: {e}") from e
    except (json.JSONDecodeError, KeyError) as e:
        raise HistoryServiceError(f"Malformed JSON response for resident '{resident_ref}': {e}") from e
