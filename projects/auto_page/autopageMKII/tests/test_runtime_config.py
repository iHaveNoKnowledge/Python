import os
import sys
from unittest.mock import MagicMock

import pytest

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import autopage_config as config_module
from autopage_config import RuntimeConfig
from functions import browser_manager as bm


def test_defaults_keep_single_instance_behaviour():
    config = RuntimeConfig()

    assert config.worker_id == "default"
    assert config.chrome_debug_host == "localhost"
    assert config.chrome_debug_port == 8989
    assert config.chrome_debugger_address == "localhost:8989"
    assert config.data_dir == os.path.dirname(os.path.abspath(config_module.__file__))


def test_env_overrides_second_instance(monkeypatch):
    monkeypatch.setenv("AUTOPAGE_WORKER_ID", "w2")
    monkeypatch.setenv("AUTOPAGE_CHROME_DEBUG_PORT", "8990")
    monkeypatch.setenv("AUTOPAGE_CHROME_DEBUG_HOST", "127.0.0.1")

    config = RuntimeConfig.from_env()

    assert config.worker_id == "w2"
    assert config.chrome_debug_port == 8990
    assert config.chrome_debug_host == "127.0.0.1"
    assert config.chrome_debugger_address == "127.0.0.1:8990"


def test_empty_values_fall_back_to_defaults():
    config = RuntimeConfig.from_env(
        {"AUTOPAGE_WORKER_ID": " ", "AUTOPAGE_CHROME_DEBUG_PORT": "", "AUTOPAGE_DATA_DIR": ""}
    )

    assert config.worker_id == "default"
    assert config.chrome_debug_port == 8989
    assert config.data_dir == config_module.PROJECT_DIR


@pytest.mark.parametrize("raw", ["abc", "0", "70000", "8989.5"])
def test_invalid_port_is_rejected(raw):
    with pytest.raises(ValueError, match="AUTOPAGE_CHROME_DEBUG_PORT"):
        RuntimeConfig.from_env({"AUTOPAGE_CHROME_DEBUG_PORT": raw})


def test_module_constants_are_still_the_defaults():
    assert bm.CHROME_DEBUG_PORT == 8989
    assert bm.CHROME_DEBUG_HOST == "localhost"


def test_setup_chrome_attaches_to_the_configured_port(monkeypatch):
    captured = {}

    class FakeOptions:
        def __init__(self):
            self.capabilities = {}
            self.experimental_options = {}
            self.arguments = []

        def set_capability(self, name, value):
            self.capabilities[name] = value

        def add_experimental_option(self, name, value):
            self.experimental_options[name] = value

        def add_argument(self, argument):
            self.arguments.append(argument)

    def fake_chrome(options=None, service=None):
        captured["address"] = options.experimental_options["debuggerAddress"]
        return object()

    monkeypatch.setattr(bm, "Options", FakeOptions)
    monkeypatch.setattr(bm.webdriver, "Chrome", fake_chrome)

    manager = object.__new__(bm.BrowserManager)
    manager.config = RuntimeConfig(worker_id="w2", chrome_debug_port=8990)
    manager.logger = MagicMock()

    bm.BrowserManager.setup_chrome(manager)

    assert captured["address"] == "localhost:8990"
    manager.logger.info.assert_called_once()
    assert "port=8990" in manager.logger.info.call_args.args[0]
