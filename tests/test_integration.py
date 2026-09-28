import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def invoke(*args, input_text=None):
    return subprocess.run(
        [sys.executable, "-m", "setwise", *args], cwd=ROOT,
        input=input_text, text=True, capture_output=True,
    )


def independent_crc(losses, parameters, alpha):
    """Independent oracle: do not call setwise or reuse its correction helpers."""
    means = [sum(row[j] for row in losses) / len(losses) for j in range(len(parameters))]
    rows = []
    for parameter, mean in zip(parameters, means):
        correction = (1.0 - mean) / (len(losses) + 1)
        bound = mean + correction
        rows.append((parameter, mean, correction, bound, bound <= alpha))
    passing = [row for row in rows if row[-1]]
    selected = min(passing, key=lambda row: parameters.index(row[0])) if passing else None
    return selected, rows


def fixture():
    # Multilabel-style false-negative proportions decrease as the set parameter grows.
    parameters = [0.10, 0.30, 0.50, 0.70, 0.90]
    losses = [
        [0.90, 0.60, 0.30, 0.10, 0.00],
        [0.70, 0.40, 0.20, 0.00, 0.00],
        [0.80, 0.50, 0.20, 0.10, 0.00],
        [0.60, 0.30, 0.10, 0.00, 0.00],
    ]
    return {"parameters": parameters, "losses": losses}


def test_end_to_end_cli_matches_independent_oracle(tmp_path):
    source = tmp_path / "multilabel losses.json"
    output = tmp_path / "calibrated result.json"
    data = fixture()
    source.write_text(json.dumps(data), encoding="utf-8")
    expected, rows = independent_crc(data["losses"], data["parameters"], 0.25)

    result = invoke("calibrate", str(source), "-o", str(output), "--alpha", "0.25")
    assert result.returncode == 0, result.stderr
    actual = json.loads(output.read_text(encoding="utf-8"))
    assert actual["selected_parameter"] == expected[0]
    assert actual["empirical_risk"] == expected[1]
    assert actual["correction"] == expected[2]
    assert actual["corrected_bound"] == expected[3]
    assert [point["admissible"] for point in actual["grid"]] == [row[-1] for row in rows]

    summary = invoke("summarize", str(source), "-o", "-")
    assert summary.returncode == 0
    summary_rows = json.loads(summary.stdout)
    assert summary_rows[0]["empirical_risk"] == sum(row[0] for row in data["losses"]) / 4


def test_cli_no_solution_and_reverse_direction(tmp_path):
    data = {"parameters": [1, 2, 3], "losses": [[0.9, 0.8, 0.7], [0.9, 0.8, 0.7]]}
    source = tmp_path / "input.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    no_solution = invoke("calibrate", str(source), "-o", "-", "--alpha", "0.1")
    assert no_solution.returncode == 0
    parsed = json.loads(no_solution.stdout)
    assert parsed["status"] == "no_solution" and parsed["selected_parameter"] is None

    reverse = {"parameters": [1, 2, 3], "losses": [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]}
    reverse_result = invoke("calibrate", "-", "-o", "-", "--alpha", "0.55",
                            "--monotone", "nondecreasing", input_text=json.dumps(reverse))
    assert reverse_result.returncode == 0
    assert json.loads(reverse_result.stdout)["selected_parameter"] == 3


def test_cli_rejects_malformed_and_nonmonotone_inputs(tmp_path):
    malformed = invoke("calibrate", "-", "-o", "-", "--alpha", "0.5", input_text="{not json")
    assert malformed.returncode == 2 and malformed.stdout == ""
    data = {"parameters": [1, 2], "losses": [[0.1, 0.4], [0.2, 0.3]]}
    invalid = invoke("validate", "-", "--alpha", "0.5", input_text=json.dumps(data))
    assert invalid.returncode == 2
    assert "monotonicity" in invalid.stderr


def load_tests(loader, standard_tests, pattern):
    import tempfile
    tests = (test_end_to_end_cli_matches_independent_oracle,
             test_cli_no_solution_and_reverse_direction,
             test_cli_rejects_malformed_and_nonmonotone_inputs)
    suite = unittest.TestSuite()
    for fn in tests:
        def case(fn=fn):
            with tempfile.TemporaryDirectory() as d:
                class P:
                    def __truediv__(self, part): return Path(d) / part
                fn(P())
        suite.addTest(unittest.FunctionTestCase(case))
    return suite
