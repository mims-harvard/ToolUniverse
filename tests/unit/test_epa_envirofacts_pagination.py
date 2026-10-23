"""Regression tests for native EPA Envirofacts row pagination and counts."""

from unittest.mock import patch

from tooluniverse.epa_envirofacts_tool import EPATRIFacilitiesTool


def test_state_search_uses_native_row_window_and_exact_count():
    tool = EPATRIFacilitiesTool({"name": "EPA_search_tri_facilities"})
    rows = [
        {"tri_facility_id": "FAC-3"},
        {"tri_facility_id": "FAC-4"},
        {"tri_facility_id": "FAC-5"},
    ]
    with patch.object(
        tool,
        "_fetch",
        side_effect=[[{"TOTALQUERYRESULTS": 5110}], rows],
    ) as fetch:
        result = tool.run({"state": "CA", "limit": 3, "offset": 3})

    assert fetch.call_args_list[0].args[0].endswith("/count/JSON")
    assert "/rows/3:5/JSON" in fetch.call_args_list[1].args[0]
    assert result["metadata"]["total_results"] == 5110
    assert result["metadata"]["total_is_exact"] is True
    assert result["metadata"]["returned"] == 3
    assert result["metadata"]["offset"] == 3
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6


def test_facility_form_lookup_pages_the_filtered_rows():
    tool = EPATRIFacilitiesTool(
        {
            "name": "EPA_get_tri_facility_chemical_releases",
            "fields": {
                "table": "tri_reporting_form",
                "lookup_column": "tri_facility_id",
                "lookup_param": "tri_facility_id",
                "row_kind": "reporting_form",
            },
        }
    )
    rows = [{"tri_facility_id": "15902CCKRN75BRI", "tri_chem_id": "CHEM3"}]
    with patch.object(
        tool,
        "_fetch",
        side_effect=[[{"TOTALQUERYRESULTS": 7}], rows],
    ):
        result = tool.run(
            {"tri_facility_id": "15902CCKRN75BRI", "limit": 1, "offset": 3}
        )

    assert result["data"][0]["tri_chem_id"] == "CHEM3"
    assert result["metadata"]["total_results"] == 7
    assert result["metadata"]["next_offset"] == 4
