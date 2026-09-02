"""Fix-R27A-3: MARRVEL only indexes current approved HGNC symbols.

A retired symbol or an alias (RP20 / LCA2 -> RPE65) comes back as HTTP 200
with an empty body, which used to be reported as a bare empty success -- and
was therefore indistinguishable from "this gene does not exist". These tests
pin the HGNC previous-symbol/alias fallback, the disclosure of the
substitution, and the graceful degradation when HGNC is unreachable.

Network is fully mocked.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.marrvel_tool import MARRVELGeneTool, MARRVELOmimTool


def _resp(status=200, json_body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _cfg(name, typ):
    return {
        "name": name,
        "type": typ,
        "parameter": {"type": "object", "properties": {}},
    }


RPE65_GENE = {
    "symbol": "RPE65",
    "name": "retinoid isomerohydrolase RPE65",
    "entrezId": 6121,
    "xref": {"hgncId": 10294, "ensemblId": "ENSG00000116745"},
    "alias": ["LCA2", "rd12"],
    "prevSymbols": ["RP20"],
}
RPE65_OMIM = {
    "mimNumber": 180069,
    "phenotypes": [
        {
            "mimNumber": 180069,
            "phenotype": "Leber congenital amaurosis 2",
            "phenotypeMimNumber": 204100,
            "phenotypeInheritance": "Autosomal recessive",
            "phenotypicSeriesNumber": "PS204000",
        }
    ],
}


def _hgnc_body(*symbols):
    return {
        "response": {
            "numFound": len(symbols),
            "docs": [{"symbol": s, "hgnc_id": "HGNC:10294"} for s in symbols],
        }
    }


def _router(mapping, calls):
    """Dispatch mocked requests.get by URL substring."""

    def _get(url, **kwargs):
        calls.append(url)
        for needle, resp in mapping.items():
            if needle in url:
                # MagicMock is itself callable, so check for it explicitly;
                # plain callables are factories that may raise.
                return resp if isinstance(resp, MagicMock) else resp()
        raise AssertionError(f"unexpected URL: {url}")

    return _get


# ---- (a) an alias/previous symbol resolves and discloses the substitution ---
def test_gene_previous_symbol_resolves_and_discloses():
    calls = []
    get = _router(
        {
            "symbol/RP20": _resp(200, {}),  # 200 + empty body: the failure mode
            "rest.genenames.org": _resp(200, _hgnc_body("RPE65")),
            "symbol/RPE65": _resp(200, RPE65_GENE),
        },
        calls,
    )
    with patch("tooluniverse.marrvel_tool.requests.get", side_effect=get):
        out = MARRVELGeneTool(_cfg("MARRVEL_get_gene", "MARRVELGeneTool")).run(
            {"gene_symbol": "RP20"}
        )

    assert out["status"] == "success"
    assert out["data"]["symbol"] == "RPE65"
    meta = out["metadata"]
    assert meta["total_results"] == 1
    assert meta["query_symbol"] == "RP20"
    assert meta["resolved_symbol"] == "RPE65"
    # The disclosure must name BOTH symbols -- answering about a different gene
    # than the caller typed without saying so is its own failure mode.
    assert "RP20" in meta["resolved_note"] and "RPE65" in meta["resolved_note"]
    assert len(calls) == 3  # MARRVEL, HGNC, MARRVEL retry -- resolved once only


def test_gene_404_takes_the_same_resolution_path():
    calls = []
    get = _router(
        {
            "symbol/LCA2": _resp(404, None),
            "rest.genenames.org": _resp(200, _hgnc_body("RPE65")),
            "symbol/RPE65": _resp(200, RPE65_GENE),
        },
        calls,
    )
    with patch("tooluniverse.marrvel_tool.requests.get", side_effect=get):
        out = MARRVELGeneTool(_cfg("MARRVEL_get_gene", "MARRVELGeneTool")).run(
            {"symbol": "LCA2"}
        )
    assert out["data"]["symbol"] == "RPE65"
    assert out["metadata"]["resolved_symbol"] == "RPE65"


def test_omim_null_body_resolves_and_discloses():
    # The omim endpoint answers an unknown symbol with 200 + literal null.
    calls = []
    get = _router(
        {
            "symbol/RP20": _resp(200, None),
            "rest.genenames.org": _resp(200, _hgnc_body("RPE65")),
            "symbol/RPE65": _resp(200, RPE65_OMIM),
        },
        calls,
    )
    with patch("tooluniverse.marrvel_tool.requests.get", side_effect=get):
        out = MARRVELOmimTool(
            _cfg("MARRVEL_get_omim_phenotypes", "MARRVELOmimTool")
        ).run({"symbol": "RP20"})

    assert out["status"] == "success"
    assert out["metadata"]["total_results"] == 1
    assert out["data"][0]["phenotype"] == "Leber congenital amaurosis 2"
    assert out["metadata"]["query_symbol"] == "RP20"
    assert out["metadata"]["resolved_symbol"] == "RPE65"
    assert "RP20" in out["metadata"]["resolved_note"]


# ---- (b) HGNC resolves nothing -> empty success with an actionable note ----
@pytest.mark.parametrize(
    "tool_cls,name,typ,empty",
    [
        (MARRVELGeneTool, "MARRVEL_get_gene", "MARRVELGeneTool", {}),
        (MARRVELOmimTool, "MARRVEL_get_omim_phenotypes", "MARRVELOmimTool", []),
    ],
)
def test_unresolvable_symbol_gets_actionable_note(tool_cls, name, typ, empty):
    calls = []
    get = _router(
        {
            "api.marrvel.org": _resp(200, None),
            "rest.genenames.org": _resp(200, _hgnc_body()),
        },
        calls,
    )
    with patch("tooluniverse.marrvel_tool.requests.get", side_effect=get):
        out = tool_cls(_cfg(name, typ)).run({"symbol": "NOTAREALGENE123"})

    assert out["status"] == "success"
    assert out["data"] == empty
    meta = out["metadata"]
    assert meta["total_results"] == 0
    assert meta["query_symbol"] == "NOTAREALGENE123"
    assert "resolved_symbol" not in meta
    note = meta["note"]
    assert "NOTAREALGENE123" in note
    assert "approved HGNC symbols" in note
    assert len(calls) == 2  # no retry when nothing resolved


def test_ambiguous_alias_is_not_guessed():
    calls = []
    get = _router(
        {
            "api.marrvel.org": _resp(200, {}),
            "rest.genenames.org": _resp(200, _hgnc_body("GENEA", "GENEB")),
        },
        calls,
    )
    with patch("tooluniverse.marrvel_tool.requests.get", side_effect=get):
        out = MARRVELGeneTool(_cfg("MARRVEL_get_gene", "MARRVELGeneTool")).run(
            {"symbol": "AMBIG1"}
        )
    assert out["status"] == "success"
    assert out["data"] == {}
    assert "resolved_symbol" not in out["metadata"]
    assert "GENEA" in out["metadata"]["note"] and "GENEB" in out["metadata"]["note"]
    assert len(calls) == 2  # never retried against a guessed gene


# ---- (c) HGNC failures degrade gracefully, never raise ----
@pytest.mark.parametrize(
    "hgnc_outcome",
    [
        lambda: (_ for _ in ()).throw(requests.exceptions.Timeout()),
        lambda: (_ for _ in ()).throw(requests.exceptions.ConnectionError()),
        lambda: _resp(500, None),
        lambda: _resp(200, "not-json-shaped"),
    ],
)
def test_hgnc_failure_still_returns_empty_success(hgnc_outcome):
    calls = []
    get = _router(
        {"api.marrvel.org": _resp(200, {}), "rest.genenames.org": hgnc_outcome},
        calls,
    )
    with patch("tooluniverse.marrvel_tool.requests.get", side_effect=get):
        out = MARRVELGeneTool(_cfg("MARRVEL_get_gene", "MARRVELGeneTool")).run(
            {"symbol": "RP20"}
        )
    assert out["status"] == "success"  # a working call never becomes an error
    assert out["data"] == {}
    assert out["metadata"]["total_results"] == 0
    assert "note" in out["metadata"]


def test_hgnc_bad_json_body_degrades():
    calls = []
    bad = _resp(200, None)
    bad.json.side_effect = ValueError("no json")
    get = _router(
        {"api.marrvel.org": _resp(200, {}), "rest.genenames.org": bad}, calls
    )
    with patch("tooluniverse.marrvel_tool.requests.get", side_effect=get):
        out = MARRVELGeneTool(_cfg("MARRVEL_get_gene", "MARRVELGeneTool")).run(
            {"symbol": "RP20"}
        )
    assert out["status"] == "success"
    assert "HGNC" in out["metadata"]["note"]


def test_marrvel_retry_failure_does_not_become_an_error():
    calls = []
    get = _router(
        {
            "symbol/RP20": _resp(200, {}),
            "rest.genenames.org": _resp(200, _hgnc_body("RPE65")),
            "symbol/RPE65": lambda: (_ for _ in ()).throw(
                requests.exceptions.Timeout()
            ),
        },
        calls,
    )
    with patch("tooluniverse.marrvel_tool.requests.get", side_effect=get):
        out = MARRVELGeneTool(_cfg("MARRVEL_get_gene", "MARRVELGeneTool")).run(
            {"symbol": "RP20"}
        )
    assert out["status"] == "success"
    assert out["data"] == {}
    assert out["metadata"]["total_results"] == 0


# ---- (d) a symbol MARRVEL knows never touches HGNC ----
def test_known_symbol_never_calls_hgnc():
    calls = []
    get = _router({"api.marrvel.org": _resp(200, RPE65_GENE)}, calls)
    with patch("tooluniverse.marrvel_tool.requests.get", side_effect=get):
        out = MARRVELGeneTool(_cfg("MARRVEL_get_gene", "MARRVELGeneTool")).run(
            {"symbol": "RPE65"}
        )
    assert out["metadata"]["total_results"] == 1
    assert "resolved_symbol" not in out["metadata"]
    assert "resolved_note" not in out["metadata"]
    assert calls == [
        "http://api.marrvel.org/data/gene/taxonId/9606/symbol/RPE65"
    ]  # exactly one request


def test_known_symbol_never_calls_hgnc_omim():
    calls = []
    get = _router({"api.marrvel.org": _resp(200, RPE65_OMIM)}, calls)
    with patch("tooluniverse.marrvel_tool.requests.get", side_effect=get):
        out = MARRVELOmimTool(
            _cfg("MARRVEL_get_omim_phenotypes", "MARRVELOmimTool")
        ).run({"symbol": "RPE65"})
    assert out["metadata"]["total_results"] == 1
    assert "resolved_symbol" not in out["metadata"]
    assert calls == ["http://api.marrvel.org/data/omim/gene/symbol/RPE65"]


# ---- input hygiene: non symbol-shaped input never reaches HGNC's Solr query --
def test_query_shaped_input_is_not_sent_to_hgnc():
    calls = []
    get = _router({"api.marrvel.org": _resp(200, {})}, calls)
    with patch("tooluniverse.marrvel_tool.requests.get", side_effect=get):
        out = MARRVELGeneTool(_cfg("MARRVEL_get_gene", "MARRVELGeneTool")).run(
            {"symbol": "BRCA1 OR TP53"}
        )
    assert out["status"] == "success"
    assert len(calls) == 1
    assert "note" in out["metadata"]


def test_hgnc_uses_its_own_short_timeout():
    calls = []
    seen = {}

    def _get(url, **kwargs):
        calls.append(url)
        if "genenames" in url:
            seen["hgnc_timeout"] = kwargs.get("timeout")
            return _resp(200, _hgnc_body())
        return _resp(200, {})

    cfg = _cfg("MARRVEL_get_gene", "MARRVELGeneTool")
    cfg["fields"] = {"timeout": 30}
    with patch("tooluniverse.marrvel_tool.requests.get", side_effect=_get):
        MARRVELGeneTool(cfg).run({"symbol": "RP20"})
    assert seen["hgnc_timeout"] < 30
