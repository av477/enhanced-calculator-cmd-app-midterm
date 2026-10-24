import pandas as pd
import pytest

from app.calculation import CalculationFactory
from app.calculator_memento import CalculatorMemento
from app.exceptions import HistoryDataError, HistoryFileError
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


def test_saved_csv_includes_results_and_timestamps(tmp_path):
    calculation = CalculationFactory.create_calculation(2, "^", 3)
    history = CalculationHistory([calculation])
    file_path = tmp_path / "history.csv"

    history.save_csv(file_path)
    dataframe = pd.read_csv(file_path)

    assert list(dataframe.columns) == [
        "operation",
        "first_number",
        "second_number",
        "result",
        "timestamp",
    ]
    assert dataframe.loc[0, "result"] == 8
    assert dataframe.loc[0, "timestamp"] == calculation.timestamp.isoformat()
    assert CalculationHistory.from_csv(file_path).get_all() == (calculation,)


def test_history_loads_legacy_csv_without_result_or_timestamp(tmp_path):
    file_path = tmp_path / "legacy.csv"
    file_path.write_text(
        "first_number,operation,second_number\n2,power,3\n",
        encoding="utf-8",
    )

    calculation = CalculationHistory.from_csv(file_path).get_all()[0]

    assert calculation.calculate() == 8
    assert calculation.timestamp.tzinfo is not None


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
        (
            "first_number,operation,second_number,result\n2,add,3,wrong\n",
            "non-numeric result",
        ),
        (
            "first_number,operation,second_number,result\n2,add,3,inf\n",
            "non-finite result",
        ),
        (
            "first_number,operation,second_number,timestamp\n2,add,3,not-a-date\n",
            "invalid timestamp",
        ),
        (
            "first_number,operation,second_number,timestamp\n2,add,3,\n",
            "empty timestamps",
        ),
        (
            "first_number,operation,second_number,result\n2,add,3,6\n",
            "does not match",
        ),
        (
            "first_number,operation,second_number\n-2,power,0.5\n",
            "cannot be evaluated",
        ),
    ],
)
def test_history_rejects_invalid_csv(tmp_path, contents, message):
    file_path = tmp_path / "invalid.csv"
    file_path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        CalculationHistory.from_csv(file_path)


def test_history_reports_empty_csv_as_data_error(tmp_path):
    file_path = tmp_path / "empty.csv"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(HistoryDataError, match="Unable to read calculator history"):
        CalculationHistory.from_csv(file_path)


def test_history_reports_missing_csv_as_file_error(tmp_path):
    with pytest.raises(HistoryFileError, match="Unable to read calculator history"):
        CalculationHistory.from_csv(tmp_path / "missing.csv")


def test_history_reports_encoding_failure_as_data_error(tmp_path):
    file_path = tmp_path / "wrong-encoding.csv"
    file_path.write_bytes(b"\xff\xfe")

    with pytest.raises(HistoryDataError, match="Unable to decode calculator history"):
        CalculationHistory.from_csv(file_path, encoding="utf-8")


def test_history_reports_csv_write_errors_as_file_error(tmp_path):
    not_a_directory = tmp_path / "file"
    not_a_directory.write_text("block", encoding="utf-8")
    history = CalculationHistory()

    with pytest.raises(HistoryFileError, match="Unable to save calculator history"):
        history.save_csv(not_a_directory / "history.csv")
