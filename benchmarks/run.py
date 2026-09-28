"""Reproducible 30-seed calibration experiment and CLI/baseline timing."""
import json
import platform
import random
import subprocess
import sys
import tempfile
import time
import argparse
import math
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).parents[1]
OUT = Path(__file__).with_name("results.json")
SEEDS = list(range(30))
PARAMETERS = [0.1 + 0.1 * i for i in range(10)]
N_CALIBRATION = 120
N_HELDOUT = 400
ALPHA = 0.20


def make_losses(seed, n):
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        difficulty = rng.random()
        rows.append([max(0.0, min(1.0, difficulty - p)) for p in PARAMETERS])
    return rows


def baseline(losses):
    means = [sum(row[j] for row in losses) / len(losses) for j in range(len(PARAMETERS))]
    admissible = [j for j, mean in enumerate(means) if mean <= ALPHA]
    return {"selected_parameter": PARAMETERS[admissible[0]] if admissible else None,
            "empirical_risk": means[admissible[0]] if admissible else None}


def baseline_subprocess(path, output):
    started = time.perf_counter()
    proc = subprocess.run([sys.executable, "-c",
        "import json,sys; d=json.load(open(sys.argv[1])); p=d['parameters']; l=d['losses']; "
        "m=[sum(r[j] for r in l)/len(l) for j in range(len(p))]; a=[j for j,x in enumerate(m) if x<=0.2]; "
        "json.dump({'selected_parameter':p[a[0]] if a else None},open(sys.argv[2],'w'))",
        str(path), str(output)], cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return json.loads(output.read_text()), time.perf_counter() - started


def realized(losses, parameter):
    if parameter is None:
        return None
    j = PARAMETERS.index(parameter)
    return sum(row[j] for row in losses) / len(losses)


def cli_calibrate(path, output):
    started = time.perf_counter()
    proc = subprocess.run([sys.executable, "-m", "setwise", "calibrate", str(path), "-o", str(output),
                           "--alpha", str(ALPHA)], cwd=ROOT, text=True, capture_output=True)
    elapsed = time.perf_counter() - started
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return json.loads(output.read_text(encoding="utf-8")), elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    records = []
    cli_times = []
    baseline_times = []
    baseline_process_times = []
    with tempfile.TemporaryDirectory(prefix="setwise-benchmark-") as directory:
        work = Path(directory)
        for seed in SEEDS:
            calibration = make_losses(seed, N_CALIBRATION)
            heldout = make_losses(1000 + seed, N_HELDOUT)
            assert PARAMETERS == sorted(set(PARAMETERS))
            assert all(row[-1] == 0.0 for row in calibration + heldout)
            assert all(all(a >= b for a,b in zip(row,row[1:])) for row in calibration + heldout)
            payload = {"parameters": PARAMETERS, "losses": calibration}
            source = work / f"seed-{seed}.json"
            output = work / f"seed-{seed}-result.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            calibrated, cli_elapsed = cli_calibrate(source, output)
            started = time.perf_counter()
            base = baseline(calibration)
            base_elapsed = time.perf_counter() - started
            base_proc, base_proc_elapsed = baseline_subprocess(source, work / f"seed-{seed}-baseline.json")
            assert base_proc["selected_parameter"] == base["selected_parameter"]
            assert calibrated["selected_parameter"] in PARAMETERS or calibrated["status"] == "no_solution"
            rational_bounds = [(sum(Fraction(str(row[j])) for row in calibration) + 1) / (N_CALIBRATION + 1)
                               for j in range(len(PARAMETERS))]
            oracle_indices = [j for j,bound in enumerate(rational_bounds) if bound <= Fraction(str(ALPHA))]
            assert calibrated['selected_index'] == (oracle_indices[0] if oracle_indices else None)
            assert all(math.isclose(float(bound), point['corrected_bound'], abs_tol=1e-14)
                       for bound,point in zip(rational_bounds,calibrated['grid']))
            assert all(point["corrected_bound"] == point["empirical_risk"] +
                       (1.0 - point["empirical_risk"]) / (N_CALIBRATION + 1)
                       for point in calibrated["grid"])
            cli_times.append(cli_elapsed)
            baseline_times.append(base_elapsed)
            baseline_process_times.append(base_proc_elapsed)
            records.append({"seed": seed, "n_calibration": N_CALIBRATION, "n_heldout": N_HELDOUT,
                            "selected_parameter_cli": calibrated["selected_parameter"],
                            "selected_parameter_baseline": base["selected_parameter"],
                            "calibration_empirical_risk_cli": calibrated["empirical_risk"],
                            "correction": calibrated["correction"], "corrected_bound": calibrated["corrected_bound"],
                            "heldout_risk_cli": realized(heldout, calibrated["selected_parameter"]),
                            "heldout_risk_baseline": realized(heldout, base["selected_parameter"]),
                            "cli_wall_seconds": cli_elapsed, "baseline_wall_seconds": base_elapsed,
                            "baseline_subprocess_wall_seconds": base_proc_elapsed})
    cli_risks = [r["heldout_risk_cli"] for r in records if r["heldout_risk_cli"] is not None]
    base_risks = [r["heldout_risk_baseline"] for r in records if r["heldout_risk_baseline"] is not None]
    result = {"protocol": {"seeds": SEEDS, "n_calibration": N_CALIBRATION, "n_heldout": N_HELDOUT,
                            "grid_size": len(PARAMETERS), "alpha": ALPHA,
                            "note": "Synthetic uniform-difficulty monotone loss tables, not real multilabel data. Descriptive realized-risk rates across seeds; not a theorem guarantee. Runtime baseline does less statistical validation; no speedup or human-time claim.",
                            "known_safe_endpoint": PARAMETERS[-1]},
              "environment": {"python": sys.version, "platform": platform.platform(),
                              "machine": platform.machine()},
              "summary": {"cli_mean_heldout_risk": sum(cli_risks) / len(cli_risks),
                          "baseline_mean_heldout_risk": sum(base_risks) / len(base_risks),
                          "cli_violation_rate": sum(r > ALPHA for r in cli_risks) / len(cli_risks),
                          "baseline_violation_rate": sum(r > ALPHA for r in base_risks) / len(base_risks),
                          "cli_mean_wall_seconds": sum(cli_times) / len(cli_times),
                          "baseline_mean_wall_seconds": sum(baseline_times) / len(baseline_times),
                          "baseline_subprocess_mean_wall_seconds": sum(baseline_process_times) / len(baseline_process_times)},
              "records": records}
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("BENCHMARK_OK")


if __name__ == "__main__":
    main()
