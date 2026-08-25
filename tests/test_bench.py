"""Smoke checks for the benchmark harness."""
from underwritekit.bench import run_bench


def test_bench_report_is_sane():
    report = run_bench(3000, seed=3)
    assert report["applications"] == 3000
    assert report["decisions_per_second"] > 0
    lat = report["latency_us"]
    assert lat["p50"] <= lat["p90"] <= lat["p99"] <= lat["max"]
