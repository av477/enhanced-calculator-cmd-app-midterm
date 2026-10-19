"""Facade coordinating calculations, history, observers, undo, and redo."""

from collections.abc import Iterable

from app.calculation import Calculation, CalculationFactory
from app.calculator_memento import CalculatorMemento
from app.calculator_observers import CalculationEvent, CalculationObserver
from app.history import CalculationHistory


class Calculator:
    """Provide a simplified interface to the calculator subsystems."""

    def __init__(
        self,
        observers: Iterable[CalculationObserver] = (),
        initial_history: Iterable[Calculation] = (),
    ) -> None:
        self._history = CalculationHistory()
        self._observers = list(observers)
        self._undo_stack: list[CalculatorMemento] = []
        self._redo_stack: list[CalculatorMemento] = []
        for calculation in initial_history:
            self._undo_stack.append(self._history.create_memento())
            self._history.add(calculation)

    @property
    def history(self) -> tuple[Calculation, ...]:
        """Return the current calculation history."""
        return self._history.get_all()

    def add_observer(self, observer: CalculationObserver) -> None:
        """Subscribe an observer to calculator state changes."""
        if observer not in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer: CalculationObserver) -> None:
        """Unsubscribe an observer from calculator state changes."""
        self._observers.remove(observer)

    def calculate(
        self,
        first_number: float,
        operation: str,
        second_number: float,
    ) -> float:
        """Calculate, retain the successful request, and notify observers."""
        calculation = CalculationFactory.create_calculation(
            first_number, operation, second_number
        )
        result = calculation.calculate()

        self._undo_stack.append(self._history.create_memento())
        self._redo_stack.clear()
        self._history.add(calculation)
        self._notify(
            CalculationEvent(
                "calculate",
                self.history,
                calculation=calculation,
                result=result,
            )
        )
        return result

    def undo(self) -> bool:
        """Restore the previous history state; return False if unavailable."""
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._history.create_memento())
        self._history.restore(self._undo_stack.pop())
        self._notify(CalculationEvent("undo", self.history))
        return True

    def redo(self) -> bool:
        """Restore the next history state; return False if unavailable."""
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._history.create_memento())
        self._history.restore(self._redo_stack.pop())
        self._notify(CalculationEvent("redo", self.history))
        return True

    def clear_history(self) -> None:
        """Clear calculation history and publish the new state."""
        self._undo_stack.append(self._history.create_memento())
        self._redo_stack.clear()
        self._history.restore(CalculatorMemento(()))
        self._notify(CalculationEvent("clear", self.history))

    def load_history(self, calculations: Iterable[Calculation]) -> None:
        """Replace history with loaded calculations and reset undo/redo."""
        self._history.restore(CalculatorMemento(tuple(calculations)))
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify(CalculationEvent("load", self.history))

    def _notify(self, event: CalculationEvent) -> None:
        for observer in tuple(self._observers):
            observer.update(event)
