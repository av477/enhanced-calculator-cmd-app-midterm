import pandas as pd
import pytest

from app.calculation import CalculationFactory
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
