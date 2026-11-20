"""The configuration files generated from the reference layout must not change unintentionally."""

import golden_tools as gt


def test_generated_conf_files_match_golden(conf):
    golden = gt.read_json(gt.CONF_GOLDEN)
    current = gt.conf_hashes()
    generated = sorted(set(golden) - set(gt.USER_CONF_FILES))

    assert sorted(set(current) - set(gt.USER_CONF_FILES)) == generated
    changed = [name for name in generated if current[name] != golden[name]]
    assert changed == [], f"The layout scripts produced different files: {changed}"


def test_user_conf_files_match_golden(conf):
    """IN, OD_matrix and service_data are inputs of the engine goldens, a local edit invalidates them."""
    golden = gt.read_json(gt.CONF_GOLDEN)
    current = gt.conf_hashes()

    changed = [name for name in gt.USER_CONF_FILES if current.get(name) != golden[name]]
    assert changed == [], f"These files differ from the reference configuration: {changed}"
