"""Benchmark decisions per second and latency percentiles, write results/bench.json."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from underwritekit.bench import run_bench


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="results/bench.json")
    args = ap.parse_args()
    report = run_bench(args.n, args.seed)
    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
