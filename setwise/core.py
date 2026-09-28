"""Dependency-free conformal risk control calibration utilities.

The correction follows Angelopoulos et al., *Conformal Risk Control*
(ICLR 2024): for losses bounded by B=1, the controlled bound is
``n/(n+1) * Rhat + 1/(n+1)``.  No confidence-delta term is used here.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from numbers import Real
from typing import Literal


Direction = Literal["nonincreasing", "nondecreasing"]


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field} must contain finite numbers")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must contain finite numbers")
    return result


def _rows(losses: Sequence[Sequence[float]]) -> list[list[float]]:
    if isinstance(losses, (str, bytes)) or not isinstance(losses, Sequence):
        raise ValueError("losses must be a non-empty sequence of rows")
    if not losses:
        raise ValueError("losses must be a non-empty sequence of rows")
    result: list[list[float]] = []
    width: int | None = None
    for i, row in enumerate(losses):
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
            raise ValueError(f"losses[{i}] must be a sequence")
        if width is None:
            width = len(row)
            if width == 0:
                raise ValueError("losses rows must not be empty")
        elif len(row) != width:
            raise ValueError("losses must be rectangular")
        values = [_number(v, f"losses[{i}]") for v in row]
        if any(v < 0.0 or v > 1.0 for v in values):
            raise ValueError("losses values must be in [0, 1] (range validation)")
        result.append(values)
    return result


def validate_calibration(
    losses: Sequence[Sequence[float]],
    parameters: Sequence[float],
    *,
    alpha: float,
    monotone: str = "nonincreasing",
) -> None:
    """Validate all assumptions required by :func:`calibrate_risk`."""
    if monotone not in ("nonincreasing", "nondecreasing"):
        raise ValueError("monotone must be 'nonincreasing' or 'nondecreasing'")
    a = _number(alpha, "alpha")
    if not 0.0 < a <= 1.0:
        raise ValueError("alpha must be in (0, 1]")
    rows = _rows(losses)
    if isinstance(parameters, (str, bytes)) or not isinstance(parameters, Sequence):
        raise ValueError("parameters must be a non-empty sequence")
    if len(parameters) != len(rows[0]):
        raise ValueError("parameters length must equal loss columns")
    if not parameters:
        raise ValueError("parameters must be a non-empty sequence")
    params = [_number(v, "parameters") for v in parameters]
    if any(b <= a for a, b in zip(params, params[1:])):
        raise ValueError("parameters must be unique and strictly increasing")
    for row in rows:
        pairs = zip(row, row[1:])
        if monotone == "nonincreasing" and any(right > left for left, right in pairs):
            raise ValueError("losses violate declared nonincreasing monotonicity")
        if monotone == "nondecreasing" and any(right < left for left, right in pairs):
            raise ValueError("losses violate declared nondecreasing monotonicity")


def summarize_risk(
    losses: Sequence[Sequence[float]], parameters: Sequence[float]
) -> list[dict[str, float]]:
    """Return column means without selecting an operating point."""
    rows = _rows(losses)
    if isinstance(parameters, (str, bytes)) or not isinstance(parameters, Sequence):
        raise ValueError("parameters must be a non-empty sequence")
    if not parameters or len(parameters) != len(rows[0]):
        raise ValueError("parameters length must equal loss columns")
    params = [_number(v, "parameters") for v in parameters]
    if any(b <= a for a, b in zip(params, params[1:])):
        raise ValueError("parameters must be unique and strictly increasing")
    n = len(rows)
    return [{"parameter": p, "empirical_risk": sum(row[j] for row in rows) / n}
            for j, p in enumerate(params)]


def calibrate_risk(
    losses: Sequence[Sequence[float]],
    parameters: Sequence[float],
    *,
    alpha: float,
    monotone: Direction = "nonincreasing",
) -> dict[str, object]:
    """Select the safest useful grid point under the CRC expectation bound."""
    validate_calibration(losses, parameters, alpha=alpha, monotone=monotone)
    rows = _rows(losses)
    params = [float(v) for v in parameters]
    n = len(rows)
    summary = summarize_risk(rows, params)
    grid: list[dict[str, object]] = []
    for item in summary:
        risk = item["empirical_risk"]
        correction = (1.0 - risk) / (n + 1)
        bound = risk + correction
        grid.append({"parameter": item["parameter"], "empirical_risk": risk,
                     "corrected_bound": bound, "admissible": bound <= float(alpha)})
    feasible = [i for i, item in enumerate(grid) if item["admissible"]]
    selected_index = (min(feasible) if monotone == "nonincreasing" else max(feasible)) if feasible else None
    selected = grid[selected_index] if selected_index is not None else None
    return {
        "schema_version": "1", "status": "ok" if selected is not None else "no_solution",
        "n_calibration": n, "n_parameters": len(params), "alpha": float(alpha),
        "monotone": monotone, "selected_parameter": selected["parameter"] if selected else None,
        "selected_index": selected_index,
        "empirical_risk": selected["empirical_risk"] if selected else None,
        "correction": (selected["corrected_bound"] - selected["empirical_risk"]) if selected else None,
        "corrected_bound": selected["corrected_bound"] if selected else None,
        "grid": grid,
    }
