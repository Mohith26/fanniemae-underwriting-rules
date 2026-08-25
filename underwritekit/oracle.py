"""Independent oracle for the rules engine.

This is a deliberately naive reimplementation of the documented rule set.
It does NOT read rules/rules.json and it does not share any code with the
engine. Every constant is hardcoded from the written spec and every ratio
is an exact fractions.Fraction, so agreement with the engine's integer
cross multiplication arithmetic is meaningful evidence, not shared bugs.
"""
from fractions import Fraction
from typing import List, Tuple

from .models import LoanApplication

_LIMITS_CENTS = {1: 80000000, 2: 102400000, 3: 123800000, 4: 153800000}

_LTV_CAPS = {
    ("primary", 1): Fraction(9700, 10000),
    ("primary", 2): Fraction(8500, 10000),
    ("primary", 3): Fraction(7500, 10000),
    ("primary", 4): Fraction(7500, 10000),
    ("second_home", 1): Fraction(9000, 10000),
    ("investment", 1): Fraction(8500, 10000),
    ("investment", 2): Fraction(7500, 10000),
    ("investment", 3): Fraction(7500, 10000),
    ("investment", 4): Fraction(7500, 10000),
}

_MANUFACTURED_CAP = Fraction(9500, 10000)

_RESERVE_MONTHS = {
    ("primary", 1): 0,
    ("primary", 2): 6,
    ("primary", 3): 6,
    ("primary", 4): 6,
    ("second_home", 1): 2,
    ("investment", 1): 6,
    ("investment", 2): 6,
    ("investment", 3): 6,
    ("investment", 4): 6,
}


def oracle_decide(app: LoanApplication) -> Tuple[str, List[str]]:
    """Return (decision, sorted reason codes) for one application."""
    codes: List[str] = []

    if app.loan_amount_cents > _LIMITS_CENTS[app.units]:
        codes.append("LIM01")

    ltv = Fraction(app.loan_amount_cents, app.property_value_cents)
    cap = _LTV_CAPS[(app.occupancy, app.units)]
    if app.property_type == "manufactured" and _MANUFACTURED_CAP < cap:
        cap = _MANUFACTURED_CAP
    if ltv > cap:
        codes.append("LTV01")

    if app.credit_score < 620:
        codes.append("CRD01")

    if app.credit_score < 660 and ltv > Fraction(75, 100):
        codes.append("CRD02")

    dti = Fraction(app.monthly_debt_cents, app.monthly_income_cents)
    factors = 0
    if app.credit_score >= 720:
        factors += 1
    if app.monthly_housing_cents == 0 or app.reserves_cents >= 6 * app.monthly_housing_cents:
        factors += 1
    if ltv <= Fraction(75, 100):
        factors += 1
    if dti > Fraction(50, 100):
        codes.append("DTI01")
    elif dti > Fraction(45, 100):
        if factors < 2:
            codes.append("DTI03")
    elif dti > Fraction(36, 100):
        if factors < 1:
            codes.append("DTI02")

    required = _RESERVE_MONTHS[(app.occupancy, app.units)] * app.monthly_housing_cents
    if app.reserves_cents < required:
        codes.append("RSV01")

    return ("refer" if codes else "approve", sorted(codes))
