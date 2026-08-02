from __future__ import annotations

import json

import pytest

from tooluniverse import vsd_discovery, vsd_tool
from tooluniverse.vsd_catalog_providers import (
    PROVIDER_ORDER,
    discover_multi_catalog_candidates,
)

pytestmark = [pytest.mark.integration, pytest.mark.network]


def test_all_reviewed_catalogs_complete_one_live_bounded_search():
    result = discover_multi_catalog_candidates(
        "cancer clinical trials",
        providers=list(PROVIDER_ORDER),
        limit=20,
        fetch_json=vsd_tool._safe_get_json,
        socrata_normalizer=vsd_discovery.discover_api_candidates,
        exclude_registered=False,
    )

    assert result["successful_provider_count"] == len(PROVIDER_ORDER)
    assert result["failed_provider_count"] == 0
    assert result["candidate_count"] >= 5
    assert result["cross_catalog_duplicate_count"] >= 1
    assert all(
        candidate["execution_allowed"] is False
        and candidate["score"]["matched_query_terms"] >= 1
        for candidate in result["candidates"]
    )
    assert "X-Api-Key" in json.dumps(result["provenance"], sort_keys=True)
    assert "TOOLUNIVERSE_DATAGOV_API_KEY" in json.dumps(
        result["provenance"], sort_keys=True
    ) or "DEMO_KEY" in json.dumps(result["provenance"], sort_keys=True)
