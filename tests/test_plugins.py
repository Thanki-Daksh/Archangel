"""Unit tests for PluginLoader manifest scanning and safe execution fault isolation."""

from archangel.plugins import PluginLoader


def test_plugin_loader_manifests():
    loader = PluginLoader()
    manifests = loader.manifests
    assert isinstance(manifests, list)
    # Check loaded manifests contain required keys
    for manifest in manifests:
        assert "name" in manifest
        assert "id" in manifest
        assert "status" in manifest


def test_plugin_safe_execute_success():
    loader = PluginLoader()

    def successful_action():
        return "success"

    result = loader.safe_execute("test_plugin", successful_action, fallback="error")
    assert result == "success"
    assert loader.get_plugin_status("test_plugin") == "enabled"


def test_plugin_safe_execute_failure_degradation():
    loader = PluginLoader()

    def failing_action():
        raise RuntimeError("Plugin failed")

    # First 2 failures: status remains enabled
    loader.safe_execute("bad_plugin", failing_action)
    loader.safe_execute("bad_plugin", failing_action)
    assert loader.get_plugin_status("bad_plugin") == "enabled"

    # 3rd failure: status becomes degraded
    loader.safe_execute("bad_plugin", failing_action)
    assert loader.get_plugin_status("bad_plugin") == "degraded"

    # 4th and 5th failure: status becomes disabled
    loader.safe_execute("bad_plugin", failing_action)
    loader.safe_execute("bad_plugin", failing_action)
    assert loader.get_plugin_status("bad_plugin") == "disabled"

    # Subsequent execution skipped due to disabled status
    res = loader.safe_execute("bad_plugin", failing_action, fallback="skipped")
    assert res == "skipped"
