from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.unpaywall_tool import UnpaywallTool


pytestmark = pytest.mark.unit


def _tool(name="Unpaywall_get_full_text_url"):
    return UnpaywallTool({"name": name})


def _payload():
    location = {
        "endpoint_id": "endpoint",
        "evidence": "oa repository",
        "host_type": "repository",
        "is_best": True,
        "license": "cc-by",
        "oa_date": "2014-01-01",
        "pmh_id": "oai:1",
        "repository_institution": "Example University",
        "updated": "2026-01-01",
        "url": "https://example.org/work",
        "url_for_landing_page": "https://example.org/work",
        "url_for_pdf": "https://example.org/work.pdf",
        "version": "publishedVersion",
    }
    return {
        "doi": "10.7554/elife.01567",
        "title": "Title",
        "is_oa": True,
        "oa_status": "gold",
        "best_oa_location": location,
        "first_oa_location": location,
        "oa_locations": [location],
        "oa_locations_embargoed": [{**location, "is_best": False}],
        "z_authors": [{"family": "Smith"}],
        "data_standard": 2,
    }


def _response(payload):
    response = MagicMock(status_code=200)
    response.json.return_value = payload
    return response


@pytest.mark.parametrize(
    "value",
    [
        "10.7554/eLife.01567",
        "doi:10.7554/eLife.01567",
        "https://doi.org/10.7554/eLife.01567",
    ],
)
def test_doi_forms_are_normalized_and_returned_identity_verified(value):
    with patch(
        "tooluniverse.unpaywall_tool.requests.get",
        return_value=_response(_payload()),
    ) as get:
        result = _tool().run({"doi": value})
    assert "/10.7554/elife.01567" in get.call_args.args[0]
    assert result["data"]["doi"] == "10.7554/elife.01567"
    assert result["metadata"]["returned_doi_verified"] is True


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({"doi": "not a doi"}, "valid DOI"),
        ({"doi": "10.1/x"}, "valid DOI"),
        ({"doi": "10.7554/eLife.01567", "email": "bad"}, "email"),
        ({"doi": "10.7554/eLife.01567", "limit": 1}, "Unrecognized"),
    ],
)
def test_invalid_controls_are_rejected_before_network(arguments, error):
    with patch("tooluniverse.unpaywall_tool.requests.get") as get:
        result = _tool().run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    get.assert_not_called()


def test_full_text_preserves_every_location_field_and_embargoed_records():
    with patch(
        "tooluniverse.unpaywall_tool.requests.get",
        return_value=_response(_payload()),
    ):
        result = _tool().run({"doi": "10.7554/eLife.01567"})
    location = result["data"]["all_oa_locations"][0]
    assert location["evidence"] == "oa repository"
    assert location["repository_institution"] == "Example University"
    assert location["endpoint_id"] == "endpoint"
    assert location["oa_date"] == "2014-01-01"
    assert len(result["data"]["embargoed_oa_locations"]) == 1
    assert result["metadata"]["source_record_complete"] is True


def test_status_response_preserves_complete_raw_record_and_counts():
    with patch(
        "tooluniverse.unpaywall_tool.requests.get",
        return_value=_response(_payload()),
    ):
        result = _tool("Unpaywall_check_oa_status").run(
            {"doi": "10.7554/eLife.01567", "email": "test@example.org"}
        )
    assert result["data"]["record"]["z_authors"] == [{"family": "Smith"}]
    assert result["metadata"]["oa_location_count"] == 1
    assert result["metadata"]["embargoed_oa_location_count"] == 1


def test_returned_doi_mismatch_is_an_error():
    payload = _payload()
    payload["doi"] = "10.1000/different"
    with patch(
        "tooluniverse.unpaywall_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool().run({"doi": "10.7554/eLife.01567"})
    assert result["status"] == "error"
    assert result["returned_doi"] == "10.1000/different"


def test_malformed_locations_are_an_error_not_silent_empty():
    payload = _payload()
    payload["oa_locations"] = [None]
    with patch(
        "tooluniverse.unpaywall_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool().run({"doi": "10.7554/eLife.01567"})
    assert result["status"] == "error"
    assert "malformed oa_locations" in result["error"]
