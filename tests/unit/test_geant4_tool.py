"""Tests for the GEANT4 depth-dose tool.

The validation and failure paths run anywhere; the simulation itself runs only
where GEANT4 is installed, and is marked so it skips elsewhere. What the
simulation test checks is physics, not plumbing: a proton's Bragg peak has to
land at its published range, which is the one assertion a wrong geometry,
wrong units or wrong scoring volume cannot survive.
"""

import shutil
import subprocess

import pytest

from tooluniverse.geant4_tool import Geant4DepthDoseTool, _summarise


def _tool():
    return Geant4DepthDoseTool.__new__(Geant4DepthDoseTool)


def _has_geant4():
    return shutil.which("geant4-config") is not None


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "arguments, fragment",
    [
        ({"particle": "unobtainium"}, "particle must be one of"),
        ({"material": "../../etc/passwd"}, "material must be one of"),
        ({"material": "G4_WATER; rm -rf /"}, "material must be one of"),
        ({"energy_mev": 0}, "energy_mev must be between"),
        ({"energy_mev": 1e9}, "energy_mev must be between"),
        ({"energy_mev": "high"}, "energy_mev must be a number"),
        ({"thickness_cm": -5}, "thickness_cm must be between"),
        ({"bins": 3.5}, "bins must be a whole number"),
        ({"bins": 0}, "bins must be between"),
        ({"events": 10**9}, "events must be between"),
        ({"timeout_seconds": 0}, "timeout_seconds must be between"),
    ],
)
def test_arguments_outside_the_advertised_range_are_refused(arguments, fragment):
    """Nothing reaches the compiled program until every number is in range."""
    result = _tool().run(arguments)
    assert result["status"] == "error"
    assert fragment in result["error"], result["error"]


def test_a_missing_installation_is_reported_as_such(monkeypatch):
    """The error has to name what to install, not look like a tool bug."""
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.delenv("GEANT4_CONFIG", raising=False)
    result = _tool().run({})
    assert result["status"] == "error"
    assert "GEANT4 was not found" in result["error"]
    assert "geant4-config" in result["error"]


def test_a_configured_path_that_cannot_run_is_reported(monkeypatch, tmp_path):
    not_executable = tmp_path / "geant4-config"
    not_executable.write_text("#!/bin/sh\n")
    monkeypatch.setenv("GEANT4_CONFIG", str(not_executable))
    result = _tool().run({})
    assert result["status"] == "error"
    assert "not executable" in result["error"]


def test_defaults_describe_a_runnable_simulation():
    settings = Geant4DepthDoseTool._validate({})
    assert settings == {
        "particle": "proton",
        "material": "G4_WATER",
        "energy_mev": 150.0,
        "thickness_cm": 20.0,
        "bins": 100,
        "events": 200,
        "timeout_seconds": 600,
    }


def test_null_arguments_fall_back_to_the_defaults():
    """An MCP client that sends every optional field as null still gets a run."""
    settings = Geant4DepthDoseTool._validate(
        {
            "particle": None,
            "material": None,
            "energy_mev": None,
            "thickness_cm": None,
            "bins": None,
            "events": None,
            "timeout_seconds": None,
        }
    )
    assert settings["particle"] == "proton"
    assert settings["events"] == 200


def test_a_timeout_says_what_to_reduce(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.geant4_tool._geant4_config", lambda: "/usr/bin/true"
    )
    monkeypatch.setattr(
        "tooluniverse.geant4_tool._build", lambda config: ("/usr/bin/true", "11.4.3")
    )

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="depth_dose", timeout=5)

    monkeypatch.setattr(
        "tooluniverse.geant4_tool.Geant4DepthDoseTool._simulate", timeout
    )
    result = _tool().run({"timeout_seconds": 5})
    assert result["status"] == "error"
    assert "did not finish within 5 seconds" in result["error"]
    assert "fewer events" in result["error"]


def test_the_summary_reads_the_curve():
    data = {
        "edep_mev_per_bin": [1.0, 2.0, 9.0, 0.5, 0.0],
        "bin_width_cm": 2.0,
        "events": 10,
        "total_edep_mev": 125.0,
    }
    summary = _summarise(data)
    assert summary["peak_bin"] == 2
    assert summary["peak_depth_cm"] == 5.0
    assert summary["last_depth_with_dose_cm"] == 8.0
    assert summary["edep_mev_per_event"] == 12.5


def test_the_tool_is_registered_with_its_configuration():
    """The JSON and the class have to agree, or the tool never loads."""
    import json
    from pathlib import Path

    import tooluniverse

    config_path = Path(tooluniverse.__file__).parent / "data" / "geant4_tools.json"
    config = json.loads(config_path.read_text())
    assert len(config) == 1
    assert config[0]["type"] == "Geant4DepthDoseTool"
    assert config[0]["parameter"]["required"] == []
    source = Path(tooluniverse.__file__).parent / "data" / "geant4" / "depth_dose.cc"
    assert source.is_file(), "the simulation source must ship with the package"


@pytest.mark.integration
@pytest.mark.skipif(not _has_geant4(), reason="GEANT4 not installed")
def test_a_proton_stops_where_its_published_range_says_it_should():
    """150 MeV protons in water have a CSDA range of 15.77 cm (ICRU 49/PSTAR).

    A one-centimetre window around it is wide enough for Monte Carlo scatter
    at a few hundred events and narrow enough to fail on a unit error, a
    mis-scored replica or a geometry built along the wrong axis.
    """
    result = _tool().run(
        {"energy_mev": 150, "events": 100, "thickness_cm": 20, "bins": 200}
    )
    assert result["status"] == "success", result
    summary = result["data"]["summary"]
    assert 15.3 <= summary["peak_depth_cm"] <= 16.3, summary
    # Nearly all of the beam energy has to be accounted for in the target.
    assert 130.0 <= summary["edep_mev_per_event"] <= 150.0, summary
    assert len(result["data"]["edep_mev_per_bin"]) == 200
