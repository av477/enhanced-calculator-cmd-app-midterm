"""Enhanced Calculator command loop and CLI entry point."""

import sys
from collections.abc import Callable

from colorama import Fore, Style, init

from app.calculator import Calculator
from app.calculator_commands import (
    CalculateCommand,
    ClearHistoryCommand,
    CommandInvoker,
    HistoryCommand,
    LoadHistoryCommand,
    RedoCommand,
    SaveHistoryCommand,
    UndoCommand,
)
from app.calculator_config import (
    INVALID_OPERATION_MESSAGE,
    OPERATION_ALIASES,
    VALID_OPERATIONS,
)
from app.calculator_observers import AutoSaveObserver, LoggingObserver
from app.config import AppConfig, ConfigurationError
from app.exceptions import (
    HistoryDataError,
    HistoryFileError,
    InvalidOperationError,
    OperationError,
    ValidationError,
)
from app.history import CalculationHistory
from app.input_validators import parse_number
from app.logger import configure_logging, get_logger

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


def _colorize(message: str, color: str) -> str:
    """Wrap one console message in a Colorama color and reset sequence."""
    return f"{color}{message}{Style.RESET_ALL}"


def _display_symbol(operation_name: str) -> str:
    """Return an operation symbol supported by the active console encoding."""
    symbol = OPERATION_ALIASES[operation_name][-1]
    encoding = sys.stdout.encoding or "utf-8"
    try:
        symbol.encode(encoding)
    except UnicodeEncodeError:
        return operation_name
    return symbol


