"""The in-memory configuration and the step by step simulation."""

import numpy as np
import pytest

import golden_tools as gt

SEED = 5


@pytest.fixture(scope="module")
def config(simulator, conf):
    return simulator.load_config(str(conf))


def kpis(results):
    return {name: getattr(results, name) for name in gt.KPI_NAMES}


def run(simulator, config, seed=SEED):
    simulation = simulator.Simulation(config, seed)
    simulation.run()
    return simulation.results()


def test_in_memory_run_matches_simulate(simulator, config):
    """The legacy function and the new interface are the same simulation."""
    assert kpis(run(simulator, config)) == gt.run_case(simulator, SEED, 1.0)


def test_configuration_can_be_reused(simulator, config):
    assert kpis(run(simulator, config)) == kpis(run(simulator, config))


def test_stepping_matches_run(simulator, config):
    simulation = simulator.Simulation(config, SEED)
    assert simulation.time == config.initial_time
    simulation.step()
    assert simulation.time == config.initial_time + 1
    while not simulation.done:
        simulation.step(997)
        simulation.results()  # asking for the results must not alter the simulation
    assert simulation.time == config.final_time
    assert kpis(simulation.results()) == kpis(run(simulator, config))


def test_recorded_bus_data_matches_simulate(simulator, config):
    simulation = simulator.Simulation(config, SEED, record=True)
    simulation.run()
    with gt.engine_cwd():
        legacy = simulator.simulate(SEED, 1, 1.0)
    data = simulation.bus_data()
    assert data.shape[1] == len(simulator.BUS_COLUMNS) + 1
    assert np.array_equal(data, np.asarray(legacy.BusData))


def test_state_can_be_observed_while_running(simulator, config):
    simulation = simulator.Simulation(config, SEED)
    simulation.step(2 * 3600)
    buses = simulation.buses()
    assert buses.ndim == 2 and buses.shape[1] == len(simulator.BUS_COLUMNS)
    assert len(buses) > 0
    occupation = buses[:, simulator.BUS_COLUMNS.index("occupation")]
    assert (occupation >= 0).all()
    assert len(simulation.station_passengers()) == len(config.stations)
    assert len(simulation.traffic_light_phases()) == len(config.traffic_lights)
    fleet = sum(depot.initial_buses for depot in config.depots)
    assert sum(simulation.parked_buses()) + len(buses) == fleet
    assert len(simulation.queued_buses()) == len(config.depots)


def test_headways_are_changed_in_memory(simulator, config, conf):
    before = (conf / "service_data.txt").read_bytes()
    modified = simulator.SimConfig(config)
    modified.lines[0].headway = 2 * config.lines[0].headway

    assert modified.lines[0].headway == 2 * config.lines[0].headway
    assert kpis(run(simulator, modified)) != kpis(run(simulator, config))
    assert (conf / "service_data.txt").read_bytes() == before


def test_fleet_and_demand_are_changed_in_memory(simulator, config):
    base = run(simulator, config)

    small_fleet = simulator.SimConfig(config)
    small_fleet.depots[0].initial_buses = 10
    assert kpis(run(simulator, small_fleet)) != kpis(base)

    low_demand = simulator.SimConfig(config)
    low_demand.demand_means = [mean / 2 for mean in config.demand_means]
    assert run(simulator, low_demand).passengers < 0.6 * base.passengers


def test_time_window_is_configurable(simulator, config):
    short = simulator.SimConfig(config)
    short.final_time = short.initial_time + 600
    simulation = simulator.Simulation(short, SEED)
    simulation.run()
    assert simulation.time == short.initial_time + 600


def test_detailed_results_are_consistent(simulator, config):
    results = run(simulator, config)
    assert results.passengers > 0
    assert sum(results.station_entries) == results.passengers
    assert sum(results.station_alightings) == results.delivered
    assert 0 < results.delivered <= results.passengers
    assert sum(results.station_boardings) == sum(results.line_boardings)
    assert sum(results.station_boardings) >= results.delivered
    assert results.travel_time > 0
    assert len(results.station_waiting) == len(config.stations)
    assert len(results.line_trip_time) == len(config.lines)
    assert sum(results.line_departures) > 0 and sum(results.line_arrivals) > 0
    assert results.occ == pytest.approx(sum(results.station_waiting) / len(config.stations), rel=1e-3)


def test_invalid_configurations_are_rejected(simulator, config):
    zero_headway = simulator.SimConfig(config)
    zero_headway.lines[0].headway = 0
    with pytest.raises(ValueError, match="headway"):
        simulator.Simulation(zero_headway, SEED)

    wrong_demand = simulator.SimConfig(config)
    wrong_demand.IN = config.IN[:-1]
    with pytest.raises(ValueError, match="IN"):
        wrong_demand.validate()


def test_simulate_rejects_an_invalid_print_argument(simulator):
    with gt.engine_cwd(), pytest.raises(ValueError):
        simulator.simulate(1, 2, 1.0)


def test_missing_configuration_files_are_reported(simulator, tmp_path):
    with pytest.raises(RuntimeError, match="station_list.txt"):
        simulator.load_config(str(tmp_path))
