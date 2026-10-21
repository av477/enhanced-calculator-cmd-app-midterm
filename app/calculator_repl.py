"""Enhanced Calculator command loop and CLI entry point."""

import sys

from colorama import Fore, init

from app.calculation import Calculation
from app.calculator import Calculator
from app.calculator_config import (
    INVALID_OPERATION_MESSAGE,
    OPERATION_ALIASES,
    OPERATION_SYMBOLS,
    VALID_OPERATIONS,
)
from app.calculator_observers import AutoSaveHistoryObserver, LoggingObserver
from app.config import AppConfig, ConfigurationError
from app.exceptions import InvalidOperationError
from app.history import CalculationHistory
from app.input_validators import parse_number
from app.logger import configure_logging

init(autoreset=True)

OPERATION_COLORS = {
    "add": Fore.CYAN,
    "subtract": Fore.YELLOW,
    "multiply": Fore.MAGENTA,
    "divide": Fore.RED,
    "power": Fore.GREEN,
    "root": Fore.BLUE,
    "modulus": Fore.CYAN,
    "integer_division": Fore.YELLOW,
    "percentage": Fore.MAGENTA,
    "absolute_difference": Fore.RED,
}


def _display_symbol(operation_name: str) -> str:
    """Return an operation symbol supported by the active console encoding."""
    symbol = OPERATION_SYMBOLS[operation_name]
    encoding = sys.stdout.encoding or "utf-8"
    try:
        symbol.encode(encoding)
    except UnicodeEncodeError:
        return operation_name
    return symbol


def _print_help() -> None:
    """Display the commands and arithmetic operations available in the REPL."""
    print("Commands: help, history, clear, undo, redo, save, load, exit")
    print(
        "Operations: "
        + ", ".join(
            f"{name} ({_display_symbol(name)})" for name in OPERATION_ALIASES
        )
    )
    print(
        "Aliases: "
        + ", ".join(
            alias
            for aliases in OPERATION_ALIASES.values()
            for alias in aliases[1:-1]
        )
    )


def _print_history(history: tuple[Calculation, ...]) -> None:
    """Display successful calculations recorded during this session."""
    if not history:
        print("No calculations in history.")
        return

    for index, calculation in enumerate(history, start=1):
        result = calculation.calculate()
        if calculation.operation == "root":
            expression = (
                f"{calculation.second_number}{_display_symbol('root')}"
                f"({calculation.first_number})"
            )
        else:
            expression = (
                f"{calculation.first_number} {calculation.symbol} "
                f"{calculation.second_number}"
            )
        print(f"{index}. {expression} = {result}")


def run_interactive(
    calculator: Calculator | None = None,
    config: AppConfig | None = None,
) -> None:
    """Run the calculator's read-evaluate-print loop."""
    try:
        config = config or AppConfig.from_environment()
        configure_logging(config.log_level)
        if calculator is None:
            initial_history = (
                CalculationHistory.from_csv(config.history_csv_path).get_all()
                if config.history_csv_path.exists()
                else ()
            )
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}")
        return
    except (OSError, ValueError) as exc:
        print(f"Unable to load calculator history: {exc}")
        return

    if calculator is None:
        observers = [LoggingObserver()]
        if config.autosave_history:
            observers.append(AutoSaveHistoryObserver(config.history_csv_path))
        calculator = Calculator(
            observers=observers,
            initial_history=initial_history,
        )
    print("-------------------- Enhanced Calculator --------------------")
    print("Available operations: " + ", ".join(OPERATION_ALIASES))
    print("----------------------------------------------------------------")

    for operation_name, aliases in OPERATION_ALIASES.items():
        symbol = _display_symbol(operation_name)
        print(
            OPERATION_COLORS[operation_name]
            + f"For {operation_name}, enter: {', '.join(aliases[:-1])}, or {symbol}"
        )

    print("----------------------------------------------------------------")
    print(
        "Type 'help' for commands, 'history' to view results, 'clear' to clear "
        "history, 'undo' or 'redo' to change history, 'save' or 'load' for CSV "
        "history, or 'exit' to quit."
    )
    history_path = config.history_csv_path

    while True:
        try:
            operation = input("Choose an operation: ").strip()
            command = operation.lower()

            if command in {"quit", "exit", "q"}:
                print("Goodbye!")
                break
            if command == "help":
                _print_help()
                continue
            if command == "history":
                _print_history(calculator.history)
                continue
            if command == "clear":
                calculator.clear_history()
                print("Calculation history cleared.")
                continue
            if command == "undo":
                print(
                    "Undid the last calculation."
                    if calculator.undo()
                    else "Nothing to undo."
                )
                continue
            if command == "redo":
                print(
                    "Redid the last calculation."
                    if calculator.redo()
                    else "Nothing to redo."
                )
                continue
            if command == "save":
                CalculationHistory(calculator.history).save_csv(history_path)
                print(f"History saved to {history_path}.")
                continue
            if command == "load":
                loaded_history = CalculationHistory.from_csv(history_path)
                calculator.load_history(loaded_history.get_all())
                print(f"History loaded from {history_path}.")
                continue

            # LBYL: reject an unknown operation before requesting operands.
            if command not in VALID_OPERATIONS:
                raise InvalidOperationError(INVALID_OPERATION_MESSAGE)

            first_number = parse_number(
                input(
                    "Enter the number to take a root of: "
                    if command in {"root", "nthroot", "√"}
                    else "Enter the first number: "
                ).strip(),
                "first",
            )
            second_number = parse_number(
                input(
                    "Enter the root degree: "
                    if command in {"root", "nthroot", "√"}
                    else "Enter the second number: "
                ).strip(),
                "second",
            )
            result = calculator.calculate(first_number, command, second_number)
            print(f"Result: {result}")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        except ValueError as exc:
            print(f"Error: {exc}")
        except ZeroDivisionError as exc:
            print(f"Error: {exc}")
        except OSError as exc:
            print(f"History file error: {exc}")


if __name__ == "__main__":
    run_interactive()
