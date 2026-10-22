import json
from pathlib import Path

import pytest
from jsonschema import validate

from tooluniverse.empiar_tool import EMPIARTool


ROOT = Path(__file__).parents[2]
CONFIG = next(
    item
    for item in json.loads(
        (ROOT / "src/tooluniverse/data/empiar_tools.json").read_text()
    )
    if item["name"] == "EMPIAR_search_entries"
)


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "hitCount": 9,
            "entries": [
                {
                    "id": "EMPIAR-10004",
                    "fields": {
                        "title": ["Ribosome"],
                        "release_date": ["20140101"],
                    },
                },
                {
                    "id": "EMPIAR-10005",
                    "fields": {
                        "title": ["Another ribosome"],
                        "release_date": ["20140202"],
                    },
                },
            ],
        }


def test_empiar_reports_exact_continuation(monkeypatch):
    captured = {}
    tool = EMPIARTool(CONFIG)

    def fake_get(_url, **kwargs):
        captured.update(kwargs["params"])
        return _Response()

    monkeypatch.setattr(tool.session, "get", fake_get)
    result = tool.run({"query": "ribosome", "page_size": 2, "start": 3})

    assert captured["start"] == 3
    assert captured["size"] == 2
    assert result["metadata"] == {
        "total_hits": 9,
        "returned": 2,
        "start": 3,
        "page_size": 2,
        "has_more": True,
        "next_start": 5,
        "truncated": True,
        "result_set_complete": False,
    }
    validate(result["data"], CONFIG["return_schema"])


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"query": ""}, "query"),
        ({"query": "ribosome", "page_size": 0}, "page_size"),
        ({"query": "ribosome", "page_size": 101}, "page_size"),
        ({"query": "ribosome", "page_size": True}, "page_size"),
        ({"query": "ribosome", "page_size": "10"}, "page_size"),
        ({"query": "ribosome", "start": -1}, "start"),
        ({"query": "ribosome", "start": True}, "start"),
        ({"query": "ribosome", "start": "2"}, "start"),
    ],
)
def test_empiar_invalid_controls_fail_before_network(monkeypatch, arguments, parameter):
    tool = EMPIARTool(CONFIG)

    def fail(*_args, **_kwargs):
        raise AssertionError("network must not be called")

    monkeypatch.setattr(tool.session, "get", fail)
    result = tool.run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
