from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tooluniverse import (
    ToolUniverse,
    vsd_dynamic_rest,
    vsd_lifecycle_cli,
    vsd_promotion,
)
from tooluniverse.vsd_lifecycle import (
    VSDLifecycleError,
    _validation_view,
    assess_openapi_drift,
    list_publication_states,
    set_publication_state,
    validate_drift_assessment,
)
from tooluniverse.vsd_openapi import inspect_openapi_document

pytestmark = pytest.mark.unit

TOOL_NAME = "VSDProtectedRareDiseaseRecord"
ENV_VAR = "TOOLUNIVERSE_VSD_LIFECYCLE_TEST_KEY"
SECRET = "lifecycle-test-secret"
RECORDS = {
    "RD-ALS": {
        "record_id": "RD-ALS",
        "disease": "Amyotrophic lateral sclerosis",
        "genes": ["C9orf72", "SOD1"],
        "trials": ["NCT05163886"],
    },
    "RD-DMD": {
        "record_id": "RD-DMD",
        "disease": "Duchenne muscular dystrophy",
        "genes": ["DMD"],
        "trials": ["NCT05096221"],
    },
    "RD-SMA": {
        "record_id": "RD-SMA",
        "disease": "Spinal muscular atrophy",
        "genes": ["SMN1", "SMN2"],
        "trials": ["NCT05337553"],
    },
}


def test_validation_view_removes_annotations_without_dropping_named_properties():
    schema = {
        "type": "object",
        "description": "Root annotation",
        "properties": {
            "description": {
                "type": "string",
                "description": "Property annotation",
            },
            "default": {"type": "number", "default": 1},
            "title": {"type": "boolean", "title": "A title"},
        },
        "required": ["description", "default", "title"],
    }
    assert _validation_view(schema) == {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "default": {"type": "number"},
            "title": {"type": "boolean"},
        },
        "required": ["description", "default", "title"],
    }


