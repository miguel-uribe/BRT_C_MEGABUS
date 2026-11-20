import pytest

import golden_tools as gt


@pytest.fixture(scope="session")
def conf():
    """The configuration files in conf/, generated from the layout when they are missing or outdated."""
    if gt.conf_is_stale():
        gt.generate_conf()
    return gt.CONF_DIR


@pytest.fixture(scope="session")
def simulator(conf):
    """The compiled engine, with its configuration files in place."""
    try:
        return gt.load_simulator()
    except ImportError as error:
        pytest.fail(f"The engine is not built, see 'Compiling the c++ source' in README.md ({error})")


@pytest.fixture(scope="session")
def engine_golden():
    """The engine results recorded for the current platform."""
    goldens = gt.read_json(gt.ENGINE_GOLDEN)
    if gt.platform_key() not in goldens:
        pytest.skip(
            f"No engine results recorded for platform {gt.platform_key()}, "
            "record them with: uv run python tests/record_goldens.py"
        )
    return goldens[gt.platform_key()]
