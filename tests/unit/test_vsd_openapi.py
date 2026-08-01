from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest
import yaml

from tooluniverse import ToolUniverse
from tooluniverse import vsd_dynamic_rest, vsd_promotion
from tooluniverse.vsd_openapi import (
    VSDOpenAPIError,
    inspect_openapi_document,
    select_openapi_candidate,
    validate_openapi_candidate,
)
from tooluniverse.vsd_promotion_cli import _execute, build_parser

pytestmark = pytest.mark.unit


def _document() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {"title": "Reviewed Trial Registry", "version": "2.4.0"},
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
                                "pattern": "^[Nn][Cc][Tt][0-9]{8}$",
                            },
                        },
                        {
                            "name": "fields",
                            "in": "query",
                            "style": "pipeDelimited",
                            "explode": False,
                            "schema": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 5,
                                "items": {"type": "string"},
                            },
                        },
                        {
                            "name": "format",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "enum": ["csv", "json"],
                                "default": "json",
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
                        "nctId": {"$ref": "#/components/schemas/NctId"},
                        "status": {"type": "string"},
                        "enrollment": {"type": "integer", "nullable": True},
                    },
                    "required": ["nctId", "status"],
                    "additionalProperties": False,
                },
                "NctId": {"type": "string", "minLength": 11, "maxLength": 11},
            }
        },
    }


def _write_document(tmp_path, document=None, *, suffix=".json"):
    value = _document() if document is None else document
    path = tmp_path / f"registry{suffix}"
    text = json.dumps(value) if suffix == ".json" else yaml.safe_dump(value)
    path.write_text(text, encoding="utf-8")
    return path


def _candidate(tmp_path):
    report = inspect_openapi_document(_write_document(tmp_path))
    assert report["candidate_count"] == 1
    return report["candidates"][0]


def _object_cases():
    return [
        {
            "arguments": {"nctId": nct_id},
            "expect": {
                "result_type": "object",
                "required_fields": ["nctId", "status"],
                "equals": {"nctId": nct_id},
                "required_paths": ["/nctId"],
                "equals_paths": {"/nctId": nct_id},
            },
        }
        for nct_id in ("NCT00522899", "NCT00791154", "NCT01766297")
    ]


def _fake_get(url, params, *, timeout):
    nct_id = url.rsplit("/", 1)[-1]
    assert params == {"format": "json"}
    assert timeout == 20.0
    payload = {"nctId": nct_id, "status": "COMPLETED", "enrollment": 120}
    return payload, {
        "status_code": 200,
        "content_type": "application/json",
        "response_bytes": len(json.dumps(payload).encode()),
        "redirects": 0,
    }


def test_json_and_yaml_documents_produce_equivalent_operation_contracts(tmp_path):
    json_candidate = inspect_openapi_document(
        _write_document(tmp_path, suffix=".json")
    )["candidates"][0]
    yaml_candidate = inspect_openapi_document(
        _write_document(tmp_path, suffix=".yaml")
    )["candidates"][0]

    ignored = {"source_document_sha256", "candidate_id", "candidate_sha256"}
    assert {k: v for k, v in json_candidate.items() if k not in ignored} == {
        k: v for k, v in yaml_candidate.items() if k not in ignored
    }
    assert json_candidate["blockers"] == []
    assert json_candidate["parameters"][1]["style"] == "pipeDelimited"
    assert json_candidate["response_schema"]["$defs"]["Study"]["properties"][
        "enrollment"
    ]["type"] == ["integer", "null"]


def test_openapi_31_boolean_response_schema_is_supported(tmp_path):
    document = _document()
    document["openapi"] = "3.1.1"
    document["paths"]["/studies/{nctId}"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] = True
    candidate = inspect_openapi_document(_write_document(tmp_path, document))[
        "candidates"
    ][0]
    assert candidate["blockers"] == []
    assert candidate["response_schema"] == {}


