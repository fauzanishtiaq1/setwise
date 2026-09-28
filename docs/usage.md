# Usage

Input is UTF-8 JSON with exactly `parameters` and `losses`. Parameters are
finite, unique, strictly increasing numbers. Losses are a non-empty rectangle
of finite values in `[0,1]`; every row must satisfy the declared monotonicity.

```bash
setwise calibrate input.json -o output.json --alpha 0.10 --monotone nonincreasing
setwise calibrate input.json -o output.json --force --alpha 0.10 --monotone nondecreasing
setwise summarize input.json -o summary.json
setwise validate input.json --alpha 0.10
setwise calibrate - -o - --alpha 0.10 < input.json
```

Existing output is protected unless `--force` is given, and the input is never
overwritten. `-` means stdin; `-o -` explicitly selects stdout. Exit codes are
0 for valid output (including `no_solution`), 2 for invalid arguments/data, 3
for file/encoding errors, and 4 for unexpected internal errors.

## Python API

```python
from setwise import core

losses = [[0.8, 0.4, 0.1], [0.7, 0.3, 0.1], [0.9, 0.5, 0.2]]
result = core.calibrate_risk(losses, [0.1, 0.2, 0.3], alpha=0.25)
assert result["status"] == "ok"
print(result["selected_parameter"])
```

`calibrate_risk` returns a JSON-safe object with the full grid, empirical risk,
correction, and corrected bound. `validate_calibration` is a preflight check;
`summarize_risk` returns empirical column means.

`corrected_bound = empirical_risk + (1 - empirical_risk)/(n + 1)` for bounded
losses. This finite correction is not a confidence interval and provides no
conditional, individual, subgroup, or distribution-shift guarantee.

The validation component supplies synthetic fixtures and the 30-seed
calibration-vs-empirical baseline protocol under `examples/` and `benchmarks/`.
Keep raw benchmark JSON and report measured values exactly; a finite benchmark
cannot establish a guarantee or human time saving.
