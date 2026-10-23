import ast
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from jsonschema import validate

from tooluniverse.impc_tool import IMPCTool


ROOT = Path(__file__).parents[2]
CONFIGS = json.loads((ROOT / "src/tooluniverse/data/impc_tools.json").read_text())


def _config(name):
    return next(config for config in CONFIGS if config["name"] == name)


def _response(docs):
    response = MagicMock()
    response.json.return_value = {"response": {"numFound": 17, "docs": docs}}
    return response


@pytest.mark.parametrize(
    "name,arguments,docs,list_key",
    [
        (
            "IMPC_search_genes",
            {"query": "App", "limit": 2, "offset": 4},
            [{"mgi_accession_id": "MGI:1"}, {"mgi_accession_id": "MGI:2"}],
            "genes",
        ),
        (
            "IMPC_get_phenotypes_by_gene",
            {"gene_symbol": "App", "limit": 2, "offset": 4},
            [
                {"marker_symbol": "App", "mp_term_id": "MP:1", "mp_term_name": "one"},
                {"marker_symbol": "App", "mp_term_id": "MP:2", "mp_term_name": "two"},
            ],
            "phenotypes",
        ),
        (
            "IMPC_get_gene_phenotype_hits",
            {"gene_symbol": "App", "limit": 2, "offset": 4},
            [{"parameter_name": "one"}, {"parameter_name": "two"}],
            "hits",
        ),
    ],
)
def test_impc_forwards_start_and_exposes_continuation(
    monkeypatch, name, arguments, docs, list_key
):
    captured = {}

    def fake_get(_url, **kwargs):
        captured.update(kwargs["params"])
        return _response(docs)

    monkeypatch.setattr("tooluniverse.impc_tool.requests.get", fake_get)
    config = _config(name)
    out = IMPCTool(config).run(arguments)
    assert out["status"] == "success"
    assert captured["rows"] == 2
    assert captured["start"] == 4
    data = out["data"]
    assert data["limit"] == 2
    assert data["offset"] == 4
    assert data["has_more"] is True
    assert data["next_offset"] == 6
    assert len(data[list_key]) == 2
    validate(data, config["return_schema"])


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"query": "App", "limit": 0}, "limit"),
        ({"query": "App", "limit": 101}, "limit"),
        ({"query": "App", "limit": True}, "limit"),
        ({"query": "App", "limit": "2"}, "limit"),
        ({"query": "App", "offset": -1}, "offset"),
        ({"query": "App", "offset": True}, "offset"),
        ({"query": "App", "offset": "2"}, "offset"),
    ],
)
def test_invalid_search_controls_fail_before_network(monkeypatch, arguments, parameter):
    monkeypatch.setattr(
        "tooluniverse.impc_tool.requests.get",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )
    out = IMPCTool(_config("IMPC_search_genes")).run(arguments)
    assert out["status"] == "error"
    assert out["parameter"] == parameter


@pytest.mark.parametrize(
    "name,defaults",
    [
        ("IMPC_get_phenotypes_by_gene", [None, None, 100, 0]),
        ("IMPC_search_genes", [20, 0]),
        ("IMPC_get_gene_phenotype_hits", [None, None, True, 100, 0]),
    ],
)
def test_generated_wrapper_defaults(name, defaults):
    function = next(
        node
        for node in ast.parse(
            (ROOT / "src/tooluniverse/tools" / f"{name}.py").read_text()
        ).body
        if isinstance(node, ast.FunctionDef)
    )
    assert [ast.literal_eval(node) for node in function.args.defaults] == defaults
