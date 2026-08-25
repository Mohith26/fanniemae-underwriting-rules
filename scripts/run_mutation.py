"""Run the rule liveness matrix and write results/mutation_matrix.json."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from underwritekit.mutation import run_mutation_matrix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/mutation_matrix.json")
    args = ap.parse_args()
    report = run_mutation_matrix()
    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
