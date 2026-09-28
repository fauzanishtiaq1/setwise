"""Command-line interface for Setwise.

The CLI deliberately keeps stdout machine-readable and sends diagnostics to stderr.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import sys
from pathlib import Path
from typing import Any, TextIO

from . import core


class UserError(Exception):
    """An input or command-line error suitable for exit code 2."""


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="setwise", description="Calibrate monotone risk on a parameter grid.")
    sub = p.add_subparsers(dest="command", required=True)
    cal = sub.add_parser("calibrate", help="select an admissible parameter")
    _input_output(cal, output_required=True)
    cal.add_argument("--alpha", required=True, type=float)
    cal.add_argument("--monotone", choices=("nonincreasing", "nondecreasing"), default="nonincreasing")
    summ = sub.add_parser("summarize", help="summarize empirical risk by parameter")
    _input_output(summ, output_required=True)
    val = sub.add_parser("validate", help="validate the calibration table")
    _input_output(val, output_required=False)
    val.add_argument("--alpha", required=True, type=float)
    val.add_argument("--monotone", choices=("nonincreasing", "nondecreasing"), default="nonincreasing")
    return p


def _input_output(p: argparse.ArgumentParser, *, output_required: bool) -> None:
    p.add_argument("input", metavar="INPUT", help="UTF-8 JSON path, or - for stdin")
    if output_required:
        p.add_argument("-o", "--output", required=True, metavar="OUTPUT", help="output path, or - for stdout")
        p.add_argument("--force", action="store_true", help="allow replacing an existing output file")


def _read_input(name: str) -> dict[str, Any]:
    try:
        if name == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(name).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise OSError(f"cannot read input: {exc}") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UserError(f"invalid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}") from exc
    if not isinstance(value, dict) or set(value) != {"parameters", "losses"}:
        raise UserError("input must contain exactly parameters and losses")
    return value


def _write_json(value: Any, name: str, *, force: bool, input_name: str | None = None) -> None:
    try:
        payload = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise UserError(f"result is not valid JSON: {exc}") from exc
    if name == "-":
        sys.stdout.write(payload)
        return
    path = Path(name)
    if input_name and input_name != "-":
        input_path = Path(input_name)
        try:
            if path.exists() and os.path.samefile(path, input_path):
                raise OSError("output must not overwrite the input file")
        except FileNotFoundError:
            pass
    try:
        path.parent.mkdir(parents=False, exist_ok=True)
        if not force:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(payload)
        else:
            fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write(payload)
                os.replace(temporary, path)
            except Exception:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
                raise
    except FileExistsError as exc:
        raise OSError(f"output already exists: {name} (use --force to replace)") from exc
    except OSError as exc:
        raise OSError(f"cannot write output: {exc}") from exc


def _run(args: argparse.Namespace) -> Any:
    data = _read_input(args.input)
    if args.command == "summarize":
        result = core.summarize_risk(data["losses"], data["parameters"])
        _write_json(result, args.output, force=args.force, input_name=args.input)
        return result
    if args.command == "validate":
        core.validate_calibration(data["losses"], data["parameters"], alpha=args.alpha, monotone=args.monotone)
        result = {"schema_version": "1", "status": "valid"}
        sys.stdout.write(json.dumps(result, indent=2) + "\n")
        return result
    result = core.calibrate_risk(data["losses"], data["parameters"], alpha=args.alpha, monotone=args.monotone)
    _write_json(result, args.output, force=args.force, input_name=args.input)
    return result


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the documented process exit code."""
    try:
        args = _parser().parse_args(argv)
        _run(args)
        return 0
    except UserError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except Exception as exc:  # pragma: no cover - defensive process boundary
        print(f"internal error: {exc}", file=sys.stderr)
        return 4
