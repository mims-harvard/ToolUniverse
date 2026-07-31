from __future__ import annotations

import json

import pytest

from tooluniverse import vsd_admin_cli, vsd_tool

pytestmark = pytest.mark.unit


def _last_json(capsys):
    return json.loads(capsys.readouterr().out)


def test_admin_cli_runs_mutable_catalog_workflow(monkeypatch, tmp_path, capsys):
    """The explicit CLI retains registration, generic query, and removal."""
    monkeypatch.setenv("TOOLUNIVERSE_VSD_DIR", str(tmp_path))
    calls = []

    def fake_safe_get(endpoint, params=None, **kwargs):
        del kwargs
        calls.append((endpoint, params or {}))
        return (
            {"call": len(calls)},
            {
                "url": endpoint,
                "status_code": 200,
                "content_type": "application/json",
                "response_bytes": 10,
                "peer_ip": "93.184.216.34",
                "redirects": 0,
            },
        )

    monkeypatch.setattr(vsd_tool, "_safe_get_json", fake_safe_get)

    assert (
        vsd_admin_cli.main(
            [
                "register",
                "study_source",
                "https://api.fda.gov/drug/label.json",
                "--default-params",
                '{"limit": 1}',
            ]
        )
        == 0
    )
    assert _last_json(capsys)["data"]["registered"] is True

    assert vsd_admin_cli.main(["list"]) == 0
    assert _last_json(capsys)["data"]["sources"][0]["source_id"] == "study_source"

    assert vsd_admin_cli.main(["query", "study_source"]) == 0
    assert _last_json(capsys)["data"]["result"] == {"call": 2}

    assert vsd_admin_cli.main(["remove", "study_source"]) == 0
    assert _last_json(capsys)["data"]["removed"] is True


@pytest.mark.parametrize("value", ["[]", "null", "1", '"text"'])
def test_admin_cli_requires_json_object_parameters(value):
    """Administrative parameter overrides must be JSON objects."""
    with pytest.raises(SystemExit):
        vsd_admin_cli.build_parser().parse_args(
            ["query", "study_source", "--params", value]
        )
