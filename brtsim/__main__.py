"""The command line interface, run it from the repository root with: uv run python -m brtsim --help"""

import argparse
import json
import sys
import warnings
from pathlib import Path

from . import ScenarioError, load, prepare, unsafe_jumps, validate
from .results import KPIS


def main(arguments=None):
    parser = argparse.ArgumentParser(prog="brtsim", description="Simulation of BRT systems")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="simulate a scenario with several seeds and show the averaged results")
    run.add_argument("scenario", help="the scenario file")
    run.add_argument("--seeds", type=int, default=10, help="the number of simulations, with seeds 1, 2, 3... (default: 10)")
    run.add_argument("--first-seed", type=int, default=1, help="the first seed (default: 1)")
    run.add_argument("--workers", type=int, help="the simulations running at the same time (default: the number of processors)")
    run.add_argument("--headway", action="append", default=[], metavar="SERVICE=SECONDS", help="the seconds between buses of a service")
    run.add_argument("--frequency", action="append", default=[], metavar="SERVICE=BUSES", help="the buses per hour of a service")
    run.add_argument("--buses", action="append", default=[], metavar="DEPOT=BUSES", help="the buses initially parked at a depot")
    run.add_argument("--demand-scale", type=float, help="a factor that multiplies the number of passengers")
    run.add_argument("--stations", action="store_true", help="show the results of each station")
    run.add_argument("--services", action="store_true", help="show the results of each service")
    run.add_argument("--output", help="a file to store the results: .json for everything, .csv for the indicators of each simulation")

    check = commands.add_parser("validate", help="check a scenario and list its problems")
    check.add_argument("scenario", help="the scenario file")

    legacy = commands.add_parser("import-megabus", help="create the Megabus scenario from the spreadsheets in layout/ and the files in conf/")
    legacy.add_argument("--output", default="scenarios/megabus.json", help="the scenario file to write (default: scenarios/megabus.json)")

    options = parser.parse_args(arguments)
    try:
        if options.command == "run":
            return _run(options)
        if options.command == "validate":
            return _validate(options)
        return _import_megabus(options)
    except (ScenarioError, ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def _pairs(values, kind, option):
    """The NAME=VALUE arguments of an option, as a dictionary."""
    pairs = {}
    for value in values:
        name, separator, number = value.rpartition("=")
        try:
            if not separator or not name:
                raise ValueError
            pairs[name] = kind(number)
        except ValueError:
            raise ValueError(f"{option} expects NAME=VALUE, got {value!r}") from None
    return pairs


def _run(options):
    model = prepare(load(options.scenario))
    changes = {
        "headways": _pairs(options.headway, int, "--headway"),
        "frequencies": _pairs(options.frequency, float, "--frequency"),
        "fleet": _pairs(options.buses, int, "--buses"),
        "demand_scale": options.demand_scale,
    }
    seeds = range(options.first_seed, options.first_seed + options.seeds)

    def progress(done, total):
        print(f"\r{done}/{total} simulations", end="", file=sys.stderr, flush=True)

    results = model.run(seeds, workers=options.workers, progress=progress, **changes)
    print(file=sys.stderr)
    print(results.summary().to_string(float_format=lambda value: f"{value:.4f}"))
    print()
    for name, description in KPIS.items():
        print(f"  {name}: {description}")
    if options.stations:
        print()
        print(results.stations.to_string(float_format=lambda value: f"{value:.1f}"))
    if options.services:
        print()
        print(results.services.to_string(float_format=lambda value: f"{value:.1f}"))
    if options.output:
        output = Path(options.output)
        if output.suffix.lower() == ".csv":
            results.per_run().to_csv(output)
        else:
            output.write_text(json.dumps(results.to_dict(), indent=1), encoding="utf-8")
        print(f"\nResults written to {output}")
    return 0


def _validate(options):
    scenario = load(options.scenario)
    problems = validate(scenario)
    if problems:
        print(f"The scenario has {len(problems)} problems and cannot be simulated:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    prepare(scenario)
    print("The scenario is valid.")
    unsafe = unsafe_jumps(scenario)
    if unsafe:
        print(f"\nWarning: {len(unsafe)} jumps do not follow the rules that prevent collisions:")
        for _, jump_problems in unsafe:
            for problem in jump_problems:
                print(f"  - {problem}")
    return 0


def _import_megabus(options):
    from .legacy import import_megabus

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        scenario = import_megabus()
    for warning in caught:
        print(f"Warning: {warning.message}")
    output = Path(options.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    scenario.save(output)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
