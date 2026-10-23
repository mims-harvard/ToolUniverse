import ast
import json
from pathlib import Path

import pytest
from jsonschema import validate

from tooluniverse.neuromorpho_tool import NeuroMorphoTool


ROOT = Path(__file__).parents[2]
CONFIGS = {
    item["name"]: item
    for item in json.loads(
        (ROOT / "src/tooluniverse/data/neuromorpho_tools.json").read_text()
    )
}


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


@pytest.mark.parametrize(
    "name,arguments,embedded_key,rows",
    [
        (
            "NeuroMorpho_search_neurons",
            {"query_value": "human"},
            "neuronResources",
            [{"neuron_id": 3}, {"neuron_id": 4}],
        ),
        (
            "NeuroMorpho_search_literature",
            {"query_value": "hippocampus"},
            "publicationResources",
            [{"article_id": "3"}, {"article_id": "4"}],
        ),
    ],
)
def test_search_pages_expose_exact_continuation(
    monkeypatch, name, arguments, embedded_key, rows
):
    captured = {}

    def fake_get(_url, **kwargs):
        captured.update(kwargs["params"])
        return _Response(
            {
                "_embedded": {embedded_key: rows},
                "page": {
                    "totalElements": 12,
                    "totalPages": 6,
                    "number": 2,
                    "size": 2,
                },
            }
        )

    monkeypatch.setattr("tooluniverse.neuromorpho_tool.requests.get", fake_get)
    result = NeuroMorphoTool(CONFIGS[name]).run({**arguments, "page": 2, "size": 2})
    assert captured["page"] == 2
    assert captured["size"] == 2
    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["truncated"] is True
    validate(result["data"], CONFIGS[name]["return_schema"])


def test_field_values_expose_continuation(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.neuromorpho_tool.requests.get",
        lambda *_args, **_kwargs: _Response(
            {
                "fields": ["human", "mouse"],
                "page": {
                    "totalElements": 7,
                    "totalPages": 4,
                    "number": 1,
                    "size": 2,
                },
            }
        ),
    )
    name = "NeuroMorpho_get_field_values"
    result = NeuroMorphoTool(CONFIGS[name]).run(
        {"field_name": "species", "page": 1, "size": 2}
    )
    assert result["metadata"]["next_page"] == 2
    assert result["metadata"]["has_more"] is True
    validate(result["data"], CONFIGS[name]["return_schema"])


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"query_value": "human", "page": -1}, "page"),
        ({"query_value": "human", "page": True}, "page"),
        ({"query_value": "human", "page": "1"}, "page"),
        ({"query_value": "human", "size": 0}, "size"),
        ({"query_value": "human", "size": 501}, "size"),
        ({"query_value": "human", "size": True}, "size"),
        ({"query_value": "human", "size": "20"}, "size"),
    ],
)
def test_invalid_page_controls_fail_before_network(monkeypatch, arguments, parameter):
    monkeypatch.setattr(
        "tooluniverse.neuromorpho_tool.requests.get",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )
    result = NeuroMorphoTool(CONFIGS["NeuroMorpho_search_neurons"]).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter


@pytest.mark.parametrize(
    "arguments,missing",
    [
        ({"filter_field": "cell_type"}, "filter_value"),
        ({"filter_value": "pyramidal"}, "filter_field"),
    ],
)
def test_incomplete_filter_pair_is_not_silently_ignored(
    monkeypatch, arguments, missing
):
    monkeypatch.setattr(
        "tooluniverse.neuromorpho_tool.requests.get",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )
    result = NeuroMorphoTool(CONFIGS["NeuroMorpho_search_neurons"]).run(
        {"query_value": "rat", **arguments}
    )
    assert result["status"] == "error"
    assert result["parameter"] == missing


def test_generated_literature_wrapper_has_concrete_pagination_defaults():
    path = ROOT / "src/tooluniverse/tools/NeuroMorpho_search_literature.py"
    function = next(
        node
        for node in ast.parse(path.read_text()).body
        if isinstance(node, ast.FunctionDef)
    )
    assert [ast.literal_eval(node) for node in function.args.defaults] == [
        "brainRegion",
        0,
        20,
    ]
