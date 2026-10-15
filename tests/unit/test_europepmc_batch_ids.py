"""The batch path must accept the ids its siblings accept, and report misses."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.europepmc_annotations_tool import EuroPMCAnnotationsTool

pytestmark = pytest.mark.unit


def _tool():
    return EuroPMCAnnotationsTool(
        {"name": "batch", "fields": {"endpoint_type": "batch_by_type"}}
    )


def _response(articles):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = articles
    return response


ARTICLE = {
    "source": "MED",
    "extId": "25780448",
    "pmcid": "PMC4353746",
    "annotations": [{"exact": "resistin", "type": "Chemicals", "tags": []}],
}


@pytest.mark.parametrize(
    "raw",
    ["PMC4353746", "25780448", "PMC:PMC4353746", " PMC4353746 , 25780448 "],
)
def test_batch_normalizes_ids_before_sending(raw):
    """Bare PMCIDs and raw PMIDs used to reach the API unchanged and 400."""
    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get",
        return_value=_response([ARTICLE]),
    ) as get:
        result = _tool().run({"article_ids": raw, "annotation_type": "Chemicals"})

    sent = get.call_args.kwargs["params"]["articleIds"]
    for part in sent.split(","):
        assert part.startswith(("PMC:", "MED:")), sent
    assert result["status"] == "success"


def test_requested_ids_with_no_article_are_reported():
    """A typo in a 200-id list must not vanish silently."""
    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get",
        return_value=_response([ARTICLE]),
    ):
        data = _tool().run(
            {
                "article_ids": "PMC:PMC4353746,PMC:PMC9999999999",
                "annotation_type": "Chemicals",
            }
        )["data"]

    assert data["not_found"] == ["PMC:PMC9999999999"]
    assert data["article_count"] == 1


def test_a_resolved_id_is_not_reported_missing():
    """PMC:PMC4353746 comes back keyed MED:25780448; that is still a match."""
    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get",
        return_value=_response([ARTICLE]),
    ):
        data = _tool().run(
            {"article_ids": "PMC:PMC4353746", "annotation_type": "Chemicals"}
        )["data"]

    assert data["not_found"] == []


def test_blank_ids_are_rejected_locally():
    with patch("tooluniverse.europepmc_annotations_tool.requests.get") as get:
        result = _tool().run({"article_ids": "  ,  ", "annotation_type": "Chemicals"})
    assert result["status"] == "error"
    get.assert_not_called()
