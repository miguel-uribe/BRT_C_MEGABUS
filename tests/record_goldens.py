"""Records the golden files used by the regression tests.

Run it from the repository root, after building the engine:
        uv run python tests/record_goldens.py

Only run it when a change in the results is intended, and commit the updated files in tests/golden/.
The engine results are stored per platform, the results of other platforms are preserved.
"""

import golden_tools as gt


def main():
    print("Generating the configuration files from the layout")
    gt.generate_conf()
    gt.write_json(gt.CONF_GOLDEN, gt.conf_hashes())
    print(f"Wrote {gt.CONF_GOLDEN}")

    simulator = gt.load_simulator()
    goldens = gt.read_json(gt.ENGINE_GOLDEN) if gt.ENGINE_GOLDEN.exists() else {}
    results = {"cases": {}}
    for seed, cfract in gt.ENGINE_CASES:
        results["cases"][gt.case_key(seed, cfract)] = gt.run_case(simulator, seed, cfract)
        print(gt.case_key(seed, cfract), results["cases"][gt.case_key(seed, cfract)])
    seed, cfract = gt.TRAJECTORY_CASE
    results["trajectory"] = {gt.case_key(seed, cfract): gt.run_trajectory(simulator, seed, cfract)}
    goldens[gt.platform_key()] = results
    gt.write_json(gt.ENGINE_GOLDEN, goldens)
    print(f"Wrote {gt.ENGINE_GOLDEN} for platform {gt.platform_key()}")


if __name__ == "__main__":
    main()
