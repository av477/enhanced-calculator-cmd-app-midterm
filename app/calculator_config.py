"""Shared calculator operation names, aliases, and display metadata."""

OPERATION_ALIASES = {
    "add": ("add", "sum", "+"),
    "subtract": ("subtract", "minus", "-"),
    "multiply": ("multiply", "times", "*"),
    "divide": ("divide", "div", "/"),
    "power": ("power", "pow", "^"),
    "root": ("root", "nthroot", "√"),
}
OPERATION_SYMBOLS = {
    name: aliases[-1] for name, aliases in OPERATION_ALIASES.items()
}
VALID_OPERATIONS = {
    alias: name
    for name, aliases in OPERATION_ALIASES.items()
    for alias in aliases
}
INVALID_OPERATION_MESSAGE = (
    "Invalid operation. Please choose one of: add (+), subtract (-), "
    "multiply (*), divide (/), power (^), or root (nthroot)."
)
