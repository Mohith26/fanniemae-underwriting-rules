"""Rule liveness harness.

Disables each rule id in turn and re-evaluates a committed set of golden
applications. A rule is live when disabling it flips the decision of at
least one golden case. Every rule must be live, otherwise the rule is dead
weight and the harness fails.
"""
import json
import os
from typing import List, Optional

from .engine import RuleEngine
from .models import LoanApplication

DEFAULT_GOLDEN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "golden_cases.json"
)


def load_golden_cases(path: Optional[str] = None) -> List[dict]:
    with open(path or DEFAULT_GOLDEN_PATH, "r") as fh:
        return json.load(fh)["cases"]


def check_golden_baseline(engine: RuleEngine, cases: List[dict]) -> List[dict]:
    """Verify each golden case has its expected baseline decision and codes."""
    failures = []
    for case in cases:
        app = LoanApplication(**case["app"])
        decision = engine.evaluate(app)
        if (
            decision.decision != case["expected_decision"]
            or sorted(decision.reason_codes) != sorted(case["expected_codes"])
        ):
            failures.append(
                {
                    "name": case["name"],
                    "expected": [case["expected_decision"], sorted(case["expected_codes"])],
                    "got": [decision.decision, sorted(decision.reason_codes)],
                }
            )
    return failures


def run_mutation_matrix(
    engine: Optional[RuleEngine] = None, golden_path: Optional[str] = None
) -> dict:
    engine = engine or RuleEngine()
    cases = load_golden_cases(golden_path)
    baseline_failures = check_golden_baseline(engine, cases)
    matrix = {}
    for rule_id in engine.order:
        flipped = []
        for case in cases:
            app = LoanApplication(**case["app"])
            base = engine.evaluate(app).decision
            mutated = engine.evaluate(app, disabled=frozenset([rule_id])).decision
            if base != mutated:
                flipped.append(case["name"])
        matrix[rule_id] = {"flipped_cases": flipped, "live": len(flipped) > 0}
    return {
        "golden_cases": len(cases),
        "baseline_failures": baseline_failures,
        "rules": matrix,
        "all_rules_live": all(v["live"] for v in matrix.values()) and not baseline_failures,
    }
