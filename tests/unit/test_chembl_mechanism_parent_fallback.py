"""Unit test: ChEMBL_get_drug_mechanisms resolves salt/child ids to the parent.

Regression: /mechanism.json indexes records under the PARENT molecule, but
ChEMBL_search_drugs hands back the salt/child id (dolutegravir CHEMBL1213165,
parent CHEMBL1229211). A mechanism query on the child matched nothing and
returned a silent empty ("no mechanism on file") -- breaking the common
search->mechanism chain. The tool now resolves the parent and retries once.
"""
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.chem_tool import ChEMBLRESTTool


def _tool():
    return ChEMBLRESTTool(
        {
            "name": "ChEMBL_get_drug_mechanisms",
            "type": "ChEMBLRESTTool",
            "fields": {"endpoint": "/mechanism.json"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


class _Resp:
    def __init__(self, payload):
        self._payload = payload
        self.url = "https://www.ebi.ac.uk/chembl/api/data/mechanism.json"

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.mark.unit
def test_empty_child_result_retries_with_parent():
    tool = _tool()
    # First mechanism query (child) -> empty; retry (parent) -> one mechanism.
    responses = [
        _Resp({"mechanisms": [], "page_meta": {"total_count": 0}}),
        _Resp(
            {
                "mechanisms": [
                    {"mechanism_of_action": "HIV-1 integrase inhibitor"}
                ]
            }
        ),
    ]
    with patch(
        "tooluniverse.chem_tool.request_with_retry", side_effect=responses
    ), patch.object(
        ChEMBLRESTTool, "_fetch_parent_chembl_id", return_value="CHEMBL1229211"
    ):
        result = tool.run({"chembl_id": "CHEMBL1213165"})

    mechs = result["data"]["mechanisms"]
    assert len(mechs) == 1
    assert mechs[0]["mechanism_of_action"] == "HIV-1 integrase inhibitor"
    assert result["metadata"]["resolved_parent_chembl_id"] == "CHEMBL1229211"
    assert "parent" in result["metadata"]["note"]


@pytest.mark.unit
def test_non_empty_result_does_not_retry():
    tool = _tool()
    resp = _Resp({"mechanisms": [{"mechanism_of_action": "x"}]})
    fetch_parent = MagicMock()
    with patch(
        "tooluniverse.chem_tool.request_with_retry", return_value=resp
    ), patch.object(ChEMBLRESTTool, "_fetch_parent_chembl_id", fetch_parent):
        result = tool.run({"chembl_id": "CHEMBL1229211"})
    # Already had mechanisms -> no parent lookup, no note.
    fetch_parent.assert_not_called()
    assert "metadata" not in result or "note" not in result.get("metadata", {})


@pytest.mark.unit
def test_no_parent_leaves_empty_result_unchanged():
    tool = _tool()
    resp = _Resp({"mechanisms": []})
    with patch(
        "tooluniverse.chem_tool.request_with_retry", return_value=resp
    ), patch.object(ChEMBLRESTTool, "_fetch_parent_chembl_id", return_value=None):
        result = tool.run({"chembl_id": "CHEMBL25"})
    assert result["data"]["mechanisms"] == []
