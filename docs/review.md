# Setwise adversarial review

Reviewed 2026-09-28 from a clean temporary directory with the installed package, then ran the repository's standard-library test suite and benchmark. Original findings and subsequent observed fixes are recorded below.

## Verdict

**Reviewed and no blocking findings remain in the checked revision.** The core implementation is small, the public workflow now demonstrates a feasible selection, CI invokes the actual benchmark, and the benchmark's timing comparison is explicitly descriptive rather than a claim of user time saved.

## Reproduced findings

### R1 — CI silently skipped the required benchmark (fixed and reverified)

The workflow now invokes `python benchmarks/run.py --output benchmarks/ci-results.json`. Local execution completed with `BENCHMARK_OK`; the YAML command no longer has a conditional skip. Matrix execution on hosted Python 3.10/3.12 and both OSes remains environment-dependent and was not run locally.

### R2 — README quickstart produced `no_solution` for its own stated alpha (fixed and reverified)

The command now uses `--alpha 0.4`; fresh execution returned `status: ok`, selected `0.3`, and corrected bound `0.35`. The README documents protected outputs and `--force`; a repeated run correctly fails safely, and an explicit `--force` rerun succeeds.

### R3 — Benchmark protocol does not measure a fair time-saving claim (addressed)

The benchmark now labels process-level and in-process timing separately, states its synthetic/descriptive scope, and explicitly makes no speedup or human-time claim. This is adequate for the repository's reproducibility check; it is not evidence of user time saved.

### R4 — Benchmark endpoint/ground-truth checks were insufficient (fixed and reverified)

The benchmark now uses an independent `Fraction` oracle for selection/bounds and asserts sorted parameters, monotone rows, and the known safe zero-loss endpoint. Fresh execution completed with `BENCHMARK_OK`.

### R5 — README repeatability conflicted with safe no-overwrite CLI behavior (fixed and reverified)

The README now explains protected outputs and the explicit `--force` rerun. Fresh verification observed the expected safe refusal and successful forced replacement.

## Checks performed

- Fresh temporary install with `pip install --no-deps --target ...` and `python -m setwise`: completed.
- Original README calibration returned `no_solution`; updated quickstart was reverified successfully below.
- `python -m unittest discover -s tests -v`: 15 tests, all passed.
- `python benchmarks/run.py --output <temporary file>`: completed with `BENCHMARK_OK` and 30 records.
- Source review covered `core.py`, `cli.py`, tests, benchmark, packaging metadata, CI, README, research/usage docs, and license/citation.
- Validation rejects bools, NaN/infinite values, non-rectangular/range-invalid losses, duplicate/non-increasing parameters, and declared monotonicity violations. The finite-grid fallback is correctly surfaced as `no_solution`; it is not a guarantee that a feasible point exists.

## Rights and claims

The repository's research note attributes the CRC method to Angelopoulos et al. and describes an independent implementation; no copied paper text, weights, or data were found in the reviewed tree. The MIT license and citation metadata are present. This review does not provide legal clearance; the README appropriately avoids a legal claim. The current benchmark must not be presented as measured user time saved.

## Reverification result

Fresh temporary install and checks on the updated revision:

- Exact README calibration: `status: ok`, selected `0.3`, corrected bound `0.35`.
- Repeated output without `--force`: safely rejected; explicit `--force`: succeeded.
- `python -m unittest discover -s tests -v`: 15 tests passed.
- `python examples/multilabel_workflow.py`: `EXAMPLE_OK`.
- `python benchmarks/run.py --output <temporary file>`: `BENCHMARK_OK`.

No unresolved release-blocking finding remains in this review. G1 is met subject to the hosted CI matrix running normally.