@pytest.mark.parametrize(
    "contents, suffix, message",
    [
        ('{"openapi":"3.0.3","openapi":"3.1.0"}', ".json", "duplicate"),
        (
            "openapi: 3.0.3\ninfo: &info\n  title: A\n  version: B\ncopy: *info\n",
            ".yaml",
            "aliases",
        ),
        (
            "openapi: 3.0.3\ninfo:\n  title: A\n  title: B\n  version: C\n",
            ".yaml",
            "duplicate",
        ),
    ],
)
def test_loader_rejects_ambiguous_json_and_yaml(tmp_path, contents, suffix, message):
    path = tmp_path / f"bad{suffix}"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(VSDOpenAPIError, match=message):
        inspect_openapi_document(path)


def test_loader_rejects_wrong_version_excessive_depth_and_file_size(tmp_path):
    wrong = _document()
    wrong["openapi"] = "2.0"
    with pytest.raises(VSDOpenAPIError, match="3.0 and 3.1"):
        inspect_openapi_document(_write_document(tmp_path, wrong))

    deep: dict = {}
    cursor = deep
    for _ in range(105):
        cursor["next"] = {}
        cursor = cursor["next"]
    path = tmp_path / "deep.json"
    path.write_text(json.dumps(deep), encoding="utf-8")
    with pytest.raises(VSDOpenAPIError, match="depth"):
        inspect_openapi_document(path)

    large = tmp_path / "large.json"
    large.write_bytes(b" " * 1_000_001)
    with pytest.raises(VSDOpenAPIError, match="1 MB"):
        inspect_openapi_document(large)


def test_inspection_exposes_explicit_non_promotable_reasons(tmp_path):
    document = _document()
    get = document["paths"]["/studies/{nctId}"]["get"]
    get["security"] = [{"bearerAuth": []}]
    get["parameters"].append(
        {
            "name": "X-Required",
            "in": "header",
            "required": True,
            "schema": {"type": "string"},
        }
    )
    document["paths"]["/studies/{nctId}"]["post"] = deepcopy(get)
    report = inspect_openapi_document(_write_document(tmp_path, document))

    by_method = {item["method"]: item for item in report["candidates"]}
    assert "authentication_required" in by_method["GET"]["blockers"]
    assert "unsupported_header_parameter:X-Required" in by_method["GET"]["blockers"]
    assert "method_not_read_only" in by_method["POST"]["blockers"]
    with pytest.raises(VSDOpenAPIError, match="not promotable"):
        validate_openapi_candidate(by_method["GET"])


def test_external_schema_reference_blocks_only_affected_operation(tmp_path):
    document = _document()
    schema = document["paths"]["/studies/{nctId}"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]
    schema["$ref"] = "https://example.org/schema.json"
    report = inspect_openapi_document(_write_document(tmp_path, document))
    assert report["promotable_count"] == 0
    assert any(
        "external_or_unsupported_schema_reference" in blocker
        for blocker in report["candidates"][0]["blockers"]
    )


def test_candidate_hash_detects_operation_metadata_tampering(tmp_path):
    candidate = _candidate(tmp_path)
    candidate["server_url"] = "https://example.org"
    with pytest.raises(VSDOpenAPIError, match="digest"):
        validate_openapi_candidate(candidate)


