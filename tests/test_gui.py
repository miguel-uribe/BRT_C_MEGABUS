"""The graphical user interface: the scenario is edited, saved and simulated without touching a text file."""

import json

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

import brtsim
import golden_tools as gt
from brtsim.gui.document import Document
from brtsim.gui.main_window import MainWindow
from brtsim.gui.tables import format_time, parse_time

SCENARIO_FILE = gt.ROOT / "scenarios" / "megabus.json"


@pytest.fixture
def window(qtbot, monkeypatch):
    # closing the window must never wait for an answer
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Discard)
    window = MainWindow(Document())
    qtbot.addWidget(window)
    assert window.open(SCENARIO_FILE)
    return window


def column(model, title):
    return [model.headerData(number, Qt.Horizontal) for number in range(model.columnCount())].index(title)


def cell(model, row, title):
    return model.index(row, column(model, title))


def test_window_shows_the_scenario(window):
    assert "Megabus (megabus.json)" in window.windowTitle() and "*" not in window.windowTitle()
    assert list(window.pages) == ["Services", "Fleet", "Traffic lights", "Demand", "Parameters", "Network", "Run"]
    services = window.pages["Services"].model
    assert services.rowCount() == 8
    assert services.data(cell(services, 0, "Service")) == "1E"
    assert services.data(cell(services, 0, "Headway (s)")) == "89"
    assert services.data(cell(services, 0, "Stops")) == "21"
    assert services.data(cell(services, 3, "Buses per hour")) == "0.00"  # a service without buses
    assert window.pages["Traffic lights"].names.count() == 79
    assert window.pages["Demand"].entries.rowCount() == 39
    assert "30,654" in window.pages["Network"].summary.text()


def test_headways_and_frequencies_are_edited(window):
    services = window.pages["Services"].model
    scenario = window.document.scenario
    assert services.setData(cell(services, 0, "Headway (s)"), "240")
    assert scenario.service("1E").headway == 240
    assert services.data(cell(services, 0, "Buses per hour")) == "15.00"
    assert services.setData(cell(services, 1, "Buses per hour"), "12")
    assert scenario.service("2E").headway == 300
    assert services.setData(cell(services, 1, "Buses per hour"), "0")
    assert scenario.service("2E").headway == 1000000
    assert services.setData(cell(services, 2, "First bus (s)"), "30")
    assert scenario.service("3E").offset == 30
    assert services.setData(cell(services, 2, "First bus (s)"), "")
    assert scenario.service("3E").offset is None
    assert "*" in window.windowTitle()


def test_wrong_values_are_refused_with_a_reason(window, qtbot):
    services = window.pages["Services"].model
    for title, value, reason in [
        ("Headway (s)", "0", "must be positive"),
        ("Headway (s)", "fast", "Headway"),
        ("Biarticulated (%)", "120", "between 0 and 100"),
        ("Buses per hour", "-3", "must not be negative"),
    ]:
        with qtbot.waitSignal(services.rejected) as signal:
            assert not services.setData(cell(services, 0, title), value)
        assert reason in signal.args[0]
    assert window.document.scenario.service("1E").headway == 89
    assert not window.document.dirty
    assert "between 0 and 100" in window.statusBar().currentMessage() or "negative" in window.statusBar().currentMessage()
    # the columns that belong to the network are read only
    assert not services.flags(cell(services, 0, "Start cell")) & Qt.ItemIsEditable


def test_changes_are_undone_and_redone(window):
    services = window.pages["Services"].model
    fleet = window.pages["Fleet"].model
    services.setData(cell(services, 0, "Headway (s)"), "240")
    fleet.setData(cell(fleet, 1, "Initial buses"), "20")
    assert window.pages["Fleet"].total.text() == "Total fleet: <b>70</b> buses"

    window.undo_action.trigger()
    assert window.document.scenario.depot("Dosquebradas").initial_buses == 0
    assert fleet.data(cell(fleet, 1, "Initial buses")) == "0"
    window.undo_action.trigger()
    assert services.data(cell(services, 0, "Headway (s)")) == "89"
    assert not window.undo_action.isEnabled() and window.redo_action.isEnabled()
    window.redo_action.trigger()
    window.redo_action.trigger()
    assert window.document.scenario.service("1E").headway == 240
    assert window.document.scenario.depot("Dosquebradas").initial_buses == 20


