from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

from tooluniverse import vsd_dynamic_rest

pytestmark = pytest.mark.unit

MODULE_PATH = (
    Path(__file__).parents[2] / "examples" / "vsd" / "openapi_als_case_study.py"
)
SPEC = importlib.util.spec_from_file_location("vsd_openapi_als_case_study", MODULE_PATH)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


def _specification() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {"title": "ClinicalTrials.gov REST API", "version": "2.0.3"},
        "servers": [{"url": "https://clinicaltrials.gov/api/v2"}],
        "paths": {
            "/studies/{nctId}": {
                "get": {
                    "operationId": "fetchStudy",
                    "summary": "Single Study",
                    "parameters": [
                        {
                            "name": "nctId",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "pattern": "^[Nn][Cc][Tt]0*[1-9]\\d{0,7}$",
                            },
                        },
                        {
                            "name": "format",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "enum": ["csv", "json"],
                            },
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Study"}
                                }
                            },
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "Study": {
                    "type": "object",
                    "properties": {
                        "protocolSection": {
                            "$ref": "#/components/schemas/ProtocolSection"
                        }
                    },
                    "required": ["protocolSection"],
                },
                "ProtocolSection": {
                    "type": "object",
                    "properties": {
                        "identificationModule": {"type": "object"},
                        "statusModule": {"type": "object"},
                        "conditionsModule": {"type": "object"},
                        "designModule": {"type": "object"},
                    },
                    "required": [
                        "identificationModule",
                        "statusModule",
                        "conditionsModule",
                    ],
                },
            }
        },
    }


def _payload(nct_id: str) -> dict:
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": nct_id,
                "briefTitle": f"ALS registry study {nct_id}",
            },
            "statusModule": {"overallStatus": "COMPLETED"},
            "conditionsModule": {"conditions": ["Amyotrophic Lateral Sclerosis"]},
            "designModule": {"phases": ["PHASE2"]},
        }
    }


def test_openapi_als_case_runs_full_hash_bound_pipeline(monkeypatch, tmp_path):
    calls = []

    def fake_get(url, params, *, timeout):
        nct_id = url.rsplit("/", 1)[-1]
        calls.append(nct_id)
        assert params == {"format": "json"}
        assert timeout == 30.0
        payload = _payload(nct_id)
        return payload, {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": len(json.dumps(payload).encode()),
            "redirects": 0,
        }

    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", fake_get)
    spec_path = tmp_path / "ctg-openapi.yaml"
    spec_path.write_text(yaml.safe_dump(_specification()), encoding="utf-8")
    snapshot = study.run_case(spec_path=spec_path, workspace=tmp_path / "promotion")
    output_json = tmp_path / "snapshot.json"
    output_md = tmp_path / "snapshot.md"
    study.write_artifacts(snapshot, output_json, output_md)

    assert calls == [*study.ALS_STUDIES, *study.ALS_STUDIES]
    assert snapshot["inspection"]["candidate_count"] == 1
    assert snapshot["promotion"]["verification_case_count"] == 3
    assert [item["nct_id"] for item in snapshot["retrieved_als_records"]] == list(
        study.ALS_STUDIES
    )
    assert all(snapshot["end_to_end_assertions"].values())
    assert len(snapshot["audit_sha256"]) == 64
    assert (
        json.loads(output_json.read_text(encoding="utf-8"))["hash_chain"]
        == (snapshot["hash_chain"])
    )
    report = output_md.read_text(encoding="utf-8")
    assert "OpenAPI-to-Tool ALS Registry Case Study" in report
    assert "Official Contract Inspection" in report
    assert "Verification And Approval" in report
    assert "End-to-End Assertions" in report

    tampered = copy.deepcopy(snapshot)
    tampered["retrieved_als_records"][0]["overall_status"] = "RECRUITING"
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_snapshot(tampered)
