"""Unit tests for discovery-round batch 9 (Pathoplexus/LAPIS). Network mocked."""

from unittest.mock import MagicMock, patch

from tooluniverse.pathoplexus_tool import PathoplexusCountTool, PathoplexusMutationsTool


def _resp(status=200, json_body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _cfg(name, typ):
    return {"name": name, "type": typ, "parameter": {"type": "object", "properties": {}}}


def test_count_requires_organism():
    out = PathoplexusCountTool(_cfg("Pathoplexus_count_sequences", "PathoplexusCountTool")).run({})
    assert out["status"] == "error"
    assert "organism" in out["error"]


def test_count_builds_filters_and_groupby_no_limit():
    body = {"data": [{"count": 15900, "geoLocCountry": "USA"}, {"count": 666, "geoLocCountry": "Greece"}]}
    captured = {}

    def fake_get(url, params=None, **kw):
        captured["url"] = url
        captured["params"] = params
        return _resp(200, body)

    with patch("tooluniverse.pathoplexus_tool.requests.get", side_effect=fake_get):
        out = PathoplexusCountTool(_cfg("Pathoplexus_count_sequences", "PathoplexusCountTool")).run(
            {"organism": "West-Nile", "country": "USA", "group_by": "geoLocCountry"})
    assert out["status"] == "success"
    assert captured["url"].endswith("/west-nile/sample/aggregated")  # organism lowercased
    assert captured["params"]["geoLocCountry"] == "USA"
    assert captured["params"]["fields"] == "geoLocCountry"
    assert "limit" not in captured["params"]  # aggregated rejects limit
    assert out["data"][0]["count"] == 15900


def test_count_http_400_is_clean_error():
    err = MagicMock()
    err.response.status_code = 400
    import requests
    with patch("tooluniverse.pathoplexus_tool.requests.get",
               side_effect=requests.exceptions.HTTPError(response=err.response)):
        out = PathoplexusCountTool(_cfg("Pathoplexus_count_sequences", "PathoplexusCountTool")).run(
            {"organism": "cchf", "group_by": "lineage"})
    assert out["status"] == "error"
    assert "400" in out["error"]


def test_mutations_requires_organism():
    out = PathoplexusMutationsTool(_cfg("Pathoplexus_get_mutations", "PathoplexusMutationsTool")).run({})
    assert out["status"] == "error"


def test_mutations_curates_and_selects_endpoint():
    body = {"data": [{"mutation": "env:V159A", "sequenceName": "env", "position": 159,
                      "mutationFrom": "V", "mutationTo": "A", "proportion": 0.95,
                      "count": 14413, "coverage": 15174}]}
    captured = {}

    def fake_get(url, params=None, **kw):
        captured["url"] = url
        captured["params"] = params
        return _resp(200, body)

    with patch("tooluniverse.pathoplexus_tool.requests.get", side_effect=fake_get):
        out = PathoplexusMutationsTool(_cfg("Pathoplexus_get_mutations", "PathoplexusMutationsTool")).run(
            {"organism": "west-nile", "min_proportion": 0.9, "mutation_type": "nucleotide"})
    assert out["status"] == "success"
    assert captured["url"].endswith("/nucleotideMutations")
    assert captured["params"]["minProportion"] == 0.9
    m = out["data"][0]
    assert m["mutation"] == "env:V159A"
    assert m["gene"] == "env"
    assert m["proportion"] == 0.95


def test_mutations_defaults_to_amino_acid():
    body = {"data": []}
    captured = {}

    def fake_get(url, params=None, **kw):
        captured["url"] = url
        return _resp(200, body)

    with patch("tooluniverse.pathoplexus_tool.requests.get", side_effect=fake_get):
        PathoplexusMutationsTool(_cfg("Pathoplexus_get_mutations", "PathoplexusMutationsTool")).run(
            {"organism": "mpox"})
    assert captured["url"].endswith("/aminoAcidMutations")
