import pytest

from app.calculation import (
    Calculation,
    CalculationFactory,
    calculate,
    evaluate_expression,
)


@pytest.mark.parametrize(
    ("first_number", "operation", "second_number", "expected_result", "expected_symbol"),
    [
        (12, "add", 8, 20, "+"),
        (-8, "add", 4, -4, "+"),
        (0, "add", 9, 9, "+"),
        (18, "subtract", 9, 9, "-"),
        (-4, "subtract", 6, -10, "-"),
        (0, "subtract", 5, -5, "-"),
        (6, "multiply", 7, 42, "*"),
        (-3, "multiply", 9, -27, "*"),
        (0, "multiply", 13, 0, "*"),
        (36, "divide", 6, 6, "/"),
        (-16, "divide", 4, -4, "/"),
        (10.5, "divide", 2.5, 4.2, "/"),
    ],
)
def test_calculation_executes_operations(
    first_number,
    operation,
    second_number,
    expected_result,
    expected_symbol,
):
    calculation = Calculation(first_number, operation, second_number)

    assert calculation.calculate() == expected_result
    assert calculation.symbol == expected_symbol


@pytest.mark.parametrize(
    ("operation_alias", "expected_operation", "expected_symbol"),
    [
        ("  ADD  ", "add", "+"),
        ("SUM", "add", "+"),
        ("+", "add", "+"),
        ("SUBTRACT", "subtract", "-"),
        ("minus", "subtract", "-"),
        ("-", "subtract", "-"),
        ("MULTIPLY", "multiply", "*"),
        ("times", "multiply", "*"),
        ("*", "multiply", "*"),
        ("DIVIDE", "divide", "/"),
        ("div", "divide", "/"),
        ("/", "divide", "/"),
        ("POWER", "power", "^"),
        ("pow", "power", "^"),
        ("^", "power", "^"),
        ("ROOT", "root", "√"),
        ("nthroot", "root", "√"),
        ("√", "root", "√"),
    ],
)
def test_calculation_factory_normalizes_aliases(
    operation_alias,
    expected_operation,
    expected_symbol,
):
    calculation = CalculationFactory.create_calculation(8, operation_alias, 2)

    assert calculation.operation == expected_operation
    assert calculation.symbol == expected_symbol


@pytest.mark.parametrize("operation", ["", "mod", "sqrt"])
def test_calculation_factory_rejects_invalid_operations(operation):
    with pytest.raises(ValueError, match="Invalid operation"):
        CalculationFactory.create_calculation(8, operation, 2)


@pytest.mark.parametrize(
    ("first_number", "operation", "second_number", "expected_result"),
    [
        (12, "+", 8, 20),
        (18, "minus", 7, 11),
        (9, "times", 6, 54),
        (48, "div", 6, 8),
        (2, "^", 4, 16),
        (27, "root", 3, 3),
    ],
)
def test_calculate_dispatches_aliases(
    first_number, operation, second_number, expected_result
):
    assert calculate(first_number, operation, second_number) == expected_result


def test_calculation_raises_on_division_by_zero():
    calculation = CalculationFactory.create_calculation(15, "/", 0)

    with pytest.raises(ZeroDivisionError, match="Cannot divide by zero"):
        calculation.calculate()


@pytest.mark.parametrize(
    ("expression", "expected_result"),
    [
        ("2 + 3 * 4", 14.0),
        ("-5 / 2", -2.5),
        ("(1.25 + 2.75) * 2", 8.0),
    ],
)
def test_evaluate_expression_returns_numeric_results(expression, expected_result):
    assert evaluate_expression(expression) == expected_result


@pytest.mark.parametrize("expression", ["bad_name + 2", "1 +"])
def test_evaluate_expression_rejects_invalid_expressions(expression):
    with pytest.raises(ValueError, match="Invalid expression"):
        evaluate_expression(expression)


@pytest.mark.parametrize("expression", ["'hello'", "[]"])
def test_evaluate_expression_rejects_non_numeric_results(expression):
    with pytest.raises(ValueError, match="Expression did not produce a number"):
        evaluate_expression(expression)