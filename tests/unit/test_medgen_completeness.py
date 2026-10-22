from unittest.mock import MagicMock, patch

from tooluniverse.medgen_tool import MedGenTool


def _tool(operation):
    return MedGenTool(
        {"name": f"MedGen_{operation}", "fields": {"operation": operation}}
    )


def test_search_forwards_retstart_and_exposes_continuation():
    search_response = MagicMock()
    search_response.json.return_value = {
        "esearchresult": {"idlist": ["4", "5", "6"], "count": "100"}
    }
    summary_response = MagicMock()
    summary_response.json.return_value = {
        "result": {
            str(i): {"title": f"Condition {i}", "conceptmeta": ""}
            for i in (4, 5, 6)
        }
    }
    tool = _tool("search")

    with patch.object(
        tool, "_ncbi_get", side_effect=[search_response, summary_response]
    ) as get:
        result = tool.run({"query": "cancer", "max_results": 3, "start": 3})

    assert get.call_args_list[0].args[1]["retstart"] == 3
    assert result["data"]["total_count"] == 100
    assert result["data"]["next_start"] == 6


def test_condition_preserves_feature_after_old_thirty_item_cutoff():
    features = "".join(
        f'<ClinicalFeature CUI="C{i}" SDUI="HP:{i:07d}">'
        f"<Name>Feature {i}</Name><Definition>Definition {i}</Definition>"
        "</ClinicalFeature>"
        for i in range(31)
    )
    response = MagicMock()
    response.json.return_value = {
        "result": {
            "41393": {
                "title": "Cystic fibrosis",
                "conceptid": "C0010674",
                "conceptmeta": features,
            }
        }
    }
    tool = _tool("get_condition")

    with patch.object(tool, "_ncbi_get", return_value=response):
        result = tool.run({"uid": "41393"})

    assert result["data"]["clinical_feature_count"] == 31
    assert len(result["data"]["clinical_features"]) == 31
    assert result["data"]["clinical_features"][30]["name"] == "Feature 30"
