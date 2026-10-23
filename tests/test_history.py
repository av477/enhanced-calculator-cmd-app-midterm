import pandas as pd
import pytest

from app.calculation import CalculationFactory
from app.calculator_memento import CalculatorMemento
from app.history import CalculationHistory


def test_history_adds_calculations_and_returns_an_immutable_view():
    history = CalculationHistory()
    calculation = CalculationFactory.create_calculation(2, "+", 3)

    history.add(calculation)

    assert history.get_all() == (calculation,)


def test_history_memento_restores_a_previous_snapshot():
    history = CalculationHistory()
    first = CalculationFactory.create_calculation(2, "+", 3)
    second = CalculationFactory.create_calculation(8, "*", 4)
    history.add(first)
    memento = history.create_memento()

    history.add(second)
    history.restore(memento)

    assert history.get_all() == (first,)


def test_history_retains_only_the_most_recent_entries():
    calculations = [
        CalculationFactory.create_calculation(value, "+", 1)
        for value in (1, 2, 3)
    ]
    history = CalculationHistory(calculations[:2], max_size=2)

    history.add(calculations[2])

    assert history.get_all() == tuple(calculations[1:])


def test_history_limit_applies_when_restoring_a_memento():
    calculations = [
        CalculationFactory.create_calculation(value, "+", 1)
        for value in (1, 2, 3)
    ]
    history = CalculationHistory(max_size=2)

    history.restore(CalculatorMemento(tuple(calculations)))

    assert history.get_all() == tuple(calculations[1:])


@pytest.mark.parametrize("max_size", [0, -1, True, 1.5, "2"])
def test_history_rejects_invalid_maximum_size(max_size):
    with pytest.raises(ValueError, match="positive integer"):
        CalculationHistory(max_size=max_size)


def test_history_uses_a_dataframe_and_returns_a_copy():
    history = CalculationHistory(
        [CalculationFactory.create_calculation(2, "+", 3)]
    )

    dataframe = history.to_dataframe()
    dataframe.loc[0, "first_number"] = 100

    assert isinstance(history.to_dataframe(), pd.DataFrame)
    assert history.get_all()[0].first_number == 2


def test_history_saves_and_loads_csv(tmp_path):
    history = CalculationHistory(
        [
            CalculationFactory.create_calculation(2, "^", 3),
            CalculationFactory.create_calculation(-27, "root", 3),
        ]
    )
    file_path = tmp_path / "nested" / "history.csv"

    history.save_csv(file_path)
    loaded = CalculationHistory.from_csv(file_path)

    assert loaded.get_all() == history.get_all()


def test_history_uses_configured_encoding_and_limit_for_csv(tmp_path):
    history = CalculationHistory(
        [
            CalculationFactory.create_calculation(value, "+", 1)
            for value in (1, 2, 3)
        ]
    )
    file_path = tmp_path / "history.csv"

    history.save_csv(file_path, encoding="cp1252")
    loaded = CalculationHistory.from_csv(
        file_path,
        encoding="cp1252",
        max_size=2,
    )

    assert [item.first_number for item in loaded.get_all()] == [2, 3]


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("first_number,operation\n2,add\n", "missing required columns"),
        ("first_number,operation,second_number\n,add,3\n", "empty calculation"),
        ("first_number,operation,second_number\nnan,add,3\n", "non-finite"),
        ("first_number,operation,second_number\nbad,add,3\n", "non-numeric"),
        ("first_number,operation,second_number\n2,invalid,3\n", "invalid operation"),
    ],
)
def test_history_rejects_invalid_csv(tmp_path, contents, message):
    file_path = tmp_path / "invalid.csv"
    file_path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        CalculationHistory.from_csv(file_path)
