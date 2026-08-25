# Results

My notes from the validation and benchmark runs behind the committed `results/*.json` files. Machine: Apple silicon MacBook, macOS 26.4.1, Python 3.9.6, single thread, pure Python. Numbers on another machine will differ, the correctness results will not.

## Oracle parity

Command:

```
.venv/bin/python scripts/run_parity.py --n 500000 --seed 1337
```

500,000 seeded applications, engine vs the independent Fraction based oracle, comparing decision plus the full sorted reason code set per application.

* Mismatches: 0 of 500,000
* Wall time for the full compare loop (generation + both implementations): 5.609 s

Output committed as `results/oracle_check.json`. The generator is boundary hostile (roughly a quarter of draws snap some field onto an exact boundary or one unit past it), so this is not 500k easy interior points. A negative control in `tests/test_oracle_parity.py` tightens the credit floor in a copy of the rules and confirms the harness reports mismatches when the implementations genuinely diverge.

## Rule liveness (mutation matrix)

Command:

```
.venv/bin/python scripts/run_mutation.py
```

Each of the 6 rules disabled in turn against 12 committed golden cases. Every rule flipped at least one golden decision, so all 6 are live:

| rule disabled | golden cases flipped |
|---|---|
| loan_limit | 1 |
| ltv_cap | 1 |
| credit_floor | 1 |
| credit_tier | 1 |
| dti | 3 (one per DTI reason code) |
| reserves | 1 |

Baseline expectations for all 12 golden cases also verified exactly (decision and reason codes). Output committed as `results/mutation_matrix.json`.

## Decision analytics

Command:

```
.venv/bin/python scripts/run_analytics.py --n 500000 --seed 1337
```

Overall approval rate 20.71% (103,551 of 500,000). That low rate is a property of the stress shaped synthetic population, not a claim about any realistic pipeline: the generator deliberately oversamples boundary and over limit loans. Reason code frequency over the population (an application can carry several):

| code | fires |
|---|---|
| LIM01 | 238,318 |
| DTI01 | 128,141 |
| LTV01 | 116,565 |
| CRD01 | 107,512 |
| CRD02 | 89,675 |
| RSV01 | 54,342 |
| DTI03 | 28,128 |
| DTI02 | 8,390 |

Sanity checks that came out as expected: approval rate under the 620 credit band is exactly 0, approval rate above a 50% DTI is exactly 0, and rates rise monotonically with credit band (21.8% for 620 to 659, 26.4% for 660 to 719, 28.4% for 720 plus). Full segment tables committed as `results/analytics.json`.

## Benchmark

Command:

```
.venv/bin/python scripts/run_bench.py --n 200000 --seed 42
```

200,000 pre generated applications (generation excluded from timing), 2,000 warmup evaluations, then one bulk wall clock pass for throughput and a second pass with `perf_counter_ns` around each call for latency percentiles.

* Throughput: 339,270 decisions/s (bulk pass, 0.5895 s for 200k)
* Latency: p50 2.88 us, p90 4.00 us, p99 5.21 us, max 145.71 us

The latency pass carries per call timer overhead, which is why throughput is reported from the bulk pass and not from summed latencies. Output committed as `results/bench.json`.

## Tests and coverage

```
.venv/bin/pytest --color=no -q --cov=underwritekit --cov-report=term
```

136 passed, 100% line coverage over the `underwritekit` package (391 statements, 0 missed). The boundary matrix alone is 66 of those tests, each rule edge exercised on both sides. Coverage is measured over the library package; the four thin scripts in `scripts/` are argument parsing wrappers around library functions that the tests call directly.
