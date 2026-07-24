"""Unit tests for discovery-round batch 12 (TogoID). Network mocked."""

from unittest.mock import MagicMock, patch

from tooluniverse.togoid_tool import TogoIDConvertTool, TogoIDDatasetsTool


def _resp(status=200, json_body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _cfg(name, typ):
    return {"name": name, "type": typ, "parameter": {"type": "object", "properties": {}}}


def test_convert_requires_all_three():
    out = TogoIDConvertTool(_cfg("TogoID_convert", "TogoIDConvertTool")).run({"ids": "X", "source": "a"})
    assert out["status"] == "error"


def test_convert_builds_route_and_returns_ids():
    body = {"ids": ["ENSG00000139618"], "results": ["P51587", "H0YD86"], "route": ["ensembl_gene", "uniprot"]}
    captured = {}

    def fake_get(url, params=None, **kw):
        captured["params"] = params
        return _resp(200, body)

    with patch("tooluniverse.togoid_tool.requests.get", side_effect=fake_get):
        out = TogoIDConvertTool(_cfg("TogoID_convert", "TogoIDConvertTool")).run(
            {"ids": "ENSG00000139618", "source": "ensembl_gene", "target": "uniprot"})
    assert out["status"] == "success"
    assert captured["params"]["route"] == "ensembl_gene,uniprot"
    assert out["data"]["converted_ids"] == ["P51587", "H0YD86"]
    assert out["data"]["target"] == "uniprot"


def test_convert_no_route_is_clean_error():
    with patch("tooluniverse.togoid_tool.requests.get",
               return_value=_resp(200, {"message": "no route: ncbigene <> chebi"})):
        out = TogoIDConvertTool(_cfg("TogoID_convert", "TogoIDConvertTool")).run(
            {"ids": "675", "source": "ncbigene", "target": "chebi"})
    assert out["status"] == "error"
    assert "no route" in out["error"]


_CFG = {
    "chebi": {"label": "ChEBI compound", "category": "Compound"},
    "pubchem_compound": {"label": "PubChem Compound", "category": "Compound"},
    "ensembl_gene": {"label": "Ensembl Gene", "category": "Gene"},
}


def test_list_datasets_all():
    with patch("tooluniverse.togoid_tool.requests.get", return_value=_resp(200, _CFG)):
        out = TogoIDDatasetsTool(_cfg("TogoID_list_datasets", "TogoIDDatasetsTool")).run({})
    assert out["status"] == "success"
    assert out["metadata"]["total"] == 3
    # sorted by category then dataset
    assert out["data"][0]["category"] == "Compound"


def test_list_datasets_filtered_by_category():
    with patch("tooluniverse.togoid_tool.requests.get", return_value=_resp(200, _CFG)):
        out = TogoIDDatasetsTool(_cfg("TogoID_list_datasets", "TogoIDDatasetsTool")).run({"category": "gene"})
    assert out["status"] == "success"
    assert out["metadata"]["total"] == 1
    assert out["data"][0]["dataset"] == "ensembl_gene"
