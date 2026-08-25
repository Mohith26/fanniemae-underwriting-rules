"""Throughput and latency benchmark for the rules engine.

Pre-generates the application list so generation cost is excluded, then
measures a bulk wall clock throughput pass and a separate per decision
latency pass with time.perf_counter_ns around each evaluate call. The
latency pass carries per call timer overhead, so throughput is reported
from the bulk pass, not from summed latencies.
"""
import time
from typing import Optional

from .engine import RuleEngine
from .generator import AppGenerator


def _percentile(sorted_values, pct: float):
    idx = min(len(sorted_values) - 1, int(len(sorted_values) * pct))
    return sorted_values[idx]


def run_bench(n: int, seed: int, engine: Optional[RuleEngine] = None) -> dict:
    engine = engine or RuleEngine()
    apps = list(AppGenerator(seed, engine.rules_doc).stream(n))

    for app in apps[: min(2000, n)]:  # warmup
        engine.evaluate(app)

    t0 = time.perf_counter()
    for app in apps:
        engine.evaluate(app)
    bulk_elapsed = time.perf_counter() - t0

    latencies_ns = []
    for app in apps:
        s = time.perf_counter_ns()
        engine.evaluate(app)
        latencies_ns.append(time.perf_counter_ns() - s)
    latencies_ns.sort()

    return {
        "applications": n,
        "seed": seed,
        "bulk_elapsed_seconds": round(bulk_elapsed, 4),
        "decisions_per_second": round(n / bulk_elapsed, 1),
        "latency_us": {
            "p50": round(_percentile(latencies_ns, 0.50) / 1000, 2),
            "p90": round(_percentile(latencies_ns, 0.90) / 1000, 2),
            "p99": round(_percentile(latencies_ns, 0.99) / 1000, 2),
            "max": round(latencies_ns[-1] / 1000, 2),
        },
    }
