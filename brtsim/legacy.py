"""The importer of the original Megabus configuration.

It reads the layout and traffic light spreadsheets, the files written by hand in conf/ (IN.txt,
OD_matrix.txt and service_data.txt) and creates the equivalent scenario. The values that were written in
the source code (the depots, the fleet, the demand curve, the unrealistic trips) are defined here.

From the repository root, the scenario file is created with:
        uv run python -m brtsim.legacy
"""

import math
import warnings
from pathlib import Path

import pandas as pd

from .model import (
    Bay,
    Demand,
    Depot,
    Jump,
    Landmark,
    LaneSegment,
    Phase,
    Scenario,
    Service,
    SignalHead,
    SpeedLimit,
    Station,
    TrafficLight,
    TransferRestriction,
)

ROOT = Path(__file__).resolve().parent.parent

# The values of the Megabus system that were written in the source code
MEGABUS_FLEET = 50
MEGABUS_DEPOTS = [("Cuba", 0, 30653), ("Dosquebradas", 19999, 10943)]  # name, origin, end
MEGABUS_INITIAL_HOUR = 4
MEGABUS_FINAL_HOUR = 9
MEGABUS_FACTOR = 3600
MEGABUS_DEMAND_PERIOD = 10
# The trips the services allow but that are unrealistic in operation, by station index:
# from Egoyá, Coliseo, Ormaza, Mercasa, El Lago and Otún back towards Cuba
MEGABUS_FORBIDDEN_ORIGINS = [9, 11, 13, 15, 17, 19]
MEGABUS_FORBIDDEN_DESTINATIONS = [32, 33, 35, 36, 37, 38, 7, 5, 4, 3, 2, 1, 0]


def megabus_demand(time):
    """The average number of passengers entering the system during MEGABUS_DEMAND_PERIOD seconds."""
    return (
        MEGABUS_FACTOR
        * (50 / 14958.5)
        * (1 / (1 + math.exp(-(time - 6.8 * 3600) / (0.58 * 3600))))
        * (1.73 * math.exp(-math.pow((time - 6.8 * 3600) / (1.29 * 3600), 2)) + 1)
    )


def read_traffic_lights(path):
    """The traffic lights of the spreadsheet, without their positions."""
    traffic_lights = []
    for _, row in pd.read_excel(path).iterrows():
        directions = [info.strip() for info in row["direction"].split("-")]
        phases = []
        number = 0
        while f"phase_{number}" in row and isinstance(row[f"phase_{number}"], str):
            duration, scheme = row[f"phase_{number}"].split(":")
            phases.append(Phase(int(duration), [bool(int(info.strip())) for info in scheme.split("-")]))
            number += 1
        traffic_lights.append(
            TrafficLight(
                name=str(row["name"]),
                directions=directions,
                phases=phases,
                offset=int(row["offset"]),
                lengths=[int(info.strip()) for info in str(row["length"]).split("-")],
            )
        )
    return traffic_lights


