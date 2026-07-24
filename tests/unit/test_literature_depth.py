"""Mocked-HTTP unit tests for the literature-cluster depth tools.

Covers four new config-only tools that reuse existing tool classes (no new
@register_tool class):

  * PubTator3_GetEntityRelations  (BaseRESTTool, PubTator3 relations graph)
  * openalex_search_sources / openalex_get_source  (OpenAlexRESTTool, journal
    bibliometric impact metrics)
  * EuropePMC_get_article_datalinks  (BaseRESTTool, article->data cross-refs)
  * LitVar_get_variant_details  (BaseRESTTool, full LitVar2 variant record)

Each tool is loaded from its real JSON config so the tests exercise the actual
endpoint templates / param maps. HTTP is mocked, so these run offline. Both a
successful parse path and an error path are covered per tool.
"""
import json
import os

import pytest

from tooluniverse import base_rest_tool
from tooluniverse import openalex_tool
from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.openalex_tool import OpenAlexRESTTool

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "src",
    "tooluniverse",
    "data",
)


def _load_config(filename, tool_name):
    with open(os.path.join(DATA_DIR, filename)) as fh:
        for entry in json.load(fh):
            if entry.get("name") == tool_name:
                return entry
    raise AssertionError(f"{tool_name} not found in {filename}")


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text="", url="http://x"):
        self.status_code = status_code
        self._json = json_data
        self.text = text if text else (json.dumps(json_data) if json_data else "")
        self.url = url
        self.headers = {"content-type": "application/json"}
        self.reason = "OK" if status_code == 200 else "Error"

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


# ---------------------------------------------------------------------------
# 1. PubTator3_GetEntityRelations  (BaseRESTTool, list payload, ranked)
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_pubtator_relations_parse_and_rank(monkeypatch):
    """Relations parse: ranked edges, client-side limit, limit not forwarded."""
    cfg = _load_config("pubtator3_ext_tools.json", "PubTator3_GetEntityRelations")
    tool = BaseRESTTool(cfg)

    edges = [
        {"type": "associate", "source": "@DISEASE_Melanoma",
         "target": "@GENE_BRAF", "publications": 4981},
        {"type": "associate", "source": "@DISEASE_Neoplasms",
         "target": "@GENE_BRAF", "publications": 4075},
        {"type": "cause", "source": "@GENE_BRAF",
         "target": "@DISEASE_X", "publications": 10},
    ]
    captured = {}

    def fake_request(session, method, url, params=None, **kwargs):
        captured["params"] = params
        return _FakeResponse(200, json_data=edges, url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run({"e1": "@GENE_BRAF", "limit": 2})
    assert out["status"] == "success"
    assert isinstance(out["data"], list)
    # client_side_limit truncates to 2 and records the original total
    assert out["count"] == 2
    assert out["total_before_limit"] == 3
    assert out["data"][0]["publications"] == 4981
    # `limit` is client-side only and must not be forwarded to the API
    assert "limit" not in captured["params"]
    # `e1` IS forwarded as a query param (endpoint has no placeholder)
    assert captured["params"]["e1"] == "@GENE_BRAF"


@pytest.mark.unit
def test_pubtator_relations_pair_query(monkeypatch):
    """Pair query forwards type and e2 as query params."""
    cfg = _load_config("pubtator3_ext_tools.json", "PubTator3_GetEntityRelations")
    tool = BaseRESTTool(cfg)
    captured = {}

    def fake_request(session, method, url, params=None, **kwargs):
        captured["params"] = params
        return _FakeResponse(
            200,
            json_data=[{"type": "treat", "source": "@CHEMICAL_Doxorubicin",
                        "target": "@DISEASE_Neoplasms", "publications": 14759}],
            url=url,
        )

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)
    out = tool.run(
        {"e1": "@CHEMICAL_Doxorubicin", "type": "treat", "e2": "@DISEASE_Neoplasms"}
    )
    assert out["status"] == "success"
    assert out["data"][0]["publications"] == 14759
    assert captured["params"]["type"] == "treat"
    assert captured["params"]["e2"] == "@DISEASE_Neoplasms"


