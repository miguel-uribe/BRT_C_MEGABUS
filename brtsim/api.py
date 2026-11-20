"""The interface to run simulations without a user interface.

        import brtsim

        scenario = brtsim.load("scenarios/megabus.json")
        results = brtsim.run(scenario, seeds=20)
        print(results.summary())

A scenario is prepared once and then simulated many times with different seeds and parameters. Nothing
is written to disk, and the simulations run in parallel threads:

        model = brtsim.prepare(scenario)
        cases = [{"frequencies": {"1E": frequency}} for frequency in range(5, 40, 5)]
        for case, results in zip(cases, model.run_many(cases, seeds=20)):
            print(case, results.mean["bus_speed"])
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from .compiler import compile_scenario
from .engine import PARAM_FIELDS, engine_config, load_engine
from .model import Scenario
from .results import Results, RunResult

# A service with no buses: its headway is longer than any simulation, and its first bus would leave at the end of it
NO_SERVICE_HEADWAY = 2**30


def prepare(scenario: Scenario):
    """Checks and compiles a scenario, raises brtsim.ScenarioError if it is not valid."""
    return Model(scenario)


def run(scenario: Scenario, seeds=1, workers=None, progress=None, **changes):
    """Simulates a scenario with several seeds, see Model.run."""
    return Model(scenario).run(seeds, workers=workers, progress=progress, **changes)


class Model:
    """A scenario ready to be simulated. It keeps its own copy of the scenario, later changes to the original do not affect it."""

    def __init__(self, scenario: Scenario):
        self.scenario = scenario.copy()
        self.compiled = compile_scenario(self.scenario)
        self._engine = load_engine()
        self._config = engine_config(self.compiled)
        self.service_names = [service.name for service in self.scenario.services]
        self.station_names = [station.name for station in self.scenario.stations]
        self.depot_names = [depot.name for depot in self.scenario.depots]

    def config(
        self,
        *,
        headways=None,
        frequencies=None,
        offsets=None,
        fleet=None,
        demand_scale=None,
        demand=None,
        entries=None,
        params=None,
        initial_time=None,
        final_time=None,
    ):
        """The configuration of the engine, with some parameters of the scenario replaced. The scenario is not compiled again.

        headways: the seconds between buses of some services, by service name.
        frequencies: the buses per hour of some services, by service name. Zero means no buses.
        offsets: the time of the first bus of some services, by service name. None means a random one.
        fleet: the buses initially parked at some depots, by depot name.
        demand_scale: a factor that multiplies the number of passengers.
        demand: the demand profile, as (times, passengers per hour).
        entries: the probability of entering the system at each station, by station name. The stations that are not given get no passengers.
        params: some parameters of the model, by the names of brtsim.model.Params.
        initial_time, final_time: the simulation window, in seconds.
        """
        config = self._engine.SimConfig(self._config)

        def index(names, name, kind):
            if name not in names:
                raise ValueError(f"There is no {kind} named {name!r}, the {kind}s are: {', '.join(names)}")
            return names.index(name)

        if headways and frequencies and set(headways) & set(frequencies):
            raise ValueError("A service cannot have both a headway and a frequency")
        for name, headway in (headways or {}).items():
            if headway <= 0:
                raise ValueError(f"The headway of service {name} must be positive")
            config.lines[index(self.service_names, name, "service")].headway = int(round(headway))
        for name, frequency in (frequencies or {}).items():
            line = config.lines[index(self.service_names, name, "service")]
            if frequency < 0:
                raise ValueError(f"The frequency of service {name} must not be negative")
            if frequency == 0:
                line.headway = NO_SERVICE_HEADWAY
                line.offset = NO_SERVICE_HEADWAY - 1
            else:
                line.headway = max(1, int(round(3600 / frequency)))
        for name, offset in (offsets or {}).items():
            config.lines[index(self.service_names, name, "service")].offset = -1 if offset is None else int(offset)
        for name, buses in (fleet or {}).items():
            config.depots[index(self.depot_names, name, "depot")].initial_buses = int(buses)
        if demand is not None:
            times, rates = demand
            config.demand_times = [int(time) for time in times]
            config.demand_rates = [float(rate) for rate in rates]
        if demand_scale is not None:
            config.demand_rates = [demand_scale * rate for rate in config.demand_rates]
        if entries is not None:
            probabilities = [0.0] * len(self.station_names)
            for name, probability in entries.items():
                probabilities[index(self.station_names, name, "station")] = float(probability)
            config.IN = probabilities
        for name, value in (params or {}).items():
            if name not in PARAM_FIELDS:
                raise ValueError(f"There is no parameter named {name!r}, the parameters are: {', '.join(PARAM_FIELDS)}")
            setattr(config.params, PARAM_FIELDS[name], value)
        if initial_time is not None:
            config.initial_time = int(initial_time)
        if final_time is not None:
            config.final_time = int(final_time)
        config.validate()
        return config

    def simulation(self, seed=1, record=False, **changes):
        """A simulation of the engine that can be advanced step by step, see the README. The changes are the ones of Model.config."""
        return self._engine.Simulation(self.config(**changes), int(seed), record)

    def run(self, seeds=1, workers=None, progress=None, **changes):
        """Simulates the scenario once for each seed and returns the Results.

        seeds: a list of seeds, or the number of seeds to use (1, 2, 3...).
        workers: the number of simulations running at the same time, by default the number of processors.
        progress: a function called as progress(done, total) every time a simulation finishes.
        changes: the parameters of the scenario to replace, see Model.config.
        """
        return self.run_many([changes], seeds, workers=workers, progress=progress)[0]

    def run_many(self, cases, seeds=1, workers=None, progress=None):
        """Simulates several cases with the same seeds, all the simulations share the workers.

        cases: a list of dictionaries with the changes of each case, see Model.config.
        Returns the list with the Results of each case.
        """
        seeds = _seed_list(seeds)
        configs = [self.config(**case) for case in cases]
        tasks = [(case, seed) for case in range(len(configs)) for seed in seeds]
        if workers is None:
            workers = os.cpu_count() or 1
        workers = max(1, min(int(workers), len(tasks)))

        def simulate(task):
            case, seed = task
            simulation = self._engine.Simulation(configs[case], seed)
            simulation.run()  # the engine does not hold the interpreter lock while it runs
            return RunResult.from_engine(seed, simulation.results())

        runs = {}
        if workers == 1:
            for done, task in enumerate(tasks, start=1):
                runs[task] = simulate(task)
                if progress:
                    progress(done, len(tasks))
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(simulate, task): task for task in tasks}
                for done, future in enumerate(as_completed(futures), start=1):
                    runs[futures[future]] = future.result()
                    if progress:
                        progress(done, len(tasks))
        return [
            Results([runs[(case, seed)] for seed in seeds], self.station_names, self.service_names)
            for case in range(len(configs))
        ]


def _seed_list(seeds):
    if isinstance(seeds, int):
        if seeds < 1:
            raise ValueError("At least one seed is needed")
        return list(range(1, seeds + 1))
    seeds = [int(seed) for seed in seeds]
    if not seeds:
        raise ValueError("At least one seed is needed")
    if len(set(seeds)) != len(seeds):
        raise ValueError("The seeds must be different")
    return seeds
