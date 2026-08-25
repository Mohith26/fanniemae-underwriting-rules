"""Engine vs independent oracle agreement."""
import pytest

from underwritekit.models import LoanApplication
from underwritekit.mutation import load_golden_cases
from underwritekit.oracle import oracle_decide
from underwritekit.parity import run_parity

GOLDEN = load_golden_cases()


def test_parity_zero_mismatches_on_20k_sample():
    report = run_parity(20000, seed=99)
    assert report["mismatches"] == 0
    assert report["applications"] == 20000


def test_parity_report_shape():
    report = run_parity(500, seed=7)
    assert set(report) == {
        "applications", "seed", "mismatches", "mismatch_examples", "elapsed_seconds",
    }
    assert report["mismatch_examples"] == []


@pytest.mark.parametrize("case", GOLDEN, ids=[c["name"] for c in GOLDEN])
def test_oracle_agrees_with_golden_expectations(case):
    decision, codes = oracle_decide(LoanApplication(**case["app"]))
    assert decision == case["expected_decision"]
    assert codes == sorted(case["expected_codes"])


def test_parity_detects_a_seeded_divergence():
    # Tighten the credit floor in a copy of the rules. The oracle still uses
    # the documented 620 floor, so the harness must record real mismatches.
    from underwritekit.engine import RuleEngine, load_rules

    doc = load_rules()
    doc["rules"]["credit_floor"]["min_score"] = 700
    report = run_parity(3000, seed=99, engine=RuleEngine(rules=doc))
    assert report["mismatches"] > 0
    example = report["mismatch_examples"][0]
    assert example["engine"]["codes"] != example["oracle"]["codes"]
