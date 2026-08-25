"""Seeded synthetic loan application generator.

Deterministic for a given seed. The sampler is boundary hostile on purpose:
a slice of every draw snaps ratios, scores, and reserves to exact rule
boundaries and to one unit past them, so the oracle parity run keeps
hammering the inclusive/exclusive edges instead of only easy interior points.

The generator may read the rule document to find boundary values to aim at.
That is a sampling concern only: the oracle never reads the rules, so parity
between engine and oracle is still an independent check.
"""
import random
from typing import Iterator, Optional

from .engine import load_rules
from .models import LoanApplication


class AppGenerator:
    def __init__(self, seed: int, rules: Optional[dict] = None):
        self.rng = random.Random(seed)
        self.rules = rules if rules is not None else load_rules()

    def _pick_occupancy_units(self):
        r = self.rng.random()
        if r < 0.70:
            occupancy = "primary"
        elif r < 0.80:
            occupancy = "second_home"
        else:
            occupancy = "investment"
        if occupancy == "second_home":
            units = 1
        else:
            u = self.rng.random()
            if u < 0.80:
                units = 1
            elif u < 0.90:
                units = 2
            elif u < 0.95:
                units = 3
            else:
                units = 4
        return occupancy, units

    def _pick_property_type(self, units: int) -> str:
        r = self.rng.random()
        if r < 0.75:
            return "single_family"
        if r < 0.95 or units > 1:
            return "condo"
        return "manufactured"

    def _effective_cap_bps(self, occupancy: str, property_type: str, units: int) -> int:
        cfg = self.rules["rules"]["ltv_cap"]
        cap = cfg["caps_bps"][occupancy][str(units)]
        override = cfg["property_type_overrides_bps"].get(property_type)
        if override is not None:
            cap = min(cap, override)
        return cap

    def _amount_for_bps(self, base_cents: int, bps: int, exceed: bool) -> int:
        """Largest numerator with numerator/base <= bps/10000, or the first
        numerator strictly above the boundary when exceed is True."""
        at = base_cents * bps // 10000
        return at + 1 if exceed else at

    def generate(self) -> LoanApplication:
        rng = self.rng
        occupancy, units = self._pick_occupancy_units()
        property_type = self._pick_property_type(units)
        if property_type == "manufactured":
            units = 1

        value = rng.randrange(10_000_000, 250_000_001)  # 100k to 2.5M dollars

        cap_bps = self._effective_cap_bps(occupancy, property_type, units)
        mode = rng.random()
        if mode < 0.06:
            loan = self._amount_for_bps(value, cap_bps, exceed=False)
        elif mode < 0.12:
            loan = self._amount_for_bps(value, cap_bps, exceed=True)
        elif mode < 0.16:
            loan = self._amount_for_bps(value, 7500, exceed=rng.random() < 0.5)
        else:
            loan = value * rng.randrange(3000, 10501) // 10000
        loan = max(loan, 1)
        if rng.random() < 0.10:
            limit = self.rules["rules"]["loan_limit"]["limits_cents"][str(units)]
            loan = limit + (1 if rng.random() < 0.5 else 0)

        income = rng.randrange(300_000, 3_000_001)
        mode = rng.random()
        if mode < 0.15:
            bps = rng.choice([3600, 4500, 5000])
            debt = self._amount_for_bps(income, bps, exceed=rng.random() < 0.5)
        else:
            debt = income * rng.randrange(1000, 6501) // 10000

        housing = rng.randrange(50_000, 500_001)
        mode = rng.random()
        if mode < 0.10:
            reserves = 6 * housing - (1 if rng.random() < 0.5 else 0)
        elif mode < 0.16:
            months = self.rules["rules"]["reserves"]["required_months"][occupancy][str(units)]
            reserves = months * housing - (1 if months > 0 and rng.random() < 0.5 else 0)
        else:
            reserves = rng.randrange(0, 24 * housing + 1)

        if self.rng.random() < 0.12:
            score = rng.choice([619, 620, 659, 660, 719, 720])
        else:
            score = rng.randrange(560, 831)

        return LoanApplication(
            loan_amount_cents=loan,
            property_value_cents=value,
            monthly_income_cents=income,
            monthly_debt_cents=debt,
            monthly_housing_cents=housing,
            reserves_cents=reserves,
            credit_score=score,
            occupancy=occupancy,
            property_type=property_type,
            units=units,
        )

    def stream(self, n: int) -> Iterator[LoanApplication]:
        for _ in range(n):
            yield self.generate()
