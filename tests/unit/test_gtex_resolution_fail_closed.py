"""Regression guards for fail-closed GTEx gene resolution."""

from unittest.mock import Mock, patch

import pytest
import requests

from tooluniverse.gtex_tool import GTExEQTLTool, GTExExpressionTool
from tooluniverse.gtex_v2_tool import GTExV2Tool, _resolve_gencode_id


pytestmark = pytest.mark.unit


BAD_GENE = "NO_SUCH_GENE_123456"


def _response(payload, status_code=200):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_v2_unresolved_gene_is_error_before_expression_request():
    """An empty reference result cannot become an empty expression success."""
    tool = GTExV2Tool(
        {
            "name": "GTEx_get_median_gene_expression",
            "parameter": {"required": []},
        }
    )
    with patch(
        "tooluniverse.gtex_v2_tool.requests.get",
        return_value=_response({"data": []}),
    ) as get:
        result = tool.run(
            {
                "operation": "get_median_gene_expression",
                "gencode_id": BAD_GENE,
                "dataset_id": "gtex_v8",
            }
        )

    assert result["status"] == "error"
    assert "could not resolve gene" in result["error"]
    assert BAD_GENE in result["error"]
    assert get.call_count == 1
    assert get.call_args.args[0].endswith("/reference/gene")


def test_v2_resolution_transport_failure_is_not_swallowed():
    """A resolver outage is surfaced instead of querying with the raw symbol."""
    with patch(
        "tooluniverse.gtex_v2_tool.requests.get",
        side_effect=requests.ConnectionError("resolver offline"),
    ):
        try:
            _resolve_gencode_id("TP53", "gtex_v8")
        except ValueError as exc:
            assert "resolution request failed" in str(exc)
            assert "resolver offline" in str(exc)
        else:
            raise AssertionError("resolution failure was silently swallowed")


def test_legacy_expression_unresolved_gene_stops_before_expression_request():
    """The legacy summary endpoint also fails closed on an unknown symbol."""
    tool = GTExExpressionTool(
        {
            "name": "GTEx_get_expression_summary",
            "settings": {"base_url": "https://gtexportal.org/api/v2", "timeout": 30},
        }
    )
    with patch("tooluniverse.gtex_tool._http_get", return_value={"data": []}) as get:
        result = tool.run({"gene_symbol": BAD_GENE})

    assert result["status"] == "error"
    assert "could not resolve gene" in result["error"]
    assert get.call_count == 1
    assert "/reference/gene?" in get.call_args.args[0]


def test_legacy_eqtl_unresolved_gene_stops_before_association_request():
    """The legacy eQTL endpoint cannot reinterpret resolution failure as no eQTLs."""
    tool = GTExEQTLTool(
        {
            "name": "GTEx_query_eqtl",
            "settings": {"base_url": "https://gtexportal.org/api/v2", "timeout": 30},
        }
    )
    with patch("tooluniverse.gtex_tool._http_get", return_value={"data": []}) as get:
        result = tool.run({"gene_symbol": BAD_GENE})

    assert result["status"] == "error"
    assert "could not resolve gene" in result["error"]
    assert get.call_count == 1
    assert "/reference/gene?" in get.call_args.args[0]


def test_v2_malformed_resolution_payload_is_an_error():
    """A successful HTTP response without gencodeId is not a valid resolution."""
    with patch(
        "tooluniverse.gtex_v2_tool.requests.get",
        return_value=_response({"data": [{"geneSymbol": "TP53"}]}),
    ):
        try:
            _resolve_gencode_id("TP53", "gtex_v8")
        except ValueError as exc:
            assert "omitted gencodeId" in str(exc)
        else:
            raise AssertionError("malformed resolution payload was accepted")


def test_v2_rejects_a_different_returned_ensembl_gene():
    """A resolver payload for a different ENSG cannot be accepted silently."""
    with patch(
        "tooluniverse.gtex_v2_tool.requests.get",
        return_value=_response({"data": [{"gencodeId": "ENSG00000146648.17"}]}),
    ):
        try:
            _resolve_gencode_id("ENSG00000141510", "gtex_v8")
        except ValueError as exc:
            assert "different gene identity" in str(exc)
        else:
            raise AssertionError("mismatched gene identity was accepted")
