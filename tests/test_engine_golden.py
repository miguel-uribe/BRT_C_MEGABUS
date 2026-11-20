"""The results of the engine for the reference configuration must not change unintentionally.

The comparisons are exact: a fixed seed must reproduce the recorded results bit by bit.
"""

import pytest

import golden_tools as gt


@pytest.mark.parametrize("seed, cfract", gt.ENGINE_CASES)
def test_results_match_golden(simulator, engine_golden, seed, cfract):
    assert gt.run_case(simulator, seed, cfract) == engine_golden["cases"][gt.case_key(seed, cfract)]


def test_bus_trajectory_matches_golden(simulator, engine_golden):
    seed, cfract = gt.TRAJECTORY_CASE
    assert gt.run_trajectory(simulator, seed, cfract) == engine_golden["trajectory"][gt.case_key(seed, cfract)]


def test_same_seed_gives_same_results(simulator):
    assert gt.run_case(simulator, 11, 1.0) == gt.run_case(simulator, 11, 1.0)


def test_different_seeds_give_different_results(simulator):
    assert gt.run_case(simulator, 11, 1.0) != gt.run_case(simulator, 12, 1.0)


def test_detailed_output_does_not_change_results(simulator):
    """Asking for the bus data must not alter the simulation."""
    seed, cfract = gt.TRAJECTORY_CASE
    with gt.engine_cwd():
        detailed = simulator.simulate(seed, 1, cfract)
    assert {name: getattr(detailed, name) for name in gt.KPI_NAMES} == gt.run_case(simulator, seed, cfract)