def _specification(
    *,
    api_version: str = "1.0.0",
    summary: str = "Retrieve one protected rare-disease record",
    server_url: str = "https://rare-registry.example.org/v1",
    auth_location: str = "header",
    path: str = "/evidence/{recordId}",
    add_response_requirement: bool = False,
    add_required_query: bool = False,
) -> dict:
    properties = {
        "record_id": {"type": "string"},
        "disease": {"type": "string"},
        "genes": {"type": "array", "items": {"type": "string"}},
        "trials": {"type": "array", "items": {"type": "string"}},
    }
    required = ["record_id", "disease", "genes", "trials"]
    if add_response_requirement:
        properties["evidence_level"] = {"type": "string", "enum": ["reviewed"]}
        required.append("evidence_level")
    parameters = [
        {
            "name": "recordId",
            "in": "path",
            "required": True,
            "schema": {"type": "string", "pattern": "^RD-[A-Z]+$"},
        }
    ]
    if add_required_query:
        parameters.append(
            {
                "name": "tenant",
                "in": "query",
                "required": True,
                "schema": {"type": "string", "minLength": 3},
            }
        )
    return {
        "openapi": "3.1.0",
        "info": {"title": "Rare Disease Registry", "version": api_version},
        "servers": [{"url": server_url}],
        "security": [{"registryKey": []}],
        "paths": {
            path: {
                "get": {
                    "operationId": "getRareDiseaseEvidence",
                    "summary": summary,
                    "parameters": parameters,
                    "responses": {
                        "200": {
                            "description": "Evidence record",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": properties,
                                        "required": required,
                                        "additionalProperties": False,
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
        "components": {
            "securitySchemes": {
                "registryKey": {
                    "type": "apiKey",
                    "in": auth_location,
                    "name": (
                        "X-Rare-Disease-Key"
                        if auth_location == "header"
                        else "registry_key"
                    ),
                }
            }
        },
    }


def _write_spec(path: Path, specification: dict) -> Path:
    path.write_text(json.dumps(specification), encoding="utf-8")
    return path


def _fake_get(url, params, *, timeout, headers):
    assert params == {}
    assert timeout == 20.0
    assert headers == {"X-Rare-Disease-Key": SECRET}
    record_id = url.rsplit("/", 1)[-1]
    payload = copy.deepcopy(RECORDS[record_id])
    return payload, {
        "status_code": 200,
        "content_type": "application/json",
        "response_bytes": len(json.dumps(payload).encode()),
        "redirects": 0,
    }


def _verification_cases() -> list[dict]:
    return [
        {
            "arguments": {"recordId": record_id},
            "expect": {
                "result_type": "object",
                "required_fields": ["record_id", "disease", "genes", "trials"],
                "equals": {"record_id": record_id},
                "required_paths": ["/genes/0", "/trials/0"],
                "equals_paths": {},
            },
        }
        for record_id in RECORDS
    ]


def _publish(tmp_path: Path, monkeypatch) -> tuple[dict, dict, Path]:
    monkeypatch.setenv(ENV_VAR, SECRET)
    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", _fake_get)
    spec_path = _write_spec(tmp_path / "baseline.json", _specification())
    report = inspect_openapi_document(spec_path)
    draft = vsd_promotion.create_openapi_draft(
        report["candidates"][0],
        tool_name=TOOL_NAME,
        description="Retrieve one reviewed protected rare-disease record by identifier.",
        include_parameters=["recordId"],
        credential_env=ENV_VAR,
        workspace=tmp_path / "workspace",
    )
    evidence = vsd_promotion.verify_draft(
        draft["draft_id"],
        _verification_cases(),
        workspace=tmp_path / "workspace",
    )
    vsd_promotion.approve_draft(
        draft["draft_id"],
        reviewed_by="Lifecycle Test Reviewer",
        decision_note="Approved after three representative protected records passed.",
        workspace=tmp_path / "workspace",
    )
    publication = vsd_promotion.publish_draft(
        draft["draft_id"], workspace=tmp_path / "workspace"
    )
    assert evidence["all_cases_passed"] is True
    return draft, publication, spec_path


def test_assessment_distinguishes_metadata_validation_and_breaking_drift(
    tmp_path, monkeypatch
):
    _, publication, baseline_path = _publish(tmp_path, monkeypatch)
    workspace = tmp_path / "workspace"
    unchanged = assess_openapi_drift(TOOL_NAME, baseline_path, workspace=workspace)
    metadata = assess_openapi_drift(
        TOOL_NAME,
        _write_spec(
            tmp_path / "metadata.json",
            _specification(
                api_version="1.0.1", summary="Retrieve reviewed registry evidence"
            ),
        ),
        workspace=workspace,
    )
    response_drift = assess_openapi_drift(
        TOOL_NAME,
        _write_spec(
            tmp_path / "response-drift.json",
            _specification(add_response_requirement=True),
        ),
        workspace=workspace,
    )
    endpoint_drift = assess_openapi_drift(
        TOOL_NAME,
        _write_spec(
            tmp_path / "endpoint-drift.json",
            _specification(server_url="https://rare-registry.example.org/v2"),
        ),
        workspace=workspace,
    )
    blocked_auth = assess_openapi_drift(
        TOOL_NAME,
        _write_spec(
            tmp_path / "query-auth.json",
            _specification(auth_location="query"),
        ),
        workspace=workspace,
    )
    missing_operation = assess_openapi_drift(
        TOOL_NAME,
        _write_spec(
            tmp_path / "missing-operation.json",
            _specification(path="/replacement/{recordId}"),
        ),
        workspace=workspace,
    )
    new_required_parameter = assess_openapi_drift(
        TOOL_NAME,
        _write_spec(
            tmp_path / "new-required.json",
            _specification(add_required_query=True),
        ),
        workspace=workspace,
    )

    assert unchanged["classification"] == "unchanged"
    assert unchanged["suspension_recommended"] is False
    assert metadata["classification"] == "metadata_only"
    assert metadata["changes"] == []
    assert response_drift["classification"] == "review_required"
    assert response_drift["changes"] == ["response_validation"]
    assert endpoint_drift["classification"] == "breaking"
    assert endpoint_drift["changes"] == ["endpoint"]
    assert blocked_auth["classification"] == "breaking"
    assert "authentication_required" in blocked_auth["blockers"]
    assert missing_operation["classification"] == "breaking"
    assert missing_operation["blockers"] == ["operation_missing"]
    assert new_required_parameter["classification"] == "breaking"
    assert new_required_parameter["blockers"][0].startswith("contract_reconstruction:")
    assert all(
        item["publication_sha256"] == publication["publication_sha256"]
        for item in (
            unchanged,
            metadata,
            response_drift,
            endpoint_drift,
            blocked_auth,
            missing_operation,
            new_required_parameter,
        )
    )
    assert len(list((workspace / "assessments" / TOOL_NAME).glob("*.json"))) == 7


def test_lifecycle_suspends_restores_retires_and_is_publication_bound(
    tmp_path, monkeypatch
):
    draft, publication, baseline_path = _publish(tmp_path, monkeypatch)
    workspace = tmp_path / "workspace"
    breaking = assess_openapi_drift(
        TOOL_NAME,
        _write_spec(
            tmp_path / "breaking.json",
            _specification(server_url="https://rare-registry.example.org/v2"),
        ),
        workspace=workspace,
    )
    suspended = set_publication_state(
        TOOL_NAME,
        "suspended",
        changed_by="Lifecycle Test Reviewer",
        reason="Suspended because the reviewed provider endpoint changed versions.",
        assessment_sha256=breaking["assessment_sha256"],
        workspace=workspace,
    )
    assert suspended["revision"] == 1
    assert (
        list_publication_states(TOOL_NAME, workspace=workspace)["tools"][0]["state"]
        == "suspended"
    )

    blocked_universe = ToolUniverse()
    try:
        assert (
            vsd_promotion.load_published_tools(blocked_universe, workspace=workspace)
            == []
        )
        assert TOOL_NAME not in blocked_universe.all_tool_dict
    finally:
        blocked_universe.close()

    with pytest.raises(VSDLifecycleError, match="requires a drift assessment"):
        set_publication_state(
            TOOL_NAME,
            "active",
            changed_by="Lifecycle Test Reviewer",
            reason="An activation without current contract evidence must be rejected.",
            workspace=workspace,
        )
    with pytest.raises(VSDLifecycleError, match="unchanged or metadata-only"):
        set_publication_state(
            TOOL_NAME,
            "active",
            changed_by="Lifecycle Test Reviewer",
            reason="Breaking provider evidence must not reactivate the publication.",
            assessment_sha256=breaking["assessment_sha256"],
            workspace=workspace,
        )
    event_directory = (
        workspace
        / "lifecycle"
        / TOOL_NAME
        / publication["publication_sha256"]
        / "events"
    )
    assert len(list(event_directory.glob("*.json"))) == 1

    repaired = assess_openapi_drift(TOOL_NAME, baseline_path, workspace=workspace)
    activated = set_publication_state(
        TOOL_NAME,
        "active",
        changed_by="Lifecycle Test Reviewer",
        reason="Restored after the original reviewed provider contract was confirmed.",
        assessment_sha256=repaired["assessment_sha256"],
        workspace=workspace,
    )
    assert activated["revision"] == 2
    assert activated["previous_event_sha256"] == suspended["event_sha256"]

    active_universe = ToolUniverse()
    try:
        assert vsd_promotion.load_published_tools(
            active_universe, workspace=workspace
        ) == [TOOL_NAME]
        result = active_universe.run_one_function(
            {"name": TOOL_NAME, "arguments": {"recordId": "RD-ALS"}},
            use_cache=False,
        )
    finally:
        active_universe.close()
    assert result["status"] == "success"
    assert result["data"]["result"]["record_id"] == "RD-ALS"

    retired = set_publication_state(
        TOOL_NAME,
        "retired",
        changed_by="Lifecycle Test Reviewer",
        reason="Retired after the reviewed registry integration was decommissioned.",
        workspace=workspace,
    )
    assert retired["revision"] == 3
    with pytest.raises(VSDLifecycleError, match="Cannot transition"):
        set_publication_state(
            TOOL_NAME,
            "active",
            changed_by="Lifecycle Test Reviewer",
            reason="This terminal publication must not be restored after retirement.",
            workspace=workspace,
        )
    retired_universe = ToolUniverse()
    try:
        assert (
            vsd_promotion.load_published_tools(retired_universe, workspace=workspace)
            == []
        )
    finally:
        retired_universe.close()

    replacement = vsd_promotion.publish_draft(
        draft["draft_id"], workspace=workspace, replace=True
    )
    assert replacement["publication_sha256"] != publication["publication_sha256"]
    replacement_status = list_publication_states(TOOL_NAME, workspace=workspace)[
        "tools"
    ][0]
    assert replacement_status["state"] == "active"
    assert replacement_status["revision"] == 0
    with pytest.raises(VSDLifecycleError, match="does not match this publication"):
        set_publication_state(
            TOOL_NAME,
            "suspended",
            changed_by="Lifecycle Test Reviewer",
            reason="A stale assessment must not control a replacement publication.",
            assessment_sha256=breaking["assessment_sha256"],
            workspace=workspace,
        )


@pytest.mark.parametrize(
    "artifact",
    [
        "assessment",
        "assessment_missing",
        "event",
        "event_missing",
        "state",
        "state_missing",
    ],
)
def test_loader_fails_before_registration_when_lifecycle_evidence_is_tampered(
    tmp_path, monkeypatch, artifact
):
    _, publication, _ = _publish(tmp_path, monkeypatch)
    workspace = tmp_path / "workspace"
    assessment = assess_openapi_drift(
        TOOL_NAME,
        _write_spec(
            tmp_path / "breaking.json",
            _specification(server_url="https://rare-registry.example.org/v2"),
        ),
        workspace=workspace,
    )
    set_publication_state(
        TOOL_NAME,
        "suspended",
        changed_by="Lifecycle Test Reviewer",
        reason="Suspended because the provider request contract changed versions.",
        assessment_sha256=assessment["assessment_sha256"],
        workspace=workspace,
    )
    lifecycle_directory = (
        workspace / "lifecycle" / TOOL_NAME / publication["publication_sha256"]
    )
    if artifact.startswith("assessment"):
        path = next((workspace / "assessments" / TOOL_NAME).glob("*.json"))
    elif artifact.startswith("event"):
        path = lifecycle_directory / "events" / "000001.json"
    else:
        path = lifecycle_directory / "state.json"
    if artifact.endswith("_missing"):
        path.unlink()
    else:
        record = json.loads(path.read_text(encoding="utf-8"))
        if artifact == "assessment":
            record["detail"] = "tampered"
        elif artifact == "event":
            record["reason"] = "tampered"
        else:
            record["revision"] = 0
        path.write_text(json.dumps(record), encoding="utf-8")

    tooluniverse = ToolUniverse()
    try:
        with pytest.raises(VSDLifecycleError):
            vsd_promotion.load_published_tools(tooluniverse, workspace=workspace)
        assert TOOL_NAME not in tooluniverse.all_tool_dict
    finally:
        tooluniverse.close()


def test_drift_assessment_validation_rejects_content_changes(tmp_path, monkeypatch):
    _, _, baseline_path = _publish(tmp_path, monkeypatch)
    assessment = assess_openapi_drift(
        TOOL_NAME, baseline_path, workspace=tmp_path / "workspace"
    )
    validate_drift_assessment(assessment)

    changed = copy.deepcopy(assessment)
    changed["classification"] = "breaking"
    with pytest.raises(VSDLifecycleError, match="modified"):
        validate_drift_assessment(changed)

    extra = copy.deepcopy(assessment)
    extra["unexpected"] = True
    body = {
        key: value
        for key, value in extra.items()
        if key not in {"assessment_id", "assessment_sha256"}
    }
    digest = vsd_promotion._canonical_digest(body)
    extra["assessment_id"] = digest[:16]
    extra["assessment_sha256"] = digest
    with pytest.raises(VSDLifecycleError, match="modified"):
        validate_drift_assessment(extra)


def test_invalid_transitions_and_review_fields_fail_without_writing(
    tmp_path, monkeypatch
):
    _publish(tmp_path, monkeypatch)
    workspace = tmp_path / "workspace"
    with pytest.raises(VSDLifecycleError, match="state must"):
        set_publication_state(
            TOOL_NAME,
            "paused",
            changed_by="Reviewer",
            reason="An unsupported state must not be recorded in lifecycle history.",
            workspace=workspace,
        )
    with pytest.raises(VSDLifecycleError, match="reason"):
        set_publication_state(
            TOOL_NAME,
            "suspended",
            changed_by="Reviewer",
            reason="too short",
            workspace=workspace,
        )
    with pytest.raises(VSDLifecycleError, match="assessment_sha256"):
        set_publication_state(
            TOOL_NAME,
            "suspended",
            changed_by="Reviewer",
            reason="A malformed assessment reference must not be accepted here.",
            assessment_sha256="not-a-digest",
            workspace=workspace,
        )
    status = list_publication_states(TOOL_NAME, workspace=workspace)["tools"][0]
    assert status["state"] == "active"
    assert status["revision"] == 0


def test_legacy_publication_loads_but_cannot_claim_lifecycle_control(
    tmp_path, monkeypatch
):
    _, publication, _ = _publish(tmp_path, monkeypatch)
    workspace = tmp_path / "workspace"
    path = workspace / "approved" / f"{TOOL_NAME}.json"
    legacy = json.loads(path.read_text(encoding="utf-8"))
    legacy.pop("lifecycle")
    body = {key: value for key, value in legacy.items() if key != "publication_sha256"}
    legacy["publication_sha256"] = vsd_promotion._canonical_digest(body)
    path.write_text(json.dumps(legacy), encoding="utf-8")

    status = list_publication_states(TOOL_NAME, workspace=workspace)["tools"][0]
    assert status["state"] == "active"
    assert status["lifecycle_managed"] is False
    tooluniverse = ToolUniverse()
    try:
        assert vsd_promotion.load_published_tools(
            tooluniverse, workspace=workspace
        ) == [TOOL_NAME]
    finally:
        tooluniverse.close()
    with pytest.raises(VSDLifecycleError, match="Legacy publication"):
        set_publication_state(
            TOOL_NAME,
            "suspended",
            changed_by="Legacy Test Reviewer",
            reason="A legacy publication needs republishing before lifecycle control.",
            workspace=workspace,
        )
    assert publication["lifecycle"]["format"].endswith("_v1")


def test_lifecycle_cli_assesses_suspends_and_reports_status(
    tmp_path, monkeypatch, capsys
):
    _publish(tmp_path, monkeypatch)
    workspace = tmp_path / "workspace"
    changed_spec = _write_spec(
        tmp_path / "changed.json",
        _specification(server_url="https://rare-registry.example.org/v2"),
    )
    base = ["--workspace", str(workspace)]

    assert (
        vsd_lifecycle_cli.main(base + ["assess-openapi", TOOL_NAME, str(changed_spec)])
        == 0
    )
    assessment = json.loads(capsys.readouterr().out)
    assert assessment["classification"] == "breaking"

    assert (
        vsd_lifecycle_cli.main(
            base
            + [
                "suspend",
                TOOL_NAME,
                "--changed-by",
                "Lifecycle CLI Reviewer",
                "--reason",
                "Suspended after the provider endpoint changed major versions.",
                "--assessment-sha256",
                assessment["assessment_sha256"],
            ]
        )
        == 0
    )
    event = json.loads(capsys.readouterr().out)
    assert event["state"] == "suspended"

    assert vsd_lifecycle_cli.main(base + ["status", TOOL_NAME]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["execution_allowed"] is False
    assert status["tools"][0]["state"] == "suspended"
