import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest

from underwritekit.engine import RuleEngine
from underwritekit.models import LoanApplication

BASE = dict(
    loan_amount_cents=30000000,
    property_value_cents=40000000,
    monthly_income_cents=1000000,
    monthly_debt_cents=300000,
    monthly_housing_cents=200000,
    reserves_cents=4800000,
    credit_score=740,
    occupancy="primary",
    property_type="single_family",
    units=1,
)


def make_app(**overrides):
    fields = dict(BASE)
    fields.update(overrides)
    return LoanApplication(**fields)


@pytest.fixture(scope="session")
def engine():
    return RuleEngine()
