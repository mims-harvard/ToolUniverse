from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import tooluniverse.vsd_catalog_providers as catalogs
from tooluniverse import ToolUniverse, vsd_discovery, vsd_promotion
from tooluniverse import vsd_reviewed_runtime as runtime
from tooluniverse.vsd_catalog_providers import (
    VSDCatalogProviderError,
    normalize_provider_payload,
    select_catalog_candidate,
    validate_catalog_candidate,
)
from tooluniverse.vsd_coverage import _operation_identity
from tooluniverse.vsd_promotion_cli import _execute, build_parser

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).parents[1] / "fixtures" / "vsd_catalogs" / "datagov.json"
GA4GH_FIXTURE = (
    Path(__file__).parents[1] / "fixtures" / "vsd_catalogs" / "ga4gh_registry.json"
)
QUERY = "ALS rare disease longitudinal cohort outcomes specialist access"


def _candidate() -> dict:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    candidates, _ = normalize_provider_payload("datagov", QUERY, payload)
    return next(item for item in candidates if item["response_format"] == "csv")


def _ga4gh_candidate() -> dict:
    payload = json.loads(GA4GH_FIXTURE.read_text(encoding="utf-8"))
    candidates, _ = normalize_provider_payload(
        "ga4gh_registry",
        "genomic research data repository service",
        payload,
    )
    return next(
        item
        for item in candidates
        if item["service_binding"]["registry_service_id"] == "bio.terra.data"
    )


def _config(endpoint: str | None = None, response_format: str = "csv") -> dict:
    return {
        "name": "VSDReviewedCareAccessSnapshot",
        "type": "VSDReviewedOperationTool",
        "description": "Return the exact reviewed specialist-access resource snapshot.",
        "category": "special_tools",
        "cacheable": False,
        "parameter": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "return_schema": {"type": "object"},
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "http",
            "protocol": "rest",
            "endpoint": endpoint or _candidate()["api_endpoint"],
            "timeout_seconds": 20,
            "auth": {"type": "none"},
            "request": {
                "method": "GET",
                "path_arguments": {},
                "query_arguments": {},
                "fixed_query": {},
                "fixed_headers": {},
                "body": {"mode": "none", "arguments": {}, "fixed": {}},
            },
            "response": {
                "format": response_format,
                "max_bytes": 100_000,
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "county": {"type": "string"},
                            "wait_days": {"type": "string"},
                        },
                        "required": ["county", "wait_days"],
                        "additionalProperties": False,
                    },
                },
                "root_pointer": "",
                "delimiter": ",",
            },
            "pagination": {"type": "none"},
        },
    }


def _cases() -> list[dict]:
    return [
        {
            "arguments": {},
            "expect": {
                "result_type": "array",
                "min_items": 2,
                "max_items": 2,
                "required_fields": ["county", "wait_days"],
            },
        }
        for _ in range(3)
    ]


def test_catalog_candidate_is_tamper_evident_and_selectable():
    candidate = _candidate()

    assert validate_catalog_candidate(candidate) == candidate
    assert select_catalog_candidate({"candidates": [candidate]}) == candidate

    tampered = copy.deepcopy(candidate)
    tampered["name"] = "Substituted resource"
    with pytest.raises(VSDCatalogProviderError, match="digest"):
        validate_catalog_candidate(tampered)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda item: item.update(interface_type="openapi"), "kind and interface"),
        (
            lambda item: item["catalog_sources"][0].update(provider="apis_guru"),
            "sources",
        ),
    ],
)
def test_catalog_candidate_rejects_rehashed_invalid_contracts(mutation, message):
    candidate = _candidate()
    mutation(candidate)
    candidate["candidate_sha256"] = catalogs._candidate_digest(candidate)

    with pytest.raises(VSDCatalogProviderError, match=message):
        validate_catalog_candidate(candidate)


