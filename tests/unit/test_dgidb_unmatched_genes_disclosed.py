"""Regression guard for Fix-R30 in dgidb_tool.py: gene/drug names DGIdb
does not recognize were dropped from the response with zero trace while
``status`` stayed ``"success"``.

Reproduced live before the fix::

    DGIdb_get_drug_gene_interactions
      {"genes": ["JAK1","JAK2","TYK2","NOTAREALGENEXYZ"],
       "interaction_types": ["inhibitor"]}
    -> "status": "success", data.genes.nodes has 3 entries,
       "metadata": {"total": 3, "genes_returned": 3, "interactions_total": 233}

Four genes were requested, three came back, and nothing in the payload said
the fourth was never matched -- ``total``/``genes_returned`` both count what
was *returned*, so they cannot reveal the loss either. Worse::

    {"genes": ["NOTAREALGENEXYZ"]}
    -> {"status": "success", "data": {"genes": {"nodes": []}},
        "metadata": {"total": 0, "genes_returned": 0}}

which is byte-indistinguishable from a real gene symbol that simply has no
drug interactions on record. A caller who typed a typo or an obsolete alias
got a confidently successful, silently incomplete answer.

The upstream cause was confirmed by querying https://dgidb.org/api/graphql
directly: DGIdb's ``names:`` filter omits unresolvable names rather than
erroring, and returns no ``errors`` key::

    {"genes": ["JAK1","NOTAREALGENEXYZ","jak2"]}
    -> {"data":{"genes":{"nodes":[{"name":"JAK2"},{"name":"JAK1"}]}}}

Note ``jak2`` -> ``JAK2``: gene matching is exact but case-insensitive
(``JAK``, ``ERBB1`` and ``HER2`` each return zero nodes, so there is no
prefix or alias resolution). Drug matching is case-insensitive *prefix*
matching instead (``imatinib`` returns both ``IMATINIB`` and ``IMATINIB
MESYLATE``), so the unmatched check has to differ per collection.

The fix reports ``metadata.unmatched_<collection>`` (echoing the caller's
original spelling) plus ``metadata.<collection>_requested``, and adds
neither key when everything matched.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.dgidb_tool import DGIdbTool, _unmatched_names

pytestmark = pytest.mark.unit


def _tool(operation):
    return DGIdbTool(
        {
            "name": f"DGIdb_{operation}",
            "type": "DGIdbTool",
            "fields": {"operation": operation},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.return_value = payload
    return r


def _gene_nodes(*names):
    return {
        "data": {
            "genes": {
                "nodes": [
                    {"name": n, "longName": f"{n} long", "interactions": []}
                    for n in names
                ]
            }
        }
    }


class TestUnmatchedNamesHelper:
    def test_exact_match_is_case_insensitive(self):
        nodes = [{"name": "JAK1"}, {"name": "JAK2"}]
        assert _unmatched_names(["JAK1", "jak2"], nodes) == []

    def test_reports_callers_original_spelling(self):
        nodes = [{"name": "JAK1"}]
        assert _unmatched_names(["JAK1", "NotARealGeneXyz"], nodes) == [
            "NotARealGeneXyz"
        ]

    def test_drug_prefix_match_does_not_flag_expanded_records(self):
        # DGIdb answers "imatinib" with IMATINIB *and* IMATINIB MESYLATE.
        nodes = [{"name": "IMATINIB"}, {"name": "IMATINIB MESYLATE"}]
        assert _unmatched_names(["imatinib"], nodes, prefix_match=True) == []
        assert _unmatched_names(["gleevec"], nodes, prefix_match=True) == ["gleevec"]

    def test_exact_mode_would_not_be_used_for_drugs(self):
        # Guards the reason prefix_match exists at all.
        nodes = [{"name": "ERLOTINIB HYDROCHLORIDE"}]
        assert _unmatched_names(["erlotinib"], nodes) == ["erlotinib"]
        assert _unmatched_names(["erlotinib"], nodes, prefix_match=True) == []


class TestInteractionsDisclosure:
    def test_mixed_request_names_the_unmatched_gene(self):
        tool = _tool("interactions")
        payload = _gene_nodes("JAK1", "JAK2", "TYK2")
        with patch(
            "tooluniverse.dgidb_tool.requests.post", return_value=_resp(payload)
        ):
            result = tool.run(
                {"genes": ["JAK1", "JAK2", "TYK2", "NOTAREALGENEXYZ"]},
            )

        assert result["status"] == "success"
        meta = result["metadata"]
        assert meta["unmatched_genes"] == ["NOTAREALGENEXYZ"]
        assert meta["genes_requested"] == 4
        assert meta["genes_returned"] == 3

    def test_all_invalid_request_is_no_longer_mistakable_for_no_interactions(self):
        tool = _tool("interactions")
        with patch(
            "tooluniverse.dgidb_tool.requests.post",
            return_value=_resp(_gene_nodes()),
        ):
            unknown = tool.run({"genes": ["NOTAREALGENEXYZ"]})
        with patch(
            "tooluniverse.dgidb_tool.requests.post",
            return_value=_resp(_gene_nodes("JAK1")),
        ):
            real_but_empty = tool.run({"genes": ["JAK1"]})

        assert unknown["metadata"]["unmatched_genes"] == ["NOTAREALGENEXYZ"]
        assert "unmatched_genes" not in real_but_empty["metadata"]
        assert unknown["metadata"] != real_but_empty["metadata"]

    def test_all_valid_request_adds_no_noise(self):
        tool = _tool("interactions")
        with patch(
            "tooluniverse.dgidb_tool.requests.post",
            return_value=_resp(_gene_nodes("JAK1", "JAK2")),
        ):
            result = tool.run({"genes": ["JAK1", "JAK2"]})

        assert result["metadata"] == {"total": 2, "genes_returned": 2}

    def test_case_difference_alone_is_not_reported_as_unmatched(self):
        tool = _tool("interactions")
        with patch(
            "tooluniverse.dgidb_tool.requests.post",
            return_value=_resp(_gene_nodes("JAK1", "JAK2")),
        ):
            result = tool.run({"genes": ["jak1", "JAK2"]})

        assert "unmatched_genes" not in result["metadata"]


class TestSiblingToolsShareTheDisclosure:
    @pytest.mark.parametrize("operation", ["genes", "categories"])
    def test_gene_operations_disclose_unmatched(self, operation):
        tool = _tool(operation)
        with patch(
            "tooluniverse.dgidb_tool.requests.post",
            return_value=_resp(_gene_nodes("EGFR")),
        ):
            result = tool.run({"genes": ["EGFR", "NOTAREALGENEXYZ"]})

        assert result["metadata"]["unmatched_genes"] == ["NOTAREALGENEXYZ"]
        assert result["metadata"]["genes_requested"] == 2

    def test_drug_operation_discloses_unmatched(self):
        tool = _tool("drugs")
        payload = {
            "data": {
                "drugs": {
                    "nodes": [
                        {"name": "IMATINIB", "conceptId": "rxcui:282388"},
                        {"name": "IMATINIB MESYLATE", "conceptId": "chembl:CHEMBL1642"},
                    ]
                }
            }
        }
        with patch(
            "tooluniverse.dgidb_tool.requests.post", return_value=_resp(payload)
        ):
            result = tool.run({"drugs": ["imatinib", "NOTAREALDRUGXYZ"]})

        assert result["metadata"]["unmatched_drugs"] == ["NOTAREALDRUGXYZ"]
        assert result["metadata"]["drugs_requested"] == 2

    def test_drug_operation_adds_no_noise_when_all_matched(self):
        tool = _tool("drugs")
        payload = {"data": {"drugs": {"nodes": [{"name": "IMATINIB"}]}}}
        with patch(
            "tooluniverse.dgidb_tool.requests.post", return_value=_resp(payload)
        ):
            result = tool.run({"drugs": ["imatinib"]})

        assert result["metadata"] == {"total": 1, "drugs_returned": 1}


class TestErrorPathUnchanged:
    def test_graphql_errors_still_short_circuit(self):
        tool = _tool("interactions")
        with patch(
            "tooluniverse.dgidb_tool.requests.post",
            return_value=_resp({"errors": [{"message": "boom"}]}),
        ):
            result = tool.run({"genes": ["JAK1"]})

        assert result["status"] == "error"
        assert "metadata" not in result
