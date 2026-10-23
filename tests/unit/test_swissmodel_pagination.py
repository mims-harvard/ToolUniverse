from unittest.mock import MagicMock, patch

from tooluniverse.swissmodel_tool import SwissModelTool


def test_models_are_recoverable_after_first_thirty():
    structures = [
        {"template": f"template-{i}", "in_complex_with": {"A": []}} for i in range(316)
    ]
    response = MagicMock()
    response.json.return_value = {
        "result": {"sequence_length": 393, "structures": structures}
    }
    tool = SwissModelTool(
        {"name": "SwissModel_get_models", "fields": {"endpoint_type": "get_models"}}
    )

    with patch("tooluniverse.swissmodel_tool.requests.get", return_value=response):
        result = tool.run({"uniprot_id": "P04637", "limit": 3, "offset": 30})

    data = result["data"]
    assert data["model_count"] == 3
    assert data["total_models"] == 316
    assert data["returned"] == 3
    assert data["has_more"] is True
    assert data["next_offset"] == 33
    assert [model["template"] for model in data["models"]] == [
        "template-30",
        "template-31",
        "template-32",
    ]


def test_batch_models_are_recoverable_after_first_thirty():
    structures = [
        {"template": f"template-{i}", "in_complex_with": {"A": []}} for i in range(316)
    ]
    response = MagicMock()
    response.json.return_value = {
        "resultset": [
            {
                "uniprot_entries": [{"ac": "P04637"}],
                "sequence_length": 393,
                "structures": structures,
            }
        ]
    }
    tool = SwissModelTool(
        {
            "name": "SwissModel_get_models_batch",
            "fields": {"endpoint_type": "get_models_batch"},
        }
    )

    with patch("tooluniverse.swissmodel_tool.requests.get", return_value=response):
        result = tool.run(
            {"uniprot_ids": ["P04637"], "model_limit": 3, "model_offset": 30}
        )

    item = result["data"]["results"][0]
    assert item["model_count"] == 316
    assert item["models_returned"] == 3
    assert item["has_more"] is True
    assert item["next_model_offset"] == 33
    assert [model["template"] for model in item["models"]] == [
        "template-30",
        "template-31",
        "template-32",
    ]
