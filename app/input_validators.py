"""Validation helpers for values entered in the calculator REPL."""

import math

from app.exceptions import InvalidNumberError


def parse_number(
    raw_value: str,
    label: str,
    maximum: float | None = None,
) -> float:
    """Convert an input string to a finite float or raise a helpful error."""
    try:
        number = float(raw_value)
    except ValueError as exc:
        raise InvalidNumberError(
            f"Invalid {label} number: {raw_value!r}. Please enter a valid number."
        ) from exc

    if not math.isfinite(number):
        raise InvalidNumberError(
            f"Invalid {label} number: {raw_value!r}. Please enter a finite number."
        )
    if maximum is not None and abs(number) > maximum:
        raise InvalidNumberError(
            f"Invalid {label} number: {raw_value!r}. "
            f"Absolute value must not exceed {maximum}."
        )
    return number
