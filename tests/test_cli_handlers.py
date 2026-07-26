"""Unit tests for Archangel CLI handlers."""

from unittest.mock import MagicMock
from archangel.cli.handlers import cmd_version, cmd_status, cmd_clear, cmd_watch


def test_cmd_version():
    console = MagicMock()
    res = cmd_version(console)
    assert res is True
    assert console.print.called


def test_cmd_status():
    console = MagicMock()
    res = cmd_status(console, as_json=True)
    assert res is True
    assert console.print.called


def test_cmd_clear():
    console = MagicMock()
    res = cmd_clear(console)
    assert res is True


def test_cmd_watch():
    console = MagicMock()
    res = cmd_watch(console, duration_seconds=0.3)
    assert res is True
    assert console.print.called
