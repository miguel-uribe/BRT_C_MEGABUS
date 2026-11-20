"""The scenario model, the importer of the original configuration and the compiler."""

import json

import numpy as np
import pytest

import golden_tools as gt
from brtsim import ScenarioError, compile_scenario, load, model, validate
from brtsim.compiler import DEFAULT_GAP, _lane_changes
from brtsim.engine import engine_config
from brtsim.legacy import import_megabus
from brtsim.model import (
    Bay,
    Demand,
    Depot,
    LaneSegment,
    Phase,
    Scenario,
    Service,
    SignalHead,
    Station,
    TrafficLight,
)

SCENARIO_FILE = gt.ROOT / "scenarios" / "megabus.json"


@pytest.fixture(scope="module")
def megabus(conf):
    # the layout has one cell with a note instead of a definition
    with pytest.warns(UserWarning, match="'Bat' is not understood"):
        return import_megabus()


def describe(config):
    """Everything in an engine configuration, as plain data."""
    line_fields = "name headway biart offset origin or_lane end stationIDs wagons stoptracks tls tldir tltracks breaks change_pos dest_line"
    tl_fields = "name directions positions lengths durations phases phasetime curr_phase"
    param_fields = "busL p p0 pentime BusRate BusCap D0 D1 MaxDwell insertion_period max_offset"
    return {
        "lines": [{name: getattr(line, name) for name in line_fields.split()} for line in config.lines],
        "stations": [(station.stop_pos, station.stop_biart) for station in config.stations],
        "traffic_lights": [{name: getattr(tl, name) for name in tl_fields.split()} for tl in config.traffic_lights],
        "depots": [(depot.name, depot.origin, depot.end, depot.initial_buses) for depot in config.depots],
        "breaks": config.breaks,
        "EL": config.EL,
        "LC": config.LC,
        "RC": config.RC,
        "V": config.V,
        "route_weights": config.route_weights,
        "IN": config.IN,
        "OD": config.OD,
        "demand_times": config.demand_times,
        "demand_rates": config.demand_rates,
        "initial_time": config.initial_time,
        "final_time": config.final_time,
        "params": {name: getattr(config.params, name) for name in param_fields.split()},
    }


def test_megabus_compiles_to_the_original_configuration(megabus, simulator, conf):
    """The compiler gives exactly what layout_interpreter.py and routegenerator.py wrote in conf/."""
    compiled = describe(engine_config(compile_scenario(megabus)))
    original = describe(simulator.load_config(str(conf)))
    for name in original:
        assert compiled[name] == original[name], f"{name} is different"


def test_megabus_scenario_reproduces_the_golden_results(megabus, simulator, engine_golden):
    seed, cfract = 1, 1.0  # the scenario has the entire fleet in the first depot
    simulation = simulator.Simulation(engine_config(compile_scenario(megabus)), seed)
    simulation.run()
    results = simulation.results()
    assert {name: getattr(results, name) for name in gt.KPI_NAMES} == engine_golden["cases"][gt.case_key(seed, cfract)]


def test_scenario_file_is_up_to_date(megabus):
    """scenarios/megabus.json is the import of the original files, recreate it with: uv run python -m brtsim.legacy"""
    assert load(SCENARIO_FILE) == megabus


def test_scenario_survives_a_round_trip(megabus, tmp_path):
    megabus.save(tmp_path / "scenario.json")
    assert load(tmp_path / "scenario.json") == megabus
    assert megabus.copy() == megabus


def test_malformed_scenario_files_are_rejected(megabus):
    data = model.to_dict(megabus)
    with pytest.raises(ValueError, match="version"):
        model.from_dict({**data, "version": 99})
    with pytest.raises(ValueError, match="unknown fields"):
        model.from_dict({**data, "colour": "red"})
    with pytest.raises(ValueError, match="scenario.length must be an integer"):
        model.from_dict({**data, "length": "long"})
    broken = json.loads(json.dumps(data))
    del broken["services"][0]["name"]
    with pytest.raises(ValueError, match=r"scenario.services\[0\]"):
        model.from_dict(broken)


def test_problems_are_reported_together(megabus):
    scenario = megabus.copy()
    scenario.services[0].headway = 0
    scenario.stations[3].bays[0].services.append("9X")
    scenario.stations[5].bays[0].lane = 0  # a lane where its services do not circulate
    scenario.lane_segments.append(LaneSegment(2, 100, 200, ["1E"]))
    scenario.demand.entries["Nowhere"] = 0.5

    problems = validate(scenario)
    assert any("service 1E must have a positive headway" in problem for problem in problems)
    assert any("9X, which is not defined" in problem for problem in problems)
    assert any("may not circulate there" in problem for problem in problems)
    assert any("overlaps another segment" in problem for problem in problems)
    assert any("station Nowhere, which is not defined" in problem for problem in problems)
    with pytest.raises(ScenarioError) as error:
        compile_scenario(scenario)
    assert error.value.problems == problems


