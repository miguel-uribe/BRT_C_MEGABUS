"""The rules that keep the jumps free of collisions."""

import pytest

from brtsim import ScenarioError, load
from brtsim.jumps import SAFE_DISTANCE, add_jump, jump_problems, unsafe_jumps
from brtsim.model import Jump, LaneSegment, Scenario, Service

import golden_tools as gt

JUMP = (999, 0, 2000, 0)  # from the last cell of the first part to the first cell of the second one


def two_parts(*extra_segments, services=("A",)):
    """Service A circulates on lane 0 from cell 0 to 999, and from cell 2000 to 2999. The system has three lanes."""
    scenario = Scenario(name="two parts", length=3000, lanes=3)
    scenario.lane_segments = [LaneSegment(0, 0, 1000, ["A"]), LaneSegment(0, 2000, 3000, ["A"]), *extra_segments]
    scenario.services = [Service(name, start_x=0, start_lane=0, end_x=2999) for name in services]
    return scenario


def lane_one(start, end, services=("A",), lane=1):
    return LaneSegment(lane, start, end, list(services))


def test_a_safe_jump_is_created():
    scenario = two_parts()
    jump = add_jump(scenario, *JUMP)
    assert scenario.jumps == [jump] == [Jump(999, 0, 2000, 0)]
    assert unsafe_jumps(scenario) == []


def rejected(scenario, jump=JUMP):
    """The problems of a jump that must be refused, the scenario must be left untouched."""
    with pytest.raises(ScenarioError) as error:
        add_jump(scenario, *jump)
    assert scenario.jumps == []
    return error.value.problems


# Rule 1: no bus can reach the landing cell along the landing lane


def test_landing_in_front_of_buses_changing_into_the_lane_is_refused():
    # the landing lane is open from cell 1900, and the buses can get into it from lane 1
    scenario = two_parts(LaneSegment(0, 1900, 2000, ["A"]), lane_one(1900, 1920))
    (problem,) = rejected(scenario)
    assert "service A" in problem and "from cell 1900" in problem and "change from lane 1 at cell 1900" in problem


def test_landing_in_front_of_a_service_starting_upstream_is_refused():
    scenario = two_parts(LaneSegment(0, 1900, 2000, ["B"]), services=("A", "B"))
    scenario.lane_segments[1].services = ["A", "B"]
    scenario.service("B").start_x = 1950
    (problem,) = rejected(scenario)
    assert "lands in front of the buses of service B" in problem and "starts at cell 1950" in problem


def test_landing_in_front_of_buses_landing_from_another_jump_is_refused():
    scenario = two_parts(LaneSegment(0, 1900, 2000, ["A"]), LaneSegment(2, 0, 500, ["A"]))
    add_jump(scenario, 499, 2, 1900, 0)
    with pytest.raises(ScenarioError, match="they land at cell 1900 from another jump"):
        add_jump(scenario, *JUMP)
    assert len(scenario.jumps) == 1


def test_cells_no_bus_can_reach_before_the_landing_are_accepted():
    # the lane is open before the landing, but no bus can get into those cells
    scenario = two_parts(LaneSegment(0, 1998, 2000, ["A"]))
    add_jump(scenario, *JUMP)


# Rule 2: no lane changes into the lane of the jump before it, nor into the landing lane after it


@pytest.mark.parametrize(
    "start, end, moment",
    [
        (900, 950, "before the jump"),  # the last change is 50 cells before the jump
        (999, 1000, "before the jump"),  # at the cell of the jump
        (2000, 2001, "after the landing"),  # at the landing cell
        (2050, 2100, "after the landing"),  # the first change is 50 cells after the landing
    ],
)
def test_lane_changes_within_the_safe_distance_are_refused(start, end, moment):
    scenario = two_parts(lane_one(start, end))
    (problem,) = rejected(scenario)
    assert f"lane changes from lane 1 into lane 0 {moment}" in problem
    assert "services A" in problem


@pytest.mark.parametrize("start, end", [(800, 949), (2051, 2100), (1000, 2000)])
def test_lane_changes_beyond_the_safe_distance_are_accepted(start, end):
    # the closest change is 51 cells away from the jump or the landing
    scenario = two_parts(lane_one(start, end))
    add_jump(scenario, *JUMP)


def test_other_services_on_the_next_lane_are_accepted():
    # service B circulates next to the jump, but neither service may use both lanes
    scenario = two_parts(lane_one(0, 3000, ["B"]), services=("A", "B"))
    add_jump(scenario, *JUMP)


def test_lane_changes_from_both_sides_are_checked():
    scenario = two_parts()
    scenario.lane_segments = [LaneSegment(1, 0, 1000, ["A"]), LaneSegment(1, 2000, 3000, ["A"]), LaneSegment(2, 2010, 2020, ["A"])]
    scenario.services[0].start_lane = 1
    (problem,) = rejected(scenario, (999, 1, 2000, 1))
    assert "from lane 2 into lane 1 after the landing, between cells 2010 and 2019" in problem


def test_a_larger_safe_distance_can_be_required():
    scenario = two_parts(lane_one(2060, 2100))
    assert jump_problems(scenario, Jump(*JUMP)) == []
    assert len(jump_problems(scenario, Jump(*JUMP), safe_distance=80)) == 1
    with pytest.raises(ValueError, match="at least 50"):
        jump_problems(scenario, Jump(*JUMP), safe_distance=SAFE_DISTANCE - 1)


# The jump itself


def test_jumps_that_make_no_sense_are_refused():
    scenario = two_parts()
    assert "outside the system" in rejected(scenario, (999, 0, 3000, 0))[0]
    assert "outside the system" in rejected(scenario, (999, 3, 2000, 0))[0]
    assert "lands where it starts" in rejected(scenario, (999, 0, 999, 0))[0]
    assert "no service circulates" in rejected(scenario, (1500, 0, 2000, 0))[0]
    assert "may not circulate on the landing cell" in rejected(scenario, (999, 0, 1500, 0))[0]
    add_jump(scenario, *JUMP)
    with pytest.raises(ScenarioError, match="already has a jump"):
        add_jump(scenario, 999, 0, 2500, 0)


def test_unsafe_jumps_are_found_after_the_lanes_change():
    scenario = two_parts()
    jump = add_jump(scenario, *JUMP)
    scenario.lane_segments.append(lane_one(2020, 2030))
    ((found, problems),) = unsafe_jumps(scenario)
    assert found is jump and len(problems) == 1


def test_megabus_jumps_that_break_the_rules():
    """The original layout has three jumps with lane changes closer than the safe distance."""
    scenario = load(gt.ROOT / "scenarios" / "megabus.json")
    unsafe = {(jump.x, jump.lane): problems for jump, problems in unsafe_jumps(scenario)}
    assert sorted(unsafe) == [(1717, 1), (7301, 0), (26834, 1)]
    assert all(len(problems) == 1 for problems in unsafe.values())
    assert "from lane 2 into lane 1 before the jump, between cells 1667 and 1707" in unsafe[(1717, 1)][0]
    assert "from lane 1 into lane 0 after the landing, between cells 23525 and 23525" in unsafe[(7301, 0)][0]
    assert "from lane 2 into lane 1 after the landing, between cells 27296 and 27306" in unsafe[(26834, 1)][0]
