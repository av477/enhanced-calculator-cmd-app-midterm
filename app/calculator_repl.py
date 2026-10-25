"""Enhanced Calculator command loop and CLI entry point."""

import sys
from typing import Protocol

from colorama import Fore, Style, init

from app.calculator import Calculator
from app.calculator_commands import (
    CalculateCommand,
    ClearHistoryCommand,
    Command,
    CommandInvoker,
    CommandRegistry,
    ExitCommand,
    HelpCommand,
    HistoryCommand,
    LoadHistoryCommand,
    RedoCommand,
    SaveHistoryCommand,
    UndoCommand,
)
from app.calculator_config import (
    build_invalid_operation_message,
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
COMMAND_COLORS = {
    "help": Fore.WHITE,
    "history": Fore.WHITE,
}
NOTICE_PREFIXES = ("Nothing to", "No calculations")


def _colorize(message: str, color: str) -> str:
    """Wrap one console message in a Colorama color and reset sequence."""
    return f"{color}{message}{Style.RESET_ALL}"


def _result_color(command_name: str, result: str) -> str:
    """Pick the color for a command result: notices are yellow."""
    if result.startswith(NOTICE_PREFIXES):
        return Fore.YELLOW
    return COMMAND_COLORS.get(command_name, Fore.GREEN)


def _display_symbol(operation_name: str) -> str:
    """Return an operation symbol supported by the active console encoding."""
    symbol = OPERATION_ALIASES[operation_name][-1]
    encoding = sys.stdout.encoding or "utf-8"
    try:
        symbol.encode(encoding)
    except UnicodeEncodeError:
        return operation_name
    return symbol


REPL_COMMANDS = CommandRegistry()


class HelpComponent(Protocol):
    """Render one section of the help menu."""

    def render(self) -> str:
        """Return help text."""


class CommandHelp:
    """Base help component listing every registered REPL command."""

    def __init__(self, registry: CommandRegistry) -> None:
        self._registry = registry

    def render(self) -> str:
        return "Commands: " + ", ".join(self._registry.names)


class HelpDecorator:
    """Base decorator that forwards rendering to the wrapped help component."""

    def __init__(self, component: HelpComponent) -> None:
        self._component = component

    def render(self) -> str:
        return self._component.render()


class OperationHelpDecorator(HelpDecorator):
    """Extend help with operations from the shared operation registry."""

    def render(self) -> str:
        return (
            super().render()
            + "\nOperations: "
            + ", ".join(
                f"{name} ({_display_symbol(name)})" for name in OPERATION_ALIASES
            )
        )


class AliasHelpDecorator(HelpDecorator):
    """Extend help with the word aliases of every registered operation."""

    def render(self) -> str:
        return (
            super().render()
            + "\nAliases: "
            + ", ".join(
                alias
                for aliases in OPERATION_ALIASES.values()
                for alias in aliases[1:-1]
            )
        )


HELP_MENU: HelpComponent = AliasHelpDecorator(
    OperationHelpDecorator(CommandHelp(REPL_COMMANDS))
)


def _print_help() -> None:
    """Display the decorated help menu."""
    print(HELP_MENU.render())


@REPL_COMMANDS.register("help")
def _help_command(_calculator: Calculator, _config: AppConfig) -> Command:
    return HelpCommand(HELP_MENU.render)


@REPL_COMMANDS.register("history")
def _history_command(calculator: Calculator, config: AppConfig) -> Command:
    return HistoryCommand(calculator, config.precision)


@REPL_COMMANDS.register("clear")
def _clear_command(calculator: Calculator, _config: AppConfig) -> Command:
    return ClearHistoryCommand(calculator)


@REPL_COMMANDS.register("undo")
def _undo_command(calculator: Calculator, _config: AppConfig) -> Command:
    return UndoCommand(calculator)


@REPL_COMMANDS.register("redo")
def _redo_command(calculator: Calculator, _config: AppConfig) -> Command:
    return RedoCommand(calculator)


@REPL_COMMANDS.register("save")
def _save_command(calculator: Calculator, config: AppConfig) -> Command:
    return SaveHistoryCommand(
        calculator,
        config.history_csv_path,
        encoding=config.default_encoding,
    )


@REPL_COMMANDS.register("load")
def _load_command(calculator: Calculator, config: AppConfig) -> Command:
    return LoadHistoryCommand(
        calculator,
        config.history_csv_path,
        encoding=config.default_encoding,
        max_history_size=config.max_history_size,
    )


@REPL_COMMANDS.register("exit", "quit", "q")
def _exit_command(_calculator: Calculator, _config: AppConfig) -> Command:
    return ExitCommand()


def _read_calculation(
    calculator: Calculator,
    config: AppConfig,
    operation: str,
) -> Command:
    """Prompt for operands and build a calculation command."""
    # LBYL: reject an unknown operation before requesting operands.
    if operation not in VALID_OPERATIONS:
        raise InvalidOperationError(build_invalid_operation_message())

    is_root = VALID_OPERATIONS[operation] == "root"
    first_prompt = (
        "Enter the number to take a root of: " if is_root else "Enter the first number: "
    )
    second_prompt = "Enter the root degree: " if is_root else "Enter the second number: "
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
    return CalculateCommand(calculator, first_number, operation, second_number)


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
    invoker = CommandInvoker()

    while True:
        try:
            user_input = input(_colorize("Choose an operation: ", Fore.CYAN))
            command_name = REPL_COMMANDS.resolve(user_input)

            if command_name is None:
                command = _read_calculation(
                    calculator, config, user_input.strip().lower()
                )
            else:
                command = REPL_COMMANDS.create(command_name, calculator, config)

            result = invoker.execute(command)
            print(_colorize(result, _result_color(command_name or "calculate", result)))

            if getattr(command, "ends_session", False):
                logger.info("Calculator session ended")
                break
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
