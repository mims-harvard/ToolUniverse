"""Regression guard for Fix-R21C-1: BVBRC_search_pathways' select_fields
list omitted gene/feature_id/product/annotation, so genuinely distinct
BV-BRC pathway records (different genes, or the same EC/pathway annotated
independently by RefSeq vs. PATRIC) collapsed into what looked like exact
duplicate rows.

Confirmed live for M. tuberculosis H37Rv (genome_id 83332.12) "Fatty acid
metabolism": querying with the old select_fields returned 10 byte-for-byte
identical rows; the same query against the raw BV-BRC Solr API with
gene/feature_id/product/annotation added showed the true underlying
records differ (fadD15 via RefSeq, fadD19/fadD35 via PATRIC, etc.). Fixed
by adding those 4 fields to select_fields so the tool's own output can
distinguish real duplicates from independently-annotated distinct records.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.bvbrc_tool import BVBRCTool

pytestmark = pytest.mark.unit


def _tool():
    return BVBRCTool(
        {"name": "bvbrc_test", "fields": {"data_type": "pathway", "action": "search"}}
    )


def test_search_pathways_requests_distinguishing_fields():
    tool = _tool()
    captured = {}

    def fake_get(url, headers=None, timeout=None, **kwargs):
        captured["url"] = url
        r = MagicMock()
        r.raise_for_status = MagicMock()
        r.json.return_value = [
            {
                "pathway_id": "00071",
                "pathway_name": "Fatty acid metabolism",
                "gene": "fadD15",
                "feature_id": "RefSeq.83332.12.NC_000962.CDS.2448160.2449962.fwd",
                "product": "long-chain-fatty-acid-CoA ligase fadD15",
                "annotation": "RefSeq",
            },
            {
                "pathway_id": "00071",
                "pathway_name": "Fatty acid metabolism",
                "gene": "fadD19",
                "feature_id": "PATRIC.83332.12.NC_000962.CDS.3950824.3952464.rev",
                "product": "Long-chain-fatty-acid--CoA ligase FadD19",
                "annotation": "PATRIC",
            },
        ]
        return r

    with patch("tooluniverse.bvbrc_tool.requests.get", side_effect=fake_get):
        result = tool.run(
            {"genome_id": "83332.12", "pathway_name": "Fatty acid", "limit": 10}
        )

    assert result["status"] == "success"
    for field in ("gene", "feature_id", "product", "annotation"):
        assert f"select(" in captured["url"] and field in captured["url"]

    genes = [row["gene"] for row in result["data"]]
    assert genes == ["fadD15", "fadD19"]
    assert len(set(genes)) == 2


def test_search_pathways_still_requires_at_least_one_filter():
    tool = _tool()
    result = tool.run({})
    assert result["status"] == "error"
