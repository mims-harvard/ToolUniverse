import ast
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from jsonschema import validate

from tooluniverse.rnacentral_tool import RNAcentralGetTool


ROOT = Path(__file__).parents[2]
CONFIG = next(
    item
    for item in json.loads(
        (ROOT / "src/tooluniverse/data/rnacentral_tools.json").read_text()
    )
    if item["name"] == "RNAcentral_get_xrefs_and_pubs"
)


def test_subresources_have_independent_pages_and_completeness(monkeypatch):
    calls = {}

    def fake_get(url, **_kwargs):
        name = "xrefs" if "/xrefs/" in url else "publications"
        query = parse_qs(urlparse(url).query)
        calls[name] = query
        return {
            "count": 83 if name == "xrefs" else 348,
            "next": f"https://example/{name}/next",
            "previous": f"https://example/{name}/previous",
            "results": [{"kind": name}, {"kind": name}],
        }

    monkeypatch.setattr("tooluniverse.rnacentral_tool._http_get", fake_get)
    result = RNAcentralGetTool(CONFIG).run(
        {
            "accession": "URS000039ED8D",
            "page_size": 2,
            "xrefs_page": 3,
            "publications_page": 5,
        }
    )

    assert calls["xrefs"]["page"] == ["3"]
    assert calls["publications"]["page"] == ["5"]
    assert calls["xrefs"]["page_size"] == ["2"]
    assert result["data"]["xrefs"]["next_page"] == 4
    assert result["data"]["publications"]["next_page"] == 6
    assert result["data"]["xrefs"]["previous_page"] == 2
    assert result["data"]["publications"]["result_set_complete"] is False
    assert result["metadata"]["unique_pmids_not_guaranteed"] is True
    validate(result["data"], CONFIG["return_schema"])


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"page_size": 0}, "page_size"),
        ({"page_size": 51}, "page_size"),
        ({"page_size": True}, "page_size"),
        ({"page_size": "10"}, "page_size"),
        ({"xrefs_page": 0}, "xrefs_page"),
        ({"xrefs_page": True}, "xrefs_page"),
        ({"publications_page": -1}, "publications_page"),
        ({"publications_page": "2"}, "publications_page"),
    ],
)
def test_invalid_subresource_controls_fail_before_network(
    monkeypatch, arguments, parameter
):
    def fail(*_args, **_kwargs):
        raise AssertionError("network must not be called")

    monkeypatch.setattr("tooluniverse.rnacentral_tool._http_get", fail)
    result = RNAcentralGetTool(CONFIG).run(
        {"accession": "URS000039ED8D", **arguments}
    )
    assert result["status"] == "error"
    assert result["parameter"] == parameter


def test_generated_aggregator_wrapper_exposes_independent_pages():
    path = ROOT / "src/tooluniverse/tools/RNAcentral_get_xrefs_and_pubs.py"
    function = next(
        node for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef)
    )
    assert [ast.literal_eval(node) for node in function.args.defaults] == [10, 1, 1]
