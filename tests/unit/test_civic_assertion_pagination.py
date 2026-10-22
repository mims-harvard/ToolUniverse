import json
from pathlib import Path

from tooluniverse.civic_tool import CIViCTool


ROOT = Path(__file__).parents[2]
CONFIG = next(
    config for config in json.loads((ROOT / "src/tooluniverse/data/civic_tools.json").read_text())
    if config["name"] == "civic_search_assertions"
)


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {"data": {"assertions": {
            "totalCount": 286,
            "nodes": [{"id": 4, "description": "x", "status": "ACCEPTED"}],
            "pageInfo": {"hasNextPage": True, "endCursor": "cursor-4"},
        }}}


def test_assertions_publish_cursor_and_total(monkeypatch):
    captured = {}
    def fake_post(_url, **kwargs):
        captured.update(kwargs["json"]["variables"])
        return _Response()
    monkeypatch.setattr("tooluniverse.civic_tool.requests.post", fake_post)
    out = CIViCTool(CONFIG).run({"limit": 1, "after": "cursor-3"})
    assert captured["after"] == "cursor-3"
    assert out["metadata"]["total_results"] == 286
    assert out["metadata"]["returned"] == 1
    assert out["metadata"]["has_more"] is True
    assert out["metadata"]["next_cursor"] == "cursor-4"
