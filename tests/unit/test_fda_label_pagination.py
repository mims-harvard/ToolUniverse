"""Regression tests for FDA label and class pagination."""

from unittest.mock import patch

from tooluniverse.fda_label_tool import FDALabelTool


class _Resp:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _tool(query_type):
    return FDALabelTool(
        {
            "name": f"FDA_{query_type}",
            "fields": {"query_type": query_type},
        }
    )


def test_label_search_forwards_skip_and_reports_total():
    payload = {
        "meta": {"results": {"total": 217}},
        "results": [{"id": f"SPL-{i}", "openfda": {}} for i in range(3, 6)],
    }
    with patch(
        "tooluniverse.fda_label_tool.requests.get",
        return_value=_Resp(payload),
    ) as get:
        result = _tool("search").run(
            {"drug_name": "metformin", "limit": 3, "offset": 3}
        )

    assert get.call_args.kwargs["params"]["skip"] == 3
    assert result["metadata"]["total"] == 217
    assert result["metadata"]["returned"] == 3
    assert result["metadata"]["offset"] == 3
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6


def test_class_catalog_pages_full_accessible_count_response():
    payload = {"results": [{"term": f"CLASS {i}", "count": 100 - i} for i in range(7)]}
    with patch(
        "tooluniverse.fda_label_tool.requests.get",
        return_value=_Resp(payload),
    ) as get:
        result = _tool("list_classes").run({"limit": 3, "offset": 3})

    assert get.call_args.kwargs["params"]["limit"] == 1000
    assert [row["drug_class"] for row in result["data"]] == [
        "CLASS 3",
        "CLASS 4",
        "CLASS 5",
    ]
    assert result["metadata"]["accessible_total"] == 7
    assert result["metadata"]["returned"] == 3
    assert result["metadata"]["next_offset"] == 6


def test_unlinked_label_fallback_pages_the_filtered_list_locally():
    """Product-text matches are filtered locally, so offset pages that filtered list."""
    unlinked = [
        {
            "id": f"SPL-{i}",
            "spl_product_data_elements": [f"OSIMERTINIB osimertinib {i}"],
        }
        for i in range(5)
    ]

    def fake_get(url, params=None, timeout=None, **kwargs):
        if params["search"].startswith("spl_product_data_elements"):
            return _Resp({"meta": {"results": {"total": 5}}, "results": unlinked})
        resp = _Resp({})
        resp.status_code = 404
        return resp

    with patch("tooluniverse.fda_label_tool.requests.get", side_effect=fake_get):
        result = _tool("search").run(
            {"drug_name": "osimertinib", "limit": 2, "offset": 2}
        )

    assert [r["spl_id"] for r in result["data"]] == ["SPL-2", "SPL-3"]
    assert result["metadata"]["total"] == 5
    assert result["metadata"]["total_is_exact"] is True
    assert result["metadata"]["next_offset"] == 4
