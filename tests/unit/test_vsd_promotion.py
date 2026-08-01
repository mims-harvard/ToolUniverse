from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from tooluniverse import ToolUniverse
from tooluniverse import vsd_dynamic_rest, vsd_promotion

pytestmark = pytest.mark.unit


RETURN_FIELDS = [
    "date_opened",
    "protocol",
    "primary_site",
    "study_phase",
    "title",
    "date_closed",
    "principal_investigator",
]


def _candidate() -> dict:
    endpoint = "https://data.ny.gov/resource/2ig8-yxf8.json"
    return {
        "api_endpoint": endpoint,
        "approval_state": "unreviewed_candidate",
        "candidate_id": hashlib.sha256(endpoint.encode()).hexdigest()[:16],
        "catalog_domain": "data.ny.gov",
        "dataset_id": "2ig8-yxf8",
        "execution_allowed": False,
        "metadata_trust": "untrusted_catalog_metadata",
        "updated_at": "2026-04-14T21:08:58.000Z",
        "fields": [
            {
                "field": name,
                "json_type": "string",
                "label": name.replace("_", " ").title(),
                "description": f"Reviewed provider field {name}.",
            }
            for name in RETURN_FIELDS
        ],
    }


def _cases(field: str, values: tuple[str, str, str]) -> list[dict]:
    return [
        {
            "arguments": {field: value},
            "expect": {
                "min_items": 1,
                "max_items": 25,
                "required_fields": ["protocol", "title", field],
                "equals": {field: value},
            },
        }
        for value in values
    ]


def _fake_socrata_get(url, params, *, timeout):
    assert url == "https://data.ny.gov/resource/2ig8-yxf8.json"
    assert params["$limit"] == 25
    assert params["$select"] == ",".join(RETURN_FIELDS)
    assert timeout == 20.0
    filter_field = next(key for key in params if not key.startswith("$"))
    value = params[filter_field]
    rows = [
        {
            "date_opened": "2024-01-01T00:00:00.000",
            "protocol": f"RPCI-{value[:3].upper()}-{index}",
            "primary_site": value if filter_field == "primary_site" else "Breast",
            "study_phase": value if filter_field == "study_phase" else "II",
            "title": f"Reviewed trial {index} for {value}",
            "principal_investigator": "Example Investigator",
        }
        for index in range(1, 3)
    ]
    encoded = json.dumps(rows).encode()
    return rows, {
        "status_code": 200,
        "content_type": "application/json; charset=utf-8",
        "response_bytes": len(encoded),
        "redirects": 0,
    }


def _draft(workspace, *, tool_name="GeneratedCancerTrialsBySite"):
    return vsd_promotion.create_draft(
        _candidate(),
        tool_name=tool_name,
        description=(
            "Query a reviewed New York State cancer-trial dataset by primary site."
        ),
        filter_fields=["primary_site"],
        return_fields=RETURN_FIELDS,
        workspace=workspace,
    )


def test_generator_builds_narrow_required_filter_contract():
    config = vsd_promotion.build_socrata_tool_config(
        _candidate(),
        tool_name="GeneratedCancerTrialsBySite",
        description="Query reviewed active cancer trials by their primary cancer site.",
        filter_fields=["primary_site"],
        return_fields=RETURN_FIELDS,
    )

    assert config["parameter"]["required"] == ["primary_site"]
    assert config["parameter"]["additionalProperties"] is False
    assert config["vsd_operation"]["method"] == "GET"
    assert config["vsd_operation"]["auth"] == {"type": "none"}
    assert config["vsd_operation"]["fixed_query"]["$limit"] == 25
    assert config["vsd_operation"]["query_arguments"] == {
        "primary_site": "primary_site"
    }


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda c: c.update(execution_allowed=True), "discovery boundary"),
        (
            lambda c: c.update(
                api_endpoint="http://data.ny.gov/resource/2ig8-yxf8.json"
            ),
            "catalog identity",
        ),
        (lambda c: c.update(candidate_id="0" * 16), "candidate ID"),
    ],
)
def test_generator_rejects_tampered_discovery_candidates(mutation, message):
    candidate = _candidate()
    mutation(candidate)
    with pytest.raises(vsd_promotion.VSDPromotionError, match=message):
        vsd_promotion.build_socrata_tool_config(
            candidate,
            tool_name="GeneratedCancerTrialsBySite",
            description="Query reviewed active cancer trials by their primary cancer site.",
            filter_fields=["primary_site"],
            return_fields=RETURN_FIELDS,
        )


def test_generator_rejects_unknown_provider_fields():
    with pytest.raises(vsd_promotion.VSDPromotionError, match="Unknown"):
        vsd_promotion.build_socrata_tool_config(
            _candidate(),
            tool_name="GeneratedCancerTrialsBySite",
            description="Query reviewed active cancer trials by their primary cancer site.",
            filter_fields=["invented_field"],
            return_fields=RETURN_FIELDS,
        )


