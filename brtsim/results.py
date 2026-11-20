"""The results of a simulation, and of a set of simulations with different seeds."""

import math
import statistics
from dataclasses import dataclass

import numpy as np
import pandas as pd

# The indicators of a simulation and their units. The cells are one meter long and the time step is one second.
KPIS = {
    "bus_speed": "average speed of the buses, including their stops (km/h)",
    "passenger_speed": "average speed of the passengers, including their waiting time (km/h)",
    "travel_time": "average travel time of the passengers that reached their destination, including their waiting time (s)",
    "waiting_passengers": "average number of passengers waiting at a station",
    "passenger_flow": "average passenger flow in the system (passengers per second)",
    "bus_hours": "total time of the buses in service (bus-hours)",
    "bus_queue": "average number of departures waiting for a bus to be available",
    "passengers": "passengers that entered the system",
    "delivered": "passengers that reached their destination",
}
# The names of the indicators and metrics for the user
LABELS = {
    "bus_speed": "Bus speed (km/h)",
    "passenger_speed": "Passenger speed (km/h)",
    "travel_time": "Travel time (s)",
    "waiting_passengers": "Passengers waiting per station",
    "passenger_flow": "Passenger flow (pass/s)",
    "bus_hours": "Bus-hours",
    "bus_queue": "Departures waiting for a bus",
    "passengers": "Passengers",
    "delivered": "Passengers delivered",
    "entries": "Entries",
    "boardings": "Boardings",
    "alightings": "Alightings",
    "waiting": "Passengers waiting",
    "departures": "Departures",
    "queued": "Departures delayed",
    "arrivals": "Arrivals",
    "trip_time": "Trip time (s)",
}
STATION_METRICS = {
    "entries": "passengers that entered the system at the station",
    "boardings": "passengers that boarded a bus at the station",
    "alightings": "passengers that finished their trip at the station",
    "waiting": "average number of passengers waiting at the station",
}
SERVICE_METRICS = {
    "departures": "buses introduced",
    "queued": "buses that were not available when they had to be introduced",
    "arrivals": "buses that finished the service",
    "trip_time": "average time of the buses that finished the service (s)",
    "boardings": "passengers that boarded the service",
}


@dataclass
class RunResult:
    """The results of one simulation."""

    seed: int
    kpis: dict  # the value of each indicator
    stations: dict  # for each station metric, an array with the value of each station
    services: dict  # for each service metric, an array with the value of each service

    @classmethod
    def from_engine(cls, seed, results):
        kpis = {
            "bus_speed": results.BSP * 3.6,
            "passenger_speed": results.passp * 3.6,
            "travel_time": results.travel_time,
            "waiting_passengers": results.occ,
            "passenger_flow": results.flow,
            "bus_hours": results.cost,
            "bus_queue": results.queue,
            "passengers": results.passengers,
            "delivered": results.delivered,
        }
        stations = {name: np.array(getattr(results, f"station_{name}"), dtype=float) for name in STATION_METRICS}
        services = {name: np.array(getattr(results, f"line_{name}"), dtype=float) for name in SERVICE_METRICS}
        return cls(int(seed), kpis, stations, services)


class Results:
    """The results of the simulations of one case with several seeds."""

    def __init__(self, runs, station_names, service_names):
        self.runs = list(runs)
        self.station_names = list(station_names)
        self.service_names = list(service_names)

    @property
    def seeds(self):
        return [run.seed for run in self.runs]

    def values(self, kpi):
        """The value of an indicator in each simulation."""
        return np.array([run.kpis[kpi] for run in self.runs], dtype=float)

    @property
    def mean(self):
        return {kpi: float(np.mean(self.values(kpi))) for kpi in KPIS}

    @property
    def std(self):
        """The standard deviation between simulations, not defined for a single one."""
        return {kpi: float(np.std(self.values(kpi), ddof=1)) if len(self.runs) > 1 else math.nan for kpi in KPIS}

    def confidence_interval(self, level=0.95):
        """The confidence interval of the mean of each indicator, as (low, high)."""
        count = len(self.runs)
        intervals = {}
        for kpi in KPIS:
            if count < 2:
                intervals[kpi] = (math.nan, math.nan)
                continue
            half = student_t_quantile(0.5 + level / 2, count - 1) * self.std[kpi] / math.sqrt(count)
            intervals[kpi] = (self.mean[kpi] - half, self.mean[kpi] + half)
        return intervals

    def summary(self, level=0.95):
        """A table with the mean, the standard deviation and the confidence interval of each indicator."""
        mean, std, intervals = self.mean, self.std, self.confidence_interval(level)
        rows = [
            {"mean": mean[kpi], "std": std[kpi], "ci_low": intervals[kpi][0], "ci_high": intervals[kpi][1], "runs": len(self.runs)}
            for kpi in KPIS
        ]
        return pd.DataFrame(rows, index=pd.Index(list(KPIS), name="indicator"))

    @property
    def stations(self):
        """A table with the mean over the simulations of the metrics of each station."""
        data = {name: np.mean([run.stations[name] for run in self.runs], axis=0) for name in STATION_METRICS}
        return pd.DataFrame(data, index=pd.Index(self.station_names, name="station"))

    @property
    def services(self):
        """A table with the mean over the simulations of the metrics of each service."""
        data = {name: np.mean([run.services[name] for run in self.runs], axis=0) for name in SERVICE_METRICS}
        return pd.DataFrame(data, index=pd.Index(self.service_names, name="service"))

    def per_run(self):
        """A table with the indicators of each simulation."""
        return pd.DataFrame([run.kpis for run in self.runs], index=pd.Index(self.seeds, name="seed"))

    def to_dict(self):
        """Everything as plain data, to be stored as JSON."""
        return {
            "seeds": self.seeds,
            "summary": self.summary().to_dict(orient="index"),
            "runs": self.per_run().to_dict(orient="index"),
            "stations": self.stations.to_dict(orient="index"),
            "services": self.services.to_dict(orient="index"),
        }

    def __repr__(self):
        return f"Results of {len(self.runs)} simulations\n{self.summary().to_string()}"


def student_t_quantile(probability, freedom):
    """The quantile of the Student t distribution, from the expansion of Cornish and Fisher around the normal one."""
    if freedom == 1:
        return math.tan(math.pi * (probability - 0.5))
    if freedom == 2:
        return (2 * probability - 1) / math.sqrt(2 * probability * (1 - probability))
    z = statistics.NormalDist().inv_cdf(probability)
    terms = [
        z,
        (z**3 + z) / 4,
        (5 * z**5 + 16 * z**3 + 3 * z) / 96,
        (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / 384,
        (79 * z**9 + 776 * z**7 + 1482 * z**5 - 1920 * z**3 - 945 * z) / 92160,
    ]
    return sum(term / freedom**power for power, term in enumerate(terms))
