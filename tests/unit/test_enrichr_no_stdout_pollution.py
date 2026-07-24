"""Regression guard: EnrichrTool must not print to stdout.

EnrichrTool emitted diagnostic lines via print() (e.g.
"[enrichr_api] Using the official gene name: 'IL6' instead of IL6" and
"Official gene names: [...]"). Because tool output is consumed as JSON by the
CLI / MCP / SDK, those lines polluted stdout and broke `tu run ... | jq`. The
messages were moved to logger.debug so they no longer contaminate stdout.
"""
import io
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.enrichr_tool import EnrichrTool


def _tool():
    return EnrichrTool(
        {
            "name": "enrichr_gene_enrichment_analysis",
            "type": "EnrichrTool",
            "parameter": {"type": "object", "properties": {}},
        }
    )


@pytest.mark.unit
def test_source_has_no_print_calls():
    src = Path("src/tooluniverse/enrichr_tool.py").read_text()
    assert "print(" not in src


@pytest.mark.unit
def test_get_official_gene_name_writes_nothing_to_stdout():
    class _Resp:
        status_code = 200
        ok = True

        def json(self):
            return {"hits": [{"symbol": "IL6", "alias": ["IFNB2"]}]}

    buf = io.StringIO()
    with patch("tooluniverse.enrichr_tool.requests.get", return_value=_Resp()):
        with redirect_stdout(buf):
            symbol = _tool().get_official_gene_name("il6")
    assert symbol == "IL6"
    assert buf.getvalue() == ""
