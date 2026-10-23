import ast
import json
from pathlib import Path

import pytest
from jsonschema import validate

from tooluniverse.allen_cell_types_tool import AllenCellTypesSpecimensTool


ROOT = Path(__file__).parents[2]
CONFIG = json.loads(
    (ROOT / "src/tooluniverse/data/allen_cell_types_tools.json").read_text()
)[0]


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "success": True,
            "total_rows": 2333,
            "num_rows": 2,
            "start_row": 2,
            "msg": [
                {
                    "specimen__id": 3,
                    "specimen__name": "cell-3",
                    "donor__species": "Homo Sapiens",
                },
                {
                    "specimen__id": 4,
                    "specimen__name": "cell-4",
                    "donor__species": "Homo Sapiens",
                },
            ],
        }


def test_allen_cell_types_forwards_start_and_exposes_continuation(monkeypatch):
    captured = {}

    def fake_get(_url, **kwargs):
        captured.update(kwargs["params"])
        return _Response()

    monkeypatch.setattr("tooluniverse.allen_cell_types_tool.requests.get", fake_get)
    result = AllenCellTypesSpecimensTool(CONFIG).run(
        {"species": "Homo Sapiens", "limit": 2, "start_row": 2}
    )
    assert captured["num_rows"] == 2
    assert captured["start_row"] == 2
    assert result["metadata"]["total_available"] == 2333
    assert result["metadata"]["next_start_row"] == 4
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["truncated"] is True
    assert [row["specimen_id"] for row in result["data"]] == [3, 4]
    assert [row["specimen_name"] for row in result["data"]] == ["cell-3", "cell-4"]
    validate(result["data"], CONFIG["return_schema"])


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"limit": 0}, "limit"),
        ({"limit": 2001}, "limit"),
        ({"limit": True}, "limit"),
        ({"limit": "20"}, "limit"),
        ({"start_row": -1}, "start_row"),
        ({"start_row": True}, "start_row"),
        ({"start_row": "2"}, "start_row"),
        ({"species": 9606}, "species"),
        ({"structure": 123}, "structure"),
    ],
)
def test_invalid_controls_fail_before_network(monkeypatch, arguments, parameter):
    monkeypatch.setattr(
        "tooluniverse.allen_cell_types_tool.requests.get",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )
    result = AllenCellTypesSpecimensTool(CONFIG).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter


def test_generated_wrapper_publishes_start_row():
    path = ROOT / "src/tooluniverse/tools/AllenCellTypes_search_specimens.py"
    function = next(
        node
        for node in ast.parse(path.read_text()).body
        if isinstance(node, ast.FunctionDef)
    )
    assert [ast.literal_eval(node) for node in function.args.defaults] == [
        None,
        None,
        20,
        0,
    ]
