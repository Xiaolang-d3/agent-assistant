from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal


class FnWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable, *args) -> None:
        super().__init__()
        self._fn = fn
        self._args = args

    def run(self) -> None:
        try:
            self.finished.emit(self._fn(*self._args))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
