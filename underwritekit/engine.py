"""Declarative eligibility rules engine.

The rule set lives in rules/rules.json as data. This module only supplies a
generic evaluator per rule id. Every threshold, cap, tier, and table comes
from the JSON document, so changing the rule set never requires code changes.

Exactness contract:
* Money is integer cents, ratios are basis points.
* A ratio check "ratio > cap_bps" is evaluated as the exact integer
  comparison numerator * 10000 > cap_bps * denominator. No floats anywhere.
* Boundary semantics are inclusive on the passing side: a value exactly at
  a cap, floor, limit, or requirement passes. Only strictly worse values fire.

Evaluation order is taken from the JSON evaluation_order list. All rules are
always evaluated (no short circuit) so the reason trail is complete: a refer
decision carries every rule that fired, not just the first one.
"""
import json
import os
from typing import Dict, FrozenSet, List, Optional

from .models import APPROVE, REFER, Decision, LoanApplication, Reason

DEFAULT_RULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules", "rules.json"
)

_EMPTY: FrozenSet[str] = frozenset()


def ratio_exceeds_bps(numerator_cents: int, denominator_cents: int, cap_bps: int) -> bool:
    """Exact test of numerator/denominator > cap_bps/10000 via cross multiplication."""
    return numerator_cents * 10000 > cap_bps * denominator_cents


def floor_bps(numerator_cents: int, denominator_cents: int) -> int:
    """Display only floor of a ratio in bps. Never used for rule comparisons."""
    return numerator_cents * 10000 // denominator_cents


def load_rules(path: Optional[str] = None) -> dict:
    with open(path or DEFAULT_RULES_PATH, "r") as fh:
        return json.load(fh)


