from __future__ import annotations

import json

import pytest

from tooluniverse.remote.docker_llm import cli

pytestmark = pytest.mark.unit


def test_cli_plan_passes_only_reviewed_lifecycle_inputs(monkeypatch, capsys, tmp_path):
    observed = {}

    def fake_plan(profile, **kwargs):
        observed.update(profile=profile, **kwargs)
        return {"docker_argv": ["docker", "run", "reviewed-image"]}

    monkeypatch.setattr(cli, "plan_container", fake_plan)
    assert (
        cli.main(
            [
                "--profile",
                str(tmp_path / "profile.json"),
                "--host-port",
                "19090",
                "--container-name",
                "reviewed-container",
                "plan",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert observed["host_port"] == 19090
    assert observed["container_name"] == "reviewed-container"


def test_cli_remove_requires_explicit_yes(monkeypatch, capsys, tmp_path):
    observed = {}

    def fake_remove(profile, **kwargs):
        observed.update(profile=profile, **kwargs)
        return {"removed": kwargs["confirm"]}

    monkeypatch.setattr(cli, "remove_container", fake_remove)
    assert (
        cli.main(
            [
                "--profile",
                str(tmp_path / "profile.json"),
                "--workspace",
                str(tmp_path / "workspace"),
                "remove",
                "--yes",
            ]
        )
        == 0
    )
    assert observed["confirm"] is True
    assert observed["workspace"] == tmp_path / "workspace"
    assert json.loads(capsys.readouterr().out)["result"]["removed"] is True
