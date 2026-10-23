import ast
import json
from pathlib import Path

import pytest
from jsonschema import validate

from tooluniverse.npatlas_tool import NPAtlasSearchTool


ROOT = Path(__file__).parents[2]
CONFIG = json.loads((ROOT / "src/tooluniverse/data/npatlas_tools.json").read_text())[0]


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return [{"npaid": "NPA4"}, {"npaid": "NPA5"}, {"npaid": "LOOKAHEAD"}]


def test_search_forwards_skip_and_uses_lookahead(monkeypatch):
    captured = {}

    def fake_post(_url, **kwargs):
        captured.update(kwargs["params"])
        return _Response()

    monkeypatch.setattr("tooluniverse.npatlas_tool.requests.post", fake_post)
    out = NPAtlasSearchTool(CONFIG).run({"name": "acid", "limit": 2, "skip": 3})
    assert captured["skip"] == 3
    assert captured["limit"] == 3
    assert [item["npaid"] for item in out["data"]] == ["NPA4", "NPA5"]
    assert out["metadata"]["has_more"] is True
    assert out["metadata"]["next_skip"] == 5
    assert out["metadata"]["total_results"] is None
    assert out["metadata"]["matches_lower_bound"] == 6
    validate(out["data"], CONFIG["return_schema"])


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"name": "acid", "limit": 0}, "limit"),
        ({"name": "acid", "limit": 101}, "limit"),
        ({"name": "acid", "limit": True}, "limit"),
        ({"name": "acid", "skip": -1}, "skip"),
        ({"name": "acid", "skip": True}, "skip"),
        ({"name": "acid", "skip": "3"}, "skip"),
    ],
)
def test_invalid_controls_fail_before_network(monkeypatch, arguments, parameter):
    monkeypatch.setattr(
        "tooluniverse.npatlas_tool.requests.post",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )
    out = NPAtlasSearchTool(CONFIG).run(arguments)
    assert out["status"] == "error"
    assert out["parameter"] == parameter


def test_generated_wrapper_defaults():
    function = next(
        node
        for node in ast.parse(
            (ROOT / "src/tooluniverse/tools/NPAtlas_search_compounds.py").read_text()
        ).body
        if isinstance(node, ast.FunctionDef)
    )
    assert [ast.literal_eval(node) for node in function.args.defaults] == [
        None,
        None,
        None,
        None,
        10,
        0,
    ]
