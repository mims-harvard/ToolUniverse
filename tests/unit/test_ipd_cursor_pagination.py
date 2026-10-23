"""Round 229: IPD search tails must be reachable through opaque cursors."""

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.ipd_imgt_hla_tool import IPDIMGTHLATool
from tooluniverse.tools.IPD_search_cells import IPD_search_cells
from tooluniverse.tools.IPD_search_hla_alleles import IPD_search_hla_alleles

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "ipd_imgt_hla_tools.json"
)


def _tool(name):
    return IPDIMGTHLATool({"name": name, "type": "IPDIMGTHLATool"})


def _response(payload):
    response = MagicMock(status_code=200)
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_allele_next_cursor_is_extracted_and_forwarded():
    """The opaque next token must reach the second request unchanged."""
    token = "gASVopaqueAlleleToken"
    payload = {
        "data": [{"accession": "HLA00008", "name": "A*02:03:01:01"}],
        "meta": {
            "total": 2095,
            "next": f"?query=x&limit=1&next={token}",
            "prev": "?query=x&limit=1&prev=previousToken",
        },
    }
    with patch(
        "tooluniverse.ipd_imgt_hla_tool.requests.get", return_value=_response(payload)
    ) as request:
        result = _tool("IPD_search_hla_alleles").run(
            {"name": "A*02", "limit": 1, "cursor": "inputToken"}
        )

    params = request.call_args.kwargs["params"]
    assert params["next"] == "inputToken"
    assert params["query"] == 'startsWith(name,"A*02")'
    assert result["data"]["next_cursor"] == token
    assert result["data"]["previous_cursor"] == "previousToken"
    assert result["data"]["has_more"] is True
    assert result["data"]["total"] == 2095
    assert result["metadata"]["total_results_is_exact"] is True


def test_cell_search_uses_same_cursor_contract():
    """Cell-line results must not remain trapped on the first page."""
    payload = {
        "data": [{"cellid": "2", "primary_name": "second"}],
        "meta": {"total": 2, "next": None, "prev": "?prev=backToken"},
    }
    with patch(
        "tooluniverse.ipd_imgt_hla_tool.requests.get", return_value=_response(payload)
    ) as request:
        result = _tool("IPD_search_cells").run(
            {"query": "cell", "limit": 1, "cursor": "cellToken"}
        )
    assert request.call_args.kwargs["params"]["next"] == "cellToken"
    assert result["data"]["previous_cursor"] == "backToken"
    assert result["data"]["has_more"] is False
    assert result["data"]["result_set_complete"] is False


@pytest.mark.parametrize(
    "arguments,fragment",
    [
        ({"name": "A*02", "limit": 0}, "limit"),
        ({"name": "A*02", "limit": True}, "limit"),
        ({"name": "A*02", "cursor": ""}, "cursor"),
    ],
)
def test_invalid_paging_controls_fail_before_network(arguments, fragment):
    """Invalid values cannot be clamped or silently ignored by IPD."""
    with patch("tooluniverse.ipd_imgt_hla_tool.requests.get") as request:
        result = _tool("IPD_search_hla_alleles").run(arguments)
    assert result["status"] == "error"
    assert fragment in result["error"]
    request.assert_not_called()


def test_allele_detail_identity_mismatch_is_rejected():
    """A record for another accession cannot satisfy a detail lookup."""
    with patch(
        "tooluniverse.ipd_imgt_hla_tool.requests.get",
        return_value=_response({"accession": "HLA00002", "name": "A*02"}),
    ):
        result = _tool("IPD_get_hla_allele").run({"accession": "HLA00001"})
    assert result["status"] == "error"
    assert "identity mismatch" in result["error"]


def test_configs_and_wrappers_expose_cursor():
    """Agents must be able to pass the continuation token publicly."""
    configs = json.loads(CONFIG_PATH.read_text())
    for name in ("IPD_search_hla_alleles", "IPD_search_cells"):
        config = next(c for c in configs if c["name"] == name)
        assert "cursor" in config["parameter"]["properties"]
        assert "next_cursor" in config["return_schema"]["oneOf"][0]["properties"]
    assert "cursor" in inspect.signature(IPD_search_hla_alleles).parameters
    assert "cursor" in inspect.signature(IPD_search_cells).parameters
