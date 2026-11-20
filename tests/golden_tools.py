"""Helpers shared by the golden regression tests and by record_goldens.py.

The goldens pin down two things for the reference Megabus configuration:
    - the configuration files produced by the layout scripts (conf_hashes.json)
    - the results of the C++ engine for a fixed list of cases (engine_results.json)
"""

import hashlib
import json
import os
import subprocess
import sys
import sysconfig
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONF_DIR = ROOT / "conf"
LAYOUT_DIR = ROOT / "layout"
SRC_CPP_DIR = ROOT / "src_cpp"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
CONF_GOLDEN = GOLDEN_DIR / "conf_hashes.json"
ENGINE_GOLDEN = GOLDEN_DIR / "engine_results.json"

# the files the user writes by hand, they are tracked by git
USER_CONF_FILES = ["IN.txt", "OD_matrix.txt", "service_data.txt"]
# the inputs of the layout scripts
LAYOUT_INPUTS = [
    "layout_file.xlsx",
    "traffic_lights_file.xlsx",
    "layout_interpreter.py",
    "routegenerator.py",
    "parameters.py",
]

# (seed, Cfract) of the simulations whose results are pinned down
ENGINE_CASES = [(1, 1.0), (2, 1.0), (3, 1.0), (1, 0.5), (7, 0.0)]
# (seed, Cfract) of the simulation whose complete bus trajectory is pinned down
TRAJECTORY_CASE = (1, 1.0)
KPI_NAMES = ["BSP", "cost", "passp", "occ", "flow", "queue"]


def platform_key():
    """The engine results depend on the standard library of the compiler, so they are stored per platform."""
    return sysconfig.get_platform()


def conf_is_stale():
    """True when the generated configuration files are missing or older than the layout inputs."""
    marker = CONF_DIR / "RouteMatrix.txt"  # the last file to be written
    if not marker.exists() or not (CONF_DIR / "service_changes.txt").exists():
        return True
    newest_input = max((LAYOUT_DIR / name).stat().st_mtime for name in LAYOUT_INPUTS)
    oldest_output = min(marker.stat().st_mtime, (CONF_DIR / "V.txt").stat().st_mtime)
    return newest_input > oldest_output


def generate_conf():
    """Runs the layout scripts, which write the configuration files in conf/."""
    for script in ["layout_interpreter.py", "routegenerator.py"]:
        subprocess.run(
            [sys.executable, script],
            cwd=LAYOUT_DIR,
            check=True,
            stdout=subprocess.DEVNULL,
        )


def conf_hashes():
    """The sha256 of every configuration file, independent of the line endings of the platform."""
    hashes = {}
    for path in sorted(CONF_DIR.glob("*.txt")):
        content = path.read_bytes().replace(b"\r\n", b"\n")
        hashes[path.name] = hashlib.sha256(content).hexdigest()
    return hashes


def load_simulator():
    """Imports the compiled engine from src_cpp/."""
    if str(SRC_CPP_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_CPP_DIR))
    import simulator

    return simulator


@contextmanager
def engine_cwd():
    """The engine opens ../conf/ relative to the working directory, so it must run from src_cpp/."""
    previous = os.getcwd()
    os.chdir(SRC_CPP_DIR)
    try:
        yield
    finally:
        os.chdir(previous)


def run_case(simulator, seed, cfract):
    """Runs one simulation without the detailed output and returns its results."""
    with engine_cwd():
        result = simulator.simulate(seed, 0, cfract)
    return {name: getattr(result, name) for name in KPI_NAMES}


def run_trajectory(simulator, seed, cfract):
    """Runs one simulation with the detailed output and returns the shape and the hash of the bus data."""
    import numpy as np

    with engine_cwd():
        result = simulator.simulate(seed, 1, cfract)
    data = np.asarray(result.BusData, dtype="<i8")
    return {"shape": list(data.shape), "sha256": hashlib.sha256(data.tobytes()).hexdigest()}


def case_key(seed, cfract):
    return f"seed={seed} Cfract={cfract}"


def read_json(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, indent=2, sort_keys=True)
        file.write("\n")
