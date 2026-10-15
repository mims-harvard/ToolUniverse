"""Unit tests for resolve_identifier_for_gene_or_protein.

These cover the parts that must not depend on a live upstream: namespace
detection (where an ordering mistake silently rewrites the caller's query into a
different namespace), source-payload parsing, and concordance ranking.
"""

from tooluniverse.compound_identifier_tool import (
    _BRIDGEDB_SOURCE,
    _ENSEMBL_DB,
    _SPECIES,
    _UNIPROT_FROM_DB,
    ENSEMBL_GENE,
    ENSEMBL_PROTEIN,
    ENSEMBL_TRANSCRIPT,
    ENTREZ,
    GENE_SYMBOL,
    HGNC,
    REFSEQ_PROTEIN,
    REFSEQ_RNA,
    UNIPROT,
    CompoundIdentifierResolutionTool,
    _drop_gprofiler_sentinel,
    _empty_resolution_error,
    _normalize_value,
    _species_from_identifier,
)


def _tool():
    return CompoundIdentifierResolutionTool(
        {
            "name": "resolve_identifier_for_gene_or_protein",
            "type": "CompoundIdentifierResolutionTool",
            "parameter": {"type": "object", "properties": {}},
        }
    )


def test_detects_each_supported_namespace():
    detect = CompoundIdentifierResolutionTool.detect
    assert detect("ENSG00000141510")[0] == ENSEMBL_GENE
    assert detect("ENST00000269305")[0] == ENSEMBL_TRANSCRIPT
    assert detect("ENSP00000269305")[0] == ENSEMBL_PROTEIN
    assert detect("HGNC:11998")[0] == HGNC
    assert detect("NM_000546")[0] == REFSEQ_RNA
    assert detect("NP_000537.3")[0] == REFSEQ_PROTEIN
    assert detect("P04637")[0] == UNIPROT
    assert detect("7157")[0] == ENTREZ
    assert detect("TP53")[0] == GENE_SYMBOL


def test_uniprot_accession_wins_over_gene_symbol():
    """Detector order is load-bearing.

    'P04637' also satisfies the permissive gene-symbol grammar. If the symbol
    pattern were tried first, the tool would query MyGene for a gene named
    'P04637' and route UniProt ID mapping with from_db=Gene_Name — resolving a
    real accession as though it were a symbol.
    """
    namespace, confidence, alternatives = CompoundIdentifierResolutionTool.detect(
        "P04637"
    )
    assert namespace == UNIPROT
    assert confidence == "high"
    assert GENE_SYMBOL in alternatives


def test_versioned_and_unrecognized_identifiers():
    detect = CompoundIdentifierResolutionTool.detect
    # Versioned Ensembl IDs are still Ensembl IDs.
    assert detect("ENSG00000141510.18")[0] == ENSEMBL_GENE
    # A bare integer is only a low-confidence Entrez guess.
    assert detect("7157")[1] == "low"
    assert detect("!!!")[0] is None
    assert detect("")[0] is None


def test_run_rejects_bad_input_without_raising():
    tool = _tool()
    assert tool.run({})["status"] == "error"
    assert tool.run({"identifier": "   "})["status"] == "error"

    unknown_ns = tool.run({"identifier": "TP53", "namespace": "pubchem_cid"})
    assert unknown_ns["status"] == "error"
    assert "pubchem_cid" in unknown_ns["error"]

    unresolvable = tool.run({"identifier": "!!!not an id!!!"})
    assert unresolvable["status"] == "error"
    # The error must point somewhere useful, not just refuse.
    assert "namespace" in unresolvable["error"]

    bad_source = tool.run({"identifier": "TP53", "sources": ["nope"]})
    assert bad_source["status"] == "error"
    assert "nope" in bad_source["error"]


def test_resolving_nothing_is_an_error_that_says_which_kind():
    """Regression: a nonexistent identifier returned success with no results.

    'ZZZFAKEGENE1' came back as status success with identifiers {}, which reads
    as an identifier that maps to nothing. Whether the resolvers looked and
    found nothing, or never answered, changes what that means entirely, so the
    two are reported differently.
    """
    # Every resolver answered and none held it: probably not a real identifier.
    looked = _empty_resolution_error(
        "ZZZFAKEGENE1", GENE_SYMBOL, ["mygene", "bridgedb", "gprofiler"], []
    )
    assert "ZZZFAKEGENE1" in looked
    assert "3 resolver(s) answered" in looked
    assert "probably not a current identifier" in looked

    # Every resolver failed: the emptiness says nothing about the identifier.
    unanswered = _empty_resolution_error(
        "TP53", GENE_SYMBOL, ["mygene"], ["mygene: HTTP 500"]
    )
    assert "not evidence the identifier does not exist" in unanswered
    assert "HTTP 500" in unanswered
    assert "probably not a current identifier" not in unanswered

    # A partial failure still counts the resolvers that did answer.
    partial = _empty_resolution_error(
        "TP53", GENE_SYMBOL, ["mygene", "bridgedb"], ["mygene: HTTP 500"]
    )
    assert "1 resolver(s) answered" in partial


