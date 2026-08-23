import pytest
from app.policy import PolicyEngine
from app.models import PolicyDecisionEnum


def test_allowed_action():
    engine = PolicyEngine()
    res = engine.evaluate("Record change of address")
    assert res.decision == PolicyDecisionEnum.ALLOWED
    assert res.policy_section in ["2.1 / 2.5", "2.1", "2.5"]


def test_approval_required_action():
    engine = PolicyEngine()
    res = engine.evaluate("Update payment details")
    assert res.decision == PolicyDecisionEnum.APPROVAL_REQUIRED
    assert res.policy_section == "3.4"


def test_denied_action():
    engine = PolicyEngine()
    res = engine.evaluate("Suspend assistance pending investigation")
    assert res.decision == PolicyDecisionEnum.DENIED
    assert "3.2" in res.policy_section or "3.7" in res.policy_section or "4.1" in res.policy_section


def test_unknown_action_defaults_to_rule_6_1():
    engine = PolicyEngine()
    res = engine.evaluate("Unknown custom action request")
    assert res.decision == PolicyDecisionEnum.APPROVAL_REQUIRED
    assert res.policy_section == "6.1"
