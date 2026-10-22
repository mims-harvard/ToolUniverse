from unittest.mock import Mock

import pytest

from tooluniverse.pubchem_tox_tool import PubChemToxTool


def _payload(heading, count, prefix="value"):
    return {
        "Record": {
            "RecordTitle": "Test compound",
            "Section": [
                {
                    "TOCHeading": heading,
                    "Information": [
                        {
                            "Name": heading,
                            "Value": {
                                "StringWithMarkup": [
                                    {"String": f"{prefix}-{index}"}
                                ]
                            },
                        }
                        for index in range(count)
                    ],
                }
            ],
        }
    }


@pytest.mark.parametrize(
    ("endpoint", "method_name", "heading", "result_key", "count_key"),
    [
        (
            "toxicity_values",
            "_get_toxicity_values",
            "Non-Human Toxicity Values",
            "toxicity_values",
            "toxicity_values_count",
        ),
        (
            "ecotoxicity_values",
            "_get_ecotoxicity_values",
            "Ecotoxicity Values",
            "ecotoxicity_values",
            "ecotoxicity_values_count",
        ),
        (
            "human_toxicity_values",
            "_get_human_toxicity_values",
            "Human Toxicity Values",
            "human_toxicity_values",
            "human_toxicity_values_count",
        ),
    ],
)
def test_toxicity_value_endpoints_support_offset(
    endpoint, method_name, heading, result_key, count_key
):
    tool = PubChemToxTool({"fields": {"endpoint": endpoint}})
    tool._resolve_cid = Mock(return_value=241)
    tool._get_pugview_data = Mock(return_value=_payload(heading, 7))

    result = getattr(tool, method_name)({"cid": 241, "limit": 3, "offset": 3})

    assert result["data"][result_key] == ["value-3", "value-4", "value-5"]
    assert result["data"][count_key] == 7
    assert result["metadata"]["total_results"] == 7
    assert result["metadata"]["next_offset"] == 6


def test_acute_effects_support_adjacent_and_tail_pages():
    tool = PubChemToxTool({"fields": {"endpoint": "acute_effects"}})
    tool._resolve_cid = Mock(return_value=241)
    counts = {"Signs and Symptoms": 8, "Acute Effects": 8, "Exposure Routes": 7}
    tool._get_pugview_data = Mock(
        side_effect=lambda _cid, heading: _payload(
            heading, counts[heading], prefix=heading
        )
    )

    first = tool._get_acute_effects({"cid": 241, "limit": 3})
    second = tool._get_acute_effects({"cid": 241, "limit": 3, "offset": 3})
    tail = tool._get_acute_effects({"cid": 241, "limit": 3, "offset": 21})

    assert first["data"]["acute_effects"] != second["data"]["acute_effects"]
    assert first["metadata"]["total_results"] == 23
    assert first["metadata"]["next_offset"] == 3
    assert len(tail["data"]["acute_effects"]) == 2
    assert tail["metadata"]["has_more"] is False
    assert tail["metadata"]["next_offset"] is None


def test_invalid_pagination_is_explicit_error():
    tool = PubChemToxTool({"fields": {"endpoint": "toxicity_values"}})
    tool._resolve_cid = Mock(return_value=241)
    tool._get_pugview_data = Mock(
        return_value=_payload("Non-Human Toxicity Values", 1)
    )

    result = tool.run({"cid": 241, "offset": -1})

    assert result == {
        "status": "error",
        "error": "offset must be a non-negative integer",
    }
