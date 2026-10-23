"""MyVariant_query_variants keeps both its assembly label and its paging contract.

The assembly label (`coordinate_assembly`, `assembly=hg38` forwarding) and the
explicit offset pagination (`from`, `metadata.next_offset`) were added to the
same method independently; a query response must carry both.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.mygene_tool import MyVariantTool

pytestmark = pytest.mark.unit

QUERY_CONFIG = {
    "name": "MyVariant_query_variants",
    "type": "MyVariantTool",
    "fields": {"operation": "query"},
    "parameter": {"properties": {}},
}


def _run(arguments, payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    with patch("tooluniverse.mygene_tool.requests.get", return_value=response) as get:
        result = MyVariantTool(QUERY_CONFIG).run(arguments)
    return result, get.call_args.kwargs["params"]


def test_query_reports_assembly_and_next_offset():
    payload = {"total": 7, "hits": [{"_id": "a"}, {"_id": "b"}]}
    result, params = _run(
        {"query": "dbnsfp.genename:CDK2", "size": 2, "offset": 2, "assembly": "hg38"},
        payload,
    )

    assert params["from"] == 2
    assert params["size"] == 2
    assert params["assembly"] == "hg38"
    assert result["status"] == "success"
    assert result["coordinate_assembly"].startswith("hg38")
    assert result["data"] == payload
    assert result["metadata"]["total_results"] == 7
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 4


def test_query_default_assembly_is_not_sent():
    result, params = _run({"query": "rs58991260"}, {"total": 1, "hits": [{}]})

    assert "assembly" not in params
    assert result["coordinate_assembly"] == "hg19 (GRCh37)"
    assert result["metadata"]["has_more"] is False