def test_catalog_resource_completes_hash_bound_promotion_and_fresh_load(
    monkeypatch, tmp_path: Path
):
    rows = [
        {"county": "Alpha", "wait_days": "21"},
        {"county": "Beta", "wait_days": "34"},
    ]

    def fake_exchange(**kwargs):
        assert kwargs["method"] == "GET"
        assert kwargs["url"] == _candidate()["api_endpoint"]
        assert kwargs["params"] == {}
        raw = b"county,wait_days\nAlpha,21\nBeta,34\n"
        return raw, {
            "url": kwargs["url"],
            "status_code": 200,
            "content_type": "text/csv",
            "response_bytes": len(raw),
            "headers": {},
            "peer_ip": "93.184.216.34",
            "redirects": 0,
        }

    monkeypatch.setattr(runtime, "_http_exchange", fake_exchange)
    workspace = tmp_path / "promotion"
    draft = vsd_promotion.create_catalog_resource_draft(
        _candidate(),
        _config(),
        review_note=(
            "Reviewed the exact catalog identity, HTTPS endpoint, CSV schema, and "
            "bounded input-free request."
        ),
        workspace=workspace,
    )
    evidence = vsd_promotion.verify_draft(
        draft["draft_id"], _cases(), workspace=workspace
    )
    approval = vsd_promotion.approve_draft(
        draft["draft_id"],
        reviewed_by="Catalog Resource Reviewer",
        decision_note=(
            "Approved after three bounded resource checks returned the reviewed fields."
        ),
        workspace=workspace,
    )
    publication = vsd_promotion.publish_draft(draft["draft_id"], workspace=workspace)

    tooluniverse = ToolUniverse()
    try:
        assert _config()["name"] not in tooluniverse.all_tool_dict
        assert vsd_promotion.load_published_tools(
            tooluniverse, workspace=workspace
        ) == [_config()["name"]]
        result = tooluniverse.run_one_function(
            {"name": _config()["name"], "arguments": {}}, use_cache=False
        )
    finally:
        tooluniverse.close()

    assert result["data"]["result"] == rows
    assert evidence["case_count"] == 3
    assert approval["verification_sha256"] == evidence["verification_sha256"]
    assert publication["config"]["vsd_promotion"]["source_type"] == ("catalog_resource")
    assert _operation_identity(publication["config"]) == (
        "GET",
        "health.example.gov",
        "/rare-disease/care-access.csv",
    )
    binding = publication["config"]["vsd_promotion"]["catalog_binding"]
    assert binding["candidate_sha256"] == _candidate()["candidate_sha256"]


def test_ga4gh_service_info_completes_strict_registry_bound_promotion(
    monkeypatch, tmp_path: Path
):
    candidate = _ga4gh_candidate()
    payload = {
        "id": "anvil.drs",
        "name": "NHGRI AnVIL",
        "type": {"group": "ORG.GA4GH", "artifact": "DRS", "version": "1.3.0"},
        "organization": {"name": "NHGRI AnVIL"},
        "version": "2.323.0",
    }

    def fake_exchange(**kwargs):
        assert kwargs["method"] == "GET"
        assert kwargs["url"] == candidate["api_endpoint"]
        assert kwargs["params"] == {}
        raw = json.dumps(payload).encode()
        return raw, {
            "url": kwargs["url"],
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": len(raw),
            "headers": {},
            "peer_ip": "93.184.216.34",
            "redirects": 0,
        }

    monkeypatch.setattr(runtime, "_http_exchange", fake_exchange)
    workspace = tmp_path / "ga4gh-promotion"
    draft = vsd_promotion.create_ga4gh_service_info_draft(
        candidate,
        tool_name="ReviewedAnvilServiceInfo",
        description="Return the reviewed GA4GH service metadata for this registry entry.",
        review_note=(
            "Reviewed the registry identity, standard Service Info path, and expected "
            "service type before verification."
        ),
        workspace=workspace,
    )
    evidence = vsd_promotion.verify_draft(
        draft["draft_id"],
        vsd_promotion.ga4gh_service_info_verification_cases(candidate),
        workspace=workspace,
    )
    approval = vsd_promotion.approve_draft(
        draft["draft_id"],
        reviewed_by="Standards Registry Reviewer",
        decision_note=(
            "Approved after three executions matched the registered name and "
            "GA4GH service type."
        ),
        workspace=workspace,
    )
    publication = vsd_promotion.publish_draft(draft["draft_id"], workspace=workspace)

    assert evidence["case_count"] == 3
    assert approval["verification_sha256"] == evidence["verification_sha256"]
    binding = publication["config"]["vsd_promotion"]["catalog_binding"]
    assert binding["service_binding"] == candidate["service_binding"]
    assert publication["config"]["vsd_reviewed_operation"]["endpoint"] == (
        "https://data.terra.bio/service-info"
    )