def test_generator_uses_socrata_number_wire_format_and_rejects_object_filters():
    candidate = _candidate()
    candidate["fields"].extend(
        [
            {
                "field": "enrollment",
                "json_type": "number",
                "provider_type": "Number",
            },
            {"field": "location", "json_type": "object", "provider_type": "Point"},
        ]
    )
    config = vsd_promotion.build_socrata_tool_config(
        candidate,
        tool_name="GeneratedTrialsByEnrollment",
        description="Query reviewed cancer trials by exact enrollment value.",
        filter_fields=["enrollment"],
        return_fields=["protocol", "enrollment", "location"],
    )
    enrollment = config["parameter"]["properties"]["enrollment"]
    assert enrollment["type"] == "string"
    assert enrollment["pattern"].startswith("^-")
    with pytest.raises(vsd_promotion.VSDPromotionError, match="Object-valued"):
        vsd_promotion.build_socrata_tool_config(
            candidate,
            tool_name="GeneratedTrialsByLocation",
            description="Query reviewed cancer trials by exact provider location.",
            filter_fields=["location"],
            return_fields=["protocol", "location"],
        )


def test_verification_requires_three_cases_and_writes_no_failed_evidence(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", _fake_socrata_get)
    draft = _draft(tmp_path)
    with pytest.raises(vsd_promotion.VSDPromotionError, match="3-20"):
        vsd_promotion.verify_draft(
            draft["draft_id"],
            _cases("primary_site", ("Breast", "Prostate", "Lung"))[:2],
            workspace=tmp_path,
        )
    assert not (tmp_path / "evidence" / f"{draft['draft_id']}.json").exists()

    failing = _cases("primary_site", ("Breast", "Prostate", "Lung"))
    failing[1]["expect"]["equals"]["primary_site"] = "Ovary"
    with pytest.raises(vsd_promotion.VSDPromotionError, match="equality"):
        vsd_promotion.verify_draft(draft["draft_id"], failing, workspace=tmp_path)
    assert not (tmp_path / "evidence" / f"{draft['draft_id']}.json").exists()


def test_cannot_publish_without_matching_verification_and_approval(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", _fake_socrata_get)
    draft = _draft(tmp_path)
    with pytest.raises(vsd_promotion.VSDPromotionError, match="does not exist"):
        vsd_promotion.publish_draft(draft["draft_id"], workspace=tmp_path)

    vsd_promotion.verify_draft(
        draft["draft_id"],
        _cases("primary_site", ("Breast", "Prostate", "Lung")),
        workspace=tmp_path,
    )
    with pytest.raises(vsd_promotion.VSDPromotionError, match="does not exist"):
        vsd_promotion.publish_draft(draft["draft_id"], workspace=tmp_path)


@pytest.mark.parametrize("artifact", ["draft", "evidence", "approval", "publication"])
def test_hash_chain_detects_artifact_tampering(tmp_path, monkeypatch, artifact):
    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", _fake_socrata_get)
    draft = _draft(tmp_path)
    evidence = vsd_promotion.verify_draft(
        draft["draft_id"],
        _cases("primary_site", ("Breast", "Prostate", "Lung")),
        workspace=tmp_path,
    )
    approval = vsd_promotion.approve_draft(
        draft["draft_id"],
        reviewed_by="Test Reviewer",
        decision_note="Approved after all three bounded integration cases passed.",
        workspace=tmp_path,
    )
    publication = vsd_promotion.publish_draft(draft["draft_id"], workspace=tmp_path)
    paths = {
        "draft": tmp_path / "drafts" / f"{draft['draft_id']}.json",
        "evidence": tmp_path / "evidence" / f"{draft['draft_id']}.json",
        "approval": tmp_path / "approvals" / f"{draft['draft_id']}.json",
        "publication": tmp_path / "approved" / f"{publication['tool_name']}.json",
    }
    record = json.loads(paths[artifact].read_text())
    record["review_tampered"] = True
    paths[artifact].write_text(json.dumps(record), encoding="utf-8")

    if artifact == "draft":

        def action():
            return vsd_promotion.verify_draft(
                draft["draft_id"],
                _cases("primary_site", ("Breast", "Prostate", "Lung")),
                workspace=tmp_path,
            )

    elif artifact == "evidence":

        def action():
            return vsd_promotion.approve_draft(
                draft["draft_id"],
                reviewed_by="Test Reviewer",
                decision_note=(
                    "Approved after all three bounded integration cases passed."
                ),
                workspace=tmp_path,
            )

    elif artifact == "approval":

        def action():
            return vsd_promotion.publish_draft(
                draft["draft_id"], workspace=tmp_path, replace=True
            )

    else:
        tooluniverse = ToolUniverse()

        def action():
            try:
                return vsd_promotion.load_published_tools(
                    tooluniverse, workspace=tmp_path
                )
            finally:
                tooluniverse.close()

    with pytest.raises(vsd_promotion.VSDPromotionError, match="digest"):
        action()
    assert evidence["all_cases_passed"] is True
    assert approval["decision"] == "approved"


def test_two_generated_tools_complete_full_promotion_and_execution(
    tmp_path, monkeypatch
):
    requests = []

    def fake_get(url, params, *, timeout):
        requests.append(deepcopy(params))
        return _fake_socrata_get(url, params, timeout=timeout)

    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", fake_get)
    specs = (
        (
            "GeneratedCancerTrialsBySite",
            "primary_site",
            ("Brain and Nervous System", "Breast", "Prostate"),
        ),
        (
            "GeneratedCancerTrialsByPhase",
            "study_phase",
            ("II", "III", "IV"),
        ),
    )
    published = []
    for name, field, values in specs:
        draft = vsd_promotion.create_draft(
            _candidate(),
            tool_name=name,
            description=f"Query the reviewed cancer-trial dataset by {field}.",
            filter_fields=[field],
            return_fields=RETURN_FIELDS,
            workspace=tmp_path,
        )
        evidence = vsd_promotion.verify_draft(
            draft["draft_id"], _cases(field, values), workspace=tmp_path
        )
        approval = vsd_promotion.approve_draft(
            draft["draft_id"],
            reviewed_by="Test Reviewer",
            decision_note="Approved after contract review and three live-equivalent cases.",
            workspace=tmp_path,
        )
        record = vsd_promotion.publish_draft(draft["draft_id"], workspace=tmp_path)
        assert evidence["case_count"] == 3
        assert approval["operation_sha256"] == draft["operation_sha256"]
        published.append(record)

    tooluniverse = ToolUniverse()
    try:
        assert vsd_promotion.load_published_tools(
            tooluniverse, workspace=tmp_path
        ) == sorted(record["tool_name"] for record in published)
        by_site = tooluniverse.run_one_function(
            {
                "name": "GeneratedCancerTrialsBySite",
                "arguments": {"primary_site": "Breast"},
            },
            use_cache=False,
        )
        by_phase = tooluniverse.run_one_function(
            {
                "name": "GeneratedCancerTrialsByPhase",
                "arguments": {"study_phase": "III"},
            },
            use_cache=False,
        )
    finally:
        tooluniverse.close()

    assert by_site["data"]["result"][0]["primary_site"] == "Breast"
    assert by_phase["data"]["result"][0]["study_phase"] == "III"
    assert len(requests) == 8
    assert vsd_promotion.list_promotion_state(workspace=tmp_path) == {
        "drafts": sorted(record["draft_id"] for record in published),
        "evidence": sorted(record["draft_id"] for record in published),
        "approvals": sorted(record["draft_id"] for record in published),
        "approved": sorted(record["tool_name"] for record in published),
    }


def test_loader_refuses_to_replace_an_existing_tool(tmp_path, monkeypatch):
    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", _fake_socrata_get)
    draft = _draft(tmp_path)
    vsd_promotion.verify_draft(
        draft["draft_id"],
        _cases("primary_site", ("Breast", "Prostate", "Lung")),
        workspace=tmp_path,
    )
    vsd_promotion.approve_draft(
        draft["draft_id"],
        reviewed_by="Test Reviewer",
        decision_note="Approved after all three bounded integration cases passed.",
        workspace=tmp_path,
    )
    vsd_promotion.publish_draft(draft["draft_id"], workspace=tmp_path)

    tooluniverse = ToolUniverse()
    try:
        vsd_promotion.register_reviewed_rest_tool(tooluniverse, draft["config"])
        with pytest.raises(vsd_promotion.VSDPromotionError, match="replace"):
            vsd_promotion.load_published_tools(tooluniverse, workspace=tmp_path)
    finally:
        tooluniverse.close()


def test_loader_validates_entire_set_before_registering_any_tool(tmp_path, monkeypatch):
    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", _fake_socrata_get)
    for name in ("GeneratedCancerTrialsAlpha", "GeneratedCancerTrialsZulu"):
        draft = _draft(tmp_path, tool_name=name)
        vsd_promotion.verify_draft(
            draft["draft_id"],
            _cases("primary_site", ("Breast", "Prostate", "Lung")),
            workspace=tmp_path,
        )
        vsd_promotion.approve_draft(
            draft["draft_id"],
            reviewed_by="Test Reviewer",
            decision_note="Approved after all three bounded integration cases passed.",
            workspace=tmp_path,
        )
        vsd_promotion.publish_draft(draft["draft_id"], workspace=tmp_path)

    bad_path = tmp_path / "approved" / "GeneratedCancerTrialsZulu.json"
    bad_record = json.loads(bad_path.read_text(encoding="utf-8"))
    bad_record["publication_sha256"] = "0" * 64
    bad_path.write_text(json.dumps(bad_record), encoding="utf-8")

    tooluniverse = ToolUniverse()
    try:
        with pytest.raises(vsd_promotion.VSDPromotionError, match="digest"):
            vsd_promotion.load_published_tools(tooluniverse, workspace=tmp_path)
        assert "GeneratedCancerTrialsAlpha" not in tooluniverse.all_tool_dict
        assert "GeneratedCancerTrialsZulu" not in tooluniverse.all_tool_dict
    finally:
        tooluniverse.close()
