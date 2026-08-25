"""Rule liveness: disabling any rule must flip at least one golden case."""
import pytest

from underwritekit.engine import RuleEngine
from underwritekit.models import LoanApplication
from underwritekit.mutation import (
    check_golden_baseline,
    load_golden_cases,
    run_mutation_matrix,
)

MATRIX = run_mutation_matrix()
RULE_IDS = sorted(MATRIX["rules"])


def test_all_golden_baselines_hold():
    assert MATRIX["baseline_failures"] == []


def test_matrix_covers_every_rule():
    assert RULE_IDS == sorted(RuleEngine().order)


@pytest.mark.parametrize("rule_id", RULE_IDS)
def test_each_rule_is_live(rule_id):
    entry = MATRIX["rules"][rule_id]
    assert entry["live"], "rule %s flipped no golden case" % rule_id
    assert len(entry["flipped_cases"]) >= 1


def test_overall_liveness_flag():
    assert MATRIX["all_rules_live"] is True


def test_baseline_checker_catches_wrong_expectation():
    engine = RuleEngine()
    cases = load_golden_cases()
    bad = dict(cases[0])
    bad["expected_decision"] = "refer"
    bad["expected_codes"] = ["LIM01"]
    failures = check_golden_baseline(engine, [bad])
    assert len(failures) == 1
    assert failures[0]["name"] == bad["name"]


def test_golden_cases_all_evaluate(engine):
    for case in load_golden_cases():
        decision = engine.evaluate(LoanApplication(**case["app"]))
        assert decision.decision in ("approve", "refer")
