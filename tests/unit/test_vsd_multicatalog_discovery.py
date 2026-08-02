from __future__ import annotations

import json
from pathlib import Path

import pytest

import tooluniverse.vsd_catalog_providers as catalogs
from tooluniverse import ToolUniverse, vsd_discovery, vsd_tool

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

    assert result["successful_provider_count"] == 4
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
    europe_call = next(item for item in calls if item[0] == "data_europa")
    assert europe_call[1]["limit"] == 10
    assert catalogs._ENDPOINTS["ckan_data_gov_uk"].startswith(
        "https://ckan.publishing.service.gov.uk/"
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
