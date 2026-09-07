"""
Regression tests: TCIA must not report an empty archive response as a bare success.

The NBIA v1 API answers every zero-result query with HTTP 200 and a completely
empty body (verified live against services.cancerimagingarchive.net):

    getModalityValues?Collection=NSCLC-Radiogenomics     -> 200, body ''
    getModalityValues?Collection=NSCLC%20Radiogenomics   -> 200, [{"Modality":"CT"},...]
    getSeries?Collection=NSCLC Radiogenomics&Modality=MR -> 200, body ''

Before the fix, BaseRESTTool decoded that empty body as plain text and returned
``{"status": "success", "data": ""}`` -- an empty *string* with no ``count``,
identical whether the collection was misspelled ('NSCLC-Radiogenomics') or the
collection was real and the filter simply matched nothing.

These tests pin the three properties that separate those cases:
  1. an unknown collection is an error naming the closest real collections,
  2. a valid collection with no matches is an honest empty *list* with count 0,
  3. ``data`` is never the empty string.

All HTTP access is patched; no live network.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"

# Trimmed stand-in for the 155 names getCollectionValues publishes. Note the
# real archive spells this collection with a space while its neighbours are
# hyphenated -- that inconsistency is what makes the typo so easy to make.
COLLECTIONS = [
    {"Collection": "LIDC-IDRI"},
    {"Collection": "NSCLC Radiogenomics"},
    {"Collection": "NSCLC-Radiomics"},
    {"Collection": "NSCLC-Radiomics-Genomics"},
    {"Collection": "TCGA-GBM"},
]


def _load_config(filename, tool_name):
    with open(DATA_DIR / filename) as f:
        tools = json.load(f)
    by_name = {t["name"]: t for t in tools}
    assert tool_name in by_name, f"{tool_name} missing from {filename}"
    return by_name[tool_name]


def _response(text="", status_code=200, url="https://tcia.example/endpoint"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.headers = {} if not text else {"content-type": "application/json"}
    resp.text = text
    resp.url = url
    if text:
        resp.json.return_value = json.loads(text)
    else:
        resp.json.side_effect = ValueError("No JSON object could be decoded")
    return resp


def _tool(tool_name):
    from tooluniverse import tcia_tool

    tcia_tool._reset_collection_cache()
    return tcia_tool.TCIATool(_load_config("tcia_tools.json", tool_name))


def _run(tool, arguments, main_response, collections=COLLECTIONS):
    """Run *tool*, stubbing the main request and the collection-list lookup."""
    with (
        patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=main_response,
        ),
        patch(
            "tooluniverse.tcia_tool.request_with_retry",
            return_value=_response(json.dumps(collections)) if collections else None,
        ) as collection_fetch,
    ):
        result = tool.run(arguments)
    return result, collection_fetch


class TestUnknownCollection:
    def test_typo_collection_is_an_error_naming_the_real_one(self):
        """'NSCLC-Radiogenomics' does not exist; the tool must say so, not succeed."""
        tool = _tool("TCIA_get_modality_values")
        result, _ = _run(tool, {"Collection": "NSCLC-Radiogenomics"}, _response(""))

        assert result["status"] == "error"
        assert "NSCLC-Radiogenomics" in result["error"]
        assert "does not exist" in result["error"]
        # The space-separated real collection is offered first.
        assert result["suggestions"][0] == "NSCLC Radiogenomics"
        assert "NSCLC Radiogenomics" in result["error"]
        assert "data" not in result

    def test_unknown_collection_is_an_error_for_every_tool_in_the_family(self):
        """The guard lives in one shared code path, so it covers the whole family."""
        for tool_name in (
            "TCIA_get_series",
            "TCIA_get_patients",
            "TCIA_get_patient_studies",
            "TCIA_get_body_part_values",
            "TCIA_get_manufacturer_values",
        ):
            tool = _tool(tool_name)
            result, _ = _run(tool, {"Collection": "No-Such-Collection"}, _response(""))
            assert result["status"] == "error", tool_name
            assert "No-Such-Collection" in result["error"], tool_name

    def test_collection_list_is_fetched_only_when_the_result_is_empty(self):
        """Validation must not tax the success path with an extra request."""
        payload = json.dumps([{"Modality": "CT"}, {"Modality": "PT"}])
        tool = _tool("TCIA_get_modality_values")
        result, collection_fetch = _run(
            tool, {"Collection": "NSCLC Radiogenomics"}, _response(payload)
        )
        assert result["status"] == "success"
        assert result["count"] == 2
        assert collection_fetch.call_count == 0

    def test_collection_list_is_fetched_once_per_process(self):
        """Repeated misses reuse the memoized collection list."""
        tool = _tool("TCIA_get_modality_values")
        with (
            patch(
                "tooluniverse.base_rest_tool.request_with_retry",
                return_value=_response(""),
            ),
            patch(
                "tooluniverse.tcia_tool.request_with_retry",
                return_value=_response(json.dumps(COLLECTIONS)),
            ) as collection_fetch,
        ):
            tool.run({"Collection": "Bad-One"})
            tool.run({"Collection": "Bad-Two"})
        assert collection_fetch.call_count == 1


class TestEmptyResultIsAnHonestEmptyList:
    def test_valid_collection_with_impossible_filter_returns_empty_list(self):
        """A real collection with no matching modality is success with data == []."""
        tool = _tool("TCIA_get_series")
        result, _ = _run(
            tool,
            {"Collection": "NSCLC Radiogenomics", "Modality": "MR"},
            _response(""),
        )
        assert result["status"] == "success"
        assert result["data"] == []
        assert result["count"] == 0
        # The note must make clear the collection is fine and the filter is not.
        assert "NSCLC Radiogenomics" in result["note"]
        assert "Modality" in result["note"]

    def test_empty_result_is_never_the_empty_string(self):
        """Regression on the original payload: data was "" with no count key."""
        tool = _tool("TCIA_get_series")
        result, _ = _run(
            tool,
            {"Collection": "NSCLC Radiogenomics", "Modality": "MR"},
            _response(""),
        )
        assert result["data"] != ""
        assert isinstance(result["data"], list)

    def test_empty_result_without_a_collection_argument(self):
        """Endpoints keyed on a UID have no collection to validate; still a list."""
        tool = _tool("TCIA_get_series_size")
        result, collection_fetch = _run(
            tool, {"SeriesInstanceUID": "1.2.3.not.real"}, _response("")
        )
        assert result["status"] == "success"
        assert result["data"] == []
        assert result["count"] == 0
        assert collection_fetch.call_count == 0
        assert "exactly" in result["note"]

    def test_empty_collection_list_endpoint_does_not_recurse(self):
        """TCIA_list_collections is the validation source; it must not call itself."""
        tool = _tool("TCIA_list_collections")
        result, collection_fetch = _run(tool, {}, _response(""))
        assert result["status"] == "success"
        assert result["data"] == []
        assert collection_fetch.call_count == 0


class TestValidationOutageDegradesGracefully:
    def test_unreachable_collection_list_does_not_invent_an_error(self):
        """If the archive's collection list is unavailable, do not claim a typo."""
        tool = _tool("TCIA_get_modality_values")
        with (
            patch(
                "tooluniverse.base_rest_tool.request_with_retry",
                return_value=_response(""),
            ),
            patch(
                "tooluniverse.tcia_tool.request_with_retry",
                side_effect=OSError("connection reset"),
            ),
        ):
            result = tool.run({"Collection": "NSCLC-Radiogenomics"})

        assert result["status"] == "success"
        assert result["data"] == []
        assert result["count"] == 0
        assert "could not be verified" in result["note"]


