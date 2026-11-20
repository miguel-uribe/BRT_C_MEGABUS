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
    """The recorded engine results, they are the same on every platform."""
    return gt.read_json(gt.ENGINE_GOLDEN)
