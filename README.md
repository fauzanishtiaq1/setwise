# Setwise

Setwise turns a JSON table of calibration losses into a defensible operating
point on an ordered parameter grid. It is deterministic, file-in/file-out, and
has no runtime dependencies: bring losses from any existing model.

## Install

```bash
git clone https://github.com/fauzanishtiaq1/setwise.git
cd setwise
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
```

Python 3.10+ is supported. Both `setwise` and `python -m setwise` are available.

## Quickstart

Create `calibration.json` (losses are in [0,1], rows are examples, and columns
match the increasing parameter grid):

```json
{"parameters": [0.1, 0.2, 0.3], "losses": [[0.8, 0.4, 0.1], [0.7, 0.3, 0.1], [0.9, 0.5, 0.2]]}
```

```bash
setwise calibrate calibration.json -o result.json --alpha 0.4
python -m json.tool result.json
```

The result contains `status`, the selected parameter (or `no_solution`), risk,
finite-sample correction, corrected bound, and the complete audit grid.
This example selects parameter `0.3`, with corrected bound `0.35`. Outputs are
protected by default: use a new filename or add `--force` to intentionally rerun.

```bash
type calibration.json | setwise calibrate - -o - --alpha 0.25  # PowerShell
setwise summarize calibration.json -o summary.json
setwise validate calibration.json --alpha 0.25
```

See [docs/usage.md](docs/usage.md) for all CLI options and the Python API.
Run `python examples/multilabel_workflow.py` for a temporary-directory example,
or supply a new output directory to retain the input and result.
Run `python benchmarks/run.py --output benchmarks/results.json` to reproduce
the [30-seed measurements](benchmarks/results.json). The benchmark labels
process-level and in-process timing separately; it is not a human time study.

## Method and scope

For losses bounded by 1, Setwise applies the CRC expectation inequality
`(n/(n+1))*Rhat + 1/(n+1) <= alpha` and no delta term. It checks the declared
monotonicity, selecting the smallest admissible parameter for nonincreasing
risk or the largest for nondecreasing risk. This is the one-dimensional
split-calibration use case described by Angelopoulos et al. (ICLR 2024), not a
reproduction of their research repository.

The assumptions are exchangeability, an independent calibration sample,
finite increasing parameters, correctly computed monotone losses, and losses in
[0,1]. The result is marginal expected-risk control, not conditional or
per-example coverage, fairness, distribution-shift robustness, or a safety
certificate. Setwise makes no per-calibration guarantee; `no_solution` is valid.

Research citations, alternatives, and rights are in
[`docs/research.md`](docs/research.md). Setwise independently implements the
mathematics and copies no source, weights, data, or paper text. MAPIE is a
broader alternative for fitted scikit-learn estimators. Check rights and patent
questions for your use case; this is not legal advice.

No time-saving number is claimed here; use the benchmark's raw JSON before
making an empirical performance claim.

## License

Original Setwise code is MIT licensed; see [LICENSE](LICENSE).
