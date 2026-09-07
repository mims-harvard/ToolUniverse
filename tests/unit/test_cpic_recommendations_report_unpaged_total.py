"""CPIC_get_recommendations must say how many rows it did not return.

Round 59: the tool applies a documented default `limit` of 50 but reported only
`count`, which is the size of the returned page. Confirmed live that guideline
100416 (CYP2D6/OPRM1/COMT and opioids) has 66 recommendation rows, so the
default response was `count: 50` with no note and no total -- indistinguishable
from the guideline having exactly 50 rows, while 16 were silently dropped.
Codeine, tramadol and hydrocodone guidance all lives on that guideline.

This is the same defect CPICGetAllelesTool in the same module already fixed
(its class docstring describes it); these tests hold the recommendations path
to that behaviour.

Fully offline: ``requests.get`` is patched.
"""

import json
from pathlib import Path
from unittest import mock

import pytest

from tooluniverse.cpic_search_pairs_tool import CPICGetRecommendationsTool

pytestmark = pytest.mark.unit


def _rows(n):
    return [
        {"id": i, "drugid": "RxNorm:2670", "phenotypes": {"CYP2D6": "Poor Metabolizer"}}
        for i in range(n)
    ]


class FakeResponse:
    def __init__(self, rows, content_range=None):
        self._rows = rows
        self.headers = {"Content-Range": content_range} if content_range else {}

    def raise_for_status(self):
        pass

    def json(self):
        return self._rows


def _run(arguments, response):
    """Run the tool and return the `data` payload of its success envelope."""
    with mock.patch(
        "tooluniverse.cpic_search_pairs_tool.requests.get", return_value=response
    ):
        result = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"}).run(
            arguments
        )
    assert result["status"] == "success", result
    return result["data"]


# One row of the filtered fixture deliberately carries a non-matching phenotype,
# so a filtered total counts matches rather than everything fetched.
_MIXED = _rows(3) + [
    {"id": 99, "drugid": "RxNorm:2670", "phenotypes": {"CYP2D6": "Normal Metabolizer"}}
]
_FILTER = {"gene": "CYP2D6", "phenotype": "Poor Metabolizer"}


@pytest.mark.parametrize(
    "arguments,rows,content_range,expected_count,expected_total,note_fragments",
    [
        ({}, _rows(50), "0-49/66", 50, 66, ["50 of 66", "offset=50"]),
        ({"limit": 1000}, _rows(66), "0-65/66", 66, 66, None),
        # No Content-Range: fall back to what was actually seen rather than
        # inventing a total that would claim rows exist beyond this page.
        ({}, _rows(50), None, 50, 50, None),
        (_FILTER, _MIXED, "0-3/66", 3, 3, None),
        (dict(_FILTER, limit=4), _rows(10), "0-9/66", 4, 10, ["4 of 10", "(filtered)"]),
    ],
    ids=["truncated", "complete", "no_content_range", "filtered", "filtered_truncated"],
)
def test_paging_totals(
    arguments, rows, content_range, expected_count, expected_total, note_fragments
):
    result = _run(
        dict(arguments, guideline_id=100416), FakeResponse(rows, content_range)
    )

    assert result["count"] == expected_count
    assert result["total_count"] == expected_total
    assert result["offset"] == 0
    if note_fragments:
        for fragment in note_fragments:
            assert fragment in result["note"]
    else:
        assert result.get("note") is None


def test_count_exact_is_requested_so_a_total_exists_at_all():
    """Without Prefer: count=exact PostgREST does not report the unpaged total."""
    with mock.patch(
        "tooluniverse.cpic_search_pairs_tool.requests.get",
        return_value=FakeResponse(_rows(50), "0-49/66"),
    ) as get:
        CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"}).run(
            {"guideline_id": 100416}
        )

    assert get.call_args.kwargs["headers"] == {"Prefer": "count=exact"}


def test_no_exact_count_is_requested_when_filtering_locally():
    """The filtered path counts matches itself, so a server-side COUNT is waste."""
    with mock.patch(
        "tooluniverse.cpic_search_pairs_tool.requests.get",
        return_value=FakeResponse(_MIXED, "0-3/66"),
    ) as get:
        CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"}).run(
            {"guideline_id": 100416, **_FILTER}
        )

    assert get.call_args.kwargs["headers"] is None


def test_error_responses_carry_no_paging_keys():
    result = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"}).run({})

    assert result["status"] == "error"
    assert "total_count" not in result


def test_config_documents_the_new_paging_fields():
    """The payload schema must describe the total, or callers won't look for it."""
    config_path = (
        Path(__file__).parent.parent.parent / "src/tooluniverse/data/cpic_tools.json"
    )
    tool = next(
        c
        for c in json.loads(config_path.read_text())
        if c["name"] == "CPIC_get_recommendations"
    )
    # Per issue #246 the return_schema describes the inner `data` payload.
    payload = tool["return_schema"]["oneOf"][0]["properties"]

    for field in ("count", "total_count", "offset"):
        assert field in payload, field
        assert payload[field]["description"]
    assert "total_count" in payload["count"]["description"]
