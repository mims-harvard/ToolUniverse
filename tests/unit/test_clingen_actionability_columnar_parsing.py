"""Regression guard for Fix-R28-5 in clingen_tool.py: ClinGen's
actionability ?flavor=flat API returns a columnar table --
{"columns": [...], "rows": [[...], ...]} -- not a list of record dicts.
Confirmed live: neither `_get_actionability` nor `_search_actionability`
recognized this shape (isinstance(data, list) is False, and there is no
top-level "data" key), so:
  - `_search_actionability`'s gene filter matched nothing for every gene
    tested (LDLR, BRCA1), always returning empty Adult/Pediatric lists
    even though real curations exist for both (e.g. LDLR,APOB,PCSK9
    familial hypercholesterolemia).
  - `_get_actionability`'s gene filter silently no-opped and it returned
    the whole raw unparsed table instead of individual records.
Also, geneOrVariant is a comma-joined multi-gene field for panel curations
(e.g. "LDLR,APOB,PCSK9"), so the filter must substring-match, not
exact-match, the field.
"""

import pytest

from tooluniverse.clingen_tool import ClinGenTool

pytestmark = pytest.mark.unit

_COLUMNAR_RESPONSE = {
    "columns": ["docId", "geneOrVariant", "disease", "overall"],
    "rows": [
        ["AC057", "LDLR,APOB,PCSK9", "Familial Hypercholesterolemia", "10CA"],
        ["AC099", "BRCA1,BRCA2", "Hereditary Breast/Ovarian Cancer", "9BA"],
        ["AC120", "MYH7", "Hypertrophic Cardiomyopathy", "8BA"],
    ],
}


def _tool(operation):
    return ClinGenTool({"fields": {"operation": operation}, "parameter": {}})


class TestActionabilityRowsToDicts:
    def test_columnar_shape_converted_to_dicts(self):
        tool = _tool("get_actionability_adult")
        rows = tool._actionability_rows_to_dicts(_COLUMNAR_RESPONSE)
        assert len(rows) == 3
        assert rows[0]["geneOrVariant"] == "LDLR,APOB,PCSK9"
        assert rows[0]["overall"] == "10CA"

    def test_plain_list_passed_through(self):
        tool = _tool("get_actionability_adult")
        data = [{"gene": "TP53"}]
        assert tool._actionability_rows_to_dicts(data) == data

    def test_unknown_shape_returns_empty_list(self):
        tool = _tool("get_actionability_adult")
        assert tool._actionability_rows_to_dicts({"unexpected": "shape"}) == []


class TestGetActionabilityGeneFilter:
    def test_substring_matches_comma_joined_gene_or_variant(self, monkeypatch):
        tool = _tool("get_actionability_adult")

        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                return _COLUMNAR_RESPONSE

        monkeypatch.setattr(
            "tooluniverse.clingen_tool.requests.get", lambda *a, **k: FakeResp()
        )
        result = tool.run({"gene": "LDLR"})

        assert result["status"] == "success"
        assert result["total"] == 1
        assert result["data"][0]["geneOrVariant"] == "LDLR,APOB,PCSK9"

    def test_second_gene_in_panel_also_matches(self, monkeypatch):
        tool = _tool("get_actionability_adult")

        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                return _COLUMNAR_RESPONSE

        monkeypatch.setattr(
            "tooluniverse.clingen_tool.requests.get", lambda *a, **k: FakeResp()
        )
        result = tool.run({"gene": "BRCA1"})

        assert result["total"] == 1
        assert result["data"][0]["geneOrVariant"] == "BRCA1,BRCA2"


class TestSearchActionabilityGeneFilter:
    def test_search_finds_gene_in_panel_curation(self, monkeypatch):
        tool = _tool("search_actionability")

        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                return _COLUMNAR_RESPONSE

        monkeypatch.setattr(
            "tooluniverse.clingen_tool.requests.get", lambda *a, **k: FakeResp()
        )
        result = tool.run({"gene": "LDLR"})

        assert result["status"] == "success"
        assert result["adult_count"] == 1
        assert result["pediatric_count"] == 1
        assert result["data"]["Adult"][0]["geneOrVariant"] == "LDLR,APOB,PCSK9"