@pytest.mark.unit
def test_pubtator_relations_error_path(monkeypatch):
    """Non-2xx PubTator response yields a status=error envelope."""
    cfg = _load_config("pubtator3_ext_tools.json", "PubTator3_GetEntityRelations")
    tool = BaseRESTTool(cfg)

    def fake_request(session, method, url, params=None, **kwargs):
        return _FakeResponse(500, text="server boom", url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)
    out = tool.run({"e1": "@GENE_BRAF"})
    assert out["status"] == "error"
    assert "error" in out


# ---------------------------------------------------------------------------
# 2. openalex_search_sources / openalex_get_source  (OpenAlexRESTTool)
# ---------------------------------------------------------------------------
_NATURE_RESULTS = {
    "meta": {"count": 281},
    "results": [
        {
            "id": "https://openalex.org/S137773608",
            "display_name": "Nature",
            "issn_l": "0028-0836",
            "is_oa": False,
            "works_count": 448746,
            "host_organization_name": "Nature Portfolio",
            "summary_stats": {
                "h_index": 1841,
                "i10_index": 120069,
                "2yr_mean_citedness": 16.826,
            },
        }
    ],
}


@pytest.mark.unit
def test_openalex_search_sources_parse(monkeypatch):
    """Source search returns summary_stats with h_index and 2yr_mean_citedness."""
    cfg = _load_config("openalex_tools.json", "openalex_search_sources")
    tool = OpenAlexRESTTool(cfg)
    captured = {}

    def fake_request(session, method, url, params=None, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse(200, json_data=_NATURE_RESULTS, url=url)

    monkeypatch.setattr(openalex_tool, "request_with_retry", fake_request)
    out = tool.run({"search": "nature", "per_page": 3})
    assert out["status"] == "success"
    src = out["data"]["results"][0]
    assert src["id"].endswith("S137773608")
    assert src["summary_stats"]["h_index"] == 1841
    assert round(src["summary_stats"]["2yr_mean_citedness"], 2) == 16.83
    # /sources endpoint, per_page mapped to OpenAlex's per-page
    assert captured["url"].endswith("/sources")
    assert captured["params"]["per-page"] == 3
    assert captured["params"]["search"] == "nature"
    # default polite-pool mailto is injected
    assert "mailto" in captured["params"]


@pytest.mark.unit
def test_openalex_get_source_by_id(monkeypatch):
    """Source detail by ID substitutes into /sources/{id} path."""
    cfg = _load_config("openalex_tools.json", "openalex_get_source")
    tool = OpenAlexRESTTool(cfg)
    detail = {
        "id": "https://openalex.org/S49861241",
        "display_name": "The Lancet",
        "host_organization_name": "Elsevier BV",
        "summary_stats": {"h_index": 1201},
    }
    captured = {}

    def fake_request(session, method, url, params=None, **kwargs):
        captured["url"] = url
        return _FakeResponse(200, json_data=detail, url=url)

    monkeypatch.setattr(openalex_tool, "request_with_retry", fake_request)
    out = tool.run({"source_id": "S49861241"})
    assert out["status"] == "success"
    assert out["data"]["display_name"] == "The Lancet"
    assert out["data"]["summary_stats"]["h_index"] == 1201
    # source_id substituted into the path
    assert captured["url"].endswith("/sources/S49861241")


@pytest.mark.unit
def test_openalex_get_source_error_path(monkeypatch):
    """404 source lookup yields a status=error envelope."""
    cfg = _load_config("openalex_tools.json", "openalex_get_source")
    tool = OpenAlexRESTTool(cfg)

    def fake_request(session, method, url, params=None, **kwargs):
        return _FakeResponse(404, text="not found", url=url)

    monkeypatch.setattr(openalex_tool, "request_with_retry", fake_request)
    out = tool.run({"source_id": "S00000000"})
    assert out["status"] == "error"
    assert out["status_code"] == 404


# ---------------------------------------------------------------------------
# 3. EuropePMC_get_article_datalinks  (BaseRESTTool, path placeholders)
# ---------------------------------------------------------------------------
_DATALINKS = {
    "version": "6.9",
    "hitCount": 12,
    "request": {},
    "dataLinkList": {
        "Category": [
            {"Name": "BioProject", "CountTotal": 2},
            {"Name": "Nucleotide Sequences", "CountTotal": 6},
            {"Name": "Altmetric", "CountTotal": 1},
        ]
    },
}


@pytest.mark.unit
def test_europepmc_datalinks_parse(monkeypatch):
    """Datalinks parse: hitCount and category names from MED source."""
    cfg = _load_config(
        "europepmc_citations_tools.json", "EuropePMC_get_article_datalinks"
    )
    tool = BaseRESTTool(cfg)
    captured = {}

    def fake_request(session, method, url, params=None, **kwargs):
        captured["url"] = url
        return _FakeResponse(200, json_data=_DATALINKS, url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)
    out = tool.run({"pmid": "23193287"})
    assert out["status"] == "success"
    data = out["data"]
    assert data["hitCount"] == 12
    names = [c["Name"] for c in data["dataLinkList"]["Category"]]
    assert "BioProject" in names and "Altmetric" in names
    # source/pmid/page/pageSize all substituted into the URL path (MED default)
    assert "/MED/23193287/datalinks" in captured["url"]


@pytest.mark.unit
def test_europepmc_datalinks_pmc_source(monkeypatch):
    """source=PMC routes the id through the PMC path segment."""
    cfg = _load_config(
        "europepmc_citations_tools.json", "EuropePMC_get_article_datalinks"
    )
    tool = BaseRESTTool(cfg)
    captured = {}

    def fake_request(session, method, url, params=None, **kwargs):
        captured["url"] = url
        return _FakeResponse(200, json_data=_DATALINKS, url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)
    out = tool.run({"pmid": "3539452", "source": "PMC"})
    assert out["status"] == "success"
    assert "/PMC/3539452/datalinks" in captured["url"]


@pytest.mark.unit
def test_europepmc_datalinks_error_path(monkeypatch):
    """Server error yields a status=error envelope."""
    cfg = _load_config(
        "europepmc_citations_tools.json", "EuropePMC_get_article_datalinks"
    )
    tool = BaseRESTTool(cfg)

    def fake_request(session, method, url, params=None, **kwargs):
        return _FakeResponse(500, text="boom", url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)
    out = tool.run({"pmid": "23193287"})
    assert out["status"] == "error"
    assert "error" in out


# ---------------------------------------------------------------------------
# 4. LitVar_get_variant_details  (BaseRESTTool, encoded path template)
# ---------------------------------------------------------------------------
_LITVAR_RECORD = {
    "_id": "litvar@rs113488022##",
    "rsid": "rs113488022",
    "clingen_ids": ["CA281998", "CA123643", "CA16602736"],
    "gene": ["BRAF"],
    "name": "p.V600E",
    "hgvs": "p.V600E",
    "data_snp_class": ["snv"],
    "data_chromosome_base_position": ["7:140753336"],
    "data_clinical_significance": [
        "other", "drug-response", "pathogenic", "likely-pathogenic"
    ],
}


@pytest.mark.unit
def test_litvar_variant_details_parse(monkeypatch):
    """Variant record parse: clingen_ids, position, clinical significance."""
    cfg = _load_config("litvar_tools.json", "LitVar_get_variant_details")
    tool = BaseRESTTool(cfg)
    captured = {}

    def fake_request(session, method, url, params=None, **kwargs):
        captured["url"] = url
        return _FakeResponse(200, json_data=_LITVAR_RECORD, url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)
    out = tool.run({"rsid": "rs113488022"})
    assert out["status"] == "success"
    data = out["data"]
    assert data["clingen_ids"] == ["CA281998", "CA123643", "CA16602736"]
    assert data["data_chromosome_base_position"] == ["7:140753336"]
    assert "pathogenic" in data["data_clinical_significance"]
    # rsid substituted; litvar@...## wrapper present and NOT the /publications path
    assert "rs113488022" in captured["url"]
    assert captured["url"].endswith("%23%23")
    assert "/publications" not in captured["url"]


@pytest.mark.unit
def test_litvar_variant_details_error_path(monkeypatch):
    """404 variant lookup yields a status=error envelope."""
    cfg = _load_config("litvar_tools.json", "LitVar_get_variant_details")
    tool = BaseRESTTool(cfg)

    def fake_request(session, method, url, params=None, **kwargs):
        return _FakeResponse(404, text="not found", url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)
    out = tool.run({"rsid": "rs000000000"})
    assert out["status"] == "error"
    assert "error" in out