def test_traffic_light_phases_are_edited(window):
    page = window.pages["Traffic lights"]
    page.names.setCurrentRow(2)
    tl = window.document.scenario.traffic_lights[2]
    assert tl.name == "S3" and [phase.duration for phase in tl.phases] == [30, 30]
    assert [page.phases.headerData(n, Qt.Horizontal) for n in range(3)] == ["Duration (s)", "Green E", "Green W"]

    assert page.phases.setData(cell(page.phases, 0, "Duration (s)"), "45")
    assert page.phases.setData(cell(page.phases, 1, "Green W"), Qt.Checked, Qt.CheckStateRole)
    page.phases_view.selectRow(1)
    page.add_phase()
    assert [(phase.duration, phase.green) for phase in tl.phases] == [(45, [True, True]), (30, [False, True]), (30, [False, False])]
    assert page.cycle.text() == "105 s in 3 phases"
    page.phases_view.selectRow(0)
    page.remove_phase()
    assert len(tl.phases) == 2
    page.offset.setValue(12)
    page.offset.editingFinished.emit()
    assert tl.offset == 12

    # another traffic light has its own phases, and undoing keeps the selection
    page.names.setCurrentRow(0)
    assert page.phases.rowCount() == 2 and page.offset.value() == 0
    page.names.setCurrentRow(2)
    window.undo_action.trigger()
    assert page.names.currentRow() == 2 and page.offset.value() == 0


def test_demand_is_edited(window):
    page = window.pages["Demand"]
    demand = window.document.scenario.demand
    before = list(demand.rates)
    page.scale(2)
    assert demand.rates == [2 * rate for rate in before]
    assert "36,0" in page.total.text()  # about twice the 18,000 passengers

    assert page.profile.data(cell(page.profile, 1, "Time")) == "04:00:10"
    assert page.profile.setData(cell(page.profile, 1, "Time"), "04:00:15")
    assert demand.times[1] == 4 * 3600 + 15
    assert not page.profile.setData(cell(page.profile, 1, "Time"), "05:00")  # after the next row
    rows = len(demand.times)
    page.profile_view.selectRow(1)
    page.add_point()
    assert len(demand.times) == rows + 1 and demand.times[1] < demand.times[2] < demand.times[3]
    page.profile_view.selectRow(2)
    page.remove_point()
    assert len(demand.times) == rows

    assert page.entries.setData(cell(page.entries, 0, "Weight"), "0")
    assert demand.entries["Intercambiador Cuba"] == 0
    assert page.entries.data(cell(page.entries, 0, "Share (%)")) == "0.00"

    destinations = page.destinations
    assert destinations.setData(destinations.index(0, 1), "0.5")
    assert demand.destinations["Intercambiador Cuba"]["San Fernando"] == 0.5
    assert destinations.setData(destinations.index(0, 1), "0")
    assert "San Fernando" not in demand.destinations["Intercambiador Cuba"]
    assert not destinations.setData(destinations.index(0, 1), "-1")


def test_parameters_are_edited(window):
    page = window.pages["Parameters"]
    scenario = window.document.scenario
    capacity = page.fields[1][0]
    assert capacity.value() == 100 and capacity.suffix() == " passengers"
    capacity.setValue(160)
    capacity.editingFinished.emit()
    assert scenario.params.bus_capacity == 160

    page.end.setText("06:30")
    page.end.editingFinished.emit()
    assert scenario.final_time == 6 * 3600 + 1800 and page.end.text() == "06:30:00"
    page.end.setText("03:00")  # before the start
    page.end.editingFinished.emit()
    assert scenario.final_time == 6 * 3600 + 1800 and page.end.text() == "06:30:00"
    page.name.setText("Megabus 2030")
    page.name.editingFinished.emit()
    assert "Megabus 2030" in window.windowTitle()
    window.undo_action.trigger()
    window.undo_action.trigger()
    window.undo_action.trigger()
    assert capacity.value() == 100 and page.end.text() == "09:00:00" and page.name.text() == "Megabus"


