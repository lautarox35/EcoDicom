"""Punto de entrada de EcoDICOM."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.config import ensure_directories
from app.storage.database import Database
from app.ui.main_window import MainWindow


def main() -> int:
    ensure_directories()
    db = Database()
    db.initialize()

    app = QApplication(sys.argv)
    app.setApplicationName("EcoDICOM")
    app.setOrganizationName("EcoDICOM")

    window = MainWindow(db=db)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
