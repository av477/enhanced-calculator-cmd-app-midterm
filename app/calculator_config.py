"""Shared calculator operation names, aliases, and display metadata."""

OPERATION_ALIASES = {
    "add": ("add", "sum", "+"),
    "subtract": ("subtract", "minus", "-"),
    "multiply": ("multiply", "times", "*"),
    "divide": ("divide", "div", "/"),
    "power": ("power", "pow", "^"),
    "root": ("root", "nthroot", "√"),
    "modulus": ("modulus", "mod", "%"),
    "integer_division": ("integer_division", "int_divide", "intdiv", "//"),
    "percentage": ("percentage", "percent", "pct"),
    "absolute_difference": ("absolute_difference", "abs_diff", "absdiff", "abs"),
}
OPERATION_SYMBOLS = {
    name: aliases[-1] for name, aliases in OPERATION_ALIASES.items()
}
VALID_OPERATIONS = {
    alias: name
    for name, aliases in OPERATION_ALIASES.items()
    for alias in aliases
}


def _ascii_hint(aliases: tuple[str, ...]) -> str:
    """Return the last alias that every console encoding can display."""
    return next(alias for alias in reversed(aliases) if alias.isascii())


def build_invalid_operation_message() -> str:
    """Build the invalid-operation message from the operation registry."""
    choices = [
        f"{name} ({_ascii_hint(aliases)})"
        for name, aliases in OPERATION_ALIASES.items()
    ]
    listed = ", ".join(choices[:-1]) + f", or {choices[-1]}"
    return f"Invalid operation. Please choose one of: {listed}."


INVALID_OPERATION_MESSAGE = build_invalid_operation_message()
