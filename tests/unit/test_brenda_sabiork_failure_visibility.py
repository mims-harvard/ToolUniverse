"""Regression guard for Fix-R14D-1: BRENDA_get_enzyme_kinetics wrapped its
entire SABIO-RK section in one bare `except Exception: pass`, so any failure
there (confirmed live: sabiork.h-its.org connection timeouts from this
network) silently dropped "kinetic_parameters" -- the tool's headline
capability -- from the response entirely, with status:"success" and no
indication SABIO-RK was even attempted. The fix records the failure in
metadata and always includes kinetic_parameters/sabiork_total_entries keys
(empty on failure) instead of omitting them.
"""

import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.brenda_tool import BRENDATool

pytestmark = pytest.mark.unit


def _tool():
    return BRENDATool({"name": "BRENDA_get_enzyme_kinetics"})


def test_sabiork_timeout_is_surfaced_not_swallowed(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(
        tool,
        "_fetch_expasy_enzyme",
        lambda ec: {
            "name": "hexokinase",
            "alternative_names": [],
            "catalytic_activity": [],
            "comments": [],
        },
    )

    def fake_sabiork(ec_number, organism, limit):
        raise requests.exceptions.ConnectTimeout("connection timed out")

    monkeypatch.setattr(tool, "_fetch_sabiork_kinetics", fake_sabiork)

    result = tool._get_enzyme_kinetics({"ec_number": "2.7.1.1"})

    assert result["status"] == "success"
    assert result["data"]["kinetic_parameters"] == []
    assert result["data"]["sabiork_total_entries"] == 0
    assert "timed out" in result["metadata"]["sabiork_error"]
    assert "SABIO-RK" not in result["metadata"]["sources"]


def test_sabiork_success_reports_no_error(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(
        tool,
        "_fetch_expasy_enzyme",
        lambda ec: {
            "name": "hexokinase",
            "alternative_names": [],
            "catalytic_activity": [],
            "comments": [],
        },
    )
    monkeypatch.setattr(
        tool,
        "_fetch_sabiork_kinetics",
        lambda ec_number, organism, limit: {
            "kinetic_laws": [{"parameters": [{"type": "Km", "value": 0.1}]}],
            "total_count": 1,
        },
    )

    result = tool._get_enzyme_kinetics({"ec_number": "2.7.1.1"})

    assert result["status"] == "success"
    assert result["data"]["sabiork_total_entries"] == 1
    assert "SABIO-RK" in result["metadata"]["sources"]
    assert "sabiork_error" not in result["metadata"]


def test_sabiork_generic_exception_still_records_error(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(
        tool,
        "_fetch_expasy_enzyme",
        lambda ec: {
            "name": "hexokinase",
            "alternative_names": [],
            "catalytic_activity": [],
            "comments": [],
        },
    )

    def fake_sabiork(ec_number, organism, limit):
        raise ValueError("unexpected SBML shape")

    monkeypatch.setattr(tool, "_fetch_sabiork_kinetics", fake_sabiork)

    result = tool._get_enzyme_kinetics({"ec_number": "2.7.1.1"})

    assert result["status"] == "success"
    assert result["data"]["kinetic_parameters"] == []
    assert "ValueError" in result["metadata"]["sabiork_error"]