class TestUnchangedBehaviour:
    def test_non_empty_payload_is_untouched(self):
        """Responses with a body keep flowing through normal BaseRESTTool parsing."""
        payload = json.dumps(
            [{"PatientId": "LUNG1-001", "Collection": "NSCLC-Radiomics"}]
        )
        tool = _tool("TCIA_get_patients")
        result, _ = _run(tool, {"Collection": "NSCLC-Radiomics"}, _response(payload))
        assert result["status"] == "success"
        assert result["count"] == 1
        assert result["data"][0]["PatientId"] == "LUNG1-001"

    def test_http_error_still_reports_the_status_code(self):
        """A real transport failure must not be masked by the empty-body handler."""
        tool = _tool("TCIA_get_patients")
        result, _ = _run(
            tool, {"Collection": "LIDC-IDRI"}, _response("", status_code=500)
        )
        assert result["status"] == "error"
        assert result["status_code"] == 500

    def test_echoed_url_includes_the_query_string(self):
        """The response must show what was actually requested."""
        tool = _tool("TCIA_get_modality_values")
        requested = (
            "https://tcia.example/getModalityValues?Collection=NSCLC+Radiogenomics"
        )
        result, _ = _run(
            tool,
            {"Collection": "NSCLC Radiogenomics"},
            _response(json.dumps([{"Modality": "CT"}]), url=requested),
        )
        assert result["url"] == requested


def test_every_tcia_tool_uses_the_hardened_class():
    """The fix is config-wired for the whole family, not just one tool."""
    with open(DATA_DIR / "tcia_tools.json") as f:
        tools = json.load(f)
    assert len(tools) >= 10
    assert {t["type"] for t in tools} == {"TCIATool"}
