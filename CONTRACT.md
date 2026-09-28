# Setwise implementation contract

This contract freezes the research leaf's interface for engine and CLI agents.
Python 3.10+, standard library only for the core. Public functions use JSON-safe
Python values and must never mutate caller-owned sequences.

## Core public API (`setwise/core.py`)

```python
def calibrate_risk(
    losses: Sequence[Sequence[float]],
    parameters: Sequence[float],
    *,
    alpha: float,
    monotone: Literal["nonincreasing", "nondecreasing"] = "nonincreasing",
) -> dict[str, object]: ...

def validate_calibration(
    losses: Sequence[Sequence[float]],
    parameters: Sequence[float],
    *, alpha: float,
    monotone: str = "nonincreasing",
) -> None: ...

def summarize_risk(
    losses: Sequence[Sequence[float]],
    parameters: Sequence[float],
) -> list[dict[str, float]]: ...
```

`losses` is n rows by m parameters, each value finite and in [0,1]. Parameters are
finite, unique, and supplied in increasing order. For each grid point, compute the
column mean `Rhat`. Apply the CRC inequality `(n/(n+1))*Rhat + 1/(n+1) <= alpha`
(`B=1`), equivalently an additive correction `(1-Rhat)/(n+1)`. For `nonincreasing`,
select the smallest admissible parameter; for `nondecreasing`, select the largest
admissible parameter. If no point passes, return `status="no_solution"` and
`selected_parameter=null`; never silently choose an unsafe point.
`validate_calibration` raises `ValueError` with a stable field-oriented message for
invalid shape/range/hyperparameters or any monotonicity violation. Monotonicity
checking is mandatory because disabling it would invalidate the stated CRC scope.

The exact correction equation and assumptions must be documented in code from the
paper cited in `docs/research.md`; do not substitute a different bound without changing
this contract and research record. Use deterministic float arithmetic and preserve
input order for ties.

## Return JSON schema

The result is an object with exactly these required keys:

```json
{
  "schema_version": "1",
  "status": "ok | no_solution",
  "n_calibration": 120,
  "n_parameters": 20,
  "alpha": 0.1,
  "monotone": "nonincreasing",
  "selected_parameter": 0.7,
  "selected_index": 13,
  "empirical_risk": 0.081,
  "correction": 0.019,
  "corrected_bound": 0.100,
  "grid": [{"parameter": 0.1, "empirical_risk": 0.9, "corrected_bound": 0.919, "admissible": false}]
}
```

For `no_solution`, selected fields are null and `grid` remains complete. Numbers are
JSON finite numbers; no NaN/Infinity. Additional diagnostic keys are forbidden in the
core result so downstream parsers remain stable.

## CLI contract (`python -m setwise` and `setwise`)

Subcommands:

* `calibrate INPUT -o OUTPUT --alpha A [--monotone nonincreasing|nondecreasing]`
* `summarize INPUT -o OUTPUT`
* `validate INPUT --alpha A [--monotone ...]`

Input is UTF-8 JSON with exactly `{"parameters":[...],"losses":[[...]...]}`. Output
is UTF-8 JSON (two-space indentation, trailing newline) and never overwrites an
existing file unless `--force` is supplied. `-` means stdin for input and stdout is
allowed only when `-o -` is explicit. `--help` is available on every command.

Exit codes: 0 for a valid result (including `no_solution`), 2 for user/input
validation errors, 3 for I/O errors, 4 for internal unexpected errors. Errors go to
stderr as one-line human-readable text; successful stdout contains JSON only.

## Required tests and benchmark behavior

Engine tests must cover a hand-calculated positive selection, `no_solution`, both
monotone directions, alpha/range validation, shape mismatch, NaN rejection,
mandatory monotonicity rejection, tie ordering, and JSON-serializable output.
CLI tests must cover each subcommand, stdin/stdout, paths containing spaces,
no-overwrite/`--force`, exit codes, and malformed JSON. Integration tests must run a
complete calibration from fixture creation through CLI output parsing. Benchmarks must
use the seeded 30-seed protocol in `docs/research.md`, preserve raw JSON results, and
compare against the empirical-only baseline without inventing a time-saving claim.
