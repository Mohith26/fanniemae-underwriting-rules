"""Run decision analytics over a seeded population, write results/analytics.json."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from underwritekit.analytics import run_analytics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500000)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--out", default="results/analytics.json")
    args = ap.parse_args()
    report = run_analytics(args.n, args.seed)
    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
