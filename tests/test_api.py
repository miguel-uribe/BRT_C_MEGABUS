"""The interface to run simulations without a user interface, and the command line."""

import json
import math

import pytest

import brtsim
import golden_tools as gt
from brtsim.__main__ import main
from brtsim.results import KPIS, student_t_quantile

SCENARIO_FILE = gt.ROOT / "scenarios" / "megabus.json"
HOUR = {"final_time": 5 * 3600}  # most tests simulate one hour instead of five


@pytest.fixture(scope="module")
def scenario():
    return brtsim.load(SCENARIO_FILE)


@pytest.fixture(scope="module")
def model(scenario, simulator):
    return brtsim.prepare(scenario)


def test_run_reproduces_the_golden_results(model, engine_golden):
    golden = engine_golden["cases"][gt.case_key(1, 1.0)]
    (run,) = model.run(seeds=[1]).runs
    assert run.seed == 1
    assert run.kpis["bus_speed"] == golden["BSP"] * 3.6
    assert run.kpis["passenger_speed"] == golden["passp"] * 3.6
    assert run.kpis["bus_hours"] == golden["cost"]
    assert run.kpis["waiting_passengers"] == golden["occ"]
    assert run.kpis["passenger_flow"] == golden["flow"]
    assert run.kpis["bus_queue"] == golden["queue"]


def test_changes_are_the_same_as_modifying_the_scenario(scenario, model):
    changes = {
        "headways": {"1E": 240},
        "frequencies": {"2W": 30},
        "offsets": {"2E": 7},
        "fleet": {"Cuba": 30, "Dosquebradas": 20},
        "demand_scale": 1.5,
        "params": {"bus_capacity": 160, "dwell_max": 45},
    }
    modified = scenario.copy()
    modified.service("1E").headway = 240
    modified.service("2W").headway = 120
    modified.service("2E").offset = 7
    modified.depot("Cuba").initial_buses = 30
    modified.depot("Dosquebradas").initial_buses = 20
    modified.demand.rates = [1.5 * rate for rate in modified.demand.rates]
    modified.params.bus_capacity = 160
    modified.params.dwell_max = 45
    modified.final_time = HOUR["final_time"]

    fast = model.run(seeds=[3], **changes, **HOUR)
    assert fast.runs[0].kpis == brtsim.run(modified, seeds=[3]).runs[0].kpis
    assert fast.runs[0].kpis != model.run(seeds=[3], **HOUR).runs[0].kpis


def test_a_model_is_not_affected_by_later_changes_to_the_scenario(scenario):
    scenario = scenario.copy()
    model = brtsim.prepare(scenario)
    before = model.run(seeds=[1], **HOUR).runs[0].kpis
    scenario.service("1E").headway = 1000
    assert model.run(seeds=[1], **HOUR).runs[0].kpis == before


def test_parallel_runs_match_sequential_runs(model):
    sequential = model.run(seeds=6, workers=1, **HOUR)
    parallel = model.run(seeds=6, workers=6, **HOUR)
    assert sequential.seeds == parallel.seeds == [1, 2, 3, 4, 5, 6]
    assert [run.kpis for run in sequential.runs] == [run.kpis for run in parallel.runs]
    assert len({run.kpis["bus_speed"] for run in parallel.runs}) == 6


def test_frequency_sweep_runs_in_parallel_without_writing_files(model, tmp_path, monkeypatch):
    """Several cases with several seeds each, nothing is read from or written to disk."""
    monkeypatch.chdir(tmp_path)
    watched = [gt.CONF_DIR, gt.ROOT / "scenarios", gt.ROOT / "src_cpp"]
    before = {path: path.stat().st_mtime_ns for folder in watched for path in folder.iterdir()}

    frequencies = [0, 6, 12, 24, 48]
    cases = [{"frequencies": {"1E": frequency}, **HOUR} for frequency in frequencies]
    calls = []
    sweep = model.run_many(cases, seeds=4, workers=8, progress=lambda done, total: calls.append((done, total)))

    assert len(sweep) == len(cases) and all(len(results.runs) == 4 for results in sweep)
    assert calls == [(done, 20) for done in range(1, 21)]
    departures = [results.services.loc["1E", "departures"] for results in sweep]
    assert departures[0] == 0
    assert departures == sorted(departures) and departures[-1] > departures[1]
    assert list(tmp_path.iterdir()) == []
    assert {path: path.stat().st_mtime_ns for folder in watched for path in folder.iterdir()} == before