def test_ga4gh_service_info_approval_requires_registered_contract_assertions(
    monkeypatch, tmp_path: Path
):
    candidate = _ga4gh_candidate()
    payload = {
        "id": "anvil.drs",
        "name": "NHGRI AnVIL",
        "type": {"group": "org.ga4gh", "artifact": "drs", "version": "1.3.0"},
        "organization": {"name": "NHGRI AnVIL"},
        "version": "2.323.0",
    }

    def fake_exchange(**kwargs):
        raw = json.dumps(payload).encode()
        return raw, {
            "url": kwargs["url"],
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": len(raw),
            "headers": {},
            "peer_ip": "93.184.216.34",
            "redirects": 0,
        }

    monkeypatch.setattr(runtime, "_http_exchange", fake_exchange)
    workspace = tmp_path / "weak-ga4gh-evidence"
    draft = vsd_promotion.create_ga4gh_service_info_draft(
        candidate,
        tool_name="ReviewedAnvilServiceInfo",
        description="Return the reviewed GA4GH service metadata for this registry entry.",
        review_note="Reviewed the exact standard endpoint before running weak evidence.",
        workspace=workspace,
    )
    weak_cases = [
        {
            "arguments": {},
            "expect": {
                "result_type": "object",
                "required_fields": ["id", "name", "type"],
            },
        }
        for _ in range(3)
    ]
    vsd_promotion.verify_draft(draft["draft_id"], weak_cases, workspace=workspace)

    with pytest.raises(vsd_promotion.VSDPromotionError, match="registered contract"):
        vsd_promotion.approve_draft(
            draft["draft_id"],
            reviewed_by="Standards Registry Reviewer",
            decision_note="This approval must fail because type assertions were omitted.",
            workspace=workspace,
        )


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (_config(endpoint="https://other.example.org/resource.csv"), "exactly match"),
        (_config(response_format="json"), "response format"),
    ],
)
def test_catalog_resource_refuses_endpoint_or_format_substitution(
    config, message, tmp_path: Path
):
    with pytest.raises(vsd_promotion.VSDPromotionError, match=message):
        vsd_promotion.create_catalog_resource_draft(
            _candidate(),
            config,
            review_note="Reviewed candidate must remain exactly bound to its resource.",
            workspace=tmp_path,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda config: config["parameter"]["properties"].update(
            query={"type": "string"}
        ),
        lambda config: config["vsd_reviewed_operation"].update(
            auth={"type": "header", "name": "Authorization", "env": "TOKEN"}
        ),
        lambda config: config["vsd_reviewed_operation"]["request"].update(
            method="POST"
        ),
        lambda config: config["vsd_reviewed_operation"]["request"][
            "fixed_headers"
        ].update(Accept="text/csv"),
        lambda config: config["vsd_reviewed_operation"].update(
            pagination={"type": "page", "argument": "page"}
        ),
    ],
)
def test_catalog_resource_refuses_an_active_or_variable_request(
    mutation, tmp_path: Path
):
    config = _config()
    mutation(config)

    with pytest.raises(vsd_promotion.VSDPromotionError):
        vsd_promotion.create_catalog_resource_draft(
            _candidate(),
            config,
            review_note="Reviewed resource requests must remain anonymous and input-free.",
            workspace=tmp_path,
        )


def test_catalog_resource_preserves_an_exact_fixed_query(tmp_path: Path):
    candidate = _candidate()
    base_endpoint = candidate["api_endpoint"]
    candidate["api_endpoint"] = f"{base_endpoint}?download=csv"
    candidate["candidate_id"] = hashlib.sha256(
        candidate["api_endpoint"].encode("utf-8")
    ).hexdigest()[:16]
    candidate["candidate_sha256"] = catalogs._candidate_digest(candidate)
    config = _config(endpoint=base_endpoint)
    config["vsd_reviewed_operation"]["request"]["fixed_query"] = {"download": "csv"}

    draft = vsd_promotion.create_catalog_resource_draft(
        candidate,
        config,
        review_note="Reviewed and preserved the exact catalog resource query binding.",
        workspace=tmp_path,
    )

    binding = draft["config"]["vsd_promotion"]["catalog_binding"]
    assert binding["identity"] == candidate["api_endpoint"]
    assert draft["config"]["vsd_reviewed_operation"]["request"]["fixed_query"] == {
        "download": "csv"
    }


def test_catalog_resource_rejects_ambiguous_duplicate_query_names(tmp_path: Path):
    candidate = _candidate()
    base_endpoint = candidate["api_endpoint"]
    candidate["api_endpoint"] = f"{base_endpoint}?format=csv&format=json"
    candidate["candidate_id"] = hashlib.sha256(
        candidate["api_endpoint"].encode("utf-8")
    ).hexdigest()[:16]
    candidate["candidate_sha256"] = catalogs._candidate_digest(candidate)

    with pytest.raises(vsd_promotion.VSDPromotionError, match="must be unique"):
        vsd_promotion.create_catalog_resource_draft(
            candidate,
            _config(endpoint=base_endpoint),
            review_note="Reviewed query ambiguity must be rejected before draft creation.",
            workspace=tmp_path,
        )


def test_catalog_resource_cli_selects_candidate_and_creates_draft(tmp_path: Path):
    candidate_file = tmp_path / "discovery.json"
    candidate_file.write_text(
        json.dumps({"candidates": [_candidate()]}), encoding="utf-8"
    )
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(_config()), encoding="utf-8")

    result = _execute(
        build_parser().parse_args(
            [
                "--workspace",
                str(tmp_path / "workspace"),
                "draft-catalog-resource",
                str(candidate_file),
                str(config_file),
                "--review-note",
                "Reviewed exact fixed resource endpoint and bounded CSV response contract.",
            ]
        )
    )

    assert result["config"]["vsd_promotion"]["source_type"] == "catalog_resource"
