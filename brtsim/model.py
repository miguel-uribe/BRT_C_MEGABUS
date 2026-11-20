"""The scenario: the complete description of a BRT system and its simulation.

A scenario is plain data. It is stored in a single JSON file and it replaces the layout and traffic
light spreadsheets, the files in conf/ and the parameter files.

The geometry of the system is described along the latent x coordinate used by the engine: every
position is a cell (one meter) and a lane. Buses always advance towards larger cells; the parts of the
system that are not consecutive in x are connected with jumps.
"""

import dataclasses
import json
import types
import typing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SCENARIO_VERSION = 1


@dataclass
class LaneSegment:
    """A stretch of a lane, the cells in [start, end), and the services that may circulate on it."""

    lane: int
    start: int
    end: int
    services: list[str]


@dataclass
class SpeedLimit:
    """The maximal speed in the cells [start, end) of a lane, elsewhere the default speed applies."""

    lane: int
    start: int
    end: int
    speed_kmh: int


@dataclass
class Bay:
    """A docking bay of a station: the cell where the buses of the given services stop."""

    x: int
    lane: int
    services: list[str]
    biarticulated: bool = False


@dataclass
class Station:
    name: str
    bays: list[Bay] = field(default_factory=list)


@dataclass
class SignalHead:
    """The cell where the buses wait when a direction of a traffic light is in red."""

    direction: str
    x: int
    lane: int


@dataclass
class Phase:
    """A phase of a traffic light: its duration in seconds and whether each direction is in green."""

    duration: int
    green: list[bool]


@dataclass
class TrafficLight:
    name: str
    directions: list[str]
    phases: list[Phase]
    offset: int = 0  # the time already elapsed in the first phase when the simulation starts
    lengths: list[int] = field(default_factory=list)  # not used by the engine
    heads: list[SignalHead] = field(default_factory=list)


@dataclass
class Jump:
    """The buses reaching the cell x in the given lane continue from the cell to_x in the lane to_lane."""

    x: int
    lane: int
    to_x: int
    to_lane: int


@dataclass
class Service:
    """A bus service. Its path is given by the lane segments and jumps, its stops by the station bays."""

    name: str
    start_x: int
    start_lane: int
    end_x: int
    headway: int = 1000000  # seconds between buses
    biarticulated_percent: int = 0
    offset: Optional[int] = None  # the time of the first bus, modulo the headway. A random one if not given
    becomes: Optional[str] = None  # the service the buses change into at end_x, keeping their passengers


@dataclass
class Depot:
    """The buses of the services starting at origin are taken from the depot, and they are parked again
    when their service ends at end."""

    name: str
    origin: int
    end: int
    initial_buses: int = 0


@dataclass
class Demand:
    # the passengers entering the system per hour at the given times, linearly interpolated
    times: list[int] = field(default_factory=list)
    rates: list[float] = field(default_factory=list)
    # the probability of entering the system at each station, by station name
    entries: dict[str, float] = field(default_factory=dict)
    # the probability of each destination for each origin, by station name
    destinations: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class TransferRestriction:
    """A trip the services allow but passengers do not make in practice."""

    origin: str
    destination: str


@dataclass
class Landmark:
    """A name for a position, it has no effect on the simulation."""

    name: str
    x: int


@dataclass
class Params:
    """The parameters of the model."""

    bus_lengths: list[int] = field(default_factory=lambda: [17, 27])  # cells, articulated and biarticulated
    braking_probability: float = 0.15
    braking_probability_stopped: float = 0.75
    lane_change_penalty: int = 5  # seconds without lane changes after leaving a stop
    bus_capacity: int = 100
    boarding_rate: int = 1  # how sharply the boarding probability falls when the bus is full
    dwell_base: int = 10  # seconds
    dwell_per_passenger: float = 0.5  # seconds
    dwell_max: int = 30  # seconds
    insertion_period: int = 10  # passengers enter the system every insertion_period seconds
    max_offset: int = 60  # the random offsets of the services are smaller than max_offset


@dataclass
class Scenario:
    name: str
    length: int  # the number of cells
    lanes: int  # the number of lanes
    initial_time: int = 4 * 3600  # seconds
    final_time: int = 9 * 3600  # seconds
    default_speed_kmh: int = 60
    lane_segments: list[LaneSegment] = field(default_factory=list)
    speed_limits: list[SpeedLimit] = field(default_factory=list)
    jumps: list[Jump] = field(default_factory=list)
    stations: list[Station] = field(default_factory=list)
    traffic_lights: list[TrafficLight] = field(default_factory=list)
    services: list[Service] = field(default_factory=list)
    depots: list[Depot] = field(default_factory=list)
    demand: Demand = field(default_factory=Demand)
    transfer_restrictions: list[TransferRestriction] = field(default_factory=list)
    landmarks: list[Landmark] = field(default_factory=list)
    params: Params = field(default_factory=Params)

    def service(self, name):
        return next(service for service in self.services if service.name == name)

    def station(self, name):
        return next(station for station in self.stations if station.name == name)

    def depot(self, name):
        return next(depot for depot in self.depots if depot.name == name)

    def copy(self):
        return from_dict(to_dict(self))

    def save(self, path):
        save(self, path)


def to_dict(scenario):
    data = {"version": SCENARIO_VERSION}
    data.update(dataclasses.asdict(scenario))
    return data


def from_dict(data):
    data = dict(data)
    version = data.pop("version", None)
    if version != SCENARIO_VERSION:
        raise ValueError(f"Unsupported scenario version {version!r}, this program reads version {SCENARIO_VERSION}")
    return _build(Scenario, data, "scenario")


def save(scenario, path):
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        json.dump(to_dict(scenario), file, ensure_ascii=False, indent=1)
        file.write("\n")


def load(path):
    with open(Path(path), encoding="utf-8") as file:
        return from_dict(json.load(file))


def _build(kind, value, where):
    """Creates the value of the given type from its JSON representation, checking its structure."""
    origin = typing.get_origin(kind)
    if origin in (typing.Union, types.UnionType):  # Optional
        if value is None:
            return None
        (kind,) = [arg for arg in typing.get_args(kind) if arg is not type(None)]
        return _build(kind, value, where)
    if origin is list:
        if not isinstance(value, list):
            raise ValueError(f"{where} must be a list")
        (item,) = typing.get_args(kind)
        return [_build(item, element, f"{where}[{index}]") for index, element in enumerate(value)]
    if origin is dict:
        if not isinstance(value, dict):
            raise ValueError(f"{where} must be an object")
        _, item = typing.get_args(kind)
        return {str(key): _build(item, element, f"{where}[{key!r}]") for key, element in value.items()}
    if dataclasses.is_dataclass(kind):
        if not isinstance(value, dict):
            raise ValueError(f"{where} must be an object")
        hints = typing.get_type_hints(kind)
        unknown = set(value) - set(hints)
        if unknown:
            raise ValueError(f"{where} has unknown fields: {sorted(unknown)}")
        try:
            return kind(**{key: _build(hints[key], element, f"{where}.{key}") for key, element in value.items()})
        except TypeError as error:
            raise ValueError(f"{where}: {error}") from None
    if kind is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{where} must be a number")
        return float(value)
    if kind is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{where} must be an integer")
        return value
    if not isinstance(value, kind):
        raise ValueError(f"{where} must be of type {kind.__name__}")
    return value
