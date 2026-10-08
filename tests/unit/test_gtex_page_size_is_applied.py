"""GTEx tools ignored their page-size argument.

* ``GTEx_query_eqtl(size=N)`` sent ``pageSize``; GTEx v2 pages with ``itemsPerPage``,
  so ``size=2`` still returned the default page of 250 (33 eQTLs for TP53).
* ``GTEx_get_median_gene_expression`` without a tissue uses the clustered endpoint,
  which returns all 54 tissues unpaged and ignores ``itemsPerPage``/``page``.
"""

from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from tooluniverse.gtex_tool import GTExEQTLTool
from tooluniverse.gtex_v2_tool import GTExV2Tool

pytestmark = pytest.mark.unit


def test_eqtl_size_is_sent_as_items_per_page():
    tool = GTExEQTLTool({"name": "GTEx_query_eqtl"})
    urls = []

    def fake_get(url, headers=None, timeout=30):
        urls.append(url)
        return {"data": [], "singleTissueEqtl": []}

    with (
        patch("tooluniverse.gtex_tool._resolve_gene_id", return_value="ENSG1.1"),
        patch("tooluniverse.gtex_tool._http_get", side_effect=fake_get),
    ):
        tool.run({"gene_symbol": "TP53", "size": 2, "page": 3})
    query = parse_qs(urlparse(urls[0]).query)
    assert query["itemsPerPage"] == ["2"]
    assert "pageSize" not in query
    assert query["page"] == ["2"]  # user-facing page is 1-indexed


def _median(arguments, body, status=200):
    response = MagicMock(status_code=status)
    response.json.return_value = body
    tool = GTExV2Tool(
        {
            "name": "GTEx_get_median_gene_expression",
            "fields": {"operation": "get_median_gene_expression"},
        }
    )
    with (
        patch(
            "tooluniverse.gtex_v2_tool._resolve_gencode_id", side_effect=lambda g, d: g
        ),
        patch("tooluniverse.gtex_v2_tool.requests.get", return_value=response) as get,
    ):
        return tool.run({"operation": "get_median_gene_expression", **arguments}), get


CLUSTERED = {
    "clusters": {},
    "medianGeneExpression": [{"tissueSiteDetailId": f"T{i}"} for i in range(54)],
}


def test_all_tissue_result_is_paged_client_side():
    result, get = _median(
        {"gencode_id": "ENSG1.1", "items_per_page": 20, "page": 2}, CLUSTERED
    )
    assert get.call_args.args[0].endswith("/clusteredMedianGeneExpression")
    assert [r["tissueSiteDetailId"] for r in result["data"]] == [
        f"T{i}" for i in range(40, 54)
    ]
    assert result["paging_info"] == {
        "numberOfPages": 3,
        "page": 2,
        "maxItemsPerPage": 20,
        "totalNumberOfItems": 54,
    }
    assert result["num_results"] == 14


def test_default_page_size_still_returns_all_tissues():
    result, _ = _median({"gencode_id": "ENSG1.1"}, CLUSTERED)
    assert len(result["data"]) == 54


def test_per_tissue_query_passes_the_api_response_through():
    body = {
        "data": [{"tissueSiteDetailId": "Lung"}],
        "paging_info": {"page": 0, "totalNumberOfItems": 1},
    }
    result, get = _median(
        {"gencode_id": "ENSG1.1", "tissue_site_detail_id": "Lung"}, body
    )
    assert get.call_args.args[0].endswith("/medianGeneExpression")
    assert result["paging_info"] == {"page": 0, "totalNumberOfItems": 1}
    assert result["data"] == [{"tissueSiteDetailId": "Lung"}]
