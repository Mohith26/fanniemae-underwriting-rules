"""Exhaustive decision table boundary matrix.

Every documented rule boundary is exercised on both sides: the exact
boundary value must pass and the first strictly worse value must fire.
The baseline application in conftest passes every rule with margin, so
each case isolates the code under test via presence/absence assertions.
"""
import pytest

from conftest import make_app

VALUE = 40000000  # divisible by 10000 so cap bps map to exact cent amounts

LTV_COMBOS = [
    ("primary", 1, "single_family", 9700),
    ("primary", 2, "single_family", 8500),
    ("primary", 3, "single_family", 7500),
    ("primary", 4, "single_family", 7500),
    ("primary", 1, "condo", 9700),
    ("primary", 1, "manufactured", 9500),
    ("second_home", 1, "single_family", 9000),
    ("second_home", 1, "manufactured", 9000),
    ("investment", 1, "single_family", 8500),
    ("investment", 1, "manufactured", 8500),
    ("investment", 2, "single_family", 7500),
    ("investment", 3, "single_family", 7500),
    ("investment", 4, "single_family", 7500),
]


@pytest.mark.parametrize("occupancy,units,ptype,cap_bps", LTV_COMBOS)
def test_ltv_at_cap_passes(engine, occupancy, units, ptype, cap_bps):
    loan = VALUE * cap_bps // 10000
    app = make_app(
        loan_amount_cents=loan, occupancy=occupancy, units=units, property_type=ptype
    )
    assert "LTV01" not in engine.evaluate(app).reason_codes


@pytest.mark.parametrize("occupancy,units,ptype,cap_bps", LTV_COMBOS)
def test_ltv_one_cent_over_cap_fires(engine, occupancy, units, ptype, cap_bps):
    loan = VALUE * cap_bps // 10000 + 1
    app = make_app(
        loan_amount_cents=loan, occupancy=occupancy, units=units, property_type=ptype
    )
    assert "LTV01" in engine.evaluate(app).reason_codes


LIMITS = [(1, 80000000), (2, 102400000), (3, 123800000), (4, 153800000)]


@pytest.mark.parametrize("units,limit", LIMITS)
def test_loan_at_limit_passes(engine, units, limit):
    app = make_app(loan_amount_cents=limit, property_value_cents=400000000, units=units)
    assert "LIM01" not in engine.evaluate(app).reason_codes


@pytest.mark.parametrize("units,limit", LIMITS)
def test_loan_one_cent_over_limit_fires(engine, units, limit):
    app = make_app(
        loan_amount_cents=limit + 1, property_value_cents=400000000, units=units
    )
    assert "LIM01" in engine.evaluate(app).reason_codes


def test_credit_score_at_floor_passes(engine):
    assert "CRD01" not in engine.evaluate(make_app(credit_score=620)).reason_codes


def test_credit_score_below_floor_fires(engine):
    assert "CRD01" in engine.evaluate(make_app(credit_score=619)).reason_codes


def test_credit_tier_low_score_at_75_ltv_passes(engine):
    app = make_app(credit_score=659, loan_amount_cents=30000000)
    assert "CRD02" not in engine.evaluate(app).reason_codes


def test_credit_tier_low_score_over_75_ltv_fires(engine):
    app = make_app(credit_score=659, loan_amount_cents=30000001)
    assert "CRD02" in engine.evaluate(app).reason_codes


def test_credit_tier_at_tier_score_over_75_ltv_passes(engine):
    app = make_app(credit_score=660, loan_amount_cents=30400000)
    assert "CRD02" not in engine.evaluate(app).reason_codes


# DTI band boundaries. no_factor kwargs remove every compensating factor:
# score 700 (below 720), reserves five months (below six), LTV 76 percent.
NO_FACTORS = dict(
    credit_score=700, reserves_cents=1000000, loan_amount_cents=30400000
)


def test_dti_at_base_max_no_factors_passes(engine):
    app = make_app(monthly_debt_cents=360000, **NO_FACTORS)
    codes = engine.evaluate(app).reason_codes
    assert not any(c.startswith("DTI") for c in codes)


def test_dti_just_over_base_no_factors_fires_flex(engine):
    app = make_app(monthly_debt_cents=360001, **NO_FACTORS)
    assert "DTI02" in engine.evaluate(app).reason_codes


