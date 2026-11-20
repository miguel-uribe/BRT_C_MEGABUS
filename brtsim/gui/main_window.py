"""The main window of the application."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QWidget,
)

from .. import unsafe_jumps, validate
from .document import Document
from .pages import DemandPage, FleetPage, NetworkPage, ParametersPage, ServicesPage, TrafficLightsPage
from .run import RunPage

FILE_FILTER = "Scenarios (*.json);;All files (*)"


class MainWindow(QMainWindow):
    def __init__(self, document=None):
        super().__init__()
        self.document = document or Document()
        self.resize(1200, 780)

        # the pages, chosen from the list on the left
        self.sections = QListWidget()
        self.sections.setFixedWidth(150)
        self.sections.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sections.setSpacing(2)
        self.stack = QStackedWidget()
        self.pages = {}
        for kind in (ServicesPage, FleetPage, TrafficLightsPage, DemandPage, ParametersPage, NetworkPage, RunPage):
            page = kind(self.document)
            page.message.connect(self.show_message)
            self.pages[kind.title] = page
            self.stack.addWidget(page)
            self.sections.addItem(kind.title)
        self.run_page = self.pages["Run"]
        self.sections.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sections.setCurrentRow(0)
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 0)
        layout.addWidget(self.sections)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        # the problems of the scenario
        self.problems = QListWidget()
        self.problems.setWordWrap(True)
        self.problems_dock = QDockWidget("Problems")
        self.problems_dock.setObjectName("problems")
        self.problems_dock.setWidget(self.problems)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.problems_dock)
        self.resizeDocks([self.problems_dock], [110], Qt.Vertical)
        self.check_timer = QTimer(self)
        self.check_timer.setSingleShot(True)
        self.check_timer.setInterval(400)
        self.check_timer.timeout.connect(self.check)

        self.create_actions()
        self.document.changed.connect(self.document_changed)
        self.document.reloaded.connect(self.check)
        self.document_changed()
        self.check()

    def create_actions(self):
        def action(text, slot, shortcut=None, tip=""):
            item = QAction(text, self)
            item.triggered.connect(lambda: slot())
            if shortcut:
                item.setShortcut(shortcut)
            item.setStatusTip(tip)
            return item

        self.open_action = action("&Open...", self.ask_open, QKeySequence.Open, "Open a scenario file")
        self.save_action = action("&Save", self.save, QKeySequence.Save, "Save the scenario")
        self.save_as_action = action("Save &as...", self.ask_save_as, QKeySequence.SaveAs, "Save the scenario in another file")
        self.quit_action = action("&Quit", self.close, QKeySequence.Quit)
        self.undo_action = action("&Undo", self.document.undo, QKeySequence.Undo, "Undo the last change")
        self.redo_action = action("&Redo", self.document.redo, QKeySequence.Redo, "Do again the change that was undone")
        self.check_action = action("&Check the scenario", self.check_now, "F7", "Look for problems in the scenario")
        self.run_action = action("&Run", self.run, "F5", "Simulate the scenario")

        file_menu = self.menuBar().addMenu("&File")
        file_menu.addActions([self.open_action, self.save_action, self.save_as_action])
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)
        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addActions([self.undo_action, self.redo_action])
        simulation_menu = self.menuBar().addMenu("&Simulation")
        simulation_menu.addActions([self.check_action, self.run_action])
        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.problems_dock.toggleViewAction())

        toolbar = self.addToolBar("Main")
        toolbar.setObjectName("main")
        toolbar.addActions([self.open_action, self.save_action])
        toolbar.addSeparator()
        toolbar.addActions([self.undo_action, self.redo_action])
        toolbar.addSeparator()
        toolbar.addActions([self.check_action, self.run_action])
        self.statusBar()

    def show_message(self, text):
        self.statusBar().showMessage(text, 8000)

    def show_page(self, title):
        self.sections.setCurrentRow(list(self.pages).index(title))

    def document_changed(self):
        name = self.document.path.name if self.document.path else "not saved"
        self.setWindowTitle(f"{self.document.scenario.name} ({name}){' *' if self.document.dirty else ''} - BRT simulator")
        self.undo_action.setEnabled(self.document.can_undo())
        self.redo_action.setEnabled(self.document.can_redo())
        self.check_timer.start()

    # ------------------------------------------------------------------ problems
    def check(self):
        """Lists the problems of the scenario, and returns whether it can be simulated."""
        scenario = self.document.scenario
        errors = validate(scenario)
        warnings = []
        if not errors:
            warnings = [problem for _, problems in unsafe_jumps(scenario) for problem in problems]
        self.problems.clear()
        for kind, texts in (("Error", errors), ("Warning", warnings)):
            for text in texts:
                item = QListWidgetItem(f"{kind}: {text[0].upper()}{text[1:]}")
                item.setData(Qt.UserRole, kind)
                self.problems.addItem(item)
        counts = []
        if errors:
            counts.append(f"{len(errors)} error{'s' if len(errors) > 1 else ''}")
        if warnings:
            counts.append(f"{len(warnings)} warning{'s' if len(warnings) > 1 else ''}")
        self.problems_dock.setWindowTitle("Problems: " + (", ".join(counts) if counts else "none"))
        return not errors

    def check_now(self):
        valid = self.check()
        self.problems_dock.show()
        self.show_message("The scenario can be simulated." if valid else "The scenario has errors, see the list of problems.")

    def run(self):
        self.show_page("Run")
        if not self.check():
            self.problems_dock.show()
            self.show_message("The scenario has errors, see the list of problems.")
            return
        self.run_page.run()

    # ------------------------------------------------------------------ files
    def ask_open(self):
        if not self.confirm_discard():
            return
        folder = str(self.document.path.parent) if self.document.path else ""
        path, _ = QFileDialog.getOpenFileName(self, "Open a scenario", folder, FILE_FILTER)
        if path:
            self.open(path)

    def open(self, path):
        try:
            self.document.open(path)
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Open a scenario", f"The file could not be opened:\n\n{error}")
            return False
        self.show_message(f"Opened {path}")
        return True

    def save(self):
        if self.document.path is None:
            return self.ask_save_as()
        return self.save_to(self.document.path)

    def ask_save_as(self):
        start = str(self.document.path) if self.document.path else "scenario.json"
        path, _ = QFileDialog.getSaveFileName(self, "Save the scenario", start, FILE_FILTER)
        return self.save_to(path) if path else False

    def save_to(self, path):
        try:
            self.document.save(path)
        except OSError as error:
            QMessageBox.critical(self, "Save the scenario", f"The file could not be saved:\n\n{error}")
            return False
        self.show_message(f"Saved {path}")
        return True

    def confirm_discard(self):
        """Whether the scenario can be replaced or closed, asking to save its changes first."""
        if not self.document.dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Unsaved changes",
            "The scenario has changes that are not saved. Do you want to save them?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if answer == QMessageBox.Save:
            return self.save()
        return answer == QMessageBox.Discard

    def closeEvent(self, event):
        if not self.confirm_discard():
            event.ignore()
            return
        if self.run_page.running:
            # the simulations that already started are left to finish
            self.run_page.cancel_run()
            self.run_page.worker.wait()
        event.accept()
