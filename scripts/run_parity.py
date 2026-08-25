"""Run the engine vs oracle parity check and write results/oracle_check.json."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from underwritekit.parity import run_parity


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500000)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--out", default="results/oracle_check.json")
    args = ap.parse_args()
    report = run_parity(args.n, args.seed)
    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
