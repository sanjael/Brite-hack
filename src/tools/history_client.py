import json
import logging
from typing import Optional, Dict, Any, List
import urllib.request
import urllib.error
from src.models.schemas import ResidentHistory, HouseholdMember, CaseEvent

logger = logging.getLogger(__name__)


class HistoryClientError(Exception):
    """Base exception for History API client errors."""
    pass


class ResidentNotFoundError(HistoryClientError):
    """Raised when a resident reference is not found in the history API."""
    pass


class HistoryClient:
    """
    Client for interacting with the Resident History API service.
    Default endpoint: http://127.0.0.1:8083
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8083", timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def check_health(self) -> Dict[str, Any]:
        """Check the health status of the Resident History API."""
        url = f"{self.base_url}/health"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
                raise HistoryClientError(f"Health check failed with status code: {resp.status}")
        except urllib.error.URLError as e:
            logger.warning(f"History API health check failed: {e}")
            raise HistoryClientError(f"Cannot connect to History API at {self.base_url}: {e}") from e

    def get_resident(self, resident_ref: str) -> ResidentHistory:
        """
        Fetch full resident record including household and case events.
        Endpoints: GET /residents/<ref>
        """
        url = f"{self.base_url}/residents/{resident_ref}"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                
                household = [HouseholdMember(**h) for h in data.get("household", [])]
                events = [CaseEvent(**e) for e in data.get("events", [])]
                
                return ResidentHistory(
                    resident_ref=data["resident_ref"],
                    status=data.get("status", "Active"),
                    benefit_code=data.get("benefit_code", "UNKNOWN"),
                    district=data.get("district", "UNKNOWN"),
                    award_monthly=float(data.get("award_monthly", 0.0)),
                    household=household,
                    events=events
                )
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise ResidentNotFoundError(f"Resident record for reference '{resident_ref}' not found.") from e
            raise HistoryClientError(f"HTTP error {e.code} fetching resident '{resident_ref}': {e.reason}") from e
        except urllib.error.URLError as e:
            raise HistoryClientError(f"Network error contacting History API: {e}") from e
        except (json.JSONDecodeError, KeyError) as e:
            raise HistoryClientError(f"Malformed response for resident '{resident_ref}': {e}") from e