def import_megabus(layout_file=None, traffic_lights_file=None, conf_dir=None, name="Megabus"):
    """The scenario equivalent to the original configuration files."""
    layout_file = Path(layout_file or ROOT / "layout" / "layout_file.xlsx")
    traffic_lights_file = Path(traffic_lights_file or ROOT / "layout" / "traffic_lights_file.xlsx")
    conf_dir = Path(conf_dir or ROOT / "conf")

    traffic_lights = read_traffic_lights(traffic_lights_file)
    tl_by_name = {tl.name: tl for tl in traffic_lights}

    layout = pd.read_excel(layout_file)
    nlanes = len(layout.columns) - 2
    length = len(layout)
    scenario = Scenario(name=name, length=length, lanes=nlanes)
    scenario.traffic_lights = traffic_lights
    scenario.initial_time = MEGABUS_INITIAL_HOUR * 3600
    scenario.final_time = MEGABUS_FINAL_HOUR * 3600

    # the first column names some positions
    for x, label in enumerate(layout.iloc[:, 0]):
        if isinstance(label, str):
            scenario.landmarks.append(Landmark(label.strip(), x))

    service_order = []  # the services in the order they appear
    stations = {}
    starts, ends, changes = {}, {}, {}
    cell_services = [[None] * length for _ in range(nlanes)]  # the services circulating on each cell
    cell_speed = [[None] * length for _ in range(nlanes)]  # the speed limit of each cell
    columns = [layout.iloc[:, lane + 2].tolist() for lane in range(nlanes)]

    def problem(x, lane, message):
        warnings.warn(f"Layout cell {x}, lane {lane}: {message}", stacklevel=3)

    # the cells are read in the order of the positions, and then of the lanes
    for x in range(length):
        for lane in range(nlanes):
            text = columns[lane][x]
            if not isinstance(text, str):
                continue
            services = None
            for item in text.split(";"):
                if item.count(":") != 1:
                    problem(x, lane, f"the text {text!r} is not understood, the rest of the cell is ignored")
                    break
                key, info = item.split(":")
                key = key.strip()
                values = [value.strip() for value in info.split(",")]
                if key == "R":
                    services = values
                    for service in services:
                        if service not in service_order:
                            service_order.append(service)
                    cell_services[lane][x] = tuple(services)
                elif services is None:
                    problem(x, lane, "the R key must come first, the rest of the cell is ignored")
                    break
                elif key == "E":
                    station = stations.setdefault(values[0], Station(values[0]))
                    station.bays.append(Bay(x, lane, list(values[1:]) if len(values) > 1 else list(services)))
                elif key == "S":
                    tl_name, direction = values
                    if tl_name not in tl_by_name:
                        problem(x, lane, f"the traffic light {tl_name} is not defined, the rest of the cell is ignored")
                        break
                    tl_by_name[tl_name].heads.append(SignalHead(direction, x, lane))
                elif key == "B":
                    to_x, to_lane = values
                    scenario.jumps.append(Jump(x, lane, int(to_x), int(to_lane)))
                elif key == "SS":
                    for service in values:
                        if service in starts:
                            problem(x, lane, f"service {service} starts more than once")
                        else:
                            starts[service] = (x, lane)
                elif key == "SF":
                    for service in values:
                        if service in ends:
                            problem(x, lane, f"service {service} ends more than once")
                        else:
                            ends[service] = x
                elif key == "C":
                    origin, destination = values
                    changes[origin] = destination
                    if origin in ends:
                        problem(x, lane, f"service {origin} ends more than once")
                    else:
                        ends[origin] = x
                elif key == "V":
                    cell_speed[lane][x] = int(info)
                else:
                    problem(x, lane, f"the key {key} is not known")

    # consecutive cells with the same content are stored as one segment
    for lane in range(nlanes):
        for start, end, services in _runs(cell_services[lane]):
            scenario.lane_segments.append(LaneSegment(lane, start, end, list(services)))
        for start, end, speed in _runs(cell_speed[lane]):
            scenario.speed_limits.append(SpeedLimit(lane, start, end, speed))
    scenario.stations = list(stations.values())

    # the headways are in the service data file, one line per service: index, headway, biarticulated percentage
    service_data = {}
    for line in (conf_dir / "service_data.txt").read_text().splitlines():
        if line.strip():
            index, headway, biart = (int(value) for value in line.split())
            service_data[index] = (headway, biart)
    for index, service in enumerate(service_order):
        if service not in starts or service not in ends:
            raise ValueError(f"Service {service} needs a start (SS key) and an end (SF or C key) in the layout")
        headway, biart = service_data.get(index, (1000000, 0))
        scenario.services.append(
            Service(
                name=service,
                start_x=starts[service][0],
                start_lane=starts[service][1],
                end_x=ends[service],
                headway=headway,
                biarticulated_percent=biart,
                becomes=changes.get(service),
            )
        )

    # the depots, with the entire fleet in the first one
    for depot_name, origin, end in MEGABUS_DEPOTS:
        scenario.depots.append(Depot(depot_name, origin, end))
    scenario.depots[0].initial_buses = MEGABUS_FLEET

    # the demand
    station_names = [station.name for station in scenario.stations]
    demand = Demand()
    demand.times = list(range(scenario.initial_time, scenario.final_time + 1, MEGABUS_DEMAND_PERIOD))
    demand.rates = [megabus_demand(time) * 3600.0 / MEGABUS_DEMAND_PERIOD for time in demand.times]
    entries = [float(line) for line in (conf_dir / "IN.txt").read_text().splitlines() if line.strip()]
    if len(entries) != len(station_names):
        raise ValueError(f"IN.txt has {len(entries)} values but the layout has {len(station_names)} stations")
    demand.entries = dict(zip(station_names, entries))
    for line in (conf_dir / "OD_matrix.txt").read_text().splitlines():
        if line.strip():
            origin, destination, probability = line.split()
            if float(probability) != 0:
                demand.destinations.setdefault(station_names[int(origin)], {})[station_names[int(destination)]] = float(probability)
    scenario.demand = demand

    for origin in MEGABUS_FORBIDDEN_ORIGINS:
        for destination in MEGABUS_FORBIDDEN_DESTINATIONS:
            scenario.transfer_restrictions.append(TransferRestriction(station_names[origin], station_names[destination]))
    return scenario


def _runs(values):
    """The runs of consecutive equal values that are not None, as (start, end, value) with end not included."""
    runs = []
    start = None
    for x, value in enumerate(values):
        if start is not None and value != values[start]:
            runs.append((start, x, values[start]))
            start = None
        if start is None and value is not None:
            start = x
    if start is not None:
        runs.append((start, len(values), values[start]))
    return runs


if __name__ == "__main__":
    target = ROOT / "scenarios" / "megabus.json"
    target.parent.mkdir(exist_ok=True)
    import_megabus().save(target)
    print(f"Wrote {target}")
