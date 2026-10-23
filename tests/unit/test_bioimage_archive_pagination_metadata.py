"""Regression tests for BioImage Archive pagination completeness metadata."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.bioimage_archive_tool import BioImageArchiveTool


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


@pytest.mark.parametrize("action", ["search", "search_bioimages"])
def test_search_preserves_lower_bound_total_qualifier(action):
    tool = BioImageArchiveTool(
        {"name": f"BioImage_{action}", "fields": {"action": action}}
    )
    payload = {
        "totalHits": 1817,
        "isTotalHitsExact": False,
        "hits": [
            {"accession": "S-BIAD1"},
            {"accession": "S-BIAD2"},
            {"accession": "S-BIAD3"},
        ],
    }
    with patch(
        "tooluniverse.bioimage_archive_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"query": "cell", "page_size": 3, "page": 1})

    metadata = result["metadata"]
    assert metadata["total_hits"] == 1817
    assert metadata["total_hits_exact"] is False
    assert metadata["total_hits_relation"] == "lower_bound"
    assert metadata["has_more"] is True
    assert metadata["next_page"] == 2
    assert "lower bound" in metadata["warning"]


def test_exact_total_stops_navigation_on_last_page():
    tool = BioImageArchiveTool(
        {"name": "BioImage_search", "fields": {"action": "search"}}
    )
    payload = {
        "totalHits": 5,
        "isTotalHitsExact": True,
        "hits": [{"accession": "S-BIAD5"}],
    }
    with patch(
        "tooluniverse.bioimage_archive_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"query": "rare", "page_size": 2, "page": 3})

    assert result["metadata"]["total_hits_relation"] == "exact"
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_page"] is None
    assert result["metadata"]["warning"] is None


def test_file_manifest_exposes_filtered_total_and_reachable_next_offset():
    tool = BioImageArchiveTool(
        {"name": "BioImage_files", "fields": {"action": "list_study_files"}}
    )
    payload = {
        "recordsTotal": 468,
        "recordsFiltered": 468,
        "data": [
            {"Name": "image-3.tif", "path": "images/image-3.tif"},
            {"Name": "image-4.tif", "path": "images/image-4.tif"},
            {"Name": "image-5.tif", "path": "images/image-5.tif"},
        ],
    }
    with patch(
        "tooluniverse.bioimage_archive_tool.requests.get",
        return_value=_response(payload),
    ) as get:
        result = tool.run({"accession": "S-BIAD634", "limit": 3, "offset": 3})

    assert get.call_args.kwargs["params"] == {"start": 3, "length": 3}
    assert result["metadata"] == {
        "source": "BioImage Archive (EBI BioStudies)",
        "accession": "S-BIAD634",
        "records_total": 468,
        "records_filtered": 468,
        "returned": 3,
        "offset": 3,
        "limit": 3,
        "has_more": True,
        "truncated": True,
        "next_offset": 6,
    }


@pytest.mark.parametrize(
    ("arguments", "error_text"),
    [
        ({"query": "cell", "page_size": 0}, "page_size"),
        ({"query": "cell", "page": 0}, "page"),
        ({"accession": "S-BIAD634", "limit": 501}, "at most 500"),
        ({"accession": "S-BIAD634", "offset": -1}, "non-negative"),
    ],
)
def test_invalid_pagination_is_rejected_instead_of_changed(arguments, error_text):
    action = "list_study_files" if "accession" in arguments else "search"
    tool = BioImageArchiveTool(
        {"name": "BioImage_invalid", "fields": {"action": action}}
    )
    with patch("tooluniverse.bioimage_archive_tool.requests.get") as get:
        result = tool.run(arguments)

    assert result["status"] == "error"
    assert error_text in result["error"]
    get.assert_not_called()


def test_configs_document_qualified_totals_and_file_navigation():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "bioimage_archive_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}

    for name in ("BioImageArchive_search_studies", "BioImageArchive_search_bioimages"):
        assert "isTotalHitsExact" in configs[name]["description"]
        page_size = configs[name]["parameter"]["properties"]["page_size"]
        assert page_size["minimum"] == 1
        assert page_size["maximum"] == 100

    files = configs["BioImageArchive_list_study_files"]
    assert "next_offset" in files["description"]
    assert files["parameter"]["properties"]["offset"]["minimum"] == 0
