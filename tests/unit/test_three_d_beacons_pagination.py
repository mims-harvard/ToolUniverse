from unittest.mock import MagicMock, patch

from tooluniverse.three_d_beacons_tool import ThreeDBeaconsTool


def _tool():
    return ThreeDBeaconsTool(
        {
            "name": "ThreeDBeacons_get_structures",
            "fields": {"endpoint": "structures"},
        }
    )


def _response(count=5):
    response = MagicMock()
    response.json.return_value = {
        "uniprot_entry": {"ac": "P04637", "sequence_length": 393},
        "structures": [
            {
                "summary": {
                    "model_identifier": f"model-{index}",
                    "provider": "PDBe",
                    "model_category": "EXPERIMENTALLY DETERMINED",
                }
            }
            for index in range(count)
        ],
    }
    response.raise_for_status.return_value = None
    return response


@patch("tooluniverse.three_d_beacons_tool.requests.get", return_value=_response())
def test_structures_adjacent_page_is_recoverable(_get):
    result = _tool().run({"accession": "P04637", "max_results": 2, "offset": 2})

    data = result["data"]
    assert [row["model_identifier"] for row in data["structures"]] == [
        "model-2",
        "model-3",
    ]
    assert data["total_matched"] == 5
    assert data["has_more"] is True
    assert data["next_offset"] == 4
    assert data["result_set_complete"] is False


@patch("tooluniverse.three_d_beacons_tool.requests.get", return_value=_response())
def test_structures_tail_page_terminates(_get):
    result = _tool().run({"accession": "P04637", "max_results": 2, "offset": 4})

    data = result["data"]
    assert [row["model_identifier"] for row in data["structures"]] == ["model-4"]
    assert data["has_more"] is False
    assert data["next_offset"] is None


def test_structures_reject_boolean_or_negative_pagination_values():
    assert "positive integer" in _tool().run(
        {"accession": "P04637", "max_results": True}
    )["error"]
    assert "non-negative integer" in _tool().run(
        {"accession": "P04637", "offset": -1}
    )["error"]
