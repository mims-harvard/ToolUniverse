from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import tooluniverse.vsd_catalog_providers as catalogs
import tooluniverse.vsd_dynamic_rest as vsd_dynamic_rest
from tooluniverse import ToolUniverse, vsd_discovery, vsd_promotion, vsd_tool
from tooluniverse.vsd_openapi import inspect_openapi_document
from tooluniverse.vsd_promotion_cli import _execute, build_parser

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parents[1] / "fixtures" / "vsd_catalogs"
QUERY = "ALS rare disease longitudinal cohort outcomes specialist access"


def _payload(provider: str) -> dict:
    name = {
        "socrata": "socrata.json",
        "datagov": "datagov.json",
        "data_europa": "data_europa.json",
        "ckan_data_gov_uk": "ckan.json",
        "apis_guru": "apis_guru.json",
        "smartapi": "smartapi.json",
        "ga4gh_registry": "ga4gh_registry.json",
    }[provider]
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _request(url: str, payload: object) -> dict:
    encoded = json.dumps(payload, sort_keys=True).encode()
    return {
        "url": url,
        "status_code": 200,
        "content_type": "application/json",
        "response_bytes": len(encoded),
        "peer_ip": "93.184.216.34",
        "redirects": 0,
    }


@pytest.mark.parametrize(
    ("provider", "expected_formats", "expected_kind"),
    [
        ("socrata", {"json"}, "data_endpoint"),
        ("datagov", {"json", "csv"}, "data_endpoint"),
        ("data_europa", {"xml"}, "data_endpoint"),
        ("ckan_data_gov_uk", {"json"}, "data_endpoint"),
        ("apis_guru", {"json"}, "openapi_specification"),
    ],
)
def test_each_provider_normalizes_only_inert_machine_readable_candidates(
    provider, expected_formats, expected_kind
):
    candidates, count = catalogs.normalize_provider_payload(
        provider,
        QUERY,
        _payload(provider),
        socrata_normalizer=vsd_discovery.discover_api_candidates,
    )

    assert count == 2
    assert candidates
    assert {item["response_format"] for item in candidates} == expected_formats
    assert all(item["candidate_kind"] == expected_kind for item in candidates)
    assert all(item["execution_allowed"] is False for item in candidates)
    assert all(item["approval_state"] == "unreviewed_candidate" for item in candidates)
    assert all(
        item["metadata_trust"] == "untrusted_catalog_metadata" for item in candidates
    )
    assert all(item["candidate_id"] for item in candidates)
    assert all(item["score"]["matched_query_terms"] >= 2 for item in candidates)


def test_multicatalog_search_deduplicates_and_isolates_one_provider_failure(
    monkeypatch,
):
    calls = []
    endpoint_to_provider = {value: key for key, value in catalogs._ENDPOINTS.items()}

    def fake_get(url, params=None, **kwargs):
        provider = endpoint_to_provider[url]
        calls.append((provider, params, kwargs))
        if provider == "data_europa":
            raise vsd_tool.VSDPolicyError("temporary catalog outage")
        payload = _payload(provider)
        return payload, _request(url, payload)

    monkeypatch.setenv("TOOLUNIVERSE_DATAGOV_API_KEY", "fixture-key-must-not-leak")
    result = catalogs.discover_multi_catalog_candidates(
        QUERY,
        providers=list(catalogs.PROVIDER_ORDER),
        limit=20,
        fetch_json=fake_get,
        socrata_normalizer=vsd_discovery.discover_api_candidates,
        exclude_registered=False,
    )

    assert result["successful_provider_count"] == 6
    assert result["failed_provider_count"] == 1
    assert result["cross_catalog_duplicate_count"] >= 2
    assert (
        len({item["candidate_id"] for item in result["candidates"]})
        == result["candidate_count"]
    )
    shared = next(
        item
        for item in result["candidates"]
        if item["api_endpoint"] == "https://data.example.gov/resource/abcd-1234.json"
    )
    assert {item["provider"] for item in shared["catalog_sources"]} == {
        "datagov",
        "socrata",
    }
    encoded = json.dumps(result, sort_keys=True)
    assert "fixture-key-must-not-leak" not in encoded
    datagov = next(
        item for item in result["provider_results"] if item["provider_id"] == "datagov"
    )
    assert datagov["provenance"]["credential_ref"] == ("TOOLUNIVERSE_DATAGOV_API_KEY")
    api_call = next(item for item in calls if item[0] == "apis_guru")
    assert api_call[2]["max_response_bytes"] == 10_000_000
    smartapi_call = next(item for item in calls if item[0] == "smartapi")
    assert smartapi_call[1]["raw"] == 1
    assert smartapi_call[2]["max_response_bytes"] == 10_000_000
    europe_call = next(item for item in calls if item[0] == "data_europa")
    assert europe_call[1]["limit"] == 10
    assert catalogs._ENDPOINTS["ckan_data_gov_uk"].startswith(
        "https://ckan.publishing.service.gov.uk/"
    )