def test_normalize_value_collapses_hgnc_forms_and_drops_empties():
    # MyGene reports 11998, BridgeDb reports HGNC:11998. If these stay distinct
    # the same identifier occupies two rows, each with half the concordance.
    assert _normalize_value(HGNC, 11998) == "HGNC:11998"
    assert _normalize_value(HGNC, "HGNC:11998") == "HGNC:11998"
    assert _normalize_value(HGNC, "hgnc:11998") == "hgnc:11998"
    assert _normalize_value(GENE_SYMBOL, "  TP53 ") == "TP53"
    assert _normalize_value(GENE_SYMBOL, "   ") is None
    assert _normalize_value(GENE_SYMBOL, None) is None
    assert _normalize_value("not_a_namespace", "TP53") is None


def test_normalize_value_strips_version_suffixes_but_not_isoforms():
    """Regression: g:Profiler's agreement was being discarded.

    g:Convert answers 'P04637.307' where MyGene, BridgeDb and UniProt answer
    'P04637', so the accession appeared twice — once at concordance 3 and once
    at 1 — instead of once at 4.
    """
    assert _normalize_value(UNIPROT, "P04637.307") == "P04637"
    assert _normalize_value(REFSEQ_PROTEIN, "NP_000537.3") == "NP_000537"
    assert _normalize_value(REFSEQ_RNA, "NM_000546.6") == "NM_000546"
    assert _normalize_value(ENSEMBL_GENE, "ENSG00000141510.18") == "ENSG00000141510"

    # An isoform is a different molecule, not a version, and must survive.
    assert _normalize_value(UNIPROT, "P04637-1") == "P04637-1"
    # Symbols are not accessions; a dot in one is part of the name.
    assert _normalize_value(GENE_SYMBOL, "TP53.1") == "TP53.1"


def _entry(order, *sources):
    return {"sources": set(sources), "order": order}


def test_rank_orders_by_concordance_and_caps():
    tool = _tool()
    found = {
        UNIPROT: {
            "E7EMR6": _entry(0, "bridgedb"),
            "P04637": _entry(1, "mygene", "bridgedb", "uniprot_idmap"),
        },
        GENE_SYMBOL: {f"SYM{i}": _entry(i, "mygene") for i in range(15)},
    }

    ranked, truncated = tool._rank(found)

    # Concordance beats arrival order.
    assert ranked[UNIPROT][0]["value"] == "P04637"
    assert ranked[UNIPROT][0]["concordance"] == 3
    assert ranked[UNIPROT][0]["sources"] == ["bridgedb", "mygene", "uniprot_idmap"]
    assert "_order" not in ranked[UNIPROT][0]
    assert GENE_SYMBOL in truncated
    assert len(ranked[GENE_SYMBOL]) == tool.VALUES_PER_NAMESPACE
    assert UNIPROT not in truncated


def test_rank_breaks_concordance_ties_by_arrival_not_alphabetically():
    """Regression: mouse Trp53 resolved to the wrong Ensembl gene.

    MyGene returns [ENSMUSG00000059552, ENSMSIG00000025886] — the reference
    assembly first. Both carry one source, so an alphabetical tie-break put
    ENSMSIG (Mus spretus) ahead of ENSMUSG (Mus musculus) and the tool answered
    with a different species' gene.
    """
    tool = _tool()
    found = {
        ENSEMBL_GENE: {
            "ENSMUSG00000059552": _entry(0, "mygene"),
            "ENSMSIG00000025886": _entry(1, "mygene"),
        }
    }
    ranked, _ = tool._rank(found)
    assert [row["value"] for row in ranked[ENSEMBL_GENE]] == [
        "ENSMUSG00000059552",
        "ENSMSIG00000025886",
    ]


