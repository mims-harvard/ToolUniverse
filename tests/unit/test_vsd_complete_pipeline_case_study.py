from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tooluniverse import vsd_discovery, vsd_dynamic_rest, vsd_tool

pytestmark = pytest.mark.unit


MODULE_PATH = (
    Path(__file__).parents[2] / "examples" / "vsd" / "complete_pipeline_case_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_complete_pipeline_case_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


def _request(url: str, payload: object) -> dict:
    return {
        "url": url,
        "status_code": 200,
        "content_type": "application/json",
        "response_bytes": len(json.dumps(payload)),
        "peer_ip": "8.8.8.8",
        "redirects": 0,
    }


def _label_payload() -> dict:
    return {
        "meta": {"results": {"total": 14}},
        "results": [
            {
                "set_id": "1e6ff055-590c-41e6-9530-1fdf04cdbd02",
                "effective_time": "20211129",
                "warnings": ["Reviewed warning section"],
                "openfda": {
                    "brand_name": ["SOLTAMOX"],
                    "generic_name": ["TAMOXIFEN CITRATE"],
                    "route": ["ORAL"],
                },
            }
        ],
    }


def _catalog_payload() -> dict:
    fields = [
        "date_opened",
        "protocol",
        "primary_site",
        "study_phase",
        "title",
        "date_closed",
        "principal_investigator",
    ]
    return {
        "results": [
            {
                "resource": {
                    "name": "Current Active Clinical Trials",
                    "id": "2ig8-yxf8",
                    "description": "Active cancer studies by site, phase, and protocol.",
                    "type": "dataset",
                    "updatedAt": "2026-04-14T21:08:58Z",
                    "provenance": "official",
                    "columns_name": [
                        field.replace("_", " ").title() for field in fields
                    ],
                    "columns_field_name": fields,
                    "columns_datatype": ["Text"] * len(fields),
                    "columns_description": [""] * len(fields),
                },
                "metadata": {"domain": "data.ny.gov"},
                "classification": {"domain_tags": ["cancer", "clinical trials"]},
                "permalink": "https://data.ny.gov/d/2ig8-yxf8",
            }
        ],
        "resultSetSize": 13,
    }


def _trial(nct_id: str, *, status: str, phase: str) -> dict:
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": nct_id,
                "briefTitle": f"Breast cancer study {nct_id}",
            },
            "statusModule": {"overallStatus": status},
            "designModule": {"phases": [phase]},
            "conditionsModule": {"conditions": ["Breast Cancer"]},
            "contactsLocationsModule": {
                "locations": [
                    {
                        "facility": "Cancer Center",
                        "city": "Buffalo",
                        "state": "New York",
                        "country": "United States",
                        "status": "RECRUITING",
                    }
                ]
            },
        }
    }


