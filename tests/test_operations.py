import pytest

from app.exceptions import OperationError, ValidationError
from app.operations import (
    absolute_difference,
    add,
    divide,
    integer_division,
    modulus,
    multiply,
    percentage,
    power,
    root,
    subtract,
)

@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (9, 6, 15),
        (-5, 11, 6),
        (0, 4, 4),
        (12.5, 3.5, 16.0),
    ],
)
def test_add(a, b, expected):
    assert add(a, b) == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (17, 9, 8),
        (-4, 6, -10),
        (0, 5, -5),
        (18.75, 2.25, 16.5),
    ],
)
def test_subtract(a, b, expected):
    assert subtract(a, b) == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (7, 8, 56),
        (-3, 9, -27),
        (0, 13, 0),
        (3.5, 4, 14.0),
    ],
)
def test_multiply(a, b, expected):
    assert multiply(a, b) == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (45, 5, 9),
        (24, 3, 8),
        (-16, 4, -4),
        (10.5, 2.5, 4.2),
    ],
)
def test_divide(a, b, expected):
    assert divide(a, b) == expected


@pytest.mark.parametrize(
    ("a", "b"),
    [
        (22, 0),
        (0, 0),
        (-8, 0),
    ],
)
def test_divide_by_zero(a, b):
    with pytest.raises(ZeroDivisionError, match="Cannot divide by zero"):
        divide(a, b)


@pytest.mark.parametrize(
    ("base", "exponent", "expected"),
    [
        (2, 3, 8),
        (5, 0, 1),
        (-2, 3, -8),
        (9, 0.5, 3),
        (2, -3, 0.125),
        (-2, -3, -0.125),
    ],
)
def test_power(base, exponent, expected):
    assert power(base, exponent) == expected


def test_power_rejects_zero_to_a_negative_exponent():
    with pytest.raises(ZeroDivisionError):
        power(0, -1)


def test_power_rejects_non_real_results_and_overflow():
    with pytest.raises(OperationError, match="real number"):
        power(-2, 0.5)
    with pytest.raises(OperationError, match="numeric range"):
        power(1e308, 2)


@pytest.mark.parametrize(
    ("radicand", "degree", "expected"),
    [(27, 3, 3), (16, 2, 4), (-27, 3, -3), (16, -2, 0.25)],
)
def test_root(radicand, degree, expected):
    assert root(radicand, degree) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("radicand", "degree", "message"),
    [
        (16, 0, "zero-degree"),
        (0, -2, "negative root degree"),
    ],
)
def test_root_rejects_invalid_degrees(radicand, degree, message):
    with pytest.raises(ZeroDivisionError, match=message):
        root(radicand, degree)


@pytest.mark.parametrize(("radicand", "degree"), [(-16, 2), (-16, 2.5)])
def test_root_rejects_non_real_negative_roots(radicand, degree):
    with pytest.raises(OperationError, match="odd integer"):
        root(radicand, degree)


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(17, 5, 2), (-17, 5, 3), (17, -5, -3), (12.5, 4, 0.5)],
)
def test_modulus(a, b, expected):
    assert modulus(a, b) == pytest.approx(expected)


def test_modulus_rejects_zero_divisor():
    with pytest.raises(ZeroDivisionError, match="zero"):
        modulus(12, 0)


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(17, 5, 3), (-17, 5, -3), (17, -5, -3), (12.5, 4, 3)],
)
def test_integer_division_discards_fraction_toward_zero(a, b, expected):
    assert integer_division(a, b) == expected


def test_integer_division_rejects_zero_divisor():
    with pytest.raises(ZeroDivisionError, match="Cannot divide by zero"):
        integer_division(12, 0)


def test_integer_division_rejects_overflowing_quotient():
    with pytest.raises(ValueError, match="supported numeric range"):
        integer_division(1e308, 1e-308)


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(25, 100, 25), (12, 30, 40), (-5, 20, -25)],
)
def test_percentage(a, b, expected):
    assert percentage(a, b) == pytest.approx(expected)


def test_percentage_rejects_zero_base():
    with pytest.raises(ZeroDivisionError, match="zero base"):
        percentage(12, 0)


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(10, 4, 6), (4, 10, 6), (-3, 5, 8), (2.5, 1, 1.5)],
)
def test_absolute_difference(a, b, expected):
    assert absolute_difference(a, b) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("operation", "first_number", "second_number", "expected"),
    [
        (add, 2, 3, 5),
        (subtract, 7, 2, 5),
        (multiply, 4, 3, 12),
        (divide, 9, 3, 3),
        (power, 2, 4, 16),
        (root, 81, 4, 3),
        (modulus, 17, 5, 2),
        (integer_division, 17, 5, 3),
        (percentage, 25, 100, 25),
        (absolute_difference, 10, 4, 6),
    ],
)
def test_operation_functions_return_expected_results(
    operation, first_number, second_number, expected
):
    assert operation(first_number, second_number) == pytest.approx(expected)