def test_a_stop_outside_the_path_is_reported(megabus):
    scenario = megabus.copy()
    # service 3E ends at cell 7273, a stop after that cell is never reached
    scenario.lane_segments.append(LaneSegment(0, 9000, 9100, ["3E"]))
    scenario.stations[0].bays.append(Bay(9050, 0, ["3E"]))
    with pytest.raises(ScenarioError, match="path of service 3E"):
        compile_scenario(scenario)


def test_headway_changes_reach_the_engine(megabus):
    scenario = megabus.copy()
    scenario.service("2E").headway = 300
    scenario.depot("Dosquebradas").initial_buses = 12
    config = engine_config(compile_scenario(scenario))
    assert config.lines[1].headway == 300
    assert config.depots[1].initial_buses == 12


def small_scenario():
    """A corridor of two kilometers with one service, three stations and a traffic light."""
    scenario = Scenario(name="small", length=2000, lanes=2, initial_time=0, final_time=1800)
    scenario.lane_segments = [LaneSegment(0, 0, 2000, ["A"]), LaneSegment(1, 400, 1600, ["A"])]
    scenario.stations = [
        Station("First", [Bay(100, 0, ["A"])]),
        Station("Second", [Bay(1000, 0, ["A"])]),
        Station("Third", [Bay(1900, 0, ["A"])]),
    ]
    scenario.traffic_lights = [
        TrafficLight("T1", ["N"], [Phase(20, [True]), Phase(20, [False])], heads=[SignalHead("N", 600, 0)])
    ]
    scenario.services = [Service("A", start_x=0, start_lane=0, end_x=1999, headway=120, offset=0)]
    scenario.depots = [Depot("Depot", origin=0, end=1999, initial_buses=10)]
    scenario.demand = Demand(
        times=[0, 1800],
        rates=[600.0, 600.0],
        entries={"First": 0.7, "Second": 0.3},
        destinations={"First": {"Second": 0.5, "Third": 0.5}, "Second": {"Third": 1.0}},
    )
    return scenario


def test_a_scenario_written_by_hand_can_be_simulated(simulator):
    compiled = compile_scenario(small_scenario())
    assert compiled.services[0].station_ids == [0, 1, 2]
    assert compiled.services[0].tls == [0]
    assert compiled.EL[0, 1, 400] == 1600 - 1 - 400  # the second lane ends at cell 1599
    assert compiled.EL[0, 0, 0] == DEFAULT_GAP  # the first lane does not end
    assert compiled.route_weights[0, 2, 0] > 0 and compiled.route_weights[2, 0, 0] == 0

    simulation = simulator.Simulation(engine_config(compiled), seed=1)
    simulation.run()
    results = simulation.results()
    assert results.passengers == pytest.approx(300, rel=0.2)
    assert results.delivered > 0.5 * results.passengers
    assert results.line_departures == [15]
    assert results.station_entries[2] == 0


def test_lane_changes_match_the_original_algorithm():
    """The vectorized lane arrays are the ones of the loops in layout_interpreter.py."""
    random = np.random.default_rng(1)
    for _ in range(20):
        nlanes, length = int(random.integers(1, 5)), int(random.integers(5, 60))
        # the original format is [cell][lane]
        lanes = (random.random((length, nlanes)) < 0.8).astype(int)

        LC = np.copy(lanes)
        LC[:, -1] = 0
        LC[(lanes - np.roll(lanes, -1, axis=1)) == 1] = 0
        RC = np.copy(lanes)
        RC[:, 0] = 0
        RC[(lanes - np.roll(lanes, 1, axis=1)) == 1] = 0
        EL = 1000 * np.ones(np.shape(lanes))
        auxEL = np.zeros(np.shape(lanes))
        auxEL[(np.roll(lanes, 1, axis=0) - lanes) == 1] = 1
        for i in range(nlanes):
            endF = False
            for j in np.arange(length - 1, -1, -1):
                if endF:
                    EL[j, i] = endPos - j
                if auxEL[j, i] == 1:
                    endF = True
                    endPos = j - 1

        new_LC, new_RC, new_EL = _lane_changes(lanes.T[np.newaxis].astype(np.int32))
        assert np.array_equal(new_LC[0].T, LC)
        assert np.array_equal(new_RC[0].T, RC)
        assert np.array_equal(new_EL[0].T, EL)
