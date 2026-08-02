from __future__ import annotations

import hashlib
import json

import pytest

from tooluniverse import vsd_dynamic_rest, vsd_promotion_cli

pytestmark = pytest.mark.unit


def _snapshot() -> dict:
    endpoint = "https://data.ny.gov/resource/2ig8-yxf8.json"
    return {
        "analysis": {
            "selected_candidate": {
                "api_endpoint": endpoint,
                "approval_state": "unreviewed_candidate",
                "candidate_id": hashlib.sha256(endpoint.encode()).hexdigest()[:16],
                "catalog_domain": "data.ny.gov",
                "dataset_id": "2ig8-yxf8",
                "execution_allowed": False,
                "metadata_trust": "untrusted_catalog_metadata",
                "fields": [
                    {"field": "primary_site", "json_type": "string"},
                    {"field": "protocol", "json_type": "string"},
                    {"field": "title", "json_type": "string"},
                ],
            }
        }
    }


def test_cli_accepts_discovery_snapshot_and_runs_every_gate(
    tmp_path, monkeypatch, capsys
):
    candidate_file = tmp_path / "discovery.json"
    candidate_file.write_text(json.dumps(_snapshot()), encoding="utf-8")
    cases_file = tmp_path / "cases.json"
    cases_file.write_text(
        json.dumps(
            [
                {
                    "arguments": {"primary_site": value},
                    "expect": {
                        "min_items": 1,
                        "max_items": 10,
                        "required_fields": ["primary_site", "protocol", "title"],
                        "equals": {"primary_site": value},
                    },
                }
                for value in ("Breast", "Prostate", "Lung")
            ]
        ),
        encoding="utf-8",
    )

    def fake_get(url, params, *, timeout):
        value = params["primary_site"]
        rows = [{"primary_site": value, "protocol": "P-1", "title": "Trial"}]
        return rows, {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": len(json.dumps(rows)),
            "redirects": 0,
        }

    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", fake_get)
    base = ["--workspace", str(tmp_path / "workspace")]
    assert (
        vsd_promotion_cli.main(
            base
            + [
                "draft-socrata",
                str(candidate_file),
                "--tool-name",
                "GeneratedCancerTrialsBySite",
                "--description",
                "Query reviewed cancer trials by their primary cancer site.",
                "--filter-fields",
                "primary_site",
                "--return-fields",
                "primary_site,protocol,title",
                "--max-records",
                "10",
            ]
        )
        == 0
    )
    draft_id = json.loads(capsys.readouterr().out)["draft_id"]
    assert vsd_promotion_cli.main(base + ["verify", draft_id, str(cases_file)]) == 0
    capsys.readouterr()
    assert (
        vsd_promotion_cli.main(
            base
            + [
                "approve",
                draft_id,
                "--reviewed-by",
                "Test Reviewer",
                "--decision-note",
                "Approved after three representative provider cases passed.",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert vsd_promotion_cli.main(base + ["publish", draft_id]) == 0
    capsys.readouterr()
    assert vsd_promotion_cli.main(base + ["list"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["approved"] == ["GeneratedCancerTrialsBySite"]
