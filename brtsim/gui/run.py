"""The page where the scenario is simulated with several seeds."""

import json
import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
)

from .. import Cancelled, ScenarioError, prepare
from ..results import KPIS, LABELS, SERVICE_METRICS, STATION_METRICS
from .pages import Page, heading
from .tables import fill_table


class RunWorker(QThread):
    """Runs the simulations in the background, with a copy of the scenario."""

    progressed = Signal(int, int)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, scenario, seeds, workers):
        super().__init__()
        self.scenario = scenario.copy()
        self.seeds = seeds
        self.workers = workers
        self.stop = False

    def run(self):
        try:
            model = prepare(self.scenario)
            results = model.run(self.seeds, workers=self.workers, progress=self.progressed.emit, cancelled=lambda: self.stop)
        except Cancelled:
            self.cancelled.emit()
        except ScenarioError as error:
            self.failed.emit("The scenario cannot be simulated:\n\n" + "\n".join(f"• {problem}" for problem in error.problems))
        except Exception as error:  # the message is shown to the user, whatever the failure
            self.failed.emit(f"The simulation failed: {error}")
        else:
            self.succeeded.emit(results)


class RunPage(Page):
    title = "Run"
    finished = Signal()  # the simulations ended, with or without results

    def __init__(self, document):
        super().__init__(document)
        self.worker = None
        self.results = None

        self.seeds = QSpinBox()
        self.seeds.setRange(1, 10000)
        self.seeds.setValue(10)
        self.seeds.setToolTip("The number of simulations, each one with a different seed. Their results are averaged")
        self.first_seed = QSpinBox()
        self.first_seed.setRange(0, 1000000)
        self.first_seed.setValue(1)
        self.first_seed.setToolTip("The seeds are consecutive numbers starting at this one, the same seeds give the same results")
        self.workers = QSpinBox()
        self.workers.setRange(1, max(1, os.cpu_count() or 1))
        self.workers.setValue(self.workers.maximum())
        self.workers.setToolTip("The number of simulations running at the same time")

        self.start = QPushButton("Run")
        self.start.setDefault(True)
        self.start.clicked.connect(self.run)
        self.cancel = QPushButton("Cancel")
        self.cancel.setEnabled(False)
        self.cancel.clicked.connect(self.cancel_run)
        self.export = QPushButton("Export...")
        self.export.setEnabled(False)
        self.export.clicked.connect(self.ask_export)
        self.progress = QProgressBar()
        self.status = QLabel("The scenario has not been simulated yet.")
        self.status.setWordWrap(True)

        for box in (self.seeds, self.first_seed, self.workers):
            box.setMaximumWidth(120)
        form = QFormLayout()
        form.addRow("Simulations:", self.seeds)
        form.addRow("First seed:", self.first_seed)
        form.addRow("At the same time:", self.workers)
        buttons = QHBoxLayout()
        for button in (self.start, self.cancel, self.export):
            buttons.addWidget(button)
        buttons.addStretch()

        self.summary = QTableWidget()
        self.stations = QTableWidget()
        self.services = QTableWidget()
        for table, metrics in ((self.summary, KPIS), (self.stations, STATION_METRICS), (self.services, SERVICE_METRICS)):
            table.setToolTip("\n".join(f"{LABELS[name]}: {description}" for name, description in metrics.items()))
        tabs = QTabWidget()
        tabs.addTab(self.summary, "Indicators")
        tabs.addTab(self.services, "Services")
        tabs.addTab(self.stations, "Stations")

        layout = QVBoxLayout(self)
        layout.addWidget(heading("Run", "Simulates the scenario several times with different seeds and averages the results."))
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        layout.addWidget(tabs, 1)

    @property
    def running(self):
        return self.worker is not None

    def run(self):
        if self.running:
            return
        first = self.first_seed.value()
        seeds = list(range(first, first + self.seeds.value()))
        self.worker = RunWorker(self.scenario, seeds, self.workers.value())
        self.worker.progressed.connect(self.show_progress)
        self.worker.succeeded.connect(self.show_results)
        self.worker.failed.connect(self.show_failure)
        self.worker.cancelled.connect(lambda: self.status.setText("The simulations were cancelled."))
        self.worker.finished.connect(self.worker_finished)
        self.progress.setRange(0, len(seeds))
        self.progress.setValue(0)
        self.status.setText("Preparing the scenario...")
        self.start.setEnabled(False)
        self.cancel.setEnabled(True)
        self.worker.start()

    def cancel_run(self):
        if self.running:
            self.worker.stop = True
            self.status.setText("Cancelling, the simulations that already started will finish...")
            self.cancel.setEnabled(False)

    def worker_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.start.setEnabled(True)
        self.cancel.setEnabled(False)
        self.finished.emit()

    def show_progress(self, done, total):
        self.progress.setValue(done)
        self.status.setText(f"{done} of {total} simulations finished...")

    def show_results(self, results):
        self.results = results
        summary = results.summary().drop(columns="runs")
        summary.columns = ["Mean", "Standard deviation", "95% interval, low", "95% interval, high"]
        fill_table(self.summary, summary.rename(index=LABELS), decimals=3)
        fill_table(self.stations, results.stations.rename(columns=LABELS), decimals=1)
        fill_table(self.services, results.services.rename(columns=LABELS), decimals=1)
        self.export.setEnabled(True)
        count = len(results.runs)
        self.status.setText(
            f"Results of {count} simulation{'s' if count > 1 else ''} of the scenario as it was when they started. "
            "Speeds in km/h, times in seconds."
        )

    def show_failure(self, message):
        self.status.setText(message)
        QMessageBox.warning(self, "Run", message)

    def ask_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export the results", "results.json", "All the results (*.json);;Indicators of each simulation (*.csv)")
        if path:
            self.export_results(path)

    def export_results(self, path):
        path = Path(path)
        if path.suffix.lower() == ".csv":
            self.results.per_run().to_csv(path)
        else:
            path.write_text(json.dumps(self.results.to_dict(), indent=1), encoding="utf-8")
        self.message.emit(f"Results written to {path}")
