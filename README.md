# Enhanced Calculator

A Python command-line calculator with a continuous read-evaluate-print loop
(REPL), ten arithmetic operations, undo/redo, and pandas-backed CSV history.
The implementation is split into focused modules and demonstrates Strategy,
Factory, Observer, Memento, and Facade patterns.

## Features

- Addition, subtraction, multiplication, division, power, nth root, modulus,
  integer division, percentage, and absolute difference
- Named operations, aliases, and symbols
- Persistent CSV history with startup loading and optional automatic saving
- `help`, `history`, `clear`, `undo`, `redo`, `save`, `load`, and exit commands
- Input validation and clear errors for invalid input and unsupported results
- File-based calculation logging and observer-driven CSV auto-save
- Pytest suite with 100% statement and branch coverage enforced in CI

## Requirements

- Python 3.11 or newer
- pip
- Runtime packages: `colorama`, `pandas`, and `python-dotenv`

## Setup

Run the following from the repository root. The virtual environment keeps the
project's Python packages separate from other installations.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

If script activation is blocked, enable it for the current PowerShell process
and activate the environment again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

The editable install includes runtime packages and the development extra adds
the test tools (`pytest` and `pytest-cov`).

## Run the calculator

From the repository root, start the REPL with:

```console
python -m app.calculator_repl
```

Choose an operation and enter its two operands when prompted:

```text
Choose an operation: add
Enter the first number: 10
Enter the second number: 5
Result: 15.0
Choose an operation: history
1. 10.0 + 5.0 = 15.0
Choose an operation: exit
Goodbye!
```

For root, enter the radicand first and the degree second: choosing `root` and
entering `27` then `3` returns `3`. Negative radicands require an odd integer
degree. Zero-degree roots and non-real results are rejected.

## Operations and aliases

| Operation | Accepted inputs | Operand order |
| --- | --- | --- |
| Addition | `add`, `sum`, `+` | first + second |
| Subtraction | `subtract`, `minus`, `-` | first - second |
| Multiplication | `multiply`, `times`, `*` | first * second |
| Division | `divide`, `div`, `/` | first / second |
| Power | `power`, `pow`, `^` | first raised to second |
| Nth root | `root`, `nthroot`, `√` | root of first with degree second |
| Modulus | `modulus`, `mod`, `%` | remainder of first divided by second |
| Integer division | `integer_division`, `intdiv`, `//` | quotient truncated toward zero |
| Percentage | `percentage`, `percent`, `pct` | `(first / second) * 100` |
| Absolute difference | `absolute_difference`, `absdiff`, `abs` | `abs(first - second)` |

Inputs must be finite numbers. Division by zero, invalid operations, malformed
numbers, and results outside the supported real-number domain are reported as
errors; failed calculations are not added to history. Modulus, integer
division, and percentage reject a zero second operand. Integer division
truncates toward zero (for example, dividing `-17` by `5` returns `-3`).
Malformed numeric inputs, unsupported operations, and calculation-domain
errors produce actionable messages without adding failed calculations to
history. CSV parsing problems and file access failures are reported separately.

## REPL commands

| Command | Behavior |
| --- | --- |
| `help` | Show commands, operations, and aliases |
| `history` | Display the current calculation history |
| `clear` | Clear history; the change can be undone |
| `undo` | Restore the prior history state, if available |
| `redo` | Reapply an undone state, if available |
| `save` | Write history to the configured CSV path |
| `load` | Replace history from the configured CSV file |
| `exit`, `quit`, `q` | Exit the REPL |

`load` resets the undo and redo stacks. A new calculation clears the redo
stack. Missing or invalid CSV files produce an error; the REPL remains
available so the user can continue or exit.

## Configuration

Settings can be provided as process environment variables or in a `.env` file
in the working directory. Process environment variables take precedence over
`.env`. The checked-in `.env.example` lists the defaults; copy it to `.env` to
customize local settings. `.env` is ignored by Git.

