"""Core data types for the underwriting rules engine.

All money is integer cents. All ratios are basis points (bps).
"""
from dataclasses import dataclass, field, asdict
from typing import Tuple

OCCUPANCIES = ("primary", "second_home", "investment")
PROPERTY_TYPES = ("single_family", "condo", "manufactured")

APPROVE = "approve"
REFER = "refer"


@dataclass(frozen=True)
class LoanApplication:
    """A synthetic loan application.

    monthly_debt_cents is the total monthly obligation figure used for DTI,
    inclusive of the proposed housing payment. monthly_housing_cents is the
    proposed monthly housing payment used for reserve requirements.
    """

    loan_amount_cents: int
    property_value_cents: int
    monthly_income_cents: int
    monthly_debt_cents: int
    monthly_housing_cents: int
    reserves_cents: int
    credit_score: int
    occupancy: str
    property_type: str
    units: int

    def validate(self) -> None:
        if self.occupancy not in OCCUPANCIES:
            raise ValueError("unknown occupancy: %r" % (self.occupancy,))
        if self.property_type not in PROPERTY_TYPES:
            raise ValueError("unknown property_type: %r" % (self.property_type,))
        if not 1 <= self.units <= 4:
            raise ValueError("units must be 1..4, got %r" % (self.units,))
        if self.occupancy == "second_home" and self.units != 1:
            raise ValueError("second_home applications must be 1 unit")
        if self.loan_amount_cents <= 0:
            raise ValueError("loan_amount_cents must be positive")
        if self.property_value_cents <= 0:
            raise ValueError("property_value_cents must be positive")
        if self.monthly_income_cents <= 0:
            raise ValueError("monthly_income_cents must be positive")
        for name in ("monthly_debt_cents", "monthly_housing_cents", "reserves_cents"):
            if getattr(self, name) < 0:
                raise ValueError("%s must be non negative" % name)
        if not 300 <= self.credit_score <= 850:
            raise ValueError("credit_score must be 300..850")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Reason:
    """One firing rule, machine readable.

    observed and threshold are in the native unit of the rule:
    bps for ratio rules, points for score rules, cents for money rules.
    """

    rule_id: str
    reason_code: str
    observed: int
    threshold: int
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Decision:
    decision: str
    reasons: Tuple[Reason, ...] = field(default_factory=tuple)

    @property
    def reason_codes(self) -> Tuple[str, ...]:
        return tuple(r.reason_code for r in self.reasons)

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "reasons": [r.to_dict() for r in self.reasons],
        }
