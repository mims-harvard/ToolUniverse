from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tooluniverse import vsd_discovery

pytestmark = pytest.mark.unit


MODULE_PATH = (
    Path(__file__).parents[2] / "examples" / "vsd" / "api_discovery_case_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_api_discovery_case_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


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


def test_complex_discovery_case_runs_and_writes_review_artifacts(
    monkeypatch, tmp_path: Path
):
    """The full discovery case finds, screens, and documents a non-executable API."""

    def fake_get(url, params, *, timeout):
        assert url == "https://api.us.socrata.com/api/catalog/v1"
        assert params["q"] == study.QUERY
        assert timeout == 20
        return _catalog_payload(), {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": 4000,
            "redirects": 0,
        }

    monkeypatch.setattr(vsd_discovery, "_safe_get_json", fake_get)
    evidence = study.run_case()
    json_path, markdown_path = study.write_artifacts(evidence, tmp_path)

    selected = evidence["analysis"]["selected_candidate"]
    assert selected["dataset_id"] == "2ig8-yxf8"
    assert selected["matched_capability_count"] == 6
    assert selected["recommended_for_contract_review"] is True
    assert selected["execution_allowed"] is False
    assert (
        json.loads(json_path.read_text(encoding="utf-8"))["analysis"][
            "normalized_candidate_count"
        ]
        == 1
    )
    report = markdown_path.read_text(encoding="utf-8")
    assert "Demand-Driven API Discovery Validation" in report
    assert "Execution allowed: **no**" in report


def test_readiness_screen_rejects_nonofficial_or_incomplete_candidates():
    """Discovery relevance cannot bypass the explicit contract-review gate."""
    candidate = vsd_discovery.discover_api_candidates(
        study.QUERY, limit=1, catalog_payload=_catalog_payload()
    )[0]
    candidate["provenance_label"] = "community"
    candidate["score"]["official_catalog_label"] = 0.0
    data = {
        "query": study.QUERY,
        "candidates": [candidate],
        "catalog_result_count": 1,
        "provenance": {},
        "boundary": "unreviewed",
    }
    result = study.analyze_discovery(data)
    assert result["recommended_candidate_count"] == 0
    assert result["selected_candidate"] is None
