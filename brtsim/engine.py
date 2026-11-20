"""The bridge between a compiled scenario and the C++ engine."""

import sys
from pathlib import Path

from .compiler import Compiled


def load_engine():
    """The compiled C++ module. It is built in src_cpp/, see the README."""
    try:
        import simulator
    except ImportError:
        source = Path(__file__).resolve().parent.parent / "src_cpp"
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
        try:
            import simulator
        except ImportError as error:
            raise ImportError(f"The simulation engine is not built, see 'Compiling the c++ source' in README.md ({error})") from None
    return simulator


def engine_config(compiled: Compiled):
    """The configuration of the engine for a compiled scenario, it is held in memory."""
    simulator = load_engine()
    config = simulator.SimConfig()

    for station in compiled.stations:
        item = simulator.Station(station.name)
        item.stop_pos = station.stop_pos
        item.stop_biart = station.stop_biart
        config.stations.append(item)

    for tl in compiled.traffic_lights:
        item = simulator.TrafficLight(tl.name, tl.offset)
        item.directions = tl.directions
        item.positions = tl.positions
        item.lengths = tl.lengths
        item.durations = tl.durations
        item.phases = tl.phases
        config.traffic_lights.append(item)

    for service in compiled.services:
        item = simulator.Line(service.name)
        item.headway = service.headway
        item.biart = service.biart
        item.offset = service.offset
        item.origin = service.origin
        item.or_lane = service.origin_lane
        item.end = service.end
        item.stationIDs = service.station_ids
        item.wagons = service.bays
        item.stoptracks = service.stop_tracks
        item.tls = service.tls
        item.tldir = service.tl_dirs
        item.tltracks = service.tl_tracks
        item.breaks = service.breaks
        item.change_pos = service.change_pos
        item.dest_line = service.dest_line
        config.lines.append(item)

    for depot in compiled.depots:
        item = simulator.Depot()
        item.name = depot.name
        item.origin = depot.origin
        item.end = depot.end
        item.initial_buses = depot.initial_buses
        config.depots.append(item)

    config.breaks = compiled.breaks
    config.EL = compiled.EL.tolist()
    config.LC = compiled.LC.tolist()
    config.RC = compiled.RC.tolist()
    config.V = compiled.V.tolist()
    config.route_weights = compiled.route_weights.tolist()
    config.IN = compiled.IN.tolist()
    config.OD = compiled.OD.tolist()
    config.demand_times = compiled.demand_times
    config.demand_rates = compiled.demand_rates
    config.initial_time = compiled.initial_time
    config.final_time = compiled.final_time

    params = compiled.params
    config.params.busL = params.bus_lengths
    config.params.p = params.braking_probability
    config.params.p0 = params.braking_probability_stopped
    config.params.pentime = params.lane_change_penalty
    config.params.BusCap = params.bus_capacity
    config.params.BusRate = params.boarding_rate
    config.params.D0 = params.dwell_base
    config.params.D1 = params.dwell_per_passenger
    config.params.MaxDwell = params.dwell_max
    config.params.insertion_period = params.insertion_period
    config.params.max_offset = params.max_offset
    config.validate()
    return config