def test_species_vocabularies_are_translated_per_resolver():
    """g:Profiler wants 'mmusculus', BridgeDb wants 'Mouse'.

    Passing MyGene's 'mouse' through unchanged made g:Profiler return HTTP 400
    and left BridgeDb silently querying its default human namespace — a source
    that reported success while contributing nothing.
    """
    assert _SPECIES["mouse"][:2] == ("mmusculus", "Mouse")
    assert _SPECIES["10090"][:2] == ("mmusculus", "Mouse")
    assert _SPECIES["human"][:2] == ("hsapiens", "Human")
    assert _SPECIES.get("nonexistent species") is None

    # Every entry must also carry a taxon: run() derives UniProt's tax_id from
    # it, and UniProt ID mapping is not species-aware without one — unfiltered
    # 'TP53' maps to a spread of vertebrate p53s that need not include P04637.
    assert _SPECIES["human"][2] == 9606
    assert _SPECIES["mouse"][2] == 10090
    assert all(isinstance(entry[2], int) for entry in _SPECIES.values())


def test_unknown_species_skips_organism_specific_sources_audibly():
    tool = _tool()
    skipped = []

    def note(source, reason):
        skipped.append((source, reason))

    def call(*_args, **_kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("resolver must not be queried for an unknown species")

    tool._from_gprofiler(call, lambda *a: None, note, "Trp53", GENE_SYMBOL, "wombat")
    tool._from_bridgedb(call, lambda *a: None, note, "Trp53", GENE_SYMBOL, "wombat")

    assert [s for s, _ in skipped] == ["gprofiler", "bridgedb"]
    # The reason must name the species, so the caller can correct the call.
    assert all("wombat" in reason for _, reason in skipped)


def test_uniprot_input_skips_the_uniprot_resolver():
    """UniProt rejects a UniProtKB-to-UniProtKB conversion.

    from_db=UniProtKB_AC-ID with to_db=UniProtKB-Swiss-Prot returns the input in
    failed_ids, so the call spends a job submission to learn nothing. It is also
    why UNIPROT carries no entry in the from_db table.
    """
    assert UNIPROT not in _UNIPROT_FROM_DB

    tool = _tool()
    skipped = []

    def call(*_args, **_kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("uniprot_idmap must not be called for UniProt input")

    tool._from_uniprot(
        call, lambda *a: None, lambda s, r: skipped.append(s), "P04637", UNIPROT, 9606
    )
    assert skipped == ["uniprot_idmap"]


def test_outbound_queries_use_the_unversioned_identifier():
    """UniProt rejects versioned ids for RefSeq_Nucleotide and Ensembl.

    'NM_000546.6' comes back in failed_ids while 'NM_000546' resolves, so
    forwarding the caller's literal silently loses the whole source.
    """
    tool = _tool()
    sent = {}

    def call(_source, _tool_name, args):
        sent.update(args)
        return {"status": "success", "data": {"results": []}}

    tool._from_uniprot(
        call, lambda *a: None, lambda *a: None, "NM_000546", REFSEQ_RNA, 9606
    )
    assert sent["ids"] == "NM_000546"
    assert sent["from_db"] == "RefSeq_Nucleotide"
    assert sent["tax_id"] == 9606


def test_species_is_inferred_from_an_ensembl_stable_id():
    """An Ensembl ID names its own species; defaulting to human loses sources.

    'ENSMUSG00000059552' resolved with UniProt at concordance 1 instead of 4,
    because UniProt, g:Profiler and BridgeDb were all pointed at human, where
    they found nothing and reported no failure.
    """
    assert _species_from_identifier("ENSMUSG00000059552") == ("mouse", None)
    assert _species_from_identifier("ENSRNOG00000010756") == ("rat", None)
    assert _species_from_identifier("ENSG00000141510") == ("human", None)
    assert _species_from_identifier("ENSP00000269305") == ("human", None)
    # A species with no resolver vocabulary is reported, never silently human.
    assert _species_from_identifier("ENSCAFG00000028805") == (None, "CAF")
    # Non-Ensembl identifiers imply nothing.
    assert _species_from_identifier("TP53") == (None, None)
    assert _species_from_identifier("P04637") == (None, None)


def test_gprofiler_sentinel_is_not_recorded_as_an_identifier():
    """Regression: the literal string 'None' was filed as a gene symbol.

    g:Convert fills every field of an unmapped row with 'None' — converted,
    name and description alike — so filtering only the conversion let the
    sentinel through as a symbol.
    """
    assert _drop_gprofiler_sentinel("None") is None
    assert _drop_gprofiler_sentinel("none") is None
    assert _drop_gprofiler_sentinel(None) is None
    assert _drop_gprofiler_sentinel("TP53") == "TP53"

    tool = _tool()
    recorded = []
    unmapped = [{"incoming": "ENSCAFG00000028805", "converted": "None", "name": "None"}]
    tool._from_gprofiler(
        lambda *a, **k: {"status": "success", "data": unmapped},
        lambda ns, value, source: recorded.append((ns, value)),
        lambda *a: None,
        "ENSCAFG00000028805",
        GENE_SYMBOL,
        "human",
    )
    assert all(value is None for _, value in recorded)


def test_mygene_symbol_query_covers_aliases_without_matching_paralogs():
    """Both halves of this query are load-bearing.

    Unscoped, 'TP53' full-text matches paralogs like TP53TG3. Scoped to `symbol`
    alone, a withdrawn symbol such as SEPT9 or MARCH1 matches nothing and MyGene
    contributes no Entrez or Ensembl at all — SEPT9 resolved with no Entrez and
    MARCH1 with neither Entrez nor Ensembl.
    """
    tool = _tool()
    sent = {}

    def call(_source, _tool_name, args):
        sent.update(args)
        return {"status": "success", "data": {"hits": []}}

    tool._from_mygene(call, lambda *a: None, "SEPT9", GENE_SYMBOL, "human")
    assert sent["query"] == 'symbol:"SEPT9" OR alias:"SEPT9"'

    # A hyphen is a Lucene operator; quoting keeps 'HLA-A' a single term.
    tool._from_mygene(call, lambda *a: None, "HLA-A", GENE_SYMBOL, "human")
    assert sent["query"] == 'symbol:"HLA-A" OR alias:"HLA-A"'

    # Accession namespaces are looked up literally, never field-scoped.
    tool._from_mygene(call, lambda *a: None, "P04637", UNIPROT, "human")
    assert sent["query"] == "P04637"


def test_notes_flag_a_tie_at_the_top_of_a_namespace():
    """Ranking implies precision the data may not have.

    AKAP17A is pseudoautosomal: its X and Y Ensembl IDs are both reported by
    three sources. Ordering them puts one first, but the order between tied
    values is only the order the sources answered in.
    """
    tool = _tool()
    tied = " ".join(
        tool._notes(
            {
                ENSEMBL_GENE: [
                    {"value": "ENSG00000292343", "concordance": 3},
                    {"value": "ENSG00000197976", "concordance": 3},
                ]
            },
            [],
            [],
            [],
            "high",
            [],
            None,
            GENE_SYMBOL,
        )
    )
    assert "tied" in tied and ENSEMBL_GENE in tied

    clear = " ".join(
        tool._notes(
            {
                ENSEMBL_GENE: [
                    {"value": "ENSG00000141510", "concordance": 3},
                    {"value": "ENSG00000999999", "concordance": 1},
                ]
            },
            [],
            [],
            [],
            "high",
            [],
            None,
            GENE_SYMBOL,
        )
    )
    assert "tied" not in clear


def test_notes_flag_a_symbol_that_resolved_through_an_alias():
    tool = _tool()
    renamed = " ".join(
        tool._notes(
            {}, [], [], [], "medium", [], None, GENE_SYMBOL, None, None, "SEPTIN9"
        )
    )
    assert "not the current one" in renamed and "SEPTIN9" in renamed

    current = " ".join(
        tool._notes({}, [], [], [], "medium", [], None, GENE_SYMBOL, None, None, None)
    )
    assert "not the current one" not in current


def test_structural_skips_are_reported_not_silent():
    """Regression: a requested resolver could vanish without a trace.

    sources=['ensembl_xrefs'] with a symbol returned values=0, queried=0,
    failed=0, skipped=0 — the caller asked for one resolver and got an empty
    table with no indication of why.
    """
    tool = _tool()

    def call(*_args, **_kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("an inapplicable resolver must not be called")

    def invoke(name, extra):
        skipped = []
        getattr(tool, name)(
            call, lambda *a: None, lambda s, r: skipped.append((s, r)), *extra
        )
        return skipped

    for name, extra, source in (
        ("_from_ensembl", ("TP53", GENE_SYMBOL), "ensembl_xrefs"),
        ("_from_bridgedb", ("NM_000546", REFSEQ_RNA, "human"), "bridgedb"),
        ("_from_uniprot", ("P04637", UNIPROT, 9606), "uniprot_idmap"),
    ):
        skipped = invoke(name, extra)
        assert [s for s, _ in skipped] == [source], f"{source} skipped silently"
        # The reason must name what could not be done, not just say "skipped".
        assert len(skipped[0][1]) > 20


def test_bridgedb_uses_the_accession_space_for_hgnc_ids():
    """'H' is BridgeDb's HGNC symbol space, 'Hac' its accession space.

    BridgeDb accepts 'HGNC:11998' against 'H' and returns zero rows, so the
    wrong code reads as a resolver that ran and simply found nothing.
    """
    assert _BRIDGEDB_SOURCE[GENE_SYMBOL] == "H"
    assert _BRIDGEDB_SOURCE[HGNC] == "Hac"


def test_ensembl_xrefs_read_the_right_field_per_namespace():
    """Regression: 'HGNC:11998' was filed as a gene symbol.

    The HGNC xref carries primary_id 'HGNC:11998' and display_id 'TP53', so a
    single field cannot serve both namespaces. UniProt is the mirror case: its
    display_id is the versioned 'P04637.312', so only primary_id is usable.
    """
    assert _ENSEMBL_DB["HGNC"] == (HGNC, GENE_SYMBOL)
    assert _ENSEMBL_DB["EntrezGene"] == (ENTREZ, GENE_SYMBOL)
    assert _ENSEMBL_DB["Uniprot/SWISSPROT"] == (UNIPROT, None)
    # Uniprot_gn's primary_id is an arbitrary TrEMBL accession, not the
    # reviewed one, so only the symbol it displays is taken.
    assert _ENSEMBL_DB["Uniprot_gn"] == (None, GENE_SYMBOL)

    tool = _tool()
    recorded = []
    rows = [
        {"dbname": "HGNC", "primary_id": "HGNC:11998", "display_id": "TP53"},
        {
            "dbname": "Uniprot/SWISSPROT",
            "primary_id": "P04637",
            "display_id": "P04637.312",
        },
        {"dbname": "Uniprot_gn", "primary_id": "A0A386NBZ1", "display_id": "TP53"},
        {"dbname": "PDB", "primary_id": "1OLG", "display_id": "1OLG"},
    ]
    tool._from_ensembl(
        lambda *a, **k: {"status": "success", "data": rows},
        lambda ns, value, source: recorded.append((ns, value)),
        lambda *a: None,
        "ENSG00000141510",
        ENSEMBL_GENE,
    )

    assert (HGNC, "HGNC:11998") in recorded
    assert (GENE_SYMBOL, "TP53") in recorded
    assert (UNIPROT, "P04637") in recorded
    # The versioned display form and the unmapped PDB xref must not leak in.
    assert (UNIPROT, "P04637.312") not in recorded
    assert not any(value == "1OLG" for _, value in recorded)
    assert (GENE_SYMBOL, "HGNC:11998") not in recorded


def test_notes_explain_failures_truncation_and_guessing():
    tool = _tool()
    notes = tool._notes(
        identifiers={UNIPROT: [{"value": "P04637"}, {"value": "E7EMR6"}]},
        sources_failed=["bridgedb: HTTP 500"],
        sources_skipped=["gprofiler: no organism code for 'wombat'"],
        truncated=[UNIPROT],
        confidence="low",
        alternatives=[GENE_SYMBOL],
        override=None,
        namespace=ENTREZ,
    )
    joined = " ".join(notes)
    # Both shortfalls are named, and counted together rather than as failures.
    assert "sources_failed" in joined and "sources_skipped" in joined
    assert "2 source(s) did not contribute" in joined
    assert "entrez_gene" in joined and "PubChem" in joined
    assert "TrEMBL" in joined

    # An overridden namespace is not a guess, so it must not be hedged as one.
    clean = tool._notes({}, [], [], [], "overridden", [], "entrez_gene", ENTREZ)
    assert not any("confidence" in n for n in clean)


def test_notes_count_only_the_shortfalls_that_occurred():
    tool = _tool()
    only_failed = " ".join(tool._notes({}, ["a: boom"], [], [], "high", [], None, HGNC))
    assert "1 source(s) did not contribute" in only_failed
    assert "sources_skipped" not in only_failed

    only_skipped = " ".join(
        tool._notes({}, [], ["b: no vocab"], [], "high", [], None, HGNC)
    )
    assert "sources_skipped" in only_skipped
    assert "sources_failed" not in only_skipped

    neither = " ".join(tool._notes({}, [], [], [], "high", [], None, HGNC))
    assert "did not contribute" not in neither
