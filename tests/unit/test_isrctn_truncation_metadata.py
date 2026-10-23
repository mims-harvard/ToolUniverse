import ast
import json
from pathlib import Path

import pytest

from tooluniverse.isrctn_tool import ISRCTNSearchTool


ROOT = Path(__file__).parents[2]
CONFIGS = json.loads((ROOT / "src/tooluniverse/data/isrctn_tools.json").read_text())


def _config(name):
    return next(config for config in CONFIGS if config["name"] == name)


XML = """<root xmlns="http://www.67bricks.com/isrctn" totalCount="4300">
  <fullTrial><trial><isrctn>1</isrctn><trialDescription><title>One</title></trialDescription></trial></fullTrial>
  <fullTrial><trial><isrctn>2</isrctn><trialDescription><title>Two</title></trialDescription></trial></fullTrial>
  <fullTrial><trial><isrctn>3</isrctn><trialDescription><title>Three</title></trialDescription></trial></fullTrial>
</root>"""


@pytest.mark.parametrize(
    "name", ["ISRCTN_search_trials", "ISRCTN_search_trials_fielded"]
)
def test_large_result_set_exposes_unreachable_upstream_matches(monkeypatch, name):
    monkeypatch.setattr(ISRCTNSearchTool, "_query", lambda _self, _params: XML)
    out = ISRCTNSearchTool(_config(name)).run({"query": "diabetes", "limit": 3})
    metadata = out["metadata"]
    assert metadata["total_available"] == "4300"
    assert metadata["total_available_count"] == 4300
    assert metadata["returned"] == 3
    assert metadata["recommended_limit"] == 100
    assert metadata["upstream_truncated"] is True
    assert metadata["unreachable_results"] == 4200
    assert metadata["all_results_reachable"] is False
    assert metadata["pagination_supported"] is False
    assert metadata["result_set_complete"] is False


@pytest.mark.parametrize("limit", [0, 101, True, "10"])
def test_invalid_limit_fails_before_network(monkeypatch, limit):
    monkeypatch.setattr(
        ISRCTNSearchTool,
        "_query",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )
    out = ISRCTNSearchTool(_config("ISRCTN_search_trials")).run(
        {"query": "diabetes", "limit": limit}
    )
    assert out["status"] == "error"
    assert out["parameter"] == "limit"


@pytest.mark.parametrize(
    "name,defaults",
    [
        ("ISRCTN_search_trials", [10]),
        ("ISRCTN_search_trials_fielded", [None] * 10 + [10]),
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
