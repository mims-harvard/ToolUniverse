"""page_size caps annotations per article; the endpoint itself cannot paginate."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.europepmc_annotations_tool import EuroPMCAnnotationsTool

pytestmark = pytest.mark.unit


def _tool():
    return EuroPMCAnnotationsTool(
        {
            "name": "EuroPMCAnnot_get_annotations_by_type",
            "fields": {"endpoint_type": "batch_by_type"},
        }
    )


def _response(annotation_count):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "source": "PMC",
            "extId": "PMC4353746",
            "pmcid": "PMC4353746",
            "annotations": [
                {"exact": f"chem{i}", "type": "Chemicals", "tags": []}
                for i in range(annotation_count)
            ],
        }
    ]
    return response


@pytest.mark.parametrize(
    ("page_size", "expected"),
    # A non-positive cap falls back to the default instead of emptying the
    # response; the schema rejects those values before they get here.
    [(None, 100), (5, 5), (250, 150), (0, 100), (-5, 100)],
)
def test_page_size_caps_returned_annotations(page_size, expected):
    arguments = {"article_ids": "PMC:PMC4353746", "annotation_type": "Chemicals"}
    if page_size is not None:
        arguments["page_size"] = page_size

    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get",
        return_value=_response(150),
    ):
        result = _tool().run(arguments)

    article = result["data"]["articles"][0]
    assert len(article["annotations"]) == expected
    # The reported count must match what the caller actually receives.
    assert article["annotation_count"] == expected
    # A capped article states its own true total, so the shortfall is
    # attributable without diffing against the batch-wide sum.
    assert article["total_annotations"] == 150
    assert result["data"]["total_annotations"] == 150


def test_page_size_is_not_sent_upstream():
    """annotationsByArticleIds ignores pageSize, so it must not be requested."""
    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get",
        return_value=_response(3),
    ) as get:
        _tool().run(
            {
                "article_ids": "PMC:PMC4353746",
                "annotation_type": "Chemicals",
                "page_size": 2,
            }
        )

    assert "pageSize" not in get.call_args.kwargs["params"]


def test_non_numeric_page_size_falls_back_to_default():
    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get",
        return_value=_response(150),
    ):
        result = _tool().run(
            {
                "article_ids": "PMC:PMC4353746",
                "annotation_type": "Chemicals",
                "page_size": "not-a-number",
            }
        )

    assert len(result["data"]["articles"][0]["annotations"]) == 100


def test_per_article_total_attributes_truncation_across_a_batch():
    """A batch must say which article was capped, not just that some were."""
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "source": "MED",
            "extId": "25780448",
            "pmcid": "PMC4353746",
            "annotations": [
                {"exact": f"g{i}", "type": "Gene_Proteins", "tags": []}
                for i in range(131)
            ],
        },
        {
            "source": "MED",
            "extId": "23193287",
            "pmcid": "PMC3531190",
            "annotations": [{"exact": "g0", "type": "Gene_Proteins", "tags": []}],
        },
    ]

    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get", return_value=response
    ):
        data = _tool().run(
            {"article_ids": "PMC:PMC4353746,PMC:PMC3531190",
             "annotation_type": "Gene_Proteins"}
        )["data"]

    capped, small = data["articles"]
    assert (capped["annotation_count"], capped["total_annotations"]) == (100, 131)
    assert (small["annotation_count"], small["total_annotations"]) == (1, 1)
    # The batch total reconciles against the per-article totals, not the
    # returned counts.
    assert data["total_annotations"] == 132
    assert sum(a["total_annotations"] for a in data["articles"]) == 132