| Variable | Default | Description |
| --- | --- | --- |
| `CALCULATOR_LOG_DIR` | `.` | Base directory for relative log file paths |
| `CALCULATOR_HISTORY_DIR` | `.` | Base directory for relative history file paths |
| `CALCULATOR_HISTORY_FILE` | `calculator_history.csv` | History CSV path; must have a `.csv` extension |
| `CALCULATOR_MAX_HISTORY_SIZE` | `1000` | Maximum number of history entries to retain |
| `CALCULATOR_AUTO_SAVE` | `true` | Automatically persist state changes; accepts `true`/`false`, `1`/`0`, `yes`/`no`, and `on`/`off` |
| `CALCULATOR_PRECISION` | `10` | Decimal places to round calculation results to (0–15) |
| `CALCULATOR_MAX_INPUT_VALUE` | `1e308` | Maximum absolute value accepted for each input |
| `CALCULATOR_DEFAULT_ENCODING` | `utf-8` | Encoding used for history and log file operations |
| `CALCULATOR_LOG_LEVEL` | `INFO` | One of `CRITICAL`, `ERROR`, `WARNING`, `INFO`, or `DEBUG` |
| `CALCULATOR_LOG_FILE` | `calculator.log` | File receiving calculation log entries |

Relative history and log filenames are resolved under their respective base
directories. Absolute filenames are used as provided. The legacy
`CALCULATOR_AUTOSAVE_HISTORY` setting remains supported when
`CALCULATOR_AUTO_SAVE` is not set. History size must be at least 1, precision
must be 0–15 decimal places, and the maximum input must be a positive finite
number.

The configured CSV is loaded at startup when it exists. When auto-save is
enabled, successful calculations and history changes (clear, undo, redo, and
load) are saved automatically. Disabling auto-save leaves manual `save` and
`load` available. Each successful calculation is logged to the configured log
file with its operation, operands, and result. Invalid settings are reported
before the REPL starts.

CSV history stores the first operand, canonical operation name, and second
operand. Results are recalculated when history is displayed.

## Python API

Use the calculation factory for a single calculation:

```python
from app.calculation import CalculationFactory

calculation = CalculationFactory.create_calculation(12, "*", 3)
print(calculation.calculate())  # 36
```

The `calculate(first_number, operation, second_number)` helper provides the
same dispatch behavior without retaining a `Calculation` object. To use the
facade with observers and state history:

```python
from app.calculator import Calculator
from app.calculator_observers import AutoSaveObserver, LoggingObserver

calculator = Calculator(
    observers=[
        LoggingObserver(),
        AutoSaveObserver("calculator_history.csv"),
    ]
)
print(calculator.calculate(2, "power", 3))
calculator.undo()
calculator.redo()
```

## Design and project layout

- **Strategy and Factory:** `OperationFactory` selects an operation strategy;
  `CalculationFactory` normalizes operation aliases and creates calculations.
- **Observer:** `Calculator` broadcasts state changes to registered observers.
  `LoggingObserver` records calculation details, and `AutoSaveObserver`
  automatically persists CSV history.
- **Logging:** The CLI writes to `CALCULATOR_LOG_FILE` (or the configured
  default log path). Successful calculations and session/history events are
  logged at INFO, invalid input and failed operations at WARNING, and history
  file/data failures at ERROR.
- **Memento:** immutable `CalculatorMemento` snapshots provide undo and redo.
- **Facade:** `Calculator` coordinates operations, history, observers, and
  state restoration.

```text
app/
    __init__.py
    calculator.py
    calculation.py
    calculator_config.py
    calculator_memento.py
    calculator_observers.py
    calculator_repl.py
    config.py
    exceptions.py
    history.py
    input_validators.py
    logger.py
    operations.py
tests/
    __init__.py
    test_calculations.py
    test_calculator_config.py
    test_calculator_facade.py
    test_calculator_memento.py
    test_calculator_repl.py
    test_config.py
    test_exceptions.py
    test_history.py
    test_input_validators.py
    test_operations.py
.env
.env.example
pyproject.toml
README.md
.github/
    workflows/
        python-app.yml
```

## Tests and coverage

Run all tests:

```console
python -m pytest
```

Measure statement and branch coverage and require both to reach 100%:

```console
python -m pytest --cov=app --cov-branch --cov-report=term-missing --cov-fail-under=100
```

Coverage exclusions should be reserved for code that cannot meaningfully be
exercised. `# pragma: no cover` excludes a marked line (and may exclude a
conditional clause); `# pragma: no branch` identifies an intentionally partial
branch. Do not exclude reachable code just to raise the coverage percentage:
add tests for those paths. This project currently has no coverage exclusions.

## Continuous integration

The GitHub Actions workflow at `.github/workflows/python-app.yml` installs
the project and development dependencies, runs pytest with branch coverage,
and fails if total coverage is below 100%.
