import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def run(*args, input_text=None):
    return subprocess.run([sys.executable, "-m", "setwise", *args], cwd=ROOT, input=input_text,
                          text=True, capture_output=True)


def payload():
    return {"parameters": [0.1, 0.2], "losses": [[0.2, 0.1], [0.3, 0.2], [0.1, 0.1]]}


def test_calibrate_stdin_stdout_and_spaces(tmp_path):
    source = tmp_path / "input with spaces.json"
    source.write_text(json.dumps(payload()), encoding="utf-8")
    p = run("calibrate", str(source), "-o", "-", "--alpha", "0.5")
    assert p.returncode == 0, p.stderr
    assert p.stderr == ""
    assert json.loads(p.stdout)["schema_version"] == "1"


def test_summarize_and_validate(tmp_path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(payload()), encoding="utf-8")
    out = tmp_path / "result with spaces.json"
    p = run("summarize", str(source), "-o", str(out))
    assert p.returncode == 0 and json.loads(out.read_text())[0]["parameter"] == 0.1
    p = run("validate", "-", "--alpha", "0.5", input_text=json.dumps(payload()))
    assert p.returncode == 0 and json.loads(p.stdout)["status"] == "valid"


def test_no_overwrite_and_force(tmp_path):
    source = tmp_path / "in.json"
    source.write_text(json.dumps(payload()), encoding="utf-8")
    out = tmp_path / "out.json"
    out.write_text("old", encoding="utf-8")
    p = run("calibrate", str(source), "-o", str(out), "--alpha", "0.5")
    assert p.returncode == 3
    p = run("calibrate", str(source), "-o", str(out), "--alpha", "0.5", "--force")
    assert p.returncode == 0 and json.loads(out.read_text())["schema_version"] == "1"


def test_malformed_json_exit_2(tmp_path):
    source = tmp_path / "bad.json"
    source.write_text("{bad", encoding="utf-8")
    p = run("calibrate", str(source), "-o", "-", "--alpha", "0.5")
    assert p.returncode == 2 and p.stdout == "" and p.stderr.startswith("invalid JSON:")


def test_force_rejects_input_alias_and_hardlink(tmp_path):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(payload()), encoding="utf-8")
    before = source.read_bytes()
    p = run("calibrate", str(source), "-o", str(source), "--alpha", "0.5", "--force")
    assert p.returncode == 3 and source.read_bytes() == before
    linked = tmp_path / "linked.json"
    linked.hardlink_to(source)
    p = run("calibrate", str(source), "-o", str(linked), "--alpha", "0.5", "--force")
    assert p.returncode == 3 and source.read_bytes() == before


def load_tests(loader, standard_tests, pattern):
    """Expose the pytest-style checks to the repository's unittest collector."""
    import tempfile

    def wrap(fn):
        def check():
            with tempfile.TemporaryDirectory() as d:
                class P:
                    def __truediv__(self, part): return Path(d) / part
                fn(P())
        return unittest.FunctionTestCase(check)
    return unittest.TestSuite(wrap(fn) for fn in (
        test_calibrate_stdin_stdout_and_spaces, test_summarize_and_validate,
        test_no_overwrite_and_force, test_malformed_json_exit_2,
        test_force_rejects_input_alias_and_hardlink))
