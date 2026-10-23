from unittest.mock import MagicMock, patch

from tooluniverse.epmc_annotations_tool import EPMCAnnotationsTool


def _tool(operation):
    return EPMCAnnotationsTool(
        {"name": f"EPMC_{operation}", "fields": {"operation": operation}}
    )


def _response(annotations):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = [{"pmcid": "PMC5500808", "annotations": annotations}]
    return response


def _annotations(entity_type, count):
    return [
        {
            "type": entity_type,
            "exact": f"Entity {i}",
            "tags": [{"name": f"Entity {i}", "uri": f"urn:test:{i}"}],
        }
        for i in range(count)
    ]


@patch("tooluniverse.epmc_annotations_tool.requests.get")
def test_all_unique_entities_are_preserved(mock_get):
    annotations = _annotations("Gene_Proteins", 76) + _annotations("Diseases", 39)
    mock_get.return_value = _response(annotations)

    data = _tool("get_annotations").run({"pmcid": "PMC5500808"})["data"]

    assert data["annotation_counts"]["Gene_Proteins"] == 76
    assert len(data["annotations"]["Gene_Proteins"]) == 76
    assert data["annotation_counts"]["Diseases"] == 39
    assert len(data["annotations"]["Diseases"]) == 39


@patch("tooluniverse.epmc_annotations_tool.requests.get")
def test_entity_specific_total_is_not_capped(mock_get):
    mock_get.return_value = _response(_annotations("Gene_Proteins", 76))

    data = _tool("get_genes").run({"pmcid": "PMC5500808"})["data"]

    assert data["total_entities"] == 76
    assert data["returned_entities"] == 76
    assert len(data["annotations"]) == 76
