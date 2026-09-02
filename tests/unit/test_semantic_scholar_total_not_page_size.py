"""Regression guard for Fix-R30 in semantic_scholar_tool.py:
SemanticScholar_search_papers reported one page of results as the complete
total.

`SemanticScholarTool.run` built its envelope as::

    return {
        "status": "success",
        "data": papers,
        "metadata": {"total": len(papers), "query": query},
    }

`len(papers)` is the size of the single page just fetched, not the number of
papers in the corpus that match the query, so `metadata.total` always came
back equal to the requested `limit`. Observed live against the real API for
one and the same query ("TYK2 lupus"): limit=10 -> total:10, limit=5 ->
total:5, limit=3 -> total:3. A caller had no way to tell a 3-paper literature
base from a 3000-paper one, and no signal at all that the result set was
truncated.

Semantic Scholar sends the real figure alongside `data`. Its OpenAPI spec
(https://api.semanticscholar.org/graph/v1/swagger.json) defines `total` on
both `PaperRelevanceSearchBatch` (/paper/search) and `PaperBulkSearchBatch`
(/paper/search/bulk) as "Approximate number of matching search results."
`_search` read only `payload.get("data", [])` and threw that away.

These tests mock the HTTP layer -- no network -- with an upstream payload
whose `total` is far larger than the page, and assert that:
  (a) the real corpus total is reported, not the page size;
  (b) the returned-count is separately visible;
  (c) truncation is flagged at the top level when total > returned;
  (d) nothing is flagged as truncated when total == returned;
  (e) an upstream payload with no `total` yields null, never a fabricated
      len(data).
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.semantic_scholar_tool import SemanticScholarTool, _coerce_total

pytestmark = pytest.mark.unit


def _paper(idx):
    return {
        "paperId": f"pid{idx}",
        "title": f"TYK2 and lupus, part {idx}",
        "abstract": f"Abstract {idx}",
        "year": 2020 + idx,
        "venue": "Journal of Testing",
        "url": f"https://example.org/{idx}",
        "authors": [{"name": f"Author {idx}"}],
        "externalIds": {"DOI": f"10.1000/{idx}"},
        "citationCount": idx,
        "referenceCount": idx,
        "isOpenAccess": False,
        "fieldsOfStudy": ["Medicine"],
    }


_THREE_PAPERS = [_paper(1), _paper(2), _paper(3)]


def _tool():
    return SemanticScholarTool(
        {
            "name": "SemanticScholar_search_papers",
            "type": "SemanticScholarTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
    )


def _resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.reason = "OK"
    r.json.return_value = payload
    return r


def _run(payload, arguments=None):
    """Run the tool against a canned upstream payload, with no network."""
    tool = _tool()
    with (
        patch.object(tool, "_enforce_rate_limit"),
        patch(
            "tooluniverse.semantic_scholar_tool.request_with_retry",
            return_value=_resp(payload),
        ),
    ):
        return tool.run(arguments or {"query": "TYK2 lupus", "limit": 3})


class TestCorpusTotalIsReported:
    def test_total_is_upstream_total_not_page_size(self):
        """(a) 4213 matches exist upstream; do not report the 3 rows fetched."""
        result = _run({"total": 4213, "data": _THREE_PAPERS})

        assert result["status"] == "success"
        assert len(result["data"]) == 3
        assert result["metadata"]["total"] == 4213
        assert result["metadata"]["total"] != len(result["data"])
        assert result["metadata"]["total_source"] == "semantic_scholar"

    def test_returned_count_is_also_visible(self):
        """(b) callers must still be able to see how many rows came back."""
        result = _run({"total": 4213, "data": _THREE_PAPERS})

        assert result["metadata"]["returned"] == 3
        assert result["metadata"]["returned"] == len(result["data"])

    def test_total_does_not_track_limit(self):
        """The original bug's signature: total moved with limit. It must not."""
        totals = []
        for limit in (10, 5, 3):
            page = [_paper(i) for i in range(1, min(limit, 3) + 1)]
            result = _run(
                {"total": 4213, "data": page},
                {"query": "TYK2 lupus", "limit": limit},
            )
            totals.append(result["metadata"]["total"])
        assert totals == [4213, 4213, 4213]

    def test_upstream_total_as_string_is_accepted(self):
        """The OpenAPI spec types `total` as a string; the live API sends an
        int. Both must be understood rather than silently dropped."""
        result = _run({"total": "4213", "data": _THREE_PAPERS})
        assert result["metadata"]["total"] == 4213