def test_smartapi_normalizes_content_addressed_openapi_candidates():
    candidates, count = catalogs.normalize_provider_payload(
        "smartapi", QUERY, _payload("smartapi")
    )

    assert count == 2
    assert len(candidates) == 2
    assert all(item["candidate_kind"] == "openapi_specification" for item in candidates)
    assert all(item["interface_type"] == "openapi" for item in candidates)
    assert all(item["api_endpoint"].startswith("https://") for item in candidates)
    assert all(
        item["specification_url"].startswith("https://smart-api.info/api/metadata/")
        for item in candidates
    )
    assert all(item["candidate_sha256"] for item in candidates)
    assert all(item["execution_allowed"] is False for item in candidates)


def test_registry_dedup_defers_smartapi_service_roots_to_contract_inspection():
    payload = _payload("smartapi")

    def fake_get(url, params=None, **kwargs):
        del params, kwargs
        return payload, _request(url, payload)

    tooluniverse = ToolUniverse()
    result = catalogs.discover_multi_catalog_candidates(
        QUERY,
        providers=["smartapi"],
        limit=5,
        fetch_json=fake_get,
        socrata_normalizer=vsd_discovery.discover_api_candidates,
        tooluniverse=tooluniverse,
        exclude_registered=True,
    )

    assert result["candidate_count"] == 2
    assert result["registered_duplicate_count"] == 0
    assert all(
        item["registry_coverage"]["classification"] == "not_assessed"
        for item in result["candidates"]
    )


def test_ga4gh_registry_keeps_services_inert_until_a_contract_is_reviewed():
    candidates, count = catalogs.normalize_provider_payload(
        "ga4gh_registry",
        "genomic research data repository service",
        _payload("ga4gh_registry"),
    )

    assert count == 2
    assert len(candidates) == 2
    assert all(item["candidate_kind"] == "service_endpoint" for item in candidates)
    assert all(item["interface_type"] == "ga4gh" for item in candidates)
    assert all(not item["specification_url"] for item in candidates)
    assert all(item["execution_allowed"] is False for item in candidates)
    for candidate in candidates:
        assert catalogs.validate_catalog_candidate(candidate) == candidate