class RuleEngine:
    def __init__(self, rules: Optional[dict] = None, rules_path: Optional[str] = None):
        self.rules_doc = rules if rules is not None else load_rules(rules_path)
        self.order: List[str] = list(self.rules_doc["evaluation_order"])
        self.rules: Dict[str, dict] = self.rules_doc["rules"]
        self._evaluators = {
            "loan_limit": self._eval_loan_limit,
            "ltv_cap": self._eval_ltv_cap,
            "credit_floor": self._eval_credit_floor,
            "credit_tier": self._eval_credit_tier,
            "dti": self._eval_dti,
            "reserves": self._eval_reserves,
        }
        for rule_id in self.order:
            if rule_id not in self._evaluators:
                raise ValueError("no evaluator for rule id %r" % rule_id)

    # rule evaluators ------------------------------------------------------

    def _eval_loan_limit(self, app: LoanApplication, cfg: dict) -> List[Reason]:
        limit = cfg["limits_cents"][str(app.units)]
        if app.loan_amount_cents > limit:
            return [
                Reason(
                    "loan_limit",
                    cfg["reason_code"],
                    app.loan_amount_cents,
                    limit,
                    "loan amount exceeds the %d unit limit" % app.units,
                )
            ]
        return []

    def effective_ltv_cap_bps(self, app: LoanApplication) -> int:
        cfg = self.rules["ltv_cap"]
        cap = cfg["caps_bps"][app.occupancy][str(app.units)]
        override = cfg["property_type_overrides_bps"].get(app.property_type)
        if override is not None:
            cap = min(cap, override)
        return cap

    def _eval_ltv_cap(self, app: LoanApplication, cfg: dict) -> List[Reason]:
        cap = self.effective_ltv_cap_bps(app)
        if ratio_exceeds_bps(app.loan_amount_cents, app.property_value_cents, cap):
            return [
                Reason(
                    "ltv_cap",
                    cfg["reason_code"],
                    floor_bps(app.loan_amount_cents, app.property_value_cents),
                    cap,
                    "LTV exceeds the %s %d unit cap" % (app.occupancy, app.units),
                )
            ]
        return []

    def _eval_credit_floor(self, app: LoanApplication, cfg: dict) -> List[Reason]:
        floor = cfg["min_score"]
        if app.credit_score < floor:
            return [
                Reason(
                    "credit_floor",
                    cfg["reason_code"],
                    app.credit_score,
                    floor,
                    "credit score below the program floor",
                )
            ]
        return []

    def _eval_credit_tier(self, app: LoanApplication, cfg: dict) -> List[Reason]:
        if app.credit_score < cfg["tier_score"] and ratio_exceeds_bps(
            app.loan_amount_cents, app.property_value_cents, cfg["tier_max_ltv_bps"]
        ):
            return [
                Reason(
                    "credit_tier",
                    cfg["reason_code"],
                    app.credit_score,
                    cfg["tier_score"],
                    "score below %d requires LTV at or below %d bps"
                    % (cfg["tier_score"], cfg["tier_max_ltv_bps"]),
                )
            ]
        return []

    def count_compensating_factors(self, app: LoanApplication) -> int:
        cfg = self.rules["dti"]["compensating_factors"]
        count = 0
        if app.credit_score >= cfg["high_credit"]["min_score"]:
            count += 1
        months = cfg["strong_reserves"]["min_months_housing"]
        if app.monthly_housing_cents == 0 or app.reserves_cents >= months * app.monthly_housing_cents:
            count += 1
        if not ratio_exceeds_bps(
            app.loan_amount_cents, app.property_value_cents, cfg["low_ltv"]["max_ltv_bps"]
        ):
            count += 1
        return count

    def _eval_dti(self, app: LoanApplication, cfg: dict) -> List[Reason]:
        debt = app.monthly_debt_cents
        income = app.monthly_income_cents
        observed = floor_bps(debt, income)
        if ratio_exceeds_bps(debt, income, cfg["hard_cap_bps"]):
            return [
                Reason(
                    "dti",
                    cfg["reason_code_hard"],
                    observed,
                    cfg["hard_cap_bps"],
                    "DTI above the hard cap, no compensating factors apply",
                )
            ]
        factors = self.count_compensating_factors(app)
        if ratio_exceeds_bps(debt, income, cfg["flex_max_bps"]):
            if factors < cfg["hard_required_factors"]:
                return [
                    Reason(
                        "dti",
                        cfg["reason_code_stretch"],
                        observed,
                        cfg["flex_max_bps"],
                        "DTI in the stretch band with %d of %d required compensating factors"
                        % (factors, cfg["hard_required_factors"]),
                    )
                ]
            return []
        if ratio_exceeds_bps(debt, income, cfg["base_max_bps"]):
            if factors < cfg["flex_required_factors"]:
                return [
                    Reason(
                        "dti",
                        cfg["reason_code_flex"],
                        observed,
                        cfg["base_max_bps"],
                        "DTI in the flex band with %d of %d required compensating factors"
                        % (factors, cfg["flex_required_factors"]),
                    )
                ]
        return []

    def _eval_reserves(self, app: LoanApplication, cfg: dict) -> List[Reason]:
        months = cfg["required_months"][app.occupancy][str(app.units)]
        required = months * app.monthly_housing_cents
        if app.reserves_cents < required:
            return [
                Reason(
                    "reserves",
                    cfg["reason_code"],
                    app.reserves_cents,
                    required,
                    "reserves below %d months of the housing payment" % months,
                )
            ]
        return []

    # public API -----------------------------------------------------------

    def evaluate(
        self, app: LoanApplication, disabled: FrozenSet[str] = _EMPTY
    ) -> Decision:
        """Evaluate one application. disabled is a set of rule ids to skip,
        used only by the mutation harness."""
        app.validate()
        reasons: List[Reason] = []
        for rule_id in self.order:
            if rule_id in disabled:
                continue
            reasons.extend(self._evaluators[rule_id](app, self.rules[rule_id]))
        return Decision(REFER if reasons else APPROVE, tuple(reasons))
