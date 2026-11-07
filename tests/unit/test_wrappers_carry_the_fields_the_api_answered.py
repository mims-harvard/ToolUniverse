"""Fields the upstream answered and the wrapper did not pass on.

The sibling file `test_wrappers_ask_for_what_they_promise.py` guards the 102
tools that declare a GraphQL query, where the selection set is in the config
and can be read statically. For the other 2,786 nothing static says what the
upstream offers, so the gap has to be measured from the call the tool already
makes -- which is what `scripts/audit_upstream_field_coverage.py` does and what
the weekly sweep now runs per shard.

These are the cases that measurement found and that the judgement rule from
devtu-silent-failures then confirmed: a dropped field is a defect when it is
the substance of what the tool's own description promises. Measured live on
2026-11-07, before the fix:

    gProfiler_enrichment      no effective_domain_size, so the N of the
                              hypergeometric test was absent and the reported
                              p_value could not be recomputed; no
                              intersection_genes though the description
                              promises "intersection genes"; and
                              meta.genes_metadata.failed was dropped, so a
                              gene list with one typo in it was enriched on the
                              rest in silence.
    GxA_get_experiment_       expressions were [{tissue, value: 381.0}] with
      expression              the row's own expressionUnit ("tpms") dropped.
    GEO_search_chipseq_       n_samples: 82 and no sample accessions, while
      datasets                the description said GSM records were "excluded
                              upstream" -- true of the esearch entry-type
                              filter, not of the per-series sample list the
                              esummary answers.
    OrthoDB_search_groups     /search answers `data` (bare ids) and `bigdata`
                              (the full record: name, level_name, present_in,
                              gene_count). Only the ids were read, and a /tab
                              request per group then fetched a subset back.
    FlyBase_get_gene_         interactorARole "suppressed gene" and
      interactions            interactorBRole "suppressor gene" dropped, so a
                              suppression result named a pair and not a
                              direction; and no reference, so it could not be
                              cited.
    EBIProteins_get_hpp_      evidence source.properties -- Best Probability,
      peptides                Number of PSMs, Times of observations -- dropped
                              from "the stringent HPP evidence set".
    MaveDB_get_gnomad_        no faf95Max, the filtering allele frequency ACMG
      variants                BA1/BS1 is read against; no variantLinks, the
                              join back to the score set the tool exists for.
    DisGeNET_search_gene      7 of 37 fields: no disease_vocabularies (MONDO,
                              DO, MeSH), no scoreBreakdown, and of the
                              "evidence counts" the description promises, only
                              the PMID count.
    ComplexPortal_get_        GO cross-references without `qualifier`, which is
      complex                 the aspect ("cellular component"), and subunits
                              without bioRole or linkedFeatures.
    DOAJ_search_articles      `keywords` was built from bibjson.subject (the
                              journal's LCC class) while bibjson.keywords -- the
                              article's own terms -- was never read, so the
                              field named keywords held neither one under its
                              own name.
    Planteome_search_         no assigned_by, though the description promises
      annotations             annotations "across evidence types and source
                              databases", and no evidence_with, so an IEA could
                              not be checked.
    ExpressionAtlas_get_      said the API "does not expose per-experiment
      experiment              design ... through this endpoint". Half true:
                              experiment.experimentalFactors really is null,
                              and the design is in columnHeaders in the same
                              response, 29 assay groups the tool did not read.
    UniProtTaxonomy_get_      no otherNames, for a tool whose description calls
      taxon                   itself "essential for cross-referencing species".
    MediaDive_search_media    no link, and `description` and `reference` are
                              null for most of the catalogue.
    IDR_search_images         1,000 hits across studies with no plate, well,
                              project or dataset, so `study` named the
                              container and nothing located the image in it.
    Synapse_list_children     no benefactor_id, the entity whose access rules
                              govern the child.

NOT DEFECTS, recorded so the next sweep does not re-litigate them. The 77
`FDA_get_drug_names_by_*` tools declare `return_fields: ["openfda.brand_name",
"openfda.generic_name"]` in the config and are named for it; the label sections
they skip are what their sibling tools return. ComplexPortal's `dbdefinition`
and `qualifierDefinition` are paragraphs of ontology prose. Planteome's
`*_closure*` fields restate the term's own hierarchy. GEO's `translationstack`
and `idlist` are esearch internals, and the query expansion is already
disclosed as `query_disclosure`. MaveDB's `recordType`, `id` and
`creationDate` are database bookkeeping.
"""

import json
import pathlib

import pytest

pytestmark = pytest.mark.unit

REPO = pathlib.Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "tooluniverse"
DATA = SRC / "data"


def _source(module):
    path = SRC / module
    assert path.is_file(), f"{module} is not in src/tooluniverse"
    return path.read_text()


