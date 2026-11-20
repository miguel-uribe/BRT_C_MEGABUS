"""The compiler: it turns a scenario into the arrays the engine works with.

It produces the same information the scripts layout_interpreter.py and routegenerator.py wrote in the
conf/ folder, without writing any file. The order of the services, stations, bays and traffic lights in
the scenario gives their indices in the engine.
"""

from dataclasses import dataclass, field

import numpy as np

from .model import Params, Scenario

FAR = 1000000  # the position of the things that do not exist: a missing traffic light, no service change
DEFAULT_GAP = 1000  # the distance to the end of a lane that does not end


class ScenarioError(ValueError):
    """The scenario is not consistent. The attribute problems lists everything that was found."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("The scenario is not valid:\n" + "\n".join(f"  - {problem}" for problem in self.problems))


@dataclass
class CompiledService:
    name: str
    headway: int
    biart: int
    offset: int  # -1 for a random offset
    origin: int
    origin_lane: int
    end: int
    station_ids: list[int] = field(default_factory=list)  # the stations where the service stops, in order
    bays: list[int] = field(default_factory=list)  # the index of the bay used at each station
    stop_tracks: list[int] = field(default_factory=list)  # the number of jumps taken before each stop
    tls: list[int] = field(default_factory=list)  # the traffic lights the service goes through, in order
    tl_dirs: list[int] = field(default_factory=list)  # the direction index of each traffic light
    tl_tracks: list[int] = field(default_factory=list)  # the number of jumps taken before each traffic light
    breaks: list[int] = field(default_factory=list)  # the jumps the service takes, in order
    change_pos: int = FAR  # the position where the service changes into another one
    dest_line: int = -1  # the service it changes into


@dataclass
class CompiledStation:
    name: str
    stop_pos: list[int]
    stop_biart: list[int]


@dataclass
class CompiledTrafficLight:
    name: str
    offset: int
    directions: list[str]
    positions: list[int]
    lengths: list[int]
    durations: list[int]
    phases: list[list[int]]


@dataclass
class CompiledDepot:
    name: str
    origin: int
    end: int
    initial_buses: int


@dataclass
class Compiled:
    """A scenario in the form the engine needs. The arrays are indexed as [service][lane][cell]."""

    services: list[CompiledService]
    stations: list[CompiledStation]
    traffic_lights: list[CompiledTrafficLight]
    breaks: list[list[int]]  # [origin cell, origin lane, destination cell, destination lane]
    depots: list[CompiledDepot]
    lanes: np.ndarray  # whether the service may circulate on the cell
    EL: np.ndarray  # the distance to the end of the lane
    LC: np.ndarray  # whether a change to the left, to the next lane, is allowed
    RC: np.ndarray  # whether a change to the right, to the previous lane, is allowed
    V: np.ndarray  # the maximal speed, in cells per second, indexed as [lane][cell]
    route_weights: np.ndarray  # the weight of each service for each trip, indexed as [origin][destination][service]
    IN: np.ndarray  # the probability of entering at each station
    OD: np.ndarray  # the probability of each destination, indexed as [origin][destination]
    demand_times: list[int]
    demand_rates: list[float]
    initial_time: int
    final_time: int
    params: Params


def kmh_to_cells(speed_kmh):
    """A speed in cells per second: the cells are one meter long and the time step is one second."""
    return int(np.round(speed_kmh * 1000 / 3600, 0))


def validate(scenario: Scenario):
    """The list of problems that prevent the scenario from being simulated, empty if it is valid."""
    problems = []
    service_names = [service.name for service in scenario.services]
    station_names = [station.name for station in scenario.stations]
    for kind, names in [
        ("service", service_names),
        ("station", station_names),
        ("traffic light", [tl.name for tl in scenario.traffic_lights]),
        ("depot", [depot.name for depot in scenario.depots]),
    ]:
        for name in sorted({name for name in names if names.count(name) > 1}):
            problems.append(f"there is more than one {kind} named {name}")
    if scenario.length <= 0 or scenario.lanes <= 0:
        problems.append("the system must have at least one cell and one lane")
        return problems
    if not scenario.services:
        problems.append("there are no services")
    if not scenario.stations:
        problems.append("there are no stations")
    if not scenario.depots:
        problems.append("there are no depots")
    if scenario.final_time <= scenario.initial_time:
        problems.append("the final time must be later than the initial time")
    if problems:
        return problems

    def inside(x, lane):
        return 0 <= x < scenario.length and 0 <= lane < scenario.lanes

    # the lanes
    known = set(service_names)
    used = np.zeros((scenario.lanes, scenario.length), dtype=bool)
    unusable = False  # whether the lanes cannot be built, the checks that need them are skipped
    for segment in scenario.lane_segments:
        where = f"the lane segment in lane {segment.lane} from {segment.start} to {segment.end}"
        if not (0 <= segment.lane < scenario.lanes and 0 <= segment.start < segment.end <= scenario.length):
            problems.append(f"{where} is outside the system")
            unusable = True
            continue
        if used[segment.lane, segment.start : segment.end].any():
            problems.append(f"{where} overlaps another segment")
        used[segment.lane, segment.start : segment.end] = True
        for name in segment.services:
            if name not in known:
                problems.append(f"{where} is used by service {name}, which is not defined")
                unusable = True
    for limit in scenario.speed_limits:
        if not (0 <= limit.lane < scenario.lanes and 0 <= limit.start < limit.end <= scenario.length):
            problems.append(f"the speed limit in lane {limit.lane} from {limit.start} to {limit.end} is outside the system")
        if limit.speed_kmh <= 0:
            problems.append(f"the speed limit in lane {limit.lane} from {limit.start} must be positive")
    if scenario.default_speed_kmh <= 0:
        problems.append("the default speed must be positive")
    if unusable:
        return problems
    lanes = _lane_arrays(scenario)
    index = {name: i for i, name in enumerate(service_names)}

    def circulates(name, x, lane):
        return bool(lanes[index[name], lane, x])

    for jump in scenario.jumps:
        if not (inside(jump.x, jump.lane) and inside(jump.to_x, jump.to_lane)):
            problems.append(f"the jump at cell {jump.x} in lane {jump.lane} has a position outside the system")

    # the services
    for service in scenario.services:
        where = f"service {service.name}"
        if service.headway <= 0:
            problems.append(f"{where} must have a positive headway")
        if not inside(service.start_x, service.start_lane):
            problems.append(f"{where} starts outside the system")
        elif any(other.becomes == service.name and other.end_x == service.start_x for other in scenario.services):
            pass  # the buses arrive from another service, they are already circulating
        elif not circulates(service.name, service.start_x, service.start_lane):
            problems.append(f"{where} starts at cell {service.start_x} in lane {service.start_lane}, where it may not circulate")
        if not 0 <= service.end_x < scenario.length:
            problems.append(f"{where} ends outside the system")
        if service.becomes is not None:
            if service.becomes not in known:
                problems.append(f"{where} changes into service {service.becomes}, which is not defined")
            elif scenario.service(service.becomes).start_x != service.end_x:
                problems.append(f"{where} changes into service {service.becomes}, which does not start where {service.name} ends")
        elif not any(depot.end == service.end_x for depot in scenario.depots):
            problems.append(f"{where} ends at cell {service.end_x}, which is not the end of any depot")
        if not 0 <= service.biarticulated_percent <= 100:
            problems.append(f"{where} must have a percentage of biarticulated buses between 0 and 100")

    # the stations
    for station in scenario.stations:
        if not station.bays:
            problems.append(f"station {station.name} has no bays")
        for number, bay in enumerate(station.bays):
            where = f"bay {number} of station {station.name}"
            if not inside(bay.x, bay.lane):
                problems.append(f"{where} is outside the system")
                continue
            for name in bay.services:
                if name not in known:
                    problems.append(f"{where} is used by service {name}, which is not defined")
                elif not circulates(name, bay.x, bay.lane):
                    problems.append(f"{where} is used by service {name}, which may not circulate there")

    # the traffic lights
    for tl in scenario.traffic_lights:
        where = f"traffic light {tl.name}"
        if not tl.phases:
            problems.append(f"{where} has no phases")
        for phase in tl.phases:
            if len(phase.green) != len(tl.directions):
                problems.append(f"{where} must have one state per direction in each phase")
            if phase.duration <= 0:
                problems.append(f"{where} must have phases with a positive duration")
        if tl.lengths and len(tl.lengths) != len(tl.directions):
            problems.append(f"{where} must have one length per direction")
        for head in tl.heads:
            if head.direction not in tl.directions:
                problems.append(f"{where} has a signal for direction {head.direction}, which it does not have")
            if not inside(head.x, head.lane):
                problems.append(f"{where} has a signal outside the system")

    # the depots
    for depot in scenario.depots:
        if depot.initial_buses < 0:
            problems.append(f"depot {depot.name} has a negative number of buses")

    # the demand
    demand = scenario.demand
    stations = set(station_names)
    if len(demand.times) != len(demand.rates):
        problems.append("the demand must have one rate per time")
    if any(later <= earlier for earlier, later in zip(demand.times, demand.times[1:])):
        problems.append("the times of the demand must be increasing")
    if any(rate < 0 for rate in demand.rates):
        problems.append("the demand rates must not be negative")
    for name, probability in demand.entries.items():
        if name not in stations:
            problems.append(f"the demand has entries at station {name}, which is not defined")
        if probability < 0:
            problems.append(f"the entry probability of station {name} must not be negative")
    if not any(probability > 0 for probability in demand.entries.values()):
        problems.append("the demand has no station where passengers enter")
    for origin, row in demand.destinations.items():
        if origin not in stations:
            problems.append(f"the demand has destinations from station {origin}, which is not defined")
        for destination, probability in row.items():
            if destination not in stations:
                problems.append(f"the demand has trips from {origin} to station {destination}, which is not defined")
            if probability < 0:
                problems.append(f"the probability of the trip from {origin} to {destination} must not be negative")
    for name, probability in demand.entries.items():
        if probability > 0 and not any(value > 0 for value in demand.destinations.get(name, {}).values()):
            problems.append(f"passengers enter at station {name} but they have no destinations")
    for restriction in scenario.transfer_restrictions:
        if restriction.origin not in stations or restriction.destination not in stations:
            problems.append(f"the transfer restriction from {restriction.origin} to {restriction.destination} uses a station that is not defined")
    return problems


def compile_scenario(scenario: Scenario) -> Compiled:
    problems = validate(scenario)
    if problems:
        raise ScenarioError(problems)

    names = [service.name for service in scenario.services]
    nservices = len(names)
    station_index = {station.name: i for i, station in enumerate(scenario.stations)}
    nstations = len(scenario.stations)

    lanes = _lane_arrays(scenario)
    LC, RC, EL = _lane_changes(lanes)
    V = np.full((scenario.lanes, scenario.length), kmh_to_cells(scenario.default_speed_kmh), dtype=np.int32)
    for limit in scenario.speed_limits:
        V[limit.lane, limit.start : limit.end] = kmh_to_cells(limit.speed_kmh)

    def services_at(x, lane):
        """The indices of the services that may circulate on a cell."""
        return np.flatnonzero(lanes[:, lane, x])

    # the stations, and the stops of each service in the order of the cells
    stations = [
        CompiledStation(station.name, [bay.x for bay in station.bays], [int(bay.biarticulated) for bay in station.bays])
        for station in scenario.stations
    ]
    stops = [[] for _ in names]  # for each service: (station, bay)
    bays = [(bay.x, bay.lane, s, b, bay) for s, station in enumerate(scenario.stations) for b, bay in enumerate(station.bays)]
    for x, lane, s, b, bay in sorted(bays, key=lambda item: item[:2]):
        for name in bay.services:
            stops[names.index(name)].append((s, b))

    # the traffic lights, and the ones each service goes through in the order of the cells
    traffic_lights = []
    heads = []
    for t, tl in enumerate(scenario.traffic_lights):
        positions = [None] * len(tl.directions)
        for head in sorted(tl.heads, key=lambda head: (head.x, head.lane)):
            positions[tl.directions.index(head.direction)] = head.x
            heads.append((head.x, head.lane, t, tl.directions.index(head.direction)))
        traffic_lights.append(
            CompiledTrafficLight(
                name=tl.name,
                offset=tl.offset,
                directions=list(tl.directions),
                positions=[FAR if position is None else position for position in positions],
                lengths=list(tl.lengths) if tl.lengths else [0] * len(tl.directions),
                durations=[phase.duration for phase in tl.phases],
                phases=[[int(green) for green in phase.green] for phase in tl.phases],
            )
        )
    service_tls = [[] for _ in names]  # for each service: (traffic light, direction)
    for x, lane, t, direction in sorted(heads):
        for i in services_at(x, lane):
            service_tls[i].append((t, direction))

    # the jumps each service takes
    service_jumps = [[] for _ in names]
    for jump in sorted(scenario.jumps, key=lambda jump: (jump.x, jump.lane)):
        for i in services_at(jump.x, jump.lane):
            service_jumps[i].append([jump.x, jump.lane, jump.to_x, jump.to_lane])

    breaks = []
    services = []
    problems = []
    for i, service in enumerate(scenario.services):
        compiled = CompiledService(
            name=service.name,
            headway=service.headway,
            biart=service.biarticulated_percent,
            offset=-1 if service.offset is None else service.offset,
            origin=service.start_x,
            origin_lane=service.start_lane,
            end=service.end_x,
        )
        if service.becomes is not None:
            compiled.change_pos = service.end_x
            compiled.dest_line = names.index(service.becomes)
        try:
            jumps = _order_jumps(service_jumps[i], service.start_x)
            jump_array = np.array(jumps) if jumps else None
            if stops[i]:
                positions = np.array([stations[s].stop_pos[b] for s, b in stops[i]])
                order, tracks = _order_along_path(positions, service.start_x, service.end_x, jump_array)
                compiled.station_ids = [stops[i][k][0] for k in order]
                compiled.bays = [stops[i][k][1] for k in order]
                compiled.stop_tracks = tracks
            if service_tls[i]:
                positions = np.array([traffic_lights[t].positions[direction] for t, direction in service_tls[i]])
                order, tracks = _order_along_path(positions, service.start_x, service.end_x, jump_array)
                compiled.tls = [service_tls[i][k][0] for k in order]
                compiled.tl_dirs = [service_tls[i][k][1] for k in order]
                compiled.tl_tracks = tracks
        except _PathError as error:
            problems.append(f"the path of service {service.name} cannot be followed: {error}")
            continue
        for jump in jumps:
            if jump not in breaks:
                breaks.append(jump)
            compiled.breaks.append(breaks.index(jump))
        services.append(compiled)
    if problems:
        raise ScenarioError(problems)

    # the passengers
    IN = np.zeros(nstations)
    for name, probability in scenario.demand.entries.items():
        IN[station_index[name]] = probability
    OD = np.zeros((nstations, nstations))
    for origin, row in scenario.demand.destinations.items():
        for destination, probability in row.items():
            OD[station_index[origin], station_index[destination]] = probability
    forbidden = {
        (station_index[restriction.origin], station_index[restriction.destination])
        for restriction in scenario.transfer_restrictions
    }

    return Compiled(
        services=services,
        stations=stations,
        traffic_lights=traffic_lights,
        breaks=breaks,
        depots=[CompiledDepot(depot.name, depot.origin, depot.end, depot.initial_buses) for depot in scenario.depots],
        lanes=lanes,
        EL=EL,
        LC=LC,
        RC=RC,
        V=V,
        route_weights=route_weights(services, nstations, forbidden),
        IN=IN,
        OD=OD,
        demand_times=list(scenario.demand.times),
        demand_rates=list(scenario.demand.rates),
        initial_time=scenario.initial_time,
        final_time=scenario.final_time,
        params=scenario.params,
    )


def _lane_arrays(scenario):
    """Whether each service may circulate on each cell, indexed as [service][lane][cell]."""
    index = {service.name: i for i, service in enumerate(scenario.services)}
    lanes = np.zeros((len(index), scenario.lanes, scenario.length), dtype=np.int32)
    for segment in scenario.lane_segments:
        for name in segment.services:
            lanes[index[name], segment.lane, segment.start : segment.end] = 1
    return lanes


def _lane_changes(lanes):
    """The lane change permissions and the distance to the end of the lane, for each service."""
    nlanes, length = lanes.shape[1:]
    # a change to the left, to the next lane, is possible when the next lane exists
    LC = lanes.copy()
    LC[:, -1, :] = 0
    LC[(lanes - np.roll(lanes, -1, axis=1)) == 1] = 0
    # a change to the right, to the previous lane, is possible when the previous lane exists
    RC = lanes.copy()
    RC[:, 0, :] = 0
    RC[(lanes - np.roll(lanes, 1, axis=1)) == 1] = 0

    # a lane ends at the cell before the first one where the service may not circulate
    ends = (np.roll(lanes, 1, axis=2) - lanes) == 1
    cells = np.arange(length)
    first_closed = np.where(ends, cells, length + DEFAULT_GAP)
    # for each cell, the first closed cell strictly after it
    following = np.minimum.accumulate(first_closed[:, :, ::-1], axis=2)[:, :, ::-1]
    following = np.concatenate([following[:, :, 1:], np.full_like(following[:, :, :1], length + DEFAULT_GAP)], axis=2)
    EL = np.where(following < length, following - 1 - cells, DEFAULT_GAP).astype(np.int32)
    return LC, RC, EL


class _PathError(Exception):
    pass


def _order_jumps(jumps, start):
    """The jumps of a service in the order they are taken: after each jump, the next one is the first after its destination."""
    if len(jumps) <= 1:
        return list(jumps)
    array = np.array(jumps)
    try:
        order = [np.where(array[:, 0] > start)[0][0]]
        while len(order) < len(array):
            order.append(np.where(array[:, 0] > array[order[-1], 2])[0][0])
    except IndexError:
        raise _PathError("its jumps do not form a path") from None
    if len(set(order)) != len(order):
        raise _PathError("its jumps form a loop")
    return [jumps[k] for k in order]


def _order_along_path(positions, start, end, jumps):
    """The order in which a service finds the given positions, and the number of jumps taken before each one.

    The positions are given in increasing order. The path of the service is made of sections: from its
    start to the first jump, from the destination of each jump to the next jump, and to its end.
    """
    has_jumps = jumps is not None
    if not has_jumps:
        sections = [(start, end)]
    else:
        sections = [(start, jumps[0, 0])]
        for k in range(len(jumps) - 1):
            sections.append((jumps[k, 2], jumps[k + 1, 0]))
        sections.append((jumps[-1, 2], end))
    # the first position in a section
    following = None
    for k, section in enumerate(sections):
        found = np.where((positions >= section[0]) & (positions <= section[1]))[0]
        if len(found) > 0:
            following = int(found[0])
            track = k
            break
    if following is None:
        raise _PathError("some of its stops or traffic lights are not on its path")
    order = [following]
    tracks = [track]
    try:
        while len(order) < len(positions):
            following += 1
            if has_jumps:
                if positions[following] > jumps[track][0]:
                    following = int(np.where(positions > jumps[track][2])[0][0])
                    track += 1
                    if track == len(jumps):
                        has_jumps = False
            order.append(following)
            tracks.append(track)
    except IndexError:
        raise _PathError("some of its stops or traffic lights are not on its path") from None
    if len(set(order)) != len(order) or max(order) >= len(positions):
        raise _PathError("some of its stops or traffic lights are not on its path")
    for k, track in zip(order, tracks):
        if not sections[track][0] <= positions[k] <= sections[track][1]:
            raise _PathError(f"the cell {positions[k]} is not on its path")
    return order, tracks


def route_weights(services, nstations, forbidden=frozenset()):
    """The weight of each service for the passengers travelling between two stations, indexed as [origin][destination][service].

    A service can be used for a trip when it stops at the destination after the origin. The weight
    decreases exponentially with the number of stops, and the services with a negligible weight are
    discarded. The buses that change into another service keep their passengers, so the stops of the
    second service count as well.
    """
    stops = [list(service.station_ids) for service in services]
    for i, service in enumerate(services):
        if service.dest_line >= 0:
            stops[i].extend(stops[service.dest_line])

    weights = np.zeros((nstations, nstations, len(services)))
    for origin in range(nstations):
        # the itineraries to each destination: (service, number of stops)
        itineraries = [[] for _ in range(nstations)]
        for i, line in enumerate(stops):
            if origin not in line:
                continue
            first = line.index(origin)
            for k in range(first + 1, len(line)):
                itinerary = (i, k - first)
                if itinerary not in itineraries[line[k]] and (origin, line[k]) not in forbidden:
                    itineraries[line[k]].append(itinerary)
        for destination in range(nstations):
            if not itineraries[destination]:
                continue
            factors = np.exp(-1.0 * np.array([nstops for _, nstops in itineraries[destination]]))
            for (i, _), weight in zip(itineraries[destination], factors / np.sum(factors)):
                if weight > 1e-3:
                    # six decimals, the precision of the files this information was stored in
                    weights[origin, destination, i] = float("%f" % weight)
    return weights
