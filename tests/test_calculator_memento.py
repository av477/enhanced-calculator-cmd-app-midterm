from dataclasses import FrozenInstanceError

import pytest

from app.calculation import CalculationFactory
from app.calculator_memento import CalculatorMemento


@pytest.mark.parametrize(
    "calculations",
    [
        (),
        (CalculationFactory.create_calculation(2, "+", 3),),
        (
            CalculationFactory.create_calculation(2, "^", 3),
            CalculationFactory.create_calculation(27, "root", 3),
        ),
    ],
)
def test_memento_preserves_calculation_snapshot(calculations):
    memento = CalculatorMemento(calculations)

    assert memento.calculations == calculations


def test_memento_is_immutable():
    memento = CalculatorMemento(
        (CalculationFactory.create_calculation(1, "+", 2),)
    )

    with pytest.raises(FrozenInstanceError):
        memento.calculations = ()