def test_smartapi_candidate_binds_to_the_exact_inspected_service(tmp_path):
    catalog_candidate = catalogs.normalize_provider_payload(
        "smartapi", QUERY, _payload("smartapi")
    )[0][0]
    document = {
        "openapi": "3.0.3",
        "info": {"title": "Rare Source", "version": "1.0.0"},
        "servers": [{"url": "https://biothings.transltr.io/rare_source"}],
        "paths": {
            "/query": {
                "get": {
                    "operationId": "queryRareSource",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "total": {"type": "integer"},
                                            "hits": {
                                                "type": "array",
                                                "items": {"type": "object"},
                                            },
                                        },
                                        "required": ["total", "hits"],
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }
    source = tmp_path / "rare-source.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    operation = inspect_openapi_document(source)["candidates"][0]

    draft = vsd_promotion.create_catalog_openapi_draft(
        catalog_candidate,
        operation,
        tool_name="GeneratedRareSourceQuery",
        description="Query reviewed rare-disease annotations by identifier.",
        review_note="Reviewed the exact registry specification and service endpoint.",
        workspace=tmp_path / "workspace",
    )

    promotion = draft["config"]["vsd_promotion"]
    assert promotion["source_type"] == "catalog_openapi"
    assert promotion["catalog_binding"]["candidate_sha256"] == (
        catalog_candidate["candidate_sha256"]
    )
    assert promotion["catalog_binding"]["source_document_sha256"] == (
        operation["source_document_sha256"]
    )
    assert promotion["catalog_binding"]["binding_sha256"]

    mismatched = copy.deepcopy(catalog_candidate)
    mismatched["api_endpoint"] = "https://different.example.org/api"
    mismatched["candidate_sha256"] = catalogs._candidate_digest(mismatched)
    with pytest.raises(vsd_promotion.VSDPromotionError, match="does not match"):
        vsd_promotion.create_catalog_openapi_draft(
            mismatched,
            operation,
            tool_name="GeneratedMismatchedSourceQuery",
            description="Query a mismatched reviewed rare-disease service.",
            review_note="This intentionally mismatched endpoint must fail validation.",
            workspace=tmp_path / "mismatch",
        )


def _missing_response_operation(tmp_path):
    document = {
        "openapi": "3.0.3",
        "info": {"title": "Rare Source", "version": "1.0.0"},
        "servers": [{"url": "https://biothings.transltr.io/rare_source"}],
        "paths": {
            "/query": {
                "get": {
                    "operationId": "queryRareSource",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string", "minLength": 2},
                        }
                    ],
                    "responses": {"200": {"description": "Success"}},
                }
            }
        },
    }
    source = tmp_path / "rare-source-missing-response.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    return inspect_openapi_document(source)["candidates"][0]


def test_reviewed_missing_response_schema_completes_full_promotion(
    tmp_path, monkeypatch
):
    catalog_candidate = catalogs.normalize_provider_payload(
        "smartapi", QUERY, _payload("smartapi")
    )[0][0]
    operation = _missing_response_operation(tmp_path)
    schema = {
        "type": "object",
        "properties": {
            "total": {"type": "integer", "minimum": 0},
            "hits": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"identifier": {"type": "string"}},
                    "required": ["identifier"],
                },
            },
        },
        "required": ["total", "hits"],
    }

    def fake_get(url, params, *, timeout):
        assert url == "https://biothings.transltr.io/rare_source/query"
        assert timeout == 20.0
        identifier = params["q"]
        payload = {"total": 1, "hits": [{"identifier": identifier}]}
        return payload, _request(url, payload)

    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", fake_get)
    workspace = tmp_path / "reviewed-response"
    draft = vsd_promotion.create_reviewed_catalog_openapi_draft(
        catalog_candidate,
        operation,
        tool_name="GeneratedRareSourceLookup",
        description="Retrieve reviewed rare-disease annotations by identifier.",
        response_schema=schema,
        resolved_blockers=["json_response_missing"],
        review_note=(
            "The provider returns JSON objects; this bounded schema was verified "
            "against three distinct identifiers before publication."
        ),
        include_parameters=["q"],
        workspace=workspace,
    )
    cases = [
        {
            "arguments": {"q": identifier},
            "expect": {
                "result_type": "object",
                "required_fields": ["total", "hits"],
                "equals": {"total": 1},
                "equals_paths": {"/hits/0/identifier": identifier},
            },
        }
        for identifier in ("MONDO:0004976", "HP:0001250", "NCBIGene:2034")
    ]
    evidence = vsd_promotion.verify_draft(
        draft["draft_id"], cases, workspace=workspace
    )
    vsd_promotion.approve_draft(
        draft["draft_id"],
        reviewed_by="Integration Reviewer",
        decision_note="Approved after all reviewed response contract cases passed.",
        workspace=workspace,
    )
    publication = vsd_promotion.publish_draft(
        draft["draft_id"], workspace=workspace
    )

    assert evidence["all_cases_passed"] is True
    promotion = publication["config"]["vsd_promotion"]
    assert promotion["source_type"] == "catalog_openapi_reviewed_response"
    assert promotion["resolved_blockers"] == ["json_response_missing"]
    assert promotion["reviewed_response_schema_sha256"]
    assert promotion["catalog_binding"]["candidate_sha256"] == (
        catalog_candidate["candidate_sha256"]
    )


