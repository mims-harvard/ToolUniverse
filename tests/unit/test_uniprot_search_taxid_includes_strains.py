"""Regression guard: UniProt_search must scope numeric taxonomy IDs with
``taxonomy_id:``, not ``organism_id:``.

UniProt's field configuration
(https://rest.uniprot.org/configure/uniprotkb/search-fields) documents these
as two distinct fields:

* ``organism_name`` / ``organism_id`` -- label "Organism [OS]" -- matches the
  entry's OWN organism node, exactly.
* ``taxonomy_name`` / ``taxonomy_id`` -- label "Taxonomy [OC]" -- matches
  anywhere in the entry's taxonomic LINEAGE, i.e. includes descendant strains.

Almost every bacterial UniProtKB entry is annotated at STRAIN level rather than
species level, so scoping a species-level taxid with ``organism_id`` silently
returns 0 hits or a large undercount -- a confident empty answer for a protein
that plainly exists. Measured live against rest.uniprot.org with ``size=0``
(X-Total-Results header):

    gene:gyrA AND <field>:1423 AND reviewed:true  ->   0 vs   1  (B. subtilis)
    gene:recA AND <field>:562                     ->   9 vs  30  (E. coli)
    gene:katG AND <field>:1773                    -> 105 vs 157  (M. tuberculosis)
    gene:TP53 AND <field>:9606                    -> 114 vs 114  (human, identical)

``organism_id:1423`` returned 0 while P05653 (GYRA_BACSU) exists. Human and
other single-node model organisms are unaffected, so the switch is strictly an
increase in correctness.

These tests never touch the network: ``requests.get`` is mocked and the
assertions are on the ``params["query"]`` actually sent to UniProt.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.uniprot_tool import UniProtRESTTool, _uniprot_organism_filter

pytestmark = pytest.mark.unit


def _tool():
    return UniProtRESTTool(
        {
            "fields": {
                "endpoint": "https://rest.uniprot.org/uniprotkb/search",
                "search_type": "search",
            },
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _resp(payload=None):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.return_value = payload if payload is not None else {"results": []}
    r.headers = {}
    return r


def _sent_query(arguments):
    """Run the tool against a mocked UniProt and return the query it sent."""
    tool = _tool()
    with patch(
        "tooluniverse.uniprot_tool.requests.get", return_value=_resp()
    ) as mock_get:
        result = tool.run(arguments)
    assert mock_get.call_count == 1
    return mock_get.call_args.kwargs["params"]["query"], result


class TestOrganismFilterHelper:
    def test_numeric_taxid_uses_taxonomy_id_not_organism_id(self):
        # organism_id:1423 returns 0 for gyrA; taxonomy_id:1423 returns 1.
        assert _uniprot_organism_filter("1423") == "taxonomy_id:1423"

    def test_named_shortcut_resolves_to_taxonomy_id(self):
        assert _uniprot_organism_filter("human") == "taxonomy_id:9606"

    def test_non_numeric_organism_still_uses_organism_name(self):
        # organism_name already has lineage semantics (confirmed live:
        # organism_name:"Escherichia coli" == 30 == taxonomy_id:562), and
        # a name passed to a numeric-only field makes UniProt reject the
        # request with HTTP 400.
        assert (
            _uniprot_organism_filter("Escherichia coli")
            == 'organism_name:"Escherichia coli"'
        )


class TestOrganismArgument:
    def test_organism_argument_taxid_becomes_taxonomy_id(self):
        query, _ = _sent_query({"query": "gene:gyrA", "organism": "1423"})
        assert "taxonomy_id:1423" in query
        assert "organism_id:" not in query

    def test_organism_argument_common_name_becomes_taxonomy_id(self):
        query, _ = _sent_query({"query": "gene:TP53", "organism": "human"})
        assert "taxonomy_id:9606" in query
        assert "organism_id:" not in query

    def test_organism_argument_species_name_still_uses_organism_name(self):
        query, _ = _sent_query({"query": "gene:recA", "organism": "Escherichia coli"})
        assert 'organism_name:"Escherichia coli"' in query


class TestBareOrganismPrefixRewrite:
    def test_bare_organism_numeric_rewrites_to_taxonomy_id(self):
        query, _ = _sent_query({"query": "gene:gyrA AND organism:1423"})
        assert query == "gene:gyrA AND taxonomy_id:1423"

    def test_bare_organism_name_rewrites_to_organism_name(self):
        query, _ = _sent_query({"query": 'gene:recA AND organism:"Escherichia coli"'})
        assert query == 'gene:recA AND organism_name:"Escherichia coli"'


class TestCallerSuppliedOrganismIdClause:
    """The tool's own description used to tell callers to write
    'organism_id:9606', so real queries arrive with that clause already in
    them. It must be rewritten too -- and the rewrite disclosed, not silent.
    """

    def test_caller_organism_id_is_rewritten_to_taxonomy_id(self):
        query, _ = _sent_query(
            {"query": "gene:gyrA AND organism_id:1423 AND reviewed:true"}
        )
        assert query == "gene:gyrA AND taxonomy_id:1423 AND reviewed:true"
        assert "organism_id:" not in query

    def test_rewrite_is_disclosed_in_normalization_note(self):
        _, result = _sent_query({"query": "gene:gyrA AND organism_id:1423"})
        note = result["data"]["normalization_note"]
        assert "organism_id" in note and "taxonomy_id" in note
        assert "strain" in note.lower()

    def test_quoted_organism_id_is_rewritten(self):
        query, _ = _sent_query({"query": 'gene:recA AND organism_id:"562"'})
        assert query == "gene:recA AND taxonomy_id:562"

    def test_multiple_organism_id_clauses_all_rewritten(self):
        query, _ = _sent_query(
            {"query": "(organism_id:9606 OR organism_id:10090) AND gene:TP53"}
        )
        assert query == "(taxonomy_id:9606 OR taxonomy_id:10090) AND gene:TP53"

    def test_no_note_when_nothing_was_rewritten(self):
        _, result = _sent_query({"query": "gene:TP53 AND taxonomy_id:9606"})
        assert "normalization_note" not in result["data"]

    def test_note_present_with_custom_fields_branch(self):
        # The `fields` branch returns raw API results via a separate return
        # statement -- the disclosure must not be dropped there.
        _, result = _sent_query(
            {"query": "gene:gyrA AND organism_id:1423", "fields": ["accession"]}
        )
        assert "normalization_note" in result["data"]


class TestOrganismArgumentNotDoubleScoped:
    """The 'already scoped by the caller' guard has to recognise the taxonomy
    fields too, or the rewritten clause would be ANDed with a second,
    conflicting organism clause.
    """

    def test_caller_organism_id_suppresses_organism_argument(self):
        query, _ = _sent_query(
            {"query": "gene:gyrA AND organism_id:1423", "organism": "human"}
        )
        assert query == "gene:gyrA AND taxonomy_id:1423"
        assert "9606" not in query

    def test_caller_taxonomy_id_suppresses_organism_argument(self):
        query, _ = _sent_query(
            {"query": "gene:gyrA AND taxonomy_id:1423", "organism": "human"}
        )
        assert query == "gene:gyrA AND taxonomy_id:1423"

    def test_caller_taxonomy_name_suppresses_organism_argument(self):
        query, _ = _sent_query(
            {
                "query": 'gene:gyrA AND taxonomy_name:"Bacillus subtilis"',
                "organism": "human",
            }
        )
        assert query == 'gene:gyrA AND taxonomy_name:"Bacillus subtilis"'

    def test_caller_organism_name_still_suppresses_organism_argument(self):
        query, _ = _sent_query(
            {
                "query": 'gene:recA AND organism_name:"Escherichia coli"',
                "organism": "human",
            }
        )
        assert query == 'gene:recA AND organism_name:"Escherichia coli"'
