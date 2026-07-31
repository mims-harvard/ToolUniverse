"""Round 85: MSigDBTool.run() read `operation` only from the caller's own
arguments (`arguments.get("operation", "get_gene_set")`), never from the
tool config's `fields.operation`. `MSigDB_check_gene_in_set` and
`MSigDB_get_gene_set_members`'s configs both had an empty `fields` dict, so
neither tool's own documented example (which never passes `operation`
itself) ever reached its real handler -- `MSigDB_check_gene_in_set` always
silently fell through to `_get_gene_set`, meaning the `gene` parameter was
never even inspected and the tool's entire membership-check purpose was
unreachable through normal use. Confirmed live: HALLMARK_APOPTOSIS + TP53
returned the full 161-gene set dump with no `is_member` field at all.
Fixed by reading `self.operation` (set from `tool_config['fields']`) as the
fallback, matching the pattern used elsewhere in the codebase (e.g.
ComplexPortalTool), and wiring both tools' configs to their real operation.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.msigdb_tool import MSigDBTool

pytestmark = pytest.mark.unit

HALLMARK_APOPTOSIS = {
    "HALLMARK_APOPTOSIS": {
        "systematicName": "M5902",
        "collection": "H",
        "pmid": "26771021",
        "geneSymbols": ["BAX", "BID", "BAK1"],
        "briefDescription": "Genes mediating programmed cell death.",
        "externalDetailsURL": [],
    }
}


def _mock_urlopen(body):
    resp = MagicMock()
    resp.read.return_value = json.dumps(body).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def test_check_gene_in_set_reachable_without_caller_passing_operation():
    """The tool's own documented example never passes `operation` -- config
    wiring must be what routes it, not a caller-supplied override."""
    tool = MSigDBTool(
        {
            "name": "MSigDB_check_gene_in_set",
            "type": "MSigDBTool",
            "fields": {"operation": "check_gene_in_set"},
        }
    )
    with patch(
        "tooluniverse.msigdb_tool.urllib.request.urlopen",
        return_value=_mock_urlopen(HALLMARK_APOPTOSIS),
    ):
        result = tool.run({"gene_set_name": "HALLMARK_APOPTOSIS", "gene": "TP53"})

    assert result["status"] == "success"
    assert "is_member" in result["data"]
    assert result["data"]["is_member"] is False


def test_check_gene_in_set_true_for_real_member():
    tool = MSigDBTool(
        {
            "name": "MSigDB_check_gene_in_set",
            "type": "MSigDBTool",
            "fields": {"operation": "check_gene_in_set"},
        }
    )
    with patch(
        "tooluniverse.msigdb_tool.urllib.request.urlopen",
        return_value=_mock_urlopen(HALLMARK_APOPTOSIS),
    ):
        result = tool.run({"gene_set_name": "HALLMARK_APOPTOSIS", "gene": "BAX"})

    assert result["data"]["is_member"] is True
    assert result["data"]["total_genes_in_set"] == 3


def test_get_gene_set_members_still_reaches_get_gene_set():
    tool = MSigDBTool(
        {
            "name": "MSigDB_get_gene_set_members",
            "type": "MSigDBTool",
            "fields": {"operation": "get_gene_set"},
        }
    )
    with patch(
        "tooluniverse.msigdb_tool.urllib.request.urlopen",
        return_value=_mock_urlopen(HALLMARK_APOPTOSIS),
    ):
        result = tool.run({"gene_set_name": "HALLMARK_APOPTOSIS"})

    assert result["status"] == "success"
    assert result["data"]["genes"] == ["BAX", "BID", "BAK1"]
    assert result["data"]["num_genes"] == 3


def test_caller_can_still_override_operation_explicitly():
    tool = MSigDBTool(
        {
            "name": "MSigDB_check_gene_in_set",
            "type": "MSigDBTool",
            "fields": {"operation": "check_gene_in_set"},
        }
    )
    with patch(
        "tooluniverse.msigdb_tool.urllib.request.urlopen",
        return_value=_mock_urlopen(HALLMARK_APOPTOSIS),
    ):
        result = tool.run(
            {"gene_set_name": "HALLMARK_APOPTOSIS", "operation": "get_gene_set"}
        )

    assert "is_member" not in result["data"]
    assert result["data"]["genes"] == ["BAX", "BID", "BAK1"]


def test_missing_config_operation_defaults_to_get_gene_set():
    tool = MSigDBTool({"name": "x", "type": "MSigDBTool", "fields": {}})
    assert tool.operation == "get_gene_set"