class TestTruncationSignal:
    def test_truncation_flagged_when_more_matches_exist(self):
        """(c) total > returned must be surfaced as a top-level flag, not
        buried in prose."""
        result = _run({"total": 4213, "data": _THREE_PAPERS})

        assert result["truncated"] is True
        assert "truncation_note" in result
        note = result["truncation_note"]
        assert "3" in note and "4213" in note

    def test_no_truncation_when_total_equals_returned(self):
        """(d) a complete result set must not be flagged as truncated."""
        result = _run({"total": 3, "data": _THREE_PAPERS})

        assert result["metadata"]["total"] == 3
        assert result["metadata"]["returned"] == 3
        assert result["truncated"] is False
        assert "truncation_note" not in result

    def test_no_truncation_flag_when_total_unknown(self):
        """Without a total there is no basis to claim truncation."""
        result = _run({"data": _THREE_PAPERS})

        assert result["truncated"] is False
        assert "truncation_note" not in result


class TestMissingTotalIsNotFabricated:
    def test_absent_total_reported_as_null(self):
        """(e) upstream omitting `total` must not fall back to len(data)."""
        result = _run({"data": _THREE_PAPERS})

        assert result["metadata"]["total"] is None
        assert result["metadata"]["returned"] == 3
        assert result["metadata"]["total_source"] == "unavailable"

    def test_garbage_total_reported_as_null(self):
        result = _run({"total": "lots", "data": _THREE_PAPERS})

        assert result["metadata"]["total"] is None
        assert result["metadata"]["total_source"] == "unavailable"

    def test_empty_result_set_reports_zero_total(self):
        """A genuine zero-hit search reports an upstream total of 0."""
        result = _run({"total": 0, "data": []})

        assert result["data"] == []
        assert result["metadata"]["total"] == 0
        assert result["metadata"]["returned"] == 0
        assert result["metadata"]["total_source"] == "semantic_scholar"
        assert result["truncated"] is False


class TestSortedBulkPathAlsoReportsTotal:
    def test_bulk_path_total_survives_client_side_slicing(self):
        """With `sort` the tool hits /paper/search/bulk and slices the page to
        `limit` client-side; the corpus total must still be the API's, not the
        slice length."""
        page = [_paper(i) for i in range(1, 11)]
        result = _run(
            {"total": 4213, "data": page},
            {"query": "TYK2 lupus", "limit": 2, "sort": "citationCount:desc"},
        )

        assert len(result["data"]) == 2
        assert result["metadata"]["returned"] == 2
        assert result["metadata"]["total"] == 4213
        assert result["truncated"] is True


class TestDegenerateAndErrorPaths:
    def test_limit_zero_shape_is_consistent(self):
        """The limit<=0 early return issues no request at all, so its `total`
        of 0 is explicitly marked `not_queried` rather than passing as a
        corpus count. Keys match the normal success shape.

        NOTE: total stays 0 here for backwards compatibility with
        tests/tools/test_paper_search_fixes.py::TestSemanticScholarLimitZero.
        """
        tool = _tool()
        result = tool.run({"query": "cancer", "limit": 0})

        assert result["status"] == "success"
        assert result["data"] == []
        assert result["metadata"]["total"] == 0
        assert result["metadata"]["returned"] == 0
        assert result["metadata"]["total_source"] == "not_queried"
        assert result["truncated"] is False

    def test_upstream_error_still_returns_error_envelope(self):
        """The total-reporting change must not swallow API errors."""
        tool = _tool()
        err = MagicMock()
        err.status_code = 429
        err.reason = "Too Many Requests"
        with (
            patch.object(tool, "_enforce_rate_limit"),
            patch(
                "tooluniverse.semantic_scholar_tool.request_with_retry",
                return_value=err,
            ),
        ):
            result = tool.run({"query": "TYK2 lupus", "limit": 3})

        assert result["status"] == "error"
        assert "429" in result["error"]
        assert result["retryable"] is True


class TestCoerceTotalHelper:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (4213, 4213),
            ("4213", 4213),
            ("  4213 ", 4213),
            (0, 0),
            (None, None),
            ("", None),
            ("lots", None),
            (-1, None),
            (True, None),
            (12.5, None),
            ({"count": 5}, None),
        ],
    )
    def test_coercion(self, raw, expected):
        assert _coerce_total(raw) == expected