def test_dti_just_over_base_one_factor_passes(engine):
    kwargs = dict(NO_FACTORS, credit_score=720)
    app = make_app(monthly_debt_cents=360001, **kwargs)
    codes = engine.evaluate(app).reason_codes
    assert not any(c.startswith("DTI") for c in codes)


def test_dti_at_flex_max_one_factor_passes(engine):
    kwargs = dict(NO_FACTORS, credit_score=720)
    app = make_app(monthly_debt_cents=450000, **kwargs)
    codes = engine.evaluate(app).reason_codes
    assert not any(c.startswith("DTI") for c in codes)


def test_dti_just_over_flex_one_factor_fires_stretch(engine):
    kwargs = dict(NO_FACTORS, credit_score=720)
    app = make_app(monthly_debt_cents=450001, **kwargs)
    assert "DTI03" in engine.evaluate(app).reason_codes


def test_dti_just_over_flex_two_factors_passes(engine):
    kwargs = dict(NO_FACTORS, credit_score=720, reserves_cents=1200000)
    app = make_app(monthly_debt_cents=450001, **kwargs)
    codes = engine.evaluate(app).reason_codes
    assert not any(c.startswith("DTI") for c in codes)


def test_dti_at_hard_cap_two_factors_passes(engine):
    kwargs = dict(NO_FACTORS, credit_score=720, reserves_cents=1200000)
    app = make_app(monthly_debt_cents=500000, **kwargs)
    codes = engine.evaluate(app).reason_codes
    assert not any(c.startswith("DTI") for c in codes)


def test_dti_just_over_hard_cap_all_factors_fires(engine):
    app = make_app(
        monthly_debt_cents=500001,
        credit_score=740,
        reserves_cents=4800000,
        loan_amount_cents=30000000,
    )
    assert "DTI01" in engine.evaluate(app).reason_codes


def test_factor_high_credit_at_720_counts(engine):
    kwargs = dict(NO_FACTORS, credit_score=720)
    app = make_app(monthly_debt_cents=400000, **kwargs)
    assert "DTI02" not in engine.evaluate(app).reason_codes


def test_factor_high_credit_719_does_not_count(engine):
    kwargs = dict(NO_FACTORS, credit_score=719)
    app = make_app(monthly_debt_cents=400000, **kwargs)
    assert "DTI02" in engine.evaluate(app).reason_codes


def test_factor_reserves_exactly_six_months_counts(engine):
    kwargs = dict(NO_FACTORS, reserves_cents=1200000)
    app = make_app(monthly_debt_cents=400000, **kwargs)
    assert "DTI02" not in engine.evaluate(app).reason_codes


def test_factor_reserves_one_cent_short_does_not_count(engine):
    kwargs = dict(NO_FACTORS, reserves_cents=1199999)
    app = make_app(monthly_debt_cents=400000, **kwargs)
    assert "DTI02" in engine.evaluate(app).reason_codes


def test_factor_low_ltv_at_75_counts(engine):
    kwargs = dict(NO_FACTORS, loan_amount_cents=30000000)
    app = make_app(monthly_debt_cents=400000, **kwargs)
    assert "DTI02" not in engine.evaluate(app).reason_codes


def test_factor_low_ltv_one_cent_over_does_not_count(engine):
    kwargs = dict(NO_FACTORS, loan_amount_cents=30000001)
    app = make_app(monthly_debt_cents=400000, **kwargs)
    assert "DTI02" in engine.evaluate(app).reason_codes


RESERVE_COMBOS = [
    ("primary", 2, 6),
    ("primary", 3, 6),
    ("primary", 4, 6),
    ("second_home", 1, 2),
    ("investment", 1, 6),
    ("investment", 2, 6),
]


@pytest.mark.parametrize("occupancy,units,months", RESERVE_COMBOS)
def test_reserves_exactly_required_pass(engine, occupancy, units, months):
    app = make_app(
        occupancy=occupancy, units=units, reserves_cents=months * 200000
    )
    assert "RSV01" not in engine.evaluate(app).reason_codes


@pytest.mark.parametrize("occupancy,units,months", RESERVE_COMBOS)
def test_reserves_one_cent_short_fire(engine, occupancy, units, months):
    app = make_app(
        occupancy=occupancy, units=units, reserves_cents=months * 200000 - 1
    )
    assert "RSV01" in engine.evaluate(app).reason_codes


def test_primary_one_unit_needs_zero_reserves(engine):
    app = make_app(reserves_cents=0)
    assert "RSV01" not in engine.evaluate(app).reason_codes
