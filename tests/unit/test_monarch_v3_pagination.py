import ast
import json
from pathlib import Path

import pytest
from jsonschema import validate

from tooluniverse.monarch_v3_tool import MonarchV3Tool


ROOT = Path(__file__).parents[2]


def _configs(filename):
    return json.loads((ROOT / "src/tooluniverse/data" / filename).read_text())


def _config(filename, name):
    return next(config for config in _configs(filename) if config["name"] == name)


class _Response:
    def __init__(self, items):
        self.items = items

    def raise_for_status(self):
        return None

    def json(self):
        return {"limit": 2, "offset": 4, "total": 19, "items": self.items}


@pytest.mark.parametrize(
    "filename,name,arguments,items",
    [
        (
            "monarch_v3_tools.json",
            "MonarchV3_search",
            {"query": "seizure", "limit": 2, "offset": 4},
            [{"id": "HP:1"}, {"id": "HP:2"}],
        ),
        (
            "monarch_v3_tools.json",
            "MonarchV3_get_associations",
            {
                "subject": "HGNC:11998",
                "category": "biolink:Association",
                "limit": 2,
                "offset": 4,
            },
            [{"subject": "HGNC:11998", "object": "MONDO:1"}, {"subject": "HGNC:11998", "object": "MONDO:2"}],
        ),
    ],
)
def test_monarch_forwards_offset_and_exposes_continuation(
    monkeypatch, filename, name, arguments, items
):
    captured = {}

    def fake_get(_url, **kwargs):
        captured.update(kwargs["params"])
        return _Response(items)

    monkeypatch.setattr("tooluniverse.monarch_v3_tool.requests.get", fake_get)
    config = _config(filename, name)
    out = MonarchV3Tool(config).run(arguments)
    assert captured["limit"] == 2
    assert captured["offset"] == 4
    assert out["metadata"]["total_results"] == 19
    assert out["metadata"]["total_results_is_exact"] is True
    assert out["metadata"]["has_more"] is True
    assert out["metadata"]["next_offset"] == 6
    assert out["metadata"]["truncated"] is True
    assert out["metadata"]["result_set_complete"] is False
    validate(out["data"], config["return_schema"])


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"query": "seizure", "limit": 0}, "limit"),
        ({"query": "seizure", "limit": 51}, "limit"),
        ({"query": "seizure", "limit": True}, "limit"),
        ({"query": "seizure", "limit": "3"}, "limit"),
        ({"query": "seizure", "offset": -1}, "offset"),
        ({"query": "seizure", "offset": True}, "offset"),
        ({"query": "seizure", "offset": "3"}, "offset"),
    ],
)
def test_invalid_search_pagination_fails_before_network(
    monkeypatch, arguments, parameter
):
    monkeypatch.setattr(
        "tooluniverse.monarch_v3_tool.requests.get",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )
    config = _config("monarch_v3_tools.json", "MonarchV3_search")
    out = MonarchV3Tool(config).run(arguments)
    assert out["status"] == "error"
    assert out["parameter"] == parameter


@pytest.mark.parametrize(
    "name,defaults",
    [
        ("MonarchV3_get_associations", [20, 0]),
        ("Monarch_get_associations", [None, None, None, 20, 0]),
        ("MonarchV3_search", [None, 10, None, None, 0]),
        ("Monarch_search", [None, 10, 0]),
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
    # Pair each default with its argument name.  Positional comparison broke
    # whenever a JSON property was reordered, even though the exposed defaults
    # were unchanged.
    arguments = [argument.arg for argument in function.args.args]
    literals = [ast.literal_eval(node) for node in function.args.defaults]
    actual = dict(zip(arguments[len(arguments) - len(literals):], literals))
    assert sorted(actual.values(), key=repr) == sorted(defaults, key=repr)


@pytest.mark.parametrize(
    "filename,name,arguments,items,total_key",
    [
        (
            "mondo_tools.json",
            "Mondo_search_disease",
            {"query": "diabetes", "limit": 2, "offset": 4},
            [{"id": "MONDO:1"}, {"id": "MONDO:2"}],
            None,
        ),
        (
            "mondo_tools.json",
            "Mondo_get_disease_phenotypes",
            {"disease_id": "MONDO:0004975", "limit": 2, "offset": 4},
            [{"object": "HP:1"}, {"object": "HP:2"}],
            "total_phenotypes",
        ),
        (
            "monarch_v3_tools.json",
            "MonarchV3_get_mappings",
            {"entity_id": "MONDO:0005148", "limit": 2, "offset": 4},
            [{"object_id": "OMIM:1"}, {"object_id": "MESH:1"}],
            "total_mappings",
        ),
    ],
)
def test_related_endpoints_forward_offset(
    monkeypatch, filename, name, arguments, items, total_key
):
    captured = {}

    def fake_get(_url, **kwargs):
        captured.update(kwargs["params"])
        return _Response(items)

    monkeypatch.setattr("tooluniverse.monarch_v3_tool.requests.get", fake_get)
    config = _config(filename, name)
    out = MonarchV3Tool(config).run(arguments)
    assert captured["offset"] == 4
    assert out["metadata"]["total_results"] == 19
    assert out["metadata"]["next_offset"] == 6
    if total_key:
        assert out["metadata"][total_key] == 19
    validate(out["data"], config["return_schema"])


@pytest.mark.parametrize(
    "name,defaults",
    [
        ("Mondo_search_disease", [10, 0]),
        ("Mondo_get_disease_phenotypes", [20, 0]),
        ("MonarchV3_get_mappings", [20, 0]),
    ],
)
def test_related_generated_wrapper_defaults(name, defaults):
    function = next(
        node
        for node in ast.parse(
            (ROOT / "src/tooluniverse/tools" / f"{name}.py").read_text()
        ).body
        if isinstance(node, ast.FunctionDef)
    )
    assert [ast.literal_eval(node) for node in function.args.defaults] == defaults
