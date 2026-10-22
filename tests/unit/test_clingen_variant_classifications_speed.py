"""Regression tests for the current ClinGen ERepo Summary API.

The legacy classifications endpoint silently returned a fixed first 25
records and ignored common pagination parameters. The official UI uses the
Summary API's count plus pg/pgSize endpoints, which expose all matches.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.clingen_tool import ClinGenTool

pytestmark = pytest.mark.unit


def _item(index=0, gene="BRCA1"):
    return {
        "caId": f"CA{index:06d}",
        "cvId": str(1000 + index),
        "gene": gene,
        "condition": "hereditary breast ovarian cancer syndrome",
        "mondoId": "MONDO:0011450",
        "classification": "Pathogenic",
        "ep": "ENIGMA BRCA1/2 VCEP",
        "moi": "Autosomal dominant inheritance",
        "metCodes": ["PS3", "PM2"],
        "unMetCodes": ["BS1"],
        "summaryDesc": "Expert evidence summary",
        "approvedDate": "2024-01-01",
        "publishedDate": "2024-02-01",
        "docVersion": "1.0",
        "uuid": f"uuid-{index}",
        "preferredVarTitle": f"NM_007294.4(BRCA1):c.{index + 1}A>G",
        "hgvs": [f"NM_007294.4:c.{index + 1}A>G"],
    }


def _tool():
    return ClinGenTool(
        {"fields": {"operation": "get_variant_classifications"}, "parameter": {}}
    )


def _resp(payload):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload
    return response


def _count(total):
    return _resp({"data": {"total": total}})


def _records(items):
    return _resp({"data": items})


class TestSummaryApiFiltering:
    def test_gene_query_uses_count_and_paginated_summary_endpoints(self):
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            side_effect=[_count(81), _records([_item()])],
        ) as mock_get:
            result = tool.run({"gene": "BRCA1", "limit": 1})

        count_call, records_call = mock_get.call_args_list
        assert count_call.args[0].endswith("/api/summary/classifications/count")
        assert records_call.args[0].endswith("/api/summary/classifications")
        assert count_call.kwargs["params"] == {
            "columns": "gene",
            "values": "BRCA1",
            "matchTypes": "exact",
            "matchMode": "and",
        }
        assert records_call.kwargs["params"] == {
            **count_call.kwargs["params"],
            "pgSize": 500,
            "pg": 1,
        }
        assert result["total"] == 81
        assert result["returned"] == 1
        assert result["next_offset"] == 1
        assert result["data"][0]["HGNC Gene Symbol"] == "BRCA1"
        assert result["data"][0]["Met Criteria"] == ["PS3", "PM2"]
        assert result["data"][0]["Summary"] == "Expert evidence summary"

    def test_uncurated_gene_uses_count_only(self):
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get", return_value=_count(0)
        ) as mock_get:
            result = tool.run({"gene": "UNCURATED1"})

        assert mock_get.call_count == 1
        assert result["data"] == []
        assert result["total"] == 0
        assert "UNCURATED1" in result["note"]

    def test_variant_caid_uses_exact_caid_filter(self):
        tool = _tool()
        variant = _item(gene="PAH")
        variant["caId"] = "CA114360"
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            side_effect=[_count(1), _records([variant])],
        ) as mock_get:
            result = tool.run({"variant": "CAR:CA114360"})

        params = mock_get.call_args_list[0].kwargs["params"]
        assert params["columns"] == "caId"
        assert params["values"] == "CA114360"
        assert params["matchTypes"] == "exact"
        assert result["data"][0]["CAID"] == "CA114360"

    def test_uncurated_variant_note_does_not_say_none(self):
        tool = _tool()
        with patch("tooluniverse.clingen_tool.requests.get", return_value=_count(0)):
            result = tool.run({"variant": "CA9999999999"})

        assert "None" not in result["note"]
        assert "CA9999999999" in result["note"]


class TestSummaryApiPagination:
    def test_arbitrary_offset_is_applied_within_server_page(self):
        tool = _tool()
        items = [_item(i) for i in range(81)]
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            side_effect=[_count(81), _records(items)],
        ):
            result = tool.run({"gene": "BRCA1", "limit": 2, "offset": 5})

        assert [row["CAID"] for row in result["data"]] == ["CA000005", "CA000006"]
        assert result["offset"] == 5
        assert result["next_offset"] == 7
        assert result["has_more"] is True

    def test_offset_crossing_server_page_fetches_both_pages(self):
        tool = _tool()
        page_one = [_item(i) for i in range(500)]
        page_two = [_item(i) for i in range(500, 502)]
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            side_effect=[_count(502), _records(page_one), _records(page_two)],
        ) as mock_get:
            result = tool.run({"gene": "BRCA1", "limit": 3, "offset": 499})

        assert [row["CAID"] for row in result["data"]] == [
            "CA000499",
            "CA000500",
            "CA000501",
        ]
        assert [
            call.kwargs["params"]["pg"] for call in mock_get.call_args_list[1:]
        ] == [
            1,
            2,
        ]
        assert result["has_more"] is False
        assert result["next_offset"] is None

    def test_offset_beyond_total_is_distinguished_from_no_matches(self):
        tool = _tool()
        with patch("tooluniverse.clingen_tool.requests.get", return_value=_count(10)):
            result = tool.run({"gene": "BRCA1", "offset": 10})

        assert result["data"] == []
        assert "beyond" in result["note"]
        assert "No variant classifications" not in result["note"]


def test_requires_gene_or_variant_without_calling_api():
    tool = _tool()
    with patch("tooluniverse.clingen_tool.requests.get") as mock_get:
        result = tool.run({})

    assert result["status"] == "error"
    assert "gene" in result["error"]
    mock_get.assert_not_called()