def _config(tool_name):
    for path in sorted(DATA.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(payload, list):
            continue
        for cfg in payload:
            if isinstance(cfg, dict) and cfg.get("name") == tool_name:
                return cfg
    raise AssertionError(f"{tool_name} is not in the catalogue")


# (wrapper module, upstream key it must read, why that key is the substance)
UPSTREAM_KEYS = [
    (
        "gprofiler_tool.py",
        "effective_domain_size",
        "N in the hypergeometric test; without it the reported p_value cannot be recomputed",
    ),
    (
        "gprofiler_tool.py",
        "intersections",
        "the intersection genes the description promises, not just their count",
    ),
    (
        "gprofiler_tool.py",
        "genes_metadata",
        "which submitted identifiers g:Profiler could not resolve",
    ),
    (
        "gxa_tool.py",
        "expressionUnit",
        "a bare 381.0 is not an expression level",
    ),
    (
        "epigenomics_tool.py",
        'uid_data.get("samples")',
        "the GSM accessions that identify the runs to download",
    ),
    (
        "epigenomics_tool.py",
        "pubmedids",
        "the publication behind the series",
    ),
    (
        "orthodb_tool.py",
        "bigdata",
        "the group records /search already returned beside the bare ids",
    ),
    (
        "orthodb_tool.py",
        'record.get("level_name")',
        "the taxonomic level a group is defined at, which is what tells two hits apart",
    ),
    (
        "alliance_genome_tool.py",
        "interactorARole",
        "which gene suppresses which; an interaction type alone has no direction",
    ),
    (
        "alliance_genome_tool.py",
        "shortCitation",
        "an interaction with no reference cannot be cited",
    ),
    (
        "ebi_proteins_ext_tool.py",
        'src.get("properties")',
        "Best Probability and the PSM counts are what make HPP evidence stringent",
    ),
    (
        "mavedb_tool.py",
        "faf95Max",
        "the filtering allele frequency ACMG BA1/BS1 thresholds are read against",
    ),
    (
        "mavedb_tool.py",
        "variantLinks",
        "the join between the score set and gnomAD, which is what the tool is for",
    ),
    (
        "disgenet_tool.py",
        "diseaseVocabularies",
        "the MONDO/DO/MeSH ids an association has to carry to be joined to anything",
    ),
    (
        "disgenet_tool.py",
        "scoreBreakdown",
        "what the association score is made of",
    ),
    (
        "disgenet_tool.py",
        "numCTsupportingAssociation",
        'an "evidence count" the description promises and only PMIDs supplied',
    ),
    (
        "complex_portal_tool.py",
        "qualifier",
        "on a GO cross-reference this is the aspect",
    ),
    (
        "complex_portal_tool.py",
        "linkedFeatures",
        "which region of a subunit binds which partner",
    ),
    (
        "complex_portal_tool.py",
        "bioRole",
        "what a subunit does in the complex, not just what it is",
    ),
    (
        "doaj_tool.py",
        'b.get("keywords")',
        "the article's own keywords, as opposed to the journal's subject class",
    ),
    (
        "doaj_tool.py",
        "affiliation",
        "what tells two authors of the same name apart",
    ),
    (
        "planteome_tool.py",
        "assigned_by",
        'the "source databases" the description promises',
    ),
    (
        "planteome_tool.py",
        "evidence_with",
        "what an IEA annotation was inferred from, which is what makes it checkable",
    ),
    (
        "expression_atlas_tool.py",
        "columnHeaders",
        "the experiment's design, in the same response that leaves experimentalFactors null",
    ),
    (
        "uniprot_taxonomy_tool.py",
        "otherNames",
        "the synonyms a cross-reference is resolved through",
    ),
    (
        "mediadive_tool.py",
        'row.get("link")',
        "the only handle on a medium whose description and reference are null",
    ),
    (
        "idr_searchengine_tool.py",
        "plate_name",
        "where a screen's image sits, which is how the paper refers to it",
    ),
    (
        "synapse_tool.py",
        "benefactorId",
        "the entity whose access rules govern the child",
    ),
]


@pytest.mark.parametrize(
    "module, key, why",
    UPSTREAM_KEYS,
    ids=[
        f"{m.removesuffix('.py')}:{k.split(chr(34))[1] if chr(34) in k else k}"
        for m, k, _ in UPSTREAM_KEYS
    ],
)
def test_the_wrapper_reads_the_field_the_api_answered(module, key, why):
    """Five of these anchors are the whole read expression, not the bare name.

    `samples`, `keywords`, `link`, `properties` and `level_name` each already
    occurred in their module before the fix -- in a docstring, in a sibling
    handler, as `reference_link` -- so a bare substring would have passed
    against the unfixed file and guarded nothing.
    """
    assert key in _source(module), (
        f"{module} does not read upstream `{key}`, which is {why}. "
        "Measured against the live API: the upstream answers it and the "
        "caller never sees it."
    )


# (tool, output field the schema must declare)
DECLARED = [
    ("gProfiler_enrichment", "effective_domain_size"),
    ("gProfiler_enrichment", "intersection_genes"),
    ("GxA_get_experiment_expression", "expression_unit"),
    ("GEO_search_chipseq_datasets", "samples"),
    ("GEO_search_chipseq_datasets", "samples_truncated"),
    ("GEO_get_dataset_details", "samples"),
    ("OrthoDB_search_groups", "level_name"),
    ("OrthoDB_search_groups", "species_count"),
    ("FlyBase_get_gene_interactions", "subject_role"),
    ("FlyBase_get_gene_interactions", "references"),
    ("EBIProteins_get_hpp_peptides", "support"),
    ("MaveDB_get_gnomad_variants", "faf95_max"),
    ("MaveDB_get_gnomad_variants", "score_set_variants"),
    ("DisGeNET_search_gene", "disease_vocabularies"),
    ("DisGeNET_search_gene", "n_clinical_trials"),
    ("ComplexPortal_get_complex", "linked_features"),
    ("ComplexPortal_get_complex", "bio_role"),
    ("DOAJ_search_articles", "subjects"),
    ("DOAJ_search_articles", "author_affiliations"),
    ("Planteome_search_annotations", "assigned_by"),
    ("ExpressionAtlas_get_experiment", "assay_groups"),
    ("UniProtTaxonomy_get_taxon", "other_names"),
    ("MediaDive_search_media", "link"),
    ("IDR_search_images", "location"),
    ("Synapse_list_children", "benefactor_id"),
]


@pytest.mark.parametrize("tool, field", DECLARED, ids=[f"{t}:{f}" for t, f in DECLARED])
def test_the_return_schema_declares_the_field_the_wrapper_now_returns(tool, field):
    """A field the caller cannot find in the schema is barely less hidden.

    The wrapper carrying it and the schema not declaring it is the shape that
    let these drops survive: an agent reads the schema to decide what a tool
    can answer.
    """
    schema = json.dumps(_config(tool).get("return_schema") or {})
    assert f'"{field}"' in schema, (
        f"{tool} returns `{field}` and its return_schema does not declare it"
    )


def test_gprofiler_says_when_it_could_not_resolve_a_gene():
    """Four genes in, one a typo, three tested, and nothing said.

    This is the paper's class in one call: the tool reported `query_size: 3`
    beside a p_value computed on three genes while the caller had submitted
    four, and `failed: ["NOTAGENE123"]` sat in the response it threw away.
    """
    source = _source("gprofiler_tool.py")
    assert "gene_resolution_warning" in source
    assert '"genes_failed"' in source
    assert '"genes_submitted"' in source
    config = _config("gProfiler_enrichment")
    assert "genes_failed" in config["description"], (
        "the disclosure is only useful if the description says it exists"
    )


def test_geo_no_longer_claims_the_sample_list_is_excluded_upstream():
    """The claim was about the esearch entry-type filter, not the sample list.

    `gse[ETYP]` does restrict the SEARCH to series. The esummary then answers
    every GSM of each series -- 82 for GSE313540 -- and the description's
    "GSM samples ... are excluded upstream" read as though that data did not
    exist.
    """
    text = (DATA / "epigenomics_tools.json").read_text()
    assert "excluded upstream" not in text, (
        "a description that says the samples are excluded upstream, beside a "
        "tool that now returns them, is worse than either alone"
    )
    assert "samples_truncated" in text


def test_doaj_keeps_the_article_keywords_apart_from_the_journal_subject():
    """The output field `keywords` used to hold `bibjson.subject`.

    Not a drop but a substitution: the LCC class "Chemical engineering" was
    returned under the name `keywords` while the article's own terms -- "oil
    palm shell", "pyrolysis" -- were never read. Both are reported now, each
    under its own name, so the next reader of this code does not re-merge them.
    """
    source = _source("doaj_tool.py")
    assert 'b.get("keywords")' in source, "the article's own keywords must be read"
    assert '"subjects": subjects' in source, (
        "the LCC classification must be reported as subjects, not as keywords"
    )


def test_expression_atlas_caveat_matches_what_the_response_holds():
    """The caveat named fields that are empty AND design data that is not.

    `experiment.experimentalFactors`, `technologyType`, `contrasts`,
    `numberOfAssays` and `pubmedIds` really are null -- measured live on
    E-MTAB-2836 -- so that half stays. The design is not missing: it is in
    `columnHeaders`, which the tool now reads.
    """
    config = _config("ExpressionAtlas_get_experiment")
    description = config["description"]
    assert "does not expose per-experiment design" not in description
    assert "assay_groups" in description
    assert "GxA_get_experiment_expression" in description, (
        "the tool that does return expression values should be named here"
    )
