from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from desktop_app.window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Agent Assistant")
    app.setOrganizationName("agent-assistant")
    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())
