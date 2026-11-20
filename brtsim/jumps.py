"""The creation of jumps, and the rules that keep them free of collisions.

The buses advance along a single coordinate, so the parts of a system that are not consecutive are
connected with jumps: the buses reaching a cell continue from another cell. A bus that jumps appears
in the landing lane, and the buses around it must be able to see it coming. Two rules guarantee it:

1. No bus can reach the landing cell along the landing lane. The lane must start at the landing
   cell, so that a jumping bus never finds buses arriving from behind.
2. No bus can change into the lane of the jump during the SAFE_DISTANCE cells before the jump, nor
   into the landing lane during the SAFE_DISTANCE cells after the landing.

add_jump refuses to create a jump that breaks these rules, and unsafe_jumps reports the jumps of a
scenario that break them, for example after its lanes are modified.
"""

from .compiler import ScenarioError, _lane_arrays
from .model import Jump, Scenario

SAFE_DISTANCE = 50  # the minimal number of cells without lane changes before and after a jump


def add_jump(scenario: Scenario, x, lane, to_x, to_lane, safe_distance=SAFE_DISTANCE):
    """Adds a jump to the scenario and returns it. Raises ScenarioError, leaving the scenario untouched, if the jump is not safe."""
    jump = Jump(x, lane, to_x, to_lane)
    problems = jump_problems(scenario, jump, safe_distance)
    if problems:
        raise ScenarioError(problems)
    scenario.jumps.append(jump)
    return jump


def unsafe_jumps(scenario: Scenario, safe_distance=SAFE_DISTANCE):
    """The jumps of the scenario that break the rules, as a list of (jump, problems)."""
    lanes = _lane_arrays(scenario)
    unsafe = []
    for jump in scenario.jumps:
        problems = jump_problems(scenario, jump, safe_distance, lanes)
        if problems:
            unsafe.append((jump, problems))
    return unsafe


def jump_problems(scenario: Scenario, jump: Jump, safe_distance=SAFE_DISTANCE, lanes=None):
    """The reasons why a jump is not safe, empty if it is. The jump may or may not be in the scenario already."""
    if safe_distance < SAFE_DISTANCE:
        raise ValueError(f"The safe distance of a jump must be at least {SAFE_DISTANCE} cells")
    where = f"the jump from cell {jump.x} in lane {jump.lane} to cell {jump.to_x} in lane {jump.to_lane}"

    def inside(x, lane):
        return 0 <= x < scenario.length and 0 <= lane < scenario.lanes

    if not (inside(jump.x, jump.lane) and inside(jump.to_x, jump.to_lane)):
        return [f"{where} has a position outside the system"]
    if (jump.x, jump.lane) == (jump.to_x, jump.to_lane):
        return [f"{where} lands where it starts"]
    if lanes is None:
        lanes = _lane_arrays(scenario)  # [service][lane][cell]
    names = [service.name for service in scenario.services]
    problems = []

    for other in scenario.jumps:
        if other is not jump and (other.x, other.lane) == (jump.x, jump.lane):
            problems.append(f"{where} starts at a cell that already has a jump")

    # the services taking the jump are the ones circulating on its cell
    jumping = [i for i in range(len(names)) if lanes[i, jump.lane, jump.x]]
    if not jumping:
        problems.append(f"{where} starts at a cell where no service circulates")
    for i in jumping:
        if not lanes[i, jump.to_lane, jump.to_x]:
            problems.append(f"{where} is taken by service {names[i]}, which may not circulate on the landing cell")

    # Rule 1: no bus can reach the landing cell along the landing lane
    for i, name in enumerate(names):
        # the cells right before the landing where the service may circulate
        first = jump.to_x
        while first > 0 and lanes[i, jump.to_lane, first - 1]:
            first -= 1
        if first == jump.to_x:
            continue
        reason = _entrance(scenario, lanes, i, jump.to_lane, first, jump.to_x, jump)
        if reason:
            problems.append(
                f"{where} lands in front of the buses of service {name}, which circulate on the landing lane "
                f"from cell {first} ({reason}). The landing lane must start at the landing cell"
            )

    # Rule 2: no lane changes into the lane of the jump before it, nor into the landing lane after it
    windows = [
        ("before the jump", jump.lane, jump.x - safe_distance, jump.x),
        ("after the landing", jump.to_lane, jump.to_x, jump.to_x + safe_distance),
    ]
    for moment, lane, first, last in windows:
        first, last = max(first, 0), min(last, scenario.length - 1)
        for neighbour in (lane - 1, lane + 1):
            if not 0 <= neighbour < scenario.lanes:
                continue
            # a service changes lane where it may circulate on both lanes
            both = lanes[:, lane, first : last + 1] & lanes[:, neighbour, first : last + 1]
            if not both.any():
                continue
            changing = ", ".join(name for name, changes in zip(names, both.any(axis=1)) if changes)
            cells = both.any(axis=0).nonzero()[0] + first
            problems.append(
                f"{where} allows lane changes from lane {neighbour} into lane {lane} {moment}, between cells "
                f"{cells[0]} and {cells[-1]} (services {changing}). Lane changes are not allowed during the "
                f"{safe_distance} cells {moment}, from cell {first} to cell {last}"
            )
    return problems


def _entrance(scenario, lanes, service, lane, first, end, jump):
    """How the buses of a service get into the cells [first, end) of a lane, None if they cannot.

    The service may not circulate on the cell before first, so the buses can only start there, land
    there from another jump, or change from the lanes at the sides.
    """
    start = scenario.services[service]
    if start.start_lane == lane and first <= start.start_x < end:
        return f"the service starts at cell {start.start_x}"
    for other in scenario.jumps:
        if other is jump or (other.x, other.lane) == (jump.x, jump.lane):
            continue
        if other.to_lane == lane and first <= other.to_x < end and lanes[service, other.lane, other.x]:
            return f"they land at cell {other.to_x} from another jump"
    for neighbour in (lane - 1, lane + 1):
        if 0 <= neighbour < scenario.lanes:
            cells = lanes[service, neighbour, first:end].nonzero()[0]
            if len(cells) > 0:
                return f"they can change from lane {neighbour} at cell {cells[0] + first}"
    return None