def test_candidate_validation_rejects_malformed_rehashed_parameter_contract(tmp_path):
    candidate = _candidate(tmp_path)
    candidate["parameters"][1]["style"] = "deepObject"
    body = {
        key: value
        for key, value in candidate.items()
        if key not in {"candidate_id", "candidate_sha256"}
    }
    digest = hashlib.sha256(
        json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()
    candidate["candidate_id"] = digest[:16]
    candidate["candidate_sha256"] = digest
    with pytest.raises(VSDOpenAPIError, match="parameter contract"):
        validate_openapi_candidate(candidate)


def test_generator_builds_narrow_mappings_and_serialization(tmp_path):
    config = vsd_promotion.build_openapi_tool_config(
        _candidate(tmp_path),
        tool_name="GeneratedTrialRecord",
        description="Fetch one reviewed trial-registry record by its NCT identifier.",
        include_parameters=["nctId", "fields"],
        fixed_query={"format": "json"},
    )
    operation = config["vsd_operation"]
    assert config["parameter"]["required"] == ["nctId"]
    assert operation["path_arguments"] == {"nctId": "nctId"}
    assert operation["query_arguments"] == {"fields": "fields"}
    assert operation["query_serialization"] == {
        "fields": {"style": "pipeDelimited", "explode": False}
    }
    assert operation["fixed_query"] == {"format": "json"}

    endpoint, query = vsd_dynamic_rest._provider_request(
        config,
        {"nctId": "NCT00522899", "fields": ["NCTId", "BriefTitle"]},
    )
    assert endpoint.endswith("/studies/NCT00522899")
    assert query == {"format": "json", "fields": "NCTId|BriefTitle"}


def test_generator_rejects_unknown_conflicting_and_invalid_fixed_parameters(tmp_path):
    candidate = _candidate(tmp_path)
    kwargs = {
        "candidate": candidate,
        "tool_name": "GeneratedTrialRecord",
        "description": "Fetch one reviewed trial-registry record by NCT identifier.",
    }
    with pytest.raises(vsd_promotion.VSDPromotionError, match="Unknown OpenAPI"):
        vsd_promotion.build_openapi_tool_config(
            **kwargs, include_parameters=["missing"]
        )
    with pytest.raises(vsd_promotion.VSDPromotionError, match="fixed and exposed"):
        vsd_promotion.build_openapi_tool_config(
            **kwargs,
            include_parameters=["nctId", "format"],
            fixed_query={"format": "json"},
        )
    with pytest.raises(vsd_promotion.VSDPromotionError, match="is invalid"):
        vsd_promotion.build_openapi_tool_config(**kwargs, fixed_query={"format": "xml"})


def test_openapi_object_operation_completes_promotion_and_fresh_load(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", _fake_get)
    draft = vsd_promotion.create_openapi_draft(
        _candidate(tmp_path),
        tool_name="GeneratedTrialRecord",
        description="Fetch one reviewed trial-registry record by its NCT identifier.",
        fixed_query={"format": "json"},
        workspace=tmp_path / "promotion",
    )
    evidence = vsd_promotion.verify_draft(
        draft["draft_id"], _object_cases(), workspace=tmp_path / "promotion"
    )
    approval = vsd_promotion.approve_draft(
        draft["draft_id"],
        reviewed_by="Test Reviewer",
        decision_note="Approved after three distinct trial identifiers passed verification.",
        workspace=tmp_path / "promotion",
    )
    publication = vsd_promotion.publish_draft(
        draft["draft_id"], workspace=tmp_path / "promotion"
    )

    tooluniverse = ToolUniverse()
    try:
        loaded = vsd_promotion.load_published_tools(
            tooluniverse, workspace=tmp_path / "promotion"
        )
        response = tooluniverse.run_one_function(
            {
                "name": "GeneratedTrialRecord",
                "arguments": {"nctId": "NCT00522899"},
            },
            use_cache=False,
        )
    finally:
        tooluniverse.close()

    assert loaded == ["GeneratedTrialRecord"]
    assert evidence["case_count"] == 3
    assert all(case["result_type"] == "object" for case in evidence["cases"])
    assert approval["operation_sha256"] == draft["operation_sha256"]
    assert publication["config"]["vsd_promotion"]["source_type"] == "openapi"
    assert response["data"]["result"]["nctId"] == "NCT00522899"


def test_cli_inspects_selects_and_creates_openapi_draft(tmp_path):
    spec_path = _write_document(tmp_path)
    report = _execute(build_parser().parse_args(["inspect-openapi", str(spec_path)]))
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    fixed_path = tmp_path / "fixed.json"
    fixed_path.write_text('{"format":"json"}', encoding="utf-8")

    draft = _execute(
        build_parser().parse_args(
            [
                "--workspace",
                str(tmp_path / "promotion"),
                "draft-openapi",
                str(report_path),
                "--candidate-id",
                report["candidates"][0]["candidate_id"],
                "--tool-name",
                "GeneratedTrialRecord",
                "--description",
                "Fetch one reviewed trial-registry record by its NCT identifier.",
                "--fixed-query-file",
                str(fixed_path),
            ]
        )
    )
    assert draft["config"]["vsd_promotion"]["operation_id"] == "fetchStudy"
    assert select_openapi_candidate(
        report, draft["config"]["vsd_promotion"]["candidate_id"]
    )
