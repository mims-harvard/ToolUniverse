from unittest.mock import patch

import pytest

from tooluniverse.proteomicsdb_tool import ProteomicsDBTool


def _tool():
    return ProteomicsDBTool({"name": "ProteomicsDB_search_proteins"})


@patch("tooluniverse.proteomicsdb_tool._odata_request")
def test_search_forwards_raw_offset_and_reports_exact_row_count(mock_request):
    mock_request.return_value = {
        "ok": True,
        "data": {
            "d": {
                "__count": "8714",
                "results": [
                    {"PROTEIN_ID": 1, "UNIQUE_IDENTIFIER": "P1", "MASS": "10"},
                    {"PROTEIN_ID": 2, "UNIQUE_IDENTIFIER": "P1", "MASS": "10"},
                    {"PROTEIN_ID": 3, "UNIQUE_IDENTIFIER": "P2", "MASS": "20"},
                ],
            }
        },
    }
    result = _tool().run(
        {"operation": "search_proteins", "query": "O'Neil", "max_results": 3, "offset": 6}
    )

    url = mock_request.call_args.args[0]
    assert "$skip=6" in url
    assert "$inlinecount=allpages" in url
    assert "O''Neil" in url
    assert result["data"]["num_results"] == 2
    assert result["metadata"]["raw_records_returned"] == 3
    assert result["metadata"]["unique_proteins_returned"] == 2
    assert result["metadata"]["total_raw_records"] == 8714
    assert result["metadata"]["next_offset"] == 9


@pytest.mark.parametrize("arguments,parameter", [({"max_results": 0}, "max_results"), ({"max_results": 101}, "max_results"), ({"offset": -1}, "offset"), ({"offset": True}, "offset")])
def test_invalid_paging_is_rejected(arguments, parameter):
    result = _tool().run(
        {"operation": "search_proteins", "query": "kinase", **arguments}
    )
    assert result["status"] == "error"
    assert result["parameter"] == parameter