def test_reviewed_openapi_path_rejects_unresolved_or_unsafe_contracts(tmp_path):
    catalog_candidate = catalogs.normalize_provider_payload(
        "smartapi", QUERY, _payload("smartapi")
    )[0][0]
    operation = _missing_response_operation(tmp_path)
    kwargs = {
        "catalog_candidate": catalog_candidate,
        "operation_candidate": operation,
        "tool_name": "GeneratedRareSourceLookup",
        "description": "Retrieve reviewed rare-disease annotations by identifier.",
        "response_schema": {"type": "object"},
        "resolved_blockers": ["json_response_missing"],
        "review_note": "The response schema was independently reviewed and tested.",
        "include_parameters": ["q"],
        "workspace": tmp_path / "rejections",
    }
    with pytest.raises(vsd_promotion.VSDPromotionError, match="acknowledge every"):
        vsd_promotion.create_reviewed_catalog_openapi_draft(
            **{**kwargs, "resolved_blockers": []}
        )
    with pytest.raises(vsd_promotion.VSDPromotionError, match="object or array"):
        vsd_promotion.create_reviewed_catalog_openapi_draft(
            **{**kwargs, "response_schema": {}}
        )

    unsafe = copy.deepcopy(operation)
    unsafe["method"] = "POST"
    unsafe["blockers"] = ["json_response_missing", "method_not_read_only"]
    unsafe["candidate_sha256"] = catalogs._candidate_digest(
        {
            key: value
            for key, value in unsafe.items()
            if key not in {"candidate_id", "candidate_sha256"}
        }
    )
    unsafe["candidate_id"] = unsafe["candidate_sha256"][:16]
    with pytest.raises(vsd_promotion.VSDPromotionError, match="not promotable"):
        vsd_promotion.create_reviewed_catalog_openapi_draft(
            **{
                **kwargs,
                "operation_candidate": unsafe,
                "resolved_blockers": unsafe["blockers"],
            }
        )


def test_reviewed_catalog_openapi_cli_uses_the_same_bounded_path(tmp_path):
    catalog_candidate = catalogs.normalize_provider_payload(
        "smartapi", QUERY, _payload("smartapi")
    )[0][0]
    operation = _missing_response_operation(tmp_path)
    catalog_path = tmp_path / "catalog.json"
    operation_path = tmp_path / "operation.json"
    schema_path = tmp_path / "response-schema.json"
    catalog_path.write_text(json.dumps(catalog_candidate), encoding="utf-8")
    operation_path.write_text(json.dumps(operation), encoding="utf-8")
    schema_path.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    draft = _execute(
        build_parser().parse_args(
            [
                "--workspace",
                str(tmp_path / "cli-workspace"),
                "draft-reviewed-catalog-openapi",
                str(catalog_path),
                str(operation_path),
                str(schema_path),
                "--tool-name",
                "GeneratedRareSourceLookup",
                "--description",
                "Retrieve reviewed rare-disease annotations by identifier.",
                "--resolved-blockers",
                "json_response_missing",
                "--review-note",
                "The response schema was independently reviewed and tested.",
                "--include-parameters",
                "q",
            ]
        )
    )

    assert draft["config"]["vsd_promotion"]["source_type"] == (
        "catalog_openapi_reviewed_response"
    )


