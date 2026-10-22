from unittest.mock import patch

from tooluniverse.openfda_tool import FDADrugLabelGetDrugNamesByIndicationStats


def _tool():
    return FDADrugLabelGetDrugNamesByIndicationStats(
        {"name": "FDA_get_drug_names_by_indication_stats", "fields": {}}
    )


def test_count_ceiling_is_not_reported_as_complete():
    generic = {"results": [{"term": f"G{i}", "count": 1} for i in range(1000)]}
    brand = {"results": [{"term": f"B{i}", "count": 1} for i in range(1000)]}

    with patch(
        "tooluniverse.openfda_tool.search_openfda", side_effect=[generic, brand]
    ):
        result = _tool().run({"indication": "pain"})

    assert result["meta"]["total_generic_names"] == 1000
    assert result["meta"]["total_brand_names"] == 1000
    assert result["meta"]["generic_names_complete"] is False
    assert result["meta"]["brand_names_complete"] is False
    assert result["meta"]["counts_are_lower_bounds"] is True
    assert "1,000-term" in result["meta"]["warning"]


def test_brand_count_failure_is_not_reported_as_zero_complete_names():
    generic = {"results": [{"term": "ASPIRIN", "count": 10}]}
    brand_error = {"error": {"code": "SERVER_ERROR"}}

    with patch(
        "tooluniverse.openfda_tool.search_openfda",
        side_effect=[generic, brand_error],
    ):
        result = _tool().run({"indication": "pain"})

    assert result["meta"]["generic_names_complete"] is True
    assert result["meta"]["brand_names_complete"] is False
    assert result["meta"]["counts_are_lower_bounds"] is True
    assert "request failed" in result["meta"]["warning"]
