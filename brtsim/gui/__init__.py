"""The graphical user interface, open it from the repository root with: uv run python -m brtsim gui [scenario]"""

import sys


def main(scenario=None):
    from PySide6.QtWidgets import QApplication

    from .document import Document
    from .main_window import MainWindow

    application = QApplication.instance() or QApplication(sys.argv[:1])
    application.setApplicationName("BRT simulator")
    window = MainWindow(Document())
    window.show()
    if scenario:
        window.open(scenario)
    return application.exec()