def test_complete_case_exercises_every_boundary_and_writes_auditable_artifacts(
    monkeypatch, tmp_path: Path
):
    label_payload = _label_payload()
    fda_calls = []

    def fake_vsd_get(url, params=None, **_kwargs):
        assert url == study.OPENFDA_ENDPOINT
        fda_calls.append(dict(params or {}))
        return label_payload, _request(url, label_payload)

    monkeypatch.setattr(
        vsd_tool, "_resolve_public_addresses", lambda _host, _port: ("8.8.8.8",)
    )
    monkeypatch.setattr(vsd_tool, "_safe_get_json", fake_vsd_get)

    catalog_payload = _catalog_payload()

    def fake_discovery_get(url, params, *, timeout):
        assert url == "https://api.us.socrata.com/api/catalog/v1"
        assert params["q"] == study.DISCOVERY_QUERY
        assert timeout == 20
        return catalog_payload, _request(url, catalog_payload)

    monkeypatch.setattr(vsd_discovery, "_safe_get_json", fake_discovery_get)

    trials = [
        _trial("NCT00000002", status="RECRUITING", phase="PHASE2"),
        _trial("NCT00000001", status="NOT_YET_RECRUITING", phase="PHASE3"),
    ]
    dynamic_calls = []

    def fake_dynamic_get(url, params, *, timeout):
        dynamic_calls.append((url, dict(params), timeout))
        if url == "https://clinicaltrials.gov/api/v2/studies":
            assert "NCTId" in params["fields"]
            assert "LocationState" in params["fields"]
            payload = {"studies": trials, "totalCount": 546, "nextPageToken": "next"}
            return payload, _request(url, payload)
        if url.endswith("/studies/NCT00000001"):
            return trials[1], _request(url, trials[1])
        assert url == "https://data.ny.gov/resource/2ig8-yxf8.json"
        filter_field = next(key for key in params if not key.startswith("$"))
        value = params[filter_field]
        rows = [
            {
                "date_opened": "2024-01-01T00:00:00.000",
                "protocol": f"RPCI-{index}",
                "primary_site": (value if filter_field == "primary_site" else "Breast"),
                "study_phase": value if filter_field == "study_phase" else "II",
                "title": f"Verified trial {index}",
                "principal_investigator": "Example Investigator",
            }
            for index in range(1, 3)
        ]
        return rows, _request(url, rows)

    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", fake_dynamic_get)

    workspace = tmp_path / "complete"
    snapshot = study.run_case(workspace=workspace)
    output_json = tmp_path / "snapshot.json"
    output_markdown = tmp_path / "snapshot.md"
    study.write_artifacts(snapshot, output_json, output_markdown)

    assert len(fda_calls) == 3
    assert len(dynamic_calls) == 10
    assert snapshot["administrative_source_lifecycle"]["catalog_restored"] is True
    assert snapshot["reviewed_source_adapter"]["administrative_tools_loaded"] == []
    assert snapshot["reviewed_source_adapter"]["label"]["generic_name"] == (
        "TAMOXIFEN CITRATE"
    )
    assert (
        snapshot["reviewed_dynamic_rest"]["detail_follow_up"]["selected_nct_id"]
        == "NCT00000001"
    )
    assert snapshot["demand_discovery"]["selected_candidate"]["dataset_id"] == (
        "2ig8-yxf8"
    )
    assert (
        snapshot["demand_discovery"]["selected_candidate"]["execution_allowed"] is False
    )
    assert snapshot["reviewed_promotion"]["verification_case_count"] == 6
    assert snapshot["reviewed_promotion"]["loaded_tools"] == [
        "VSDTotalCancerTrialsByPhase",
        "VSDTotalCancerTrialsBySite",
    ]
    assert all(snapshot["end_to_end_assertions"].values())
    assert len(snapshot["audit_chain"]["sha256"]) == 64
    assert (
        json.loads(output_json.read_text(encoding="utf-8"))["audit_chain"]
        == (snapshot["audit_chain"])
    )
    report = output_markdown.read_text(encoding="utf-8")
    assert "Complete VSD Oncology Source-Governance Case Study" in report
    assert "Administrator-only source catalog" in report
    assert "Demand-Driven API Discovery" in report
    assert "End-to-End Assertions" in report

    tampered = copy.deepcopy(snapshot)
    tampered["reviewed_promotion"]["runtime_checks"][0]["provenance"][
        "payload_sha256"
    ] = "0" * 64
    with pytest.raises(ValueError, match="Audit-chain inputs"):
        study.validate_snapshot(tampered)

    incomplete = copy.deepcopy(snapshot)
    incomplete["end_to_end_assertions"].pop("administrative_catalog_restored")
    with pytest.raises(ValueError, match="end-to-end assertions"):
        study.validate_snapshot(incomplete)


def test_discovery_review_refuses_an_executable_or_incomplete_candidate():
    candidates = vsd_discovery.discover_api_candidates(
        study.DISCOVERY_QUERY,
        limit=1,
        catalog_payload=_catalog_payload(),
    )
    candidates[0]["execution_allowed"] = True
    with pytest.raises(RuntimeError, match="No discovered API"):
        study._review_discovery({"candidates": candidates})

    candidates = vsd_discovery.discover_api_candidates(
        study.DISCOVERY_QUERY,
        limit=1,
        catalog_payload=_catalog_payload(),
    )
    candidates[0]["fields"] = [
        field
        for field in candidates[0]["fields"]
        if field["field"] != "principal_investigator"
    ]
    with pytest.raises(RuntimeError, match="No discovered API"):
        study._review_discovery({"candidates": candidates})


def test_checked_complete_pipeline_artifacts_are_synchronized_and_valid():
    artifacts = MODULE_PATH.parent / "artifacts"
    snapshot = json.loads(
        (artifacts / "complete_pipeline_snapshot.json").read_text(encoding="utf-8")
    )
    study.validate_snapshot(snapshot)
    assert (artifacts / "complete_pipeline_snapshot.md").read_text(
        encoding="utf-8"
    ) == study.render_markdown(snapshot)
    assert all(snapshot["end_to_end_assertions"].values())

    workspace = artifacts / "complete_pipeline_workspace"
    assert json.loads(
        (workspace / "catalog" / "sources.json").read_text(encoding="utf-8")
    ) == {"version": 1, "sources": {}}
    for promotion in snapshot["reviewed_promotion"]["promotions"]:
        draft_id = promotion["draft_id"]
        tool_name = promotion["tool_name"]
        records = {
            "draft_sha256": workspace / "promotion" / "drafts" / f"{draft_id}.json",
            "verification_sha256": workspace
            / "promotion"
            / "evidence"
            / f"{draft_id}.json",
            "approval_sha256": workspace
            / "promotion"
            / "approvals"
            / f"{draft_id}.json",
            "publication_sha256": workspace
            / "promotion"
            / "approved"
            / f"{tool_name}.json",
        }
        for hash_field, path in records.items():
            record = json.loads(path.read_text(encoding="utf-8"))
            assert record[hash_field] == promotion[hash_field]
