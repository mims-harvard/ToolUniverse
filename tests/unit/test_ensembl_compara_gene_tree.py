"""Regression guard for Fix-R26E-2: EnsemblCompara_get_gene_tree
(EnsemblComparaTool, endpoint "gene_tree") never returned usable data in
any input form, confirmed live for TP53 (the tool's own documented
example) and LYZ:

1. tree_id was read from the nonexistent data["tree"]["id"] instead of
   the real top-level data["id"] -- always null.
2. Leaf members were detected via `"species" in node`, but leaf nodes
   carry taxonomy info under "taxonomy", never "species" -- members was
   always empty.
3. `newick` was read from a "newick" JSON field that Ensembl's genetree
   endpoint never returns in JSON mode; real Newick text is only served
   via a separate request with a "text/x-nh" Content-Type header.
4. The Ensembl-gene-ID path form (`/genetree/member/id/{gene}`) 404d
   because it's missing a required {species} path segment
   (`/genetree/member/id/{species}/{gene}`).

All four are fixed in ensembl_compara_tool.py. Network mocked.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.ensembl_compara_tool import EnsemblComparaTool

pytestmark = pytest.mark.unit

_TREE_JSON = {
    "type": "gene tree",
    "rooted": 1,
    "id": "ENSGT00950000183153",
    "tree": {
        "taxonomy": {"scientific_name": "Bilateria"},
        "children": [
            {
                "id": {"source": "EnsEMBL", "accession": "ENSG00000141510"},
                "taxonomy": {"scientific_name": "Homo sapiens"},
                "branch_length": 0.01,
            },
            {
                "id": {"source": "EnsEMBL", "accession": "ENSMUSG00000059552"},
                "taxonomy": {"scientific_name": "Mus musculus"},
                "branch_length": 0.02,
            },
        ],
    },
}
_NEWICK_TEXT = "(ENSG00000141510:0.01,ENSMUSG00000059552:0.02);"


def _json_resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


def _text_resp(text, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.raise_for_status.return_value = None
    return r


def _tool():
    return EnsemblComparaTool({"fields": {"endpoint": "gene_tree"}, "timeout": 30})


class TestGeneTreeParsing:
    def test_symbol_lookup_populates_tree_id_members_and_newick(self):
        tool = _tool()
        with patch(
            "tooluniverse.ensembl_compara_tool.requests.get",
            side_effect=[_json_resp(_TREE_JSON), _text_resp(_NEWICK_TEXT)],
        ):
            result = tool.run({"gene": "TP53", "species": "human"})

        assert result["status"] == "success"
        data = result["data"]
        assert data["tree_id"] == "ENSGT00950000183153"
        assert data["newick"] == _NEWICK_TEXT
        assert data["total_members"] == 2
        assert {m["gene_id"] for m in data["members"]} == {
            "ENSG00000141510",
            "ENSMUSG00000059552",
        }
        assert {m["species"] for m in data["members"]} == {
            "Homo sapiens",
            "Mus musculus",
        }

    def test_ensembl_id_lookup_includes_species_in_path(self):
        tool = _tool()
        with patch(
            "tooluniverse.ensembl_compara_tool.requests.get",
            side_effect=[_json_resp(_TREE_JSON), _text_resp(_NEWICK_TEXT)],
        ) as mock_get:
            tool.run({"gene": "ENSG00000090382", "species": "human"})

        first_call_url = mock_get.call_args_list[0].args[0]
        assert first_call_url == (
            "https://rest.ensembl.org/genetree/member/id/human/ENSG00000090382"
        )

    def test_newick_fetch_failure_does_not_fail_whole_call(self):
        tool = _tool()
        with patch(
            "tooluniverse.ensembl_compara_tool.requests.get",
            side_effect=[_json_resp(_TREE_JSON), _text_resp("", status_code=500)],
        ):
            result = tool.run({"gene": "TP53", "species": "human"})

        assert result["status"] == "success"
        assert result["data"]["newick"] is None
        assert result["data"]["total_members"] == 2
