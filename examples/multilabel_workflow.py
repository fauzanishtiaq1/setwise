"""Create a synthetic multilabel loss table and calibrate it through the CLI."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main(output_dir):
    out = Path(output_dir)
    payload = {"parameters": [0.1, 0.3, 0.5, 0.7, 0.9],
               "losses": [[0.8, 0.5, 0.2, 0.1, 0.0], [0.6, 0.4, 0.2, 0.0, 0.0],
                          [0.7, 0.4, 0.1, 0.1, 0.0]]}
    source = out / "losses.json"
    result = out / "calibration.json"
    with source.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
    subprocess.run([sys.executable, "-m", "setwise", "calibrate", str(source), "-o", str(result),
                    "--alpha", "0.3"], check=True)
    parsed = json.loads(result.read_text(encoding="utf-8"))
    assert parsed['status'] == 'ok' and parsed['selected_parameter'] == 0.7
    print(json.dumps(parsed, indent=2))
    print("EXAMPLE_OK")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        output = Path(sys.argv[1])
        output.mkdir(parents=True, exist_ok=False)
        main(output)
    else:
        with tempfile.TemporaryDirectory(prefix="setwise-example-") as directory:
            main(directory)
