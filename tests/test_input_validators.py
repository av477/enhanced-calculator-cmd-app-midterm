import pytest

from app.exceptions import InvalidNumberError
from app.input_validators import parse_number


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("0", 0.0),
        ("-12", -12.0),
        (" 3.5 ", 3.5),
        ("1e3", 1000.0),
    ],
)
def test_parse_number_accepts_finite_numeric_inputs(raw_value, expected):
    assert parse_number(raw_value, "operand") == expected


@pytest.mark.parametrize("raw_value", ["", "abc", "2.3.4", "1/2"])
def test_parse_number_rejects_malformed_input(raw_value):
    with pytest.raises(InvalidNumberError, match="Please enter a valid number"):
        parse_number(raw_value, "operand")


@pytest.mark.parametrize("raw_value", ["nan", "inf", "-inf", "Infinity"])
def test_parse_number_rejects_non_finite_input(raw_value):
    with pytest.raises(InvalidNumberError, match="Please enter a finite number"):
        parse_number(raw_value, "operand")


def test_parse_number_includes_operand_label_and_value_in_error():
    with pytest.raises(InvalidNumberError, match="Invalid second number: 'oops'"):
        parse_number("oops", "second")
