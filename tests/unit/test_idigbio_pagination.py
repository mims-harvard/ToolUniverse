import ast
import json
from pathlib import Path

import pytest
from jsonschema import validate

from tooluniverse.idigbio_tool import iDigBioSearchTool


ROOT = Path(__file__).parents[2]
CONFIGS = json.loads((ROOT / "src/tooluniverse/data/idigbio_tools.json").read_text())


def _config(name):
    return next(config for config in CONFIGS if config["name"] == name)


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "itemCount": 23,
            "items": [
                {"uuid": "item-5", "indexTerms": {"genus": "quercus"}},
                {"uuid": "item-6", "indexTerms": {"genus": "quercus"}},
            ],
        }


@pytest.mark.parametrize("name", ["iDigBio_search_records", "iDigBio_search_media"])
def test_search_forwards_offset_and_exposes_continuation(monkeypatch, name):
    captured = {}

    def fake_get(_url, **kwargs):
        captured.update(kwargs["params"])
        return _Response()

    monkeypatch.setattr("tooluniverse.idigbio_tool.requests.get", fake_get)
    out = iDigBioSearchTool(_config(name)).run(
        {"genus": "Quercus", "limit": 2, "offset": 5}
    )
    assert captured["limit"] == 2
    assert captured["offset"] == 5
    assert out["metadata"] == {
        "total_available": 23,
        "total_available_is_exact": True,
        "returned": 2,
        "limit": 2,
        "offset": 5,
        "has_more": True,
        "next_offset": 7,
        "truncated": True,
        "result_set_complete": False,
        "query": {"genus": "Quercus"},
        "source": "iDigBio",
    }
    validate(out["data"], _config(name)["return_schema"])


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"genus": "Quercus", "limit": 0}, "limit"),
        ({"genus": "Quercus", "limit": 101}, "limit"),
        ({"genus": "Quercus", "limit": True}, "limit"),
        ({"genus": "Quercus", "limit": "3"}, "limit"),
        ({"genus": "Quercus", "offset": -1}, "offset"),
        ({"genus": "Quercus", "offset": True}, "offset"),
        ({"genus": "Quercus", "offset": "3"}, "offset"),
    ],
)
def test_invalid_pagination_fails_before_network(monkeypatch, arguments, parameter):
    monkeypatch.setattr(
        "tooluniverse.idigbio_tool.requests.get",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )
    out = iDigBioSearchTool(_config("iDigBio_search_records")).run(arguments)
    assert out["status"] == "error"
    assert out["parameter"] == parameter


@pytest.mark.parametrize(
    "name,expected",
    [
        ("iDigBio_search_records", [None] * 11 + [10, 0]),
        ("iDigBio_search_media", [None] * 11 + [10, 0]),
    ],
)
def test_generated_wrappers_match_pagination_defaults(name, expected):
    path = ROOT / "src/tooluniverse/tools" / f"{name}.py"
    function = next(
        node
        for node in ast.parse(path.read_text()).body
        if isinstance(node, ast.FunctionDef)
    )
    assert [ast.literal_eval(node) for node in function.args.defaults] == expected
