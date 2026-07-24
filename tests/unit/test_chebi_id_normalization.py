"""Unit test for ChEBI_get_compound accepting the CURIE id form.

Regression for Feature-008B-02 / 007F-01: ChEBI_search returns ids as
chebi_accession="CHEBI:27732", but ChEBI_get_compound required a bare
integer and rejected the string, breaking the natural search->get chain.
"""
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.chebi_tool import ChEBITool, _strip_html


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1<em>H</em>-purin", "1H-purin"),
        ("plain text", "plain text"),
        ("<b>bold</b> and <i>italic</i>", "bold and italic"),
        (None, None),
        (42, 42),
    ],
)
def test_strip_html(raw, expected):
    # Feature-008B-03: ChEBI embeds <em> highlight tags in name/synonym fields.
    assert _strip_html(raw) == expected


def _make_tool():
    return ChEBITool(
        {
            "name": "ChEBI_get_compound",
            "type": "ChEBITool",
            "fields": {"endpoint_type": "get_compound"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


@pytest.mark.unit
@pytest.mark.parametrize("chebi_id", [27732, "27732", "CHEBI:27732", "chebi:27732"])
def test_get_compound_accepts_int_and_curie_forms(chebi_id):
    tool = _make_tool()
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"id": 27732, "name": "caffeine", "chebi_accession": "CHEBI:27732"}

    with patch(
        "tooluniverse.chebi_tool.requests.get", return_value=resp
    ) as mock_get:
        result = tool.run({"chebi_id": chebi_id})

    # The request URL must always use the bare integer, regardless of input form.
    called_url = mock_get.call_args[0][0]
    assert called_url.endswith("/compound/27732/")
    assert result["status"] == "success"
