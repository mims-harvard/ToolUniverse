"""Unit test: LipidMaps compound query rejects unknown params (no false empty).

Regression: LipidMaps_get_compound_by_xref's `xref_type` has a default
(kegg_id), so a typo'd param name like `input_type` (instead of `xref_type`) was
silently accepted and the lookup fell back to kegg_id -- a PubChem CID searched
as a KEGG id returned an empty "not found" the user wrongly trusted. The tool
now names the unrecognized parameter instead of returning a false empty.
"""
from unittest.mock import patch

import pytest

from tooluniverse.lipidmaps_tool import LipidMapsTool


def _tool():
    return LipidMapsTool(
        {
            "name": "LipidMaps_get_compound_by_xref",
            "type": "LipidMapsTool",
            "parameter": {"type": "object", "properties": {}},
            "fields": {"context": "compound", "input_item": "kegg_id"},
        }
    )


@pytest.mark.unit
def test_unknown_param_is_rejected_not_silently_ignored():
    result = _tool()._query_compound(
        {"input_value": "5997", "input_type": "pubchem_cid"}
    )
    assert result["status"] == "error"
    assert "input_type" in result["error"]
    assert "xref_type" in result["error"]


@pytest.mark.unit
def test_correct_params_pass_the_guard():
    """A recognized param set must reach the request layer, not the guard."""
    with patch.object(
        LipidMapsTool, "_make_request", return_value={"status": "success", "data": {}}
    ) as mock_req:
        result = _tool()._query_compound(
            {"input_value": "5997", "xref_type": "pubchem_cid"}
        )
    assert result["status"] == "success"
    # pubchem_cid was honored (not silently defaulted to kegg_id).
    assert "pubchem_cid/5997" in mock_req.call_args[0][0]
