"""Regression guard for two Fix-R27A bugs in DepMapTool (depmap_tool.py).

Fix-R27A-1 (search always returns the same hardcoded result): the Cell
Model Passports API silently ignores `filter[model]=model_name:...` on
/models -- confirmed live that A549, HeLa, MCF7, and even a nonsense
string all returned the API's identical unfiltered first page
(model_id SIDM01774 every time). The real name-search endpoint is
/search/models?q=... . Fixed by switching endpoints.

Fix-R27A-2 (wrong/missing field mapping): even with a correctly-resolved
model_id, most fields came back null -- confirmed live that tissue,
cancer_type, sample_site, gender, ethnicity, age_at_sampling,
tissue_status, and msi_status are not attributes on the /models/{id}
resource at all (they live on related sample/patient/model_msi_status
resources reachable only via JSON:API `include`), and
`mutational_burden`/`model_name` were read from nonexistent attribute
keys (real keys are `mutations_per_mb` and `names`, a list). Fixed by
requesting `include=sample,sample.tissue,sample.cancer_type,sample.
patient,model_msi_status` and resolving the relationship chain (also
normalizing id types to str, since tissue/cancer_type ids come back as
int while the relationship pointer's id is a str -- confirmed live).

Fix-R27A-3 (get_cell_lines list endpoint): the same broken filter[model]
pattern affects the plural list endpoint too -- confirmed live that
tissue="Lung" and tissue="Breast" returned identical results (every
filter[...] syntax tried was silently ignored), model_name read a
nonexistent attribute key, and meta.total read a nonexistent key (the
real key is meta.count). Fixed the field mapping and added an explicit
note when a tissue/cancer_type filter is passed, since the API can't
honor it.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.depmap_tool import DepMapTool

pytestmark = pytest.mark.unit

_A549_GET_RESPONSE = {
    "data": {
        "id": "SIDM00903",
        "attributes": {
            "names": ["A549", "NCI-A549", "A549/ATCC", "hA549"],
            "growth_properties": "Adherent",
            "ploidy": 2.76,
            "mutations_per_mb": 39.18,
        },
        "relationships": {
            "sample": {"data": {"type": "sample", "id": "SIDS00075"}},
            "model_msi_status": {"data": {"type": "model_msi_status", "id": "754"}},
        },
    },
    "included": [
        {
            "type": "sample",
            "id": "SIDS00075",
            "attributes": {
                "sample_site": "Unknown",
                "tissue_status": "Tumour",
                "age_at_sampling": 58.0,
            },
            "relationships": {
                "tissue": {"data": {"type": "tissue", "id": "10"}},
                "cancer_type": {"data": {"type": "cancer_type", "id": "14"}},
                "patient": {"data": {"type": "patient", "id": "SIDP00060"}},
            },
        },
        # tissue/cancer_type ids come back as ints, unlike the string id
        # in the relationship pointer above -- this is the exact live
        # mismatch that broke resolution before normalizing to str.
        {"type": "tissue", "id": 10, "attributes": {"name": "Lung"}},
        {
            "type": "cancer_type",
            "id": 14,
            "attributes": {"name": "Non-Small Cell Lung Carcinoma"},
        },
        {
            "type": "patient",
            "id": "SIDP00060",
            "attributes": {"gender": "Male", "ethnicity": "White"},
        },
        {
            "type": "model_msi_status",
            "id": "754",
            "attributes": {"msi_status": "MSS"},
        },
    ],
}

_SEARCH_RESPONSE = {
    "data": [
        {"id": "SIDM00903", "attributes": {"names": ["A549", "NCI-A549"]}},
    ]
}


def _resp(payload):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = payload
    return r


def _tool():
    return DepMapTool({"fields": {"operation": "get_cell_line"}})


class TestSearchUsesRealEndpoint:
    def test_search_hits_search_models_not_broken_filter(self):
        tool = DepMapTool({"fields": {"operation": "search_cell_lines"}})
        with patch(
            "tooluniverse.depmap_tool.requests.get", return_value=_resp(_SEARCH_RESPONSE)
        ) as mock_get:
            result = tool.run({"query": "A549"})

        called_url = mock_get.call_args.args[0]
        assert called_url == "https://api.cellmodelpassports.sanger.ac.uk/search/models"
        called_params = mock_get.call_args.kwargs["params"]
        assert called_params["q"] == "A549"
        assert "filter[model]" not in called_params
        assert result["data"]["cell_lines"][0]["model_id"] == "SIDM00903"
        assert result["data"]["cell_lines"][0]["model_name"] == "A549"

    def test_exact_match_sorted_first_despite_upstream_order(self):
        # Confirmed live: /search/models?q=HCC38 returns "HCC38-BL" before
        # the exact "HCC38" match -- upstream order is not exact-match-first.
        # DepMap_get_cell_line's by-name lookup relies on cell_lines[0], so
        # this must be re-sorted client-side rather than trusted as-is.
        tool = DepMapTool({"fields": {"operation": "search_cell_lines"}})
        upstream_order = {
            "data": [
                {"id": "SIDM00674", "attributes": {"names": ["HCC38-BL"]}},
                {"id": "SIDM00675", "attributes": {"names": ["HCC38", "HCC0038"]}},
            ]
        }
        with patch(
            "tooluniverse.depmap_tool.requests.get", return_value=_resp(upstream_order)
        ):
            result = tool.run({"query": "HCC38"})

        cell_lines = result["data"]["cell_lines"]
        assert cell_lines[0]["model_name"] == "HCC38"
        assert cell_lines[0]["exact_match"] is True
        assert cell_lines[1]["model_name"] == "HCC38-BL"
        assert cell_lines[1]["exact_match"] is False


class TestGetCellLineFieldMapping:
    def test_resolves_related_fields_via_include(self):
        tool = _tool()
        with patch(
            "tooluniverse.depmap_tool.requests.get",
            return_value=_resp(_A549_GET_RESPONSE),
        ):
            result = tool.run({"model_id": "SIDM00903"})

        assert result["status"] == "success"
        data = result["data"]
        assert data["model_name"] == "A549"
        assert data["tissue"] == "Lung"
        assert data["cancer_type"] == "Non-Small Cell Lung Carcinoma"
        assert data["sample_site"] == "Unknown"
        assert data["tissue_status"] == "Tumour"
        assert data["age_at_sampling"] == 58.0
        assert data["gender"] == "Male"
        assert data["ethnicity"] == "White"
        assert data["msi_status"] == "MSS"
        assert data["mutational_burden"] == 39.18

    def test_missing_relationships_do_not_crash(self):
        tool = _tool()
        bare_response = {
            "data": {
                "id": "SIDM00001",
                "attributes": {"names": ["X"], "mutations_per_mb": None},
            }
        }
        with patch(
            "tooluniverse.depmap_tool.requests.get", return_value=_resp(bare_response)
        ):
            result = tool.run({"model_id": "SIDM00001"})

        assert result["status"] == "success"
        assert result["data"]["tissue"] is None
        assert result["data"]["cancer_type"] is None


class TestGetCellLinesListEndpoint:
    def test_model_name_and_total_use_real_keys(self):
        tool = DepMapTool({"fields": {"operation": "get_cell_lines"}})
        payload = {
            "data": [{"id": "SIDM01774", "attributes": {"names": ["PK-59"]}}],
            "meta": {"count": 2266},
        }
        with patch(
            "tooluniverse.depmap_tool.requests.get", return_value=_resp(payload)
        ):
            result = tool.run({"page_size": 1})

        assert result["data"]["cell_lines"][0]["model_name"] == "PK-59"
        assert result["data"]["total"] == 2266

    def test_tissue_filter_gets_honest_note_not_silent_no_op(self):
        # The upstream API silently ignores every filter[...] syntax on
        # this endpoint (confirmed live) -- a tissue/cancer_type filter
        # must surface a note, not pretend it was applied.
        tool = DepMapTool({"fields": {"operation": "get_cell_lines"}})
        payload = {"data": [], "meta": {"count": 0}}
        with patch(
            "tooluniverse.depmap_tool.requests.get", return_value=_resp(payload)
        ):
            result = tool.run({"tissue": "Lung"})

        assert "does not support server-side" in result["metadata"]["note"]

    def test_no_filter_gets_no_note(self):
        tool = DepMapTool({"fields": {"operation": "get_cell_lines"}})
        payload = {"data": [], "meta": {"count": 0}}
        with patch(
            "tooluniverse.depmap_tool.requests.get", return_value=_resp(payload)
        ):
            result = tool.run({})

        assert "metadata" not in result
