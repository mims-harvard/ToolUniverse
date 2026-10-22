import json
from pathlib import Path

from jsonschema import validate

from tooluniverse.plant_reactome_tool import PlantReactomeTool


ROOT = Path(__file__).parents[2]
CONFIG = next(
    config
    for config in json.loads(
        (ROOT / "src/tooluniverse/data/plant_reactome_tools.json").read_text()
    )
    if config["name"] == "PlantReactome_search_pathways"
)


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "numberOfMatches": 215,
            "numberOfGroups": 1,
            "rowCount": 2,
            "results": [
                {
                    "entries": [
                        {"stId": "R-OSA-1", "name": "<b>Metabolism</b> one"},
                        {"stId": "R-OSA-2", "name": "Metabolism two"},
                    ]
                }
            ],
        }


def test_search_exposes_upstream_hard_truncation(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.plant_reactome_tool.requests.get",
        lambda *_args, **_kwargs: _Response(),
    )
    out = PlantReactomeTool(CONFIG).run({"query": "metabolism"})
    metadata = out["metadata"]
    assert metadata["total_results"] == 215
    assert metadata["returned"] == 2
    assert metadata["upstream_row_count"] == 2
    assert metadata["upstream_truncated"] is True
    assert metadata["unreachable_results"] == 213
    assert metadata["pagination_supported"] is False
    assert metadata["result_set_complete"] is False
    validate(out["data"], CONFIG["return_schema"])