def test_results_are_aggregated(model):
    results = model.run(seeds=[11, 12, 13, 14, 15], **HOUR)
    summary = results.summary()
    assert list(summary.index) == list(KPIS)
    for kpi in KPIS:
        values = results.values(kpi)
        assert results.mean[kpi] == pytest.approx(values.mean())
        assert summary.loc[kpi, "ci_low"] <= results.mean[kpi] <= summary.loc[kpi, "ci_high"]
    # the half width of the interval is t * s / sqrt(n), with t = 2.776 for 4 degrees of freedom
    low, high = results.confidence_interval()["bus_speed"]
    assert (high - low) / 2 == pytest.approx(2.776 * results.std["bus_speed"] / math.sqrt(5), rel=2e-3)
    assert list(results.stations.index) == model.station_names
    assert list(results.services.index) == model.service_names
    assert results.stations["entries"].sum() == pytest.approx(results.mean["passengers"])
    assert list(results.per_run().index) == [11, 12, 13, 14, 15]
    assert json.loads(json.dumps(results.to_dict()))["seeds"] == [11, 12, 13, 14, 15]


def test_a_single_run_has_no_deviation(model):
    results = model.run(seeds=1, **HOUR)
    assert math.isnan(results.std["bus_speed"])
    assert results.mean["bus_speed"] > 0


def test_student_quantiles():
    # the quantiles for a 95% interval, from the tables
    for freedom, expected in [(1, 12.706), (2, 4.303), (3, 3.182), (4, 2.776), (9, 2.262), (19, 2.093), (39, 2.023)]:
        assert student_t_quantile(0.975, freedom) == pytest.approx(expected, rel=2e-3)


def test_wrong_changes_are_rejected(model):
    with pytest.raises(ValueError, match="no service named '9X'"):
        model.run(headways={"9X": 100})
    with pytest.raises(ValueError, match="no depot named"):
        model.run(fleet={"Nowhere": 3})
    with pytest.raises(ValueError, match="both a headway and a frequency"):
        model.run(headways={"1E": 100}, frequencies={"1E": 10})
    with pytest.raises(ValueError, match="no parameter named"):
        model.run(params={"colour": 1})
    with pytest.raises(ValueError, match="must be different"):
        model.run(seeds=[1, 1])
    with pytest.raises(ValueError, match="headway"):
        model.run(headways={"1E": 0})


def test_step_by_step_simulation(model):
    simulation = model.simulation(seed=2, frequencies={"1E": 60}, **HOUR)
    simulation.step(1800)
    assert len(simulation.buses()) > 0
    assert len(simulation.station_passengers()) == len(model.station_names)


def test_command_line_run(tmp_path, capsys, simulator):
    output = tmp_path / "results.json"
    code = main(["run", str(SCENARIO_FILE), "--seeds", "2", "--frequency", "1E=20", "--buses", "Cuba=40", "--services", "--output", str(output)])
    printed = capsys.readouterr().out
    assert code == 0
    assert "bus_speed" in printed and "departures" in printed
    stored = json.loads(output.read_text())
    assert stored["seeds"] == [1, 2] and set(stored["summary"]) == set(KPIS)

    assert main(["run", str(SCENARIO_FILE), "--seeds", "2", "--first-seed", "5", "--output", str(tmp_path / "runs.csv")]) == 0
    assert (tmp_path / "runs.csv").read_text().splitlines()[1].startswith("5,")


def test_command_line_reports_errors(tmp_path, capsys, scenario):
    assert main(["run", str(SCENARIO_FILE), "--headway", "9X=100"]) == 1
    assert "no service named '9X'" in capsys.readouterr().err
    assert main(["run", str(SCENARIO_FILE), "--headway", "1E"]) == 1
    assert "expects NAME=VALUE" in capsys.readouterr().err
    assert main(["run", str(tmp_path / "missing.json")]) == 1

    broken = scenario.copy()
    broken.service("1E").headway = 0
    broken.save(tmp_path / "broken.json")
    assert main(["validate", str(tmp_path / "broken.json")]) == 1
    assert "service 1E must have a positive headway" in capsys.readouterr().out


def test_command_line_validate_warns_about_unsafe_jumps(capsys):
    assert main(["validate", str(SCENARIO_FILE)]) == 0
    printed = capsys.readouterr().out
    assert "The scenario is valid." in printed
    assert "3 jumps do not follow the rules" in printed