def test_irrelevant_catalog_metadata_is_not_returned_as_a_candidate():
    candidates, count = catalogs.normalize_provider_payload(
        "apis_guru",
        QUERY,
        {
            "weather.example.org": {
                "preferred": "v1",
                "versions": {
                    "v1": {
                        "swaggerUrl": "https://api.apis.guru/weather.json",
                        "info": {
                            "title": "Weather API",
                            "description": "Daily temperature observations.",
                        },
                    }
                },
            }
        },
    )

    assert count == 1
    assert candidates == []


def test_fixed_retrieval_time_makes_provider_provenance_reproducible():
    def fake_get(url, params=None, **kwargs):
        del params, kwargs
        payload = _payload("datagov")
        return payload, _request(url, payload)

    result = catalogs.discover_multi_catalog_candidates(
        QUERY,
        providers=["datagov"],
        limit=5,
        fetch_json=fake_get,
        socrata_normalizer=vsd_discovery.discover_api_candidates,
        exclude_registered=False,
        retrieved_at="2026-08-01T12:00:00+00:00",
    )

    assert result["provenance"]["providers"][0]["retrieved_at"] == (
        "2026-08-01T12:00:00+00:00"
    )


def test_registry_exact_endpoint_is_removed_with_auditable_reason():
    tooluniverse = ToolUniverse()
    tooluniverse.all_tools.append(
        {
            "name": "ExistingRareDiseaseCohort",
            "type": "VSDReviewedOperationTool",
            "description": "Rare Disease Longitudinal Cohort",
            "parameter": {"type": "object", "properties": {}},
            "return_schema": {"type": "object"},
            "vsd_operation": {
                "method": "GET",
                "endpoint": "https://data.example.gov/resource/abcd-1234.json",
            },
        }
    )
    candidates, _ = catalogs.normalize_provider_payload(
        "socrata",
        QUERY,
        _payload("socrata"),
        socrata_normalizer=vsd_discovery.discover_api_candidates,
    )

    kept, duplicates, registry_count = catalogs._registry_deduplicate(
        candidates, tooluniverse
    )

    assert kept == []
    assert registry_count >= 2700
    assert duplicates[0]["classification"] == "existing_exact"
    assert "ExistingRareDiseaseCohort" in duplicates[0]["matches"]


def test_registry_semantic_match_at_different_path_is_retained():
    tooluniverse = ToolUniverse()
    tooluniverse.all_tools.append(
        {
            "name": "ExistingIrishMortalityContext",
            "type": "VSDReviewedOperationTool",
            "description": "Principal Cause of Death",
            "parameter": {"type": "object", "properties": {}},
            "return_schema": {"type": "object"},
            "vsd_operation": {
                "method": "GET",
                "endpoint": (
                    "https://ws.cso.ie/public/api.restful/"
                    "PxStat.Data.Cube_API.ReadDataset/KTA31/JSON-stat/1.0/en"
                ),
            },
        }
    )
    exact = {
        "candidate_id": "exact",
        "name": "Principal Cause of Death",
        "description": "Principal Cause of Death",
        "api_endpoint": (
            "https://ws.cso.ie/public/api.restful/"
            "PxStat.Data.Cube_API.ReadDataset/KTA31/JSON-stat/1.0/en"
        ),
        "fields": [],
    }
    distinct = {
        **exact,
        "candidate_id": "distinct",
        "api_endpoint": (
            "https://ws.cso.ie/public/api.restful/"
            "PxStat.Data.Cube_API.ReadDataset/VSD17/JSON-stat/1.0/en"
        ),
    }

    kept, duplicates, _ = catalogs._registry_deduplicate(
        [exact, distinct], tooluniverse
    )

    assert [item["candidate_id"] for item in duplicates] == ["exact"]
    assert [item["candidate_id"] for item in kept] == ["distinct"]
    assert kept[0]["registry_coverage"]["classification"] == "existing_partial"
    assert kept[0]["registry_coverage"]["semantic_classification"] == ("existing_exact")


