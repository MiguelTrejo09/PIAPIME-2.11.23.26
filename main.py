#!/usr/bin/env python3
"""Punto de entrada de PIAPIME — Analizador de Curvas Dosis-Respuesta."""

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from piapime.ui.main_window import MainWindow
from piapime.ui.style import DARK_STYLESHEET


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("PIAPIME")
    app.setApplicationVersion("2.11.23.26")
    app.setOrganizationName("UNAM FESC")
    app.setOrganizationDomain("fesc.unam.mx")

    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
