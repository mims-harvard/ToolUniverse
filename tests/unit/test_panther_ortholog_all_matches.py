"""Regression guard for PANTHER_ortholog publishing every ortholog match.

PANTHER's ortholog/matchortho endpoint returns a bare object when exactly one
ortholog matches and a JSON list when several do. The tool collapsed the list
with `mapped = mapped[0]`, so every match past the first was discarded without
any indication that data had been dropped -- including under
`ortholog_type='O'`, whose own parameter description promises "all orthologs".

Confirmed live against https://pantherdb.org/services/oai/pantherdb before the
fix: human ABCB1 -> mouse (orthologType=O) returns two rows, Abcb1b (O) and
Abcb1a (LDO). The tool published only Abcb1b, silently losing Abcb1a -- the
P-glycoprotein paralogue pair that makes mouse Abcb1a/1b the standard model
for human ABCB1 efflux, so dropping one is a substantive loss for anyone
mapping human transporter biology onto a mouse model.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.panther_tool import PANTHERTool

pytestmark = pytest.mark.unit


def _tool():
    return PANTHERTool({"fields": {"endpoint_type": "ortholog"}})


def _resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status.return_value = None
    r.json.return_value = payload
    return r


# Trimmed from the real live payload for
# geneInputList=ABCB1&organism=9606&targetOrganism=10090&orthologType=O
_ABCB1B = {
    "target_gene_symbol": "Abcb1b",
    "persistent_id": "PTN002516972",
    "target_persistent_id": "PTN000657248",
    "ortholog": "O",
    "gene": "HUMAN|HGNC=40|UniProtKB=P08183",
    "target_gene": "MOUSE|MGI=MGI=97568|UniProtKB=P06795",
    "id": "ABCB1",
}
_ABCB1A = {
    "target_gene_symbol": "Abcb1a",
    "persistent_id": "PTN002516972",
    "target_persistent_id": "PTN000657251",
    "ortholog": "LDO",
    "gene": "HUMAN|HGNC=40|UniProtKB=P08183",
    "target_gene": "MOUSE|MGI=MGI=97570|UniProtKB=P21447",
    "id": "ABCB1",
}


def _payload(mapped):
    return {"search": {"mapping": {"mapped": mapped}}}


def _run(mapped, **overrides):
    args = {
        "gene_id": "ABCB1",
        "organism": 9606,
        "target_organism": 10090,
        "ortholog_type": "O",
    }
    args.update(overrides)
    with patch(
        "tooluniverse.panther_tool.requests.get",
        return_value=_resp(_payload(mapped)),
    ):
        return _tool().run(args)


class TestEveryOrthologIsPublished:
    def test_second_ortholog_is_not_dropped(self):
        """The assertion that bites: reverting to `mapped[0]` loses Abcb1a."""
        result = _run([_ABCB1B, _ABCB1A])

        symbols = [m["target_gene_symbol"] for m in result["data"]["mappings"]]
        assert symbols == ["Abcb1b", "Abcb1a"]

    def test_total_mappings_matches_the_rows_beside_it(self):
        result = _run([_ABCB1B, _ABCB1A])

        data = result["data"]
        assert data["total_mappings"] == 2
        assert data["total_mappings"] == len(data["mappings"])

    def test_ortholog_type_is_carried_per_match_not_flattened(self):
        """Abcb1b is an O and Abcb1a an LDO -- one shared value would be wrong."""
        result = _run([_ABCB1B, _ABCB1A])

        assert [m["ortholog_type"] for m in result["data"]["mappings"]] == ["O", "LDO"]


class TestSingleAndEmptyShapes:
    def test_bare_object_response_still_parses(self):
        """PANTHER sends a dict, not a list, when exactly one ortholog matches."""
        result = _run(_ABCB1A, ortholog_type="LDO")

        data = result["data"]
        assert data["total_mappings"] == 1
        assert data["mappings"][0]["target_gene_symbol"] == "Abcb1a"

    def test_no_match_reports_zero_rather_than_a_phantom_row(self):
        result = _run({})

        data = result["data"]
        assert data["mappings"] == []
        assert data["total_mappings"] == 0
        assert data["mapping"] is None


class TestBackwardCompatibleSingularField:
    def test_mapping_remains_the_first_match(self):
        result = _run([_ABCB1B, _ABCB1A])

        data = result["data"]
        assert data["mapping"] == data["mappings"][0]
        assert data["mapping"]["target_gene_symbol"] == "Abcb1b"