def test_agent_facing_tool_runs_explicit_multicatalog_search(monkeypatch):
    endpoint_to_provider = {value: key for key, value in catalogs._ENDPOINTS.items()}

    def fake_get(url, params=None, **kwargs):
        del params, kwargs
        provider = endpoint_to_provider[url]
        payload = _payload(provider)
        return payload, _request(url, payload)

    monkeypatch.setattr(vsd_discovery, "_safe_get_json", fake_get)
    tooluniverse = ToolUniverse()
    tooluniverse.load_tools(include_tools=["VSDDiscoverAPICandidates"], quiet=True)
    try:
        result = tooluniverse.run_one_function(
            {
                "name": "VSDDiscoverAPICandidates",
                "arguments": {
                    "query": QUERY,
                    "providers": ["socrata", "datagov", "apis_guru"],
                    "exclude_registered": False,
                    "limit": 10,
                },
            },
            use_cache=False,
        )
    finally:
        tooluniverse.close()

    assert result["status"] == "success"
    assert result["data"]["successful_provider_count"] == 3
    assert result["data"]["candidate_count"] >= 3
    assert all(not item["execution_allowed"] for item in result["data"]["candidates"])


def test_all_provider_failures_fail_closed():
    def fail(*_args, **_kwargs):
        raise vsd_tool.VSDPolicyError("unavailable")

    with pytest.raises(catalogs.VSDCatalogProviderError, match="All requested"):
        catalogs.discover_multi_catalog_candidates(
            QUERY,
            providers=["socrata", "datagov"],
            limit=5,
            fetch_json=fail,
            socrata_normalizer=vsd_discovery.discover_api_candidates,
            exclude_registered=False,
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"query": "x"},
        {"providers": []},
        {"providers": ["socrata", "socrata"]},
        {"providers": ["unknown"]},
        {"limit": 0},
        {"limit": True},
        {"exclude_registered": "yes"},
        {"retrieved_at": 123},
    ],
)
def test_reusable_dispatcher_rejects_invalid_controls_before_transport(overrides):
    calls = []

    def unexpected_fetch(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("transport must not run")

    arguments = {
        "query": QUERY,
        "providers": ["socrata"],
        "limit": 5,
        "fetch_json": unexpected_fetch,
        "socrata_normalizer": vsd_discovery.discover_api_candidates,
        "exclude_registered": False,
    }
    arguments.update(overrides)

    with pytest.raises(catalogs.VSDCatalogProviderError):
        catalogs.discover_multi_catalog_candidates(**arguments)
    assert calls == []


@pytest.mark.parametrize(
    "arguments",
    [
        {"providers": []},
        {"providers": ["socrata", "socrata"]},
        {"providers": ["arbitrary_web"]},
        {"providers": "socrata"},
        {"providers": ["socrata"], "exclude_registered": "yes"},
    ],
)
def test_agent_tool_rejects_invalid_multicatalog_controls_without_network(arguments):
    tool = vsd_discovery.VSDDiscoverAPICandidates({})
    with pytest.raises(vsd_discovery.VSDDiscoveryError):
        tool.run({"query": "rare disease", **arguments})


def test_transport_allows_only_bounded_catalog_override():
    with pytest.raises(ValueError, match="max_response_bytes"):
        vsd_tool._safe_get_json(
            "https://api.apis.guru/v2/list.json",
            max_response_bytes=10_000_001,
        )
    with pytest.raises(ValueError, match="max_response_bytes"):
        vsd_tool._safe_get_json(
            "https://api.apis.guru/v2/list.json",
            max_response_bytes=True,
        )