class OperationHelpDecorator:
    """Extend command help with operations from the shared operation registry."""

    def __init__(self, render_commands: Callable[[], None]) -> None:
        self._render_commands = render_commands

    def __call__(self) -> None:
        self._render_commands()
        print(
            "Operations: "
            + ", ".join(
                f"{name} ({_display_symbol(name)})"
                for name in OPERATION_ALIASES
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


@OperationHelpDecorator
def _print_help() -> None:
    """Display non-calculation commands; the decorator adds operation help."""
    print("Commands: help, history, clear, undo, redo, save, load, exit")


def run_interactive(
    calculator: Calculator | None = None,
    config: AppConfig | None = None,
) -> None:
    """Run the calculator's read-evaluate-print loop."""
    try:
        config = config or AppConfig.from_environment()
    except ConfigurationError as exc:
        print(_colorize(f"Configuration error: {exc}", Fore.RED))
        return

    try:
        configure_logging(
            config.log_level,
            config.log_file_path,
            encoding=config.default_encoding,
        )
    except OSError as exc:
        print(_colorize(f"Unable to configure calculator logging: {exc}", Fore.RED))
        return

    logger = get_logger()
    logger.info("Starting calculator")

    if calculator is None:
        try:
            initial_history = (
                CalculationHistory.from_csv(
                    config.history_csv_path,
                    encoding=config.default_encoding,
                    max_size=config.max_history_size,
                ).get_all()
                if config.history_csv_path.exists()
                else ()
            )
        except (HistoryDataError, HistoryFileError, ValueError, OSError) as exc:
            logger.error("Unable to load calculator history: %s", exc)
            print(_colorize(f"Unable to load calculator history: {exc}", Fore.RED))
            return

        observers = [LoggingObserver()]
        if config.autosave_history:
            observers.append(
                AutoSaveObserver(
                    config.history_csv_path,
                    encoding=config.default_encoding,
                )
            )
        calculator = Calculator(
            observers=observers,
            initial_history=initial_history,
            max_history_size=config.max_history_size,
            precision=config.precision,
        )
    print(_colorize("-------------------- Enhanced Calculator --------------------", Fore.CYAN))
    print(_colorize("Available operations: " + ", ".join(OPERATION_ALIASES), Fore.CYAN))
    print("----------------------------------------------------------------")

    for operation_name, aliases in OPERATION_ALIASES.items():
        symbol = _display_symbol(operation_name)
        print(
            OPERATION_COLORS.get(operation_name, Fore.WHITE)
            + f"For {operation_name}, enter: {', '.join(aliases[:-1])}, or {symbol}"
        )

    print("----------------------------------------------------------------")
    print(
        _colorize(
            "Type 'help' for commands, 'history' to view results, 'clear' to clear "
            "history, 'undo' or 'redo' to change history, 'save' or 'load' for CSV "
            "history, or 'exit' to quit.",
            Fore.CYAN,
        )
    )
    history_path = config.history_csv_path
    invoker = CommandInvoker()

    while True:
        try:
            operation = input(_colorize("Choose an operation: ", Fore.CYAN)).strip()
            command = operation.lower()

            if command in {"quit", "exit", "q"}:
                logger.info("Calculator session ended")
                print(_colorize("Goodbye!", Fore.GREEN))
                break
            if command == "help":
                _print_help()
                continue
            if command == "history":
                print(
                    invoker.execute(HistoryCommand(calculator, config.precision))
                )
                continue
            if command == "clear":
                print(
                    _colorize(
                        invoker.execute(ClearHistoryCommand(calculator)),
                        Fore.GREEN,
                    )
                )
                continue
            if command == "undo":
                result = invoker.execute(UndoCommand(calculator))
                color = Fore.GREEN if result.startswith("Undid") else Fore.YELLOW
                print(_colorize(result, color))
                continue
            if command == "redo":
                result = invoker.execute(RedoCommand(calculator))
                color = Fore.GREEN if result.startswith("Redid") else Fore.YELLOW
                print(_colorize(result, color))
                continue
            if command == "save":
                print(
                    _colorize(
                        invoker.execute(
                            SaveHistoryCommand(
                                calculator,
                                history_path,
                                encoding=config.default_encoding,
                            )
                        ),
                        Fore.GREEN,
                    )
                )
                continue
            if command == "load":
                print(
                    _colorize(
                        invoker.execute(
                            LoadHistoryCommand(
                                calculator,
                                history_path,
                                encoding=config.default_encoding,
                                max_history_size=config.max_history_size,
                            )
                        ),
                        Fore.GREEN,
                    )
                )
                continue

            # LBYL: reject an unknown operation before requesting operands.
            if command not in VALID_OPERATIONS:
                raise InvalidOperationError(INVALID_OPERATION_MESSAGE)

            is_root = command in {"root", "nthroot", "√"}
            first_prompt = (
                "Enter the number to take a root of: "
                if is_root
                else "Enter the first number: "
            )
            second_prompt = (
                "Enter the root degree: "
                if is_root
                else "Enter the second number: "
            )
            first_number = parse_number(
                input(_colorize(first_prompt, Fore.CYAN)).strip(),
                "first",
                maximum=config.max_input_value,
            )
            second_number = parse_number(
                input(_colorize(second_prompt, Fore.CYAN)).strip(),
                "second",
                maximum=config.max_input_value,
            )
            result = invoker.execute(
                CalculateCommand(calculator, first_number, command, second_number)
            )
            print(_colorize(result, Fore.GREEN))
        except (EOFError, KeyboardInterrupt):
            logger.info("Calculator session interrupted")
            print(_colorize("\nGoodbye!", Fore.GREEN))
            break
        except HistoryDataError as exc:
            logger.error("History data error: %s", exc)
            print(_colorize(f"History data error: {exc}", Fore.RED))
        except HistoryFileError as exc:
            logger.error("History file error: %s", exc)
            print(_colorize(f"History file error: {exc}", Fore.RED))
        except ValidationError as exc:
            logger.warning("Input validation failed: %s", exc)
            print(_colorize(f"Error: {exc}", Fore.RED))
        except OperationError as exc:
            logger.warning("Operation failed: %s", exc)
            print(_colorize(f"Error: {exc}", Fore.RED))
        except ValueError as exc:
            logger.error("Calculation or command failed: %s", exc)
            print(_colorize(f"Error: {exc}", Fore.RED))
        except ZeroDivisionError as exc:
            logger.warning("Calculation failed: %s", exc)
            print(_colorize(f"Error: {exc}", Fore.RED))
        except OSError as exc:
            logger.error("History file operation failed: %s", exc)
            print(_colorize(f"History file error: {exc}", Fore.RED))


if __name__ == "__main__":
    run_interactive()
