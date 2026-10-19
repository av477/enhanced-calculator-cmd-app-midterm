import pytest

from app.calculator_config import (
    INVALID_OPERATION_MESSAGE,
    OPERATION_ALIASES,
    OPERATION_SYMBOLS,
    VALID_OPERATIONS,
)


@pytest.mark.parametrize(
    ("operation", "aliases", "symbol"),
    [
        ("add", ("add", "sum", "+"), "+"),
        ("subtract", ("subtract", "minus", "-"), "-"),
        ("multiply", ("multiply", "times", "*"), "*"),
        ("divide", ("divide", "div", "/"), "/"),
        ("power", ("power", "pow", "^"), "^"),
        ("root", ("root", "nthroot", "√"), "√"),
    ],
)
def test_operation_config_defines_canonical_aliases_and_symbols(
    operation, aliases, symbol
):
    assert OPERATION_ALIASES[operation] == aliases
    assert OPERATION_SYMBOLS[operation] == symbol
    for alias in aliases:
        assert VALID_OPERATIONS[alias] == operation


def test_operation_aliases_are_unique():
    aliases = [
        alias for operation_aliases in OPERATION_ALIASES.values()
        for alias in operation_aliases
    ]

    assert len(aliases) == len(set(aliases))


def test_invalid_operation_message_lists_supported_operations():
    for operation in OPERATION_ALIASES:
        assert operation in INVALID_OPERATION_MESSAGE
