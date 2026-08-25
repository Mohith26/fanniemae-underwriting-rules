"""Decision analytics over a seeded population.

Approval rates by segment plus a reason code frequency table. DTI band
edges use the same exact cross multiplication as the rules so a boundary
application lands in the band its decision was made in.
"""
from collections import Counter, defaultdict
from typing import Optional

from .engine import RuleEngine, ratio_exceeds_bps
from .generator import AppGenerator


def credit_band(score: int) -> str:
    if score < 620:
        return "under_620"
    if score < 660:
        return "620_659"
    if score < 720:
        return "660_719"
    return "720_plus"


def dti_band(debt: int, income: int) -> str:
    if not ratio_exceeds_bps(debt, income, 3600):
        return "le_36"
    if not ratio_exceeds_bps(debt, income, 4500):
        return "36_45"
    if not ratio_exceeds_bps(debt, income, 5000):
        return "45_50"
    return "over_50"


def _rate_table(counts) -> dict:
    return {
        key: {
            "applications": total,
            "approved": approved,
            "approval_rate": round(approved / total, 4),
        }
        for key, (approved, total) in sorted(counts.items())
    }


def run_analytics(n: int, seed: int, engine: Optional[RuleEngine] = None) -> dict:
    engine = engine or RuleEngine()
    gen = AppGenerator(seed, engine.rules_doc)
    approved = 0
    reason_counts = Counter()
    segments = {
        "occupancy": defaultdict(lambda: [0, 0]),
        "units": defaultdict(lambda: [0, 0]),
        "credit_band": defaultdict(lambda: [0, 0]),
        "dti_band": defaultdict(lambda: [0, 0]),
    }
    for app in gen.stream(n):
        decision = engine.evaluate(app)
        is_approved = decision.decision == "approve"
        approved += is_approved
        for code in decision.reason_codes:
            reason_counts[code] += 1
        keys = {
            "occupancy": app.occupancy,
            "units": str(app.units),
            "credit_band": credit_band(app.credit_score),
            "dti_band": dti_band(app.monthly_debt_cents, app.monthly_income_cents),
        }
        for segment, key in keys.items():
            cell = segments[segment][key]
            cell[0] += is_approved
            cell[1] += 1
    return {
        "applications": n,
        "seed": seed,
        "approved": approved,
        "overall_approval_rate": round(approved / n, 4),
        "approval_by_segment": {name: _rate_table(vals) for name, vals in segments.items()},
        "reason_code_frequency": dict(reason_counts.most_common()),
    }
