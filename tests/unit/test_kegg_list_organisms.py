"""Regression guard for Fix-R23D-1: KEGGListOrganisms hit KEGG's retired
/list/organism endpoint, which now returns HTTP 400 (confirmed live) --
the tool was completely non-functional. /list/genome serves the same
organism catalog but in a different line format ("T01001\thsa; Homo
sapiens (human)" instead of the old 3-column layout), so parsing had to
change along with the endpoint.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.kegg_tool import KEGGListOrganisms

pytestmark = pytest.mark.unit

_GENOME_LIST_TEXT = (
    "T01001\thsa; Homo sapiens (human)\nT01005\tptr; Pan troglodytes (chimpanzee)\n"
)


def _tool():
    return KEGGListOrganisms({"name": "kegg_test", "fields": {}})


def _resp(text):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    r.headers = {"content-type": "text/plain"}
    return r


class TestListOrganisms:
    def test_uses_list_genome_endpoint(self):
        tool = _tool()
        assert tool.endpoint == "/list/genome"

    def test_parses_code_and_description_from_genome_format(self):
        tool = _tool()
        resp = _resp(_GENOME_LIST_TEXT)

        with patch.object(tool.session, "get", return_value=resp):
            result = tool.run({})

        assert result["status"] == "success"
        assert result["count"] == 2
        hsa = result["data"][0]
        assert hsa["organism_code"] == "hsa"
        assert hsa["organism_name"] == "Homo sapiens (human)"
        assert hsa["kegg_genome_id"] == "T01001"
