# UnderwriteKit

I wanted to understand what actually sits inside an automated underwriting system, so I built one: a small eligibility rules engine that takes a loan application and returns approve or refer with a complete, machine readable trail of every rule that fired. The interesting part was not writing the rules. It was proving that every rule does exactly what the documentation says at every boundary, and that none of them are dead code.

To be clear up front: the rule set is invented. The thresholds are realistic in shape (LTV caps by occupancy and unit count, DTI bands with compensating factors, credit tiers, reserve requirements, loan limits) but they are illustrative numbers I wrote for this project. They are not the actual guidelines of any agency, investor, or lender, and nothing here should be read as a statement about how any real underwriting system decides.

## How a decision happens

An application is ten fields: loan amount, property value, income, monthly debt, housing payment, reserves (all integer cents), credit score, occupancy, property type, and unit count. The engine loads `rules/rules.json`, walks the rules in the declared evaluation order, and always evaluates every rule with no short circuiting. Any rule that fires appends a reason with a code, the observed value, and the threshold it broke. Zero reasons means approve, otherwise refer with the full trail.

The rules are data, not code. Every cap, tier, table, and limit lives in the JSON document, and the engine only supplies one generic evaluator per rule id. Changing the rule set means editing JSON, not Python.

Arithmetic is exact. Money is integer cents, ratios are basis points, and a check like "LTV above 97 percent" is evaluated as `loan * 10000 > 9700 * value`, an integer cross multiplication with no floats and no rounding anywhere in the decision path. Boundary semantics are inclusive on the passing side and documented in the JSON itself: a DTI of exactly 36.00 percent passes the base band, a score of exactly 620 clears the floor, reserves exactly at the requirement pass, and one cent or one point worse fires the rule.

## The rule set, briefly

* Loan limits by unit count (1 to 4 units).
* LTV caps by occupancy and units, with a property type override (manufactured homes cap lower); the effective cap is the minimum.
* A hard credit floor at 620, plus a tier rule: scores under 660 are only eligible at or below 75 percent LTV.
* DTI in three bands: at or under 36 percent always passes, 36 to 45 needs one compensating factor, 45 to 50 needs two, above 50 always fires. The factors are a 720 plus score, six months of housing payment in reserves, or LTV at or under 75 percent.
* Reserve requirements in months of housing payment by occupancy and units.

Reason codes are LIM01, LTV01, CRD01, CRD02, DTI01, DTI02, DTI03, and RSV01.

## How I convinced myself it is correct

Three independent legs, because any one of them alone can lie to you.

**A boundary matrix.** Every documented boundary is tested on both sides: the exact boundary value must pass and the value one cent, one basis point, or one score point worse must fire. That is 13 LTV cap combinations, all four loan limits, both credit rules, all three DTI bands, all three compensating factor edges, and six reserve requirements, each exercised from both directions.

**An independent oracle.** A second, deliberately naive implementation of the same written spec that shares no code with the engine, never reads the JSON, and uses exact `fractions.Fraction` arithmetic instead of integer cross multiplication. I ran engine and oracle over 500,000 seeded synthetic applications from a boundary hostile generator (a slice of every draw snaps ratios, scores, and reserves onto exact boundaries and one unit past them) and compared not just the decision but the full sorted reason code set: 0 mismatches. There is also a test that deliberately tightens one threshold in a copy of the rules and asserts the harness reports the divergence, so I know the parity check can actually fail.

**A rule liveness matrix.** A mutation harness disables each of the six rules in turn and re-evaluates a committed set of golden applications, each hand built so exactly one rule fires. Every rule, when disabled, flips at least one golden decision from refer to approve. That proves no rule is silently dead, which is the failure mode declarative rule systems are best at hiding.

On top of that there is a decision analytics pass over the same seeded population (approval rate by occupancy, units, credit band, and DTI band, plus a reason code frequency table) committed under `results/`, and a benchmark that measures bulk throughput and per decision latency percentiles.

## Running it

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest                       # 136 tests
.venv/bin/python scripts/run_parity.py --n 500000 --seed 1337
.venv/bin/python scripts/run_mutation.py
.venv/bin/python scripts/run_analytics.py --n 500000 --seed 1337
.venv/bin/python scripts/run_bench.py --n 200000 --seed 42
```

Measured numbers and the exact commands behind them are in RESULTS.md.

## Limitations

The rule set is illustrative, not real agency guidance, and it is far smaller than a production underwriting matrix: no income documentation logic, no credit event seasoning, no ARM or property specific overlays, no pricing. Applications are synthetic and the generator's population is deliberately stress shaped toward rule boundaries, so the committed approval rates describe this population only and say nothing about any real origination mix. The oracle proves the engine matches the written spec, not that the spec itself is sensible. Reason observed values for ratios are floored to basis points for display, which is documented and kept out of the decision path. Everything is single threaded pure Python, and the throughput and latency numbers are specific to the machine noted in RESULTS.md. There is no UI, no persistence, and no service wrapper: this is a library plus harnesses on purpose.
