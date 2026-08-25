"""Engine behavior: reason trails, ordering, disabling, validation."""
import json

import pytest

from conftest import make_app

from underwritekit.engine import RuleEngine, floor_bps, load_rules
from underwritekit.models import LoanApplication


def test_approve_has_empty_reason_trail(engine):
    decision = engine.evaluate(make_app())
    assert decision.decision == "approve"
    assert decision.reasons == ()


def test_refer_reason_trail_is_complete(engine):
    app = make_app(
        loan_amount_cents=80000001,
        monthly_debt_cents=510000,
        reserves_cents=0,
        credit_score=619,
        occupancy="investment",
    )
    decision = engine.evaluate(app)
    assert decision.decision == "refer"
    assert sorted(decision.reason_codes) == [
        "CRD01", "CRD02", "DTI01", "LIM01", "LTV01", "RSV01",
    ]


def test_reason_trail_follows_evaluation_order(engine):
    app = make_app(
        loan_amount_cents=80000001,
        monthly_debt_cents=510000,
        reserves_cents=0,
        credit_score=619,
        occupancy="investment",
    )
    rule_ids = [r.rule_id for r in engine.evaluate(app).reasons]
    assert rule_ids == engine.order


def test_disabled_rule_is_skipped(engine):
    app = make_app(credit_score=619)
    assert engine.evaluate(app).decision == "refer"
    relaxed = engine.evaluate(app, disabled=frozenset(["credit_floor"]))
    assert relaxed.decision == "approve"


def test_decision_serializes_machine_readable(engine):
    decision = engine.evaluate(make_app(credit_score=619))
    payload = json.loads(json.dumps(decision.to_dict()))
    assert payload["decision"] == "refer"
    reason = payload["reasons"][0]
    assert set(reason) == {"rule_id", "reason_code", "observed", "threshold", "detail"}
    assert reason["observed"] == 619
    assert reason["threshold"] == 620


def test_ltv_reason_carries_bps_observed(engine):
    app = make_app(loan_amount_cents=39200000)  # 98 percent
    reasons = [r for r in engine.evaluate(app).reasons if r.rule_id == "ltv_cap"]
    assert reasons[0].observed == 9800
    assert reasons[0].threshold == 9700


def test_unknown_rule_in_order_raises():
    doc = load_rules()
    doc["evaluation_order"] = ["not_a_rule"]
    with pytest.raises(ValueError):
        RuleEngine(rules=doc)


def test_load_rules_default_path():
    doc = load_rules()
    assert doc["version"] == "1.0"
    assert "rules" in doc


def test_floor_bps_is_display_floor():
    assert floor_bps(1, 3) == 3333
    assert floor_bps(75, 100) == 7500


def test_effective_cap_uses_min_of_override(engine):
    app = make_app(property_type="manufactured")
    assert engine.effective_ltv_cap_bps(app) == 9500
    app2 = make_app(occupancy="investment", property_type="manufactured")
    assert engine.effective_ltv_cap_bps(app2) == 8500


@pytest.mark.parametrize(
    "overrides",
    [
        {"occupancy": "vacation"},
        {"property_type": "boat"},
        {"units": 0},
        {"units": 5},
        {"occupancy": "second_home", "units": 2},
        {"loan_amount_cents": 0},
        {"property_value_cents": 0},
        {"monthly_income_cents": 0},
        {"monthly_debt_cents": -1},
        {"reserves_cents": -5},
        {"credit_score": 299},
        {"credit_score": 851},
    ],
)
def test_invalid_applications_raise(engine, overrides):
    app = make_app(**overrides)
    with pytest.raises(ValueError):
        engine.evaluate(app)


def test_zero_housing_payment_satisfies_reserve_factor(engine):
    app = make_app(
        monthly_housing_cents=0,
        reserves_cents=0,
        monthly_debt_cents=400000,
        credit_score=700,
        loan_amount_cents=30400000,
    )
    codes = engine.evaluate(app).reason_codes
    assert "DTI02" not in codes
    assert "RSV01" not in codes