def test_scenario_is_saved_and_opened(window, tmp_path):
    services = window.pages["Services"].model
    services.setData(cell(services, 0, "Headway (s)"), "240")
    target = tmp_path / "edited.json"
    assert window.save_to(target)
    assert "edited.json" in window.windowTitle() and "*" not in window.windowTitle()
    assert brtsim.load(target).service("1E").headway == 240
    assert brtsim.load(SCENARIO_FILE).service("1E").headway == 89  # the original file is untouched

    assert window.open(SCENARIO_FILE)
    assert services.data(cell(services, 0, "Headway (s)")) == "89"
    assert not window.undo_action.isEnabled()


def test_a_broken_file_is_not_opened(window, tmp_path, monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "critical", lambda parent, title, text: shown.append(text))
    broken = tmp_path / "broken.json"
    broken.write_text('{"version": 1, "name": "x"}')
    assert not window.open(broken)
    assert "could not be opened" in shown[0]
    assert window.document.scenario.name == "Megabus"


def test_problems_are_listed(window):
    window.check()
    assert window.problems_dock.windowTitle() == "Problems: 3 warnings"
    assert window.problems.item(0).text().startswith("Warning: The jump from cell 1717")

    window.document.scenario.lane_segments[0].services.append("9X")
    assert not window.check()
    assert window.problems_dock.windowTitle() == "Problems: 1 error"
    assert "9X, which is not defined" in window.problems.item(0).text()


def test_scenario_is_simulated_from_the_window(window, qtbot, tmp_path, simulator):
    """The complete task: change the scenario, run it with several seeds and read the results."""
    page = window.run_page
    window.pages["Parameters"].end.setText("05:00")
    window.pages["Parameters"].end.editingFinished.emit()
    services = window.pages["Services"].model
    services.setData(cell(services, 0, "Buses per hour"), "20")
    page.seeds.setValue(3)
    page.first_seed.setValue(5)

    with qtbot.waitSignal(page.finished, timeout=60000):
        window.run_action.trigger()
    assert window.stack.currentWidget() is page
    assert page.results.seeds == [5, 6, 7]
    assert page.progress.value() == 3
    assert page.status.text().startswith("Results of 3 simulations")
    assert page.summary.rowCount() == 9 and page.summary.verticalHeaderItem(0).text() == "Bus speed (km/h)"
    assert float(page.summary.item(0, 0).text()) == pytest.approx(page.results.mean["bus_speed"], abs=1e-3)
    assert page.services.rowCount() == 8 and page.stations.rowCount() == 39
    assert page.start.isEnabled() and not page.cancel.isEnabled()

    # the results are the ones of the interface without a window
    modified = brtsim.load(SCENARIO_FILE)
    modified.final_time = 5 * 3600
    modified.service("1E").headway = 180
    assert page.results.mean == brtsim.run(modified, seeds=[5, 6, 7]).mean

    page.export_results(tmp_path / "results.json")
    assert json.loads((tmp_path / "results.json").read_text())["seeds"] == [5, 6, 7]
    page.export_results(tmp_path / "runs.csv")
    assert (tmp_path / "runs.csv").read_text().startswith("seed,")


def test_a_scenario_with_errors_is_not_simulated(window):
    window.document.scenario.service("1E").headway = 0
    window.run_action.trigger()
    assert not window.run_page.running
    assert "errors" in window.statusBar().currentMessage()


def test_simulations_can_be_cancelled(window, qtbot, simulator):
    page = window.run_page
    page.seeds.setValue(40)
    page.workers.setValue(1)
    with qtbot.waitSignal(page.finished, timeout=60000):
        page.run()
        qtbot.waitUntil(lambda: page.progress.value() >= 1, timeout=30000)
        page.cancel_run()
    assert page.results is None
    assert "cancelled" in page.status.text()
    assert page.start.isEnabled()


def test_times_are_written_as_hours():
    assert format_time(4 * 3600 + 75) == "04:01:15"
    assert parse_time("04:01:15") == parse_time("4:01:15") == 4 * 3600 + 75
    assert parse_time("06:30") == 6 * 3600 + 1800
    assert parse_time("14400") == 14400
    for wrong in ("06:75", "1:2:3:4", "soon"):
        with pytest.raises(ValueError):
            parse_time(wrong)
