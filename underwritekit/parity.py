"""Oracle parity harness: engine vs independent oracle over seeded apps.

A mismatch is any application where the engine and the oracle disagree on
the decision OR on the sorted set of reason codes. Comparing the full code
set is deliberately stricter than comparing approve/refer alone.
"""
import time
from typing import Optional

from .engine import RuleEngine
from .generator import AppGenerator
from .oracle import oracle_decide


def run_parity(n: int, seed: int, engine: Optional[RuleEngine] = None) -> dict:
    engine = engine or RuleEngine()
    gen = AppGenerator(seed, engine.rules_doc)
    mismatches = 0
    examples = []
    t0 = time.perf_counter()
    for app in gen.stream(n):
        decision = engine.evaluate(app)
        engine_codes = sorted(decision.reason_codes)
        oracle_decision, oracle_codes = oracle_decide(app)
        if decision.decision != oracle_decision or engine_codes != oracle_codes:
            mismatches += 1
            if len(examples) < 10:
                examples.append(
                    {
                        "app": app.to_dict(),
                        "engine": {"decision": decision.decision, "codes": engine_codes},
                        "oracle": {"decision": oracle_decision, "codes": oracle_codes},
                    }
                )
    elapsed = time.perf_counter() - t0
    return {
        "applications": n,
        "seed": seed,
        "mismatches": mismatches,
        "mismatch_examples": examples,
        "elapsed_seconds": round(elapsed, 3),
    }
