"""Small, dependency-free validators for remotely callable tool arguments."""

from __future__ import annotations

import math
from typing import Any, Iterable


def require_argument_object(arguments: Any) -> dict[str, Any]:
    """Require the public argument payload to be a JSON object."""
    if not isinstance(arguments, dict):
        raise ValueError("Arguments must be an object.")
    return arguments


def bounded_integer(
    value: Any,
    name: str,
    *,
    default: int | None = None,
    minimum: int,
    maximum: int,
) -> int | None:
    """Return a strict JSON integer inside an inclusive range."""
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"{name} must be an integer between {minimum} and {maximum}."
        )
    if not minimum <= value <= maximum:
        raise ValueError(
            f"{name} must be an integer between {minimum} and {maximum}."
        )
    return value


def bounded_number(
    value: Any,
    name: str,
    *,
    default: float | None = None,
    minimum: float,
    maximum: float,
    exclusive_minimum: bool = False,
    exclusive_maximum: bool = False,
) -> float | None:
    """Return a strict finite JSON number inside the requested range."""
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number in the allowed range.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number in the allowed range.")
    lower_ok = result > minimum if exclusive_minimum else result >= minimum
    upper_ok = result < maximum if exclusive_maximum else result <= maximum
    if not lower_ok or not upper_ok:
        raise ValueError(f"{name} must be a finite number in the allowed range.")
    return result


def bounded_text(
    value: Any,
    name: str,
    *,
    default: str | None = None,
    maximum: int = 128,
    allowed: Iterable[str] | None = None,
) -> str | None:
    """Return a non-empty bounded string, optionally from an allowlist."""
    if value is None:
        return default
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{name} must be a non-empty string of at most {maximum} characters.")
    if allowed is not None and value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{name} must be one of: {choices}.")
    return value
