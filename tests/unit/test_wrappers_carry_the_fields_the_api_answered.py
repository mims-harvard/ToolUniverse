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
    # Second round: the families the catalogue-wide run ranked highest.
    (
        "omnipath_tool.py",
        "_omnipath_references",
        "the papers behind an interaction; `sources` names the databases, not the evidence",
    ),
    (
        "omnipath_tool.py",
        '"source": item.get("source"),\n                    "consensus_score"',
        "whether an intercell row is about a protein, a complex or a miRNA",
    ),
    (
        "alliance_genome_tool.py",
        "referenceCuries",
        "the literature about the gene -- 4,461 publications on the MGI record",
    ),
    (
        "alliance_genome_tool.py",
        "geneSecondaryIds",
        "retired accessions, which is how the older literature cites the gene",
    ),
    (
        "alliance_genome_tool.py",
        "relatedNotes",
        "the curator notes the model-organism database wrote about the gene",
    ),
    (
        "alliance_genome_tool.py",
        "predictedVariantConsequences",
        "the VEP impact and transcript consequence, which is the content of an allele record",
    ),
    (
        "alliance_genome_tool.py",
        "associatedPhenotype",
        "what is wrong with the mutant strain, beside a hasPhenotype boolean that said only that something is",
    ),
    (
        "alliance_genome_tool.py",
        '"stringency": r.get("stringencyFilter"),\n                    "subject_taxon_id"',
        "which stringency band an ortholog row met, for a call that takes a stringency",
    ),
    (
        "alliance_genome_tool.py",
        "conditionRelations",
        "the conditions a phenotype was observed under",
    ),
    (
        "alliance_genome_tool.py",
        "automatedGeneDescription",
        "what a search hit is known for, so hits can be ranked without a call each",
    ),
    # Round two: the families the catalogue-wide run ranked highest.
    (
        "epigenomics_tool.py",
        'item.get("sourceIds")',
        "which ENCODE experiments support a TF cluster, beside a sourceCount that said how many",
    ),
    (
        "epigenomics_tool.py",
        'feat.get("extended_start")',
        "the Regulatory Build's flanking bounds, a different overlap question from the core ones",
    ),
    (
        "monarch_v3_tool.py",
        "knowledge_level",
        "whether a Biolink association is a curated assertion or a prediction",
    ),
    (
        "monarch_v3_tool.py",
        "has_percentage",
        "how often a phenotype occurs in the disease, not merely that it has been seen",
    ),
    (
        "monarch_v3_tool.py",
        "mapping_justification",
        "whether a cross-ontology mapping was curated or produced by a string match",
    ),
    (
        "monarch_v3_tool.py",
        "causes_disease",
        "the diseases a gene causes, in the same response as its name",
    ),
    (
        "ebi_proteins_ext_tool.py",
        "predictions",
        "SIFT and PolyPhen, dropped from a variant tool that answered the position",
    ),
    (
        "ebi_proteins_ext_tool.py",
        "populationFrequencies",
        "how common the variant is, without which a clinical significance cannot be weighed",
    ),
    (
        "ebi_proteins_ext_tool.py",
        '"consequence_type": feature.get("consequenceType")',
        "what the variant does to the protein; present on all 3,662 features of P04637",
    ),
    (
        "ebi_proteins_ext_tool.py",
        "reviewStatus",
        "what separates a reviewed ClinVar assertion from one unreviewed submission",
    ),
    (
        "ebi_proteins_ext_tool.py",
        '"exons": [',
        "the exon coordinates, beside a num_exons that was the count of them",
    ),
    (
        "ebi_proteins_ext_tool.py",
        '"ligand": {',
        "what binds at a binding site, for a feature that named only the position",
    ),
    (
        "sgd_tool.py",
        'i.get("bait_hit")',
        "the direction SGD states; 83 of 180 rows are Hit-Bait and the labels were positional",
    ),
    (
        "sgd_tool.py",
        '(i.get("experiment") or {}).get("display_name")',
        "the experiment type, which was read from a key the API does not send",
    ),
    (
        "sgd_tool.py",
        '"is_reference_strain"',
        "which of 41 strains the returned sequence is, where the fallback was silent",
    ),
    (
        "sgd_tool.py",
        "alias_details",
        "what kind of alias each name is; a GenBank accession is not a gene synonym",
    ),
    (
        "sgd_tool.py",
        'a.get("sga_score")',
        "the quantitative strength of a genetic interaction and its p-value",
    ),
    (
        "mgnify_expanded_tool.py",
        '"rna_16s": attrs.get("rna-16s"),\n                    "rna_23s"',
        "the MIMAG criteria a MAG's quality is judged by, beside its completeness",
    ),
    (
        "mgnify_expanded_tool.py",
        "sample-metadata",
        "the submitter's own pH, temperature and depth, where the fixed fields are null",
    ),
    (
        "ctg_tool.py",
        '"countries": countries',
        "where a trial runs, which is what a trial search is filtered on",
    ),
    # Round three.
    (
        "graphql_tool.py",
        '"total_associated_targets": total_count',
        "the denominator: 918 targets with a score is 918 of 4,461, not of nothing",
    ),
    (
        "zooma_tool.py",
        '"derived_from": {',
        "the database that curated the mapping, where the tool reported its own inference step",
    ),
    (
        "zooma_tool.py",
        '"title": s.get("title")',
        "the name of each datasource, from a tool whose only job is to list them",
    ),
    (
        "oma_tool.py",
        'orth.get("entry_nr")',
        "the key OMA's own endpoints take, without which a result is a dead end",
    ),
    (
        "hpo_tool.py",
        "_hpo_medical_actions",
        "a phenotype's curated treatments, which no tool exposed while sitting in the response",
    ),
    (
        "hpo_tool.py",
        "also_in_this_response",
        "that the one request also answered 3,136 diseases and 14 medical actions",
    ),
    (
        "hpo_tool.py",
        'term.get("publicationReferences")',
        "what a term's definition rests on",
    ),
    (
        "ctg_tool.py",
        'ref.get("pmid")',
        "the trial's publications, for a search result that could not be followed",
    ),
    (
        "alliance_genome_tool.py",
        "predictionMethodsNotMatched",
        "the methods that did NOT support an ortholog call, which is what makes method_count mean anything",
    ),
    # Round four.
    (
        "genome_nexus_tool.py",
        'data.get("mutation_assessor")',
        "a predictor the call asks for in its own fields= parameter and then dropped",
    ),
    (
        "genome_nexus_tool.py",
        'tc.get("biotype")',
        "whether the consequence is on a coding transcript or one marked for decay",
    ),
    (
        "genome_nexus_tool.py",
        'item.get("missenseCount")',
        "what a hotspot's tumour count is made of; 897 missense and 0 truncating at BRAF V600",
    ),
    (
        "genome_nexus_tool.py",
        'data.get("exons")',
        "the exon structure, from the tool whose whole job is the canonical transcript",
    ),
    (
        "genome_nexus_tool.py",
        "transcriptConsequenceSummary",
        "the canonical summary, read before the list so the symbol is not whichever came first",
    ),
    (
        "disgenet_tool.py",
        'row.get("geneSymbol_keyword")',
        "the gene a variant sits in; a VDA row spells it differently and returned null",
    ),
    (
        "disgenet_tool.py",
        'row.get("mostSevereConsequences")',
        "what the variant does, from a variant-disease association tool",
    ),
    (
        "disgenet_tool.py",
        "alleleFreqExome",
        "how common the allele is; rs1801133's C677T is 32% and that bears on the association",
    ),
    (
        "disgenet_tool.py",
        'row.get("polyphen_score")',
        "the pathogenicity prediction on the same row as the rsID",
    ),
    (
        "epigraphdb_tool.py",
        'rel.get("action_type")',
        "whether the drug inhibits or activates; all 43 EGFR rows carry it and none of the CPIC fields",
    ),
    (
        "epigraphdb_tool.py",
        'pick("rg_intercept")',
        "the LDSC intercept that says whether an rg of 0.95 is sample overlap",
    ),
    (
        "epigraphdb_tool.py",
        'gs.get("pval")',
        "the p-value this tool takes pval_threshold to filter on and did not report",
    ),
    (
        "epigraphdb_tool.py",
        'assoc.get("id")',
        "the outcome trait each repurposing estimate was measured against",
    ),
    # Round five.
    (
        "glygen_tool.py",
        'raw.get("enzyme")',
        "the biosynthetic enzymes the class docstring names, which no GlyGen tool exposed",
    ),
    (
        "glygen_tool.py",
        'raw.get("residues")',
        "the structure residue by residue, where number_monosaccharides was all that was said",
    ),
    (
        "glygen_tool.py",
        'raw.get("glycation")',
        "glycation at a site, the one of the three PTM sections the site tool never read",
    ),
    (
        "glygen_tool.py",
        'raw.get("neighbors")',
        "the annotated sites around this one, with distance and direction",
    ),
    (
        "glygen_tool.py",
        "reported_n_glycosites",
        "the key a /protein/list row actually carries; the two that were read do not exist",
    ),
    (
        "glygen_tool.py",
        'v.get("glycoeffect")',
        "what an SNV does to the glycosylation, which is the question GlyGen answers",
    ),
    (
        "glygen_tool.py",
        'item.get("ec_number_list")',
        "the EC numbers of a protein a glycoprotein search returned 51 of",
    ),
    (
        "pubchem_tox_tool.py",
        "_reference_index",
        "who stated an LD50, which every statement points at and none of them carried",
    ),
    (
        "pubchem_tox_tool.py",
        "ExternalTableName",
        "PubChem answering that the data is in a table elsewhere, which read as no data",
    ),
    (
        "pubchem_tox_tool.py",
        "_statements_in_subtree",
        "the statements a summary topic counted, at the depth they actually sit",
    ),
    (
        "openfda_device_tool.py",
        "_mdr_texts",
        "what happened, from a MAUDE row that carried problem codes and no narrative",
    ),
    (
        "openfda_device_tool.py",
        "code_info",
        "which models and serial numbers a recall covers",
    ),
    (
        "openfda_device_tool.py",
        "mri_safety",
        "whether a device is safe near an MRI, which the UDI record states",
    ),
    (
        "openfda_device_tool.py",
        "_openfda_ids",
        "the clearance and establishment numbers the device endpoints take as input",
    ),
    (
        "openfda_device_tool.py",
        "supplement_number",
        "which PMA decision a row is, where one number covers the approval and every change",
    ),
]


@pytest.mark.parametrize(
    "module, key, why",
    UPSTREAM_KEYS,
    ids=[
        f"{m.removesuffix('.py')}:{k.split(chr(34))[1] if chr(34) in k else k}"[:60]
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
    # Round four.
    ("GenomeNexus_annotate_variant", "mutation_assessor"),
    ("GenomeNexus_annotate_variant", "biotype"),
    ("GenomeNexus_annotate_variant", "protein_start"),
    ("GenomeNexus_get_canonical_transcript", "exons"),
    ("GenomeNexus_get_canonical_transcript", "utrs"),
    ("GenomeNexus_get_cancer_hotspots", "missenseCount"),
    ("DisGeNET_get_vda", "most_severe_consequence"),
    ("DisGeNET_get_vda", "allele_frequencies"),
    ("DisGeNET_get_vda", "polyphen_score"),
    ("DisGeNET_get_vda", "gene_symbols"),
    ("DisGeNET_get_disease_genes", "disease_name"),
    ("DisGeNET_get_disease_genes", "score_breakdown"),
    ("DisGeNET_get_disease_genes", "year_first"),
    ("DisGeNET_get_gda", "gene_protein_classes"),
    ("DisGeNET_get_gda", "disease_inheritance"),
    ("EpiGraphDB_get_gene_drug_associations", "action_type"),
    ("EpiGraphDB_get_genetic_correlations", "rg_intercept"),
    ("EpiGraphDB_get_genetic_correlations", "h2_se"),
    ("EpiGraphDB_get_drugs_for_trait", "evidence"),
    ("EpiGraphDB_get_drugs_for_trait", "exposure_trait_id"),
    ("EpiGraphDB_get_literature_evidence", "pval"),
    # Round five.
    ("GlyGen_get_glycan", "enzymes"),
    ("GlyGen_get_glycan", "residues"),
    ("GlyGen_get_glycan", "biosynthesis_steps"),
    ("GlyGen_get_glycan", "publications"),
    ("GlyGen_get_glycoprotein", "diseases"),
    ("GlyGen_get_glycoprotein", "snvs"),
    ("GlyGen_get_glycoprotein", "glycoeffect"),
    ("GlyGen_get_glycoprotein", "pathways"),
    ("GlyGen_get_site", "glycation"),
    ("GlyGen_get_site", "neighbors"),
    ("GlyGen_get_site", "protein_name"),
    ("GlyGen_search_glycoproteins", "n_linked_site_count"),
    ("GlyGen_search_glycoproteins", "ec_numbers"),
    ("PubChemTox_get_toxicity_values", "source_name"),
    ("PubChemTox_get_toxicity_values", "license_note"),
    ("PubChemTox_get_carcinogen_classification", "source_url"),
    ("PubChemTox_get_acute_effects", "effect_truncated"),
    ("PubChemTox_get_toxicity_summary", "statements"),
    ("OpenFDADevice_search_adverse_events", "narratives"),
    ("OpenFDADevice_search_adverse_events", "devices"),
    ("OpenFDADevice_search_adverse_events", "report_number"),
    ("OpenFDADevice_search_recalls", "code_info"),
    ("OpenFDADevice_search_recalls", "identifiers"),
    ("OpenFDADevice_search_udi", "mri_safety"),
    ("OpenFDADevice_search_udi", "is_labeled_as_nrl"),
    ("OpenFDADevice_get_classification", "definition"),
    ("OpenFDADevice_search_510k", "decision_code"),
    ("OpenFDADevice_search_pma", "supplement_number"),
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


def test_pubchem_tox_statements_say_who_stated_them():
    """An LD50 with no source is a number a reader cannot weigh.

    Every PUG View statement carries a `ReferenceNumber` and the record
    carries the references it points into -- ECHA for aspirin's GHS
    classification, IARC with its own copyright note for arsenic's carcinogen
    listing, ILO-WHO's ICSC for the acute signs. None of it reached the
    caller, and the licence terms travel with the source.
    """
    source = _source("pubchem_tox_tool.py")
    assert "_reference_index" in source
    assert '"license_note": reference.get("license_note")' in source or (
        'reference.get("license_note")' in source
    )
    # And the cut that used to happen in silence now says so.
    assert 'item["value"][:500]' not in source, (
        "a clinical description cut at 500 characters with no flag was the bug"
    )
    assert "effect_truncated" in source


def test_glygen_search_counts_the_sites_the_row_actually_reports():
    """Every result of every glycoprotein search said 0.

    `total_n_glycosites` and `total_o_glycosites` are not keys a
    /protein/list row carries; `reported_n_glycosites` and
    `reported_o_glycosites` are. With `or 0` wrapped around each missing key
    the sum came out as 0 on every row -- from a tool whose description
    promises "glycosylation-site counts" -- and HGF, which has four N-linked
    and one O-linked reported site, was indistinguishable from a protein with
    none. A count the API never sent now reads as null.
    """
    source = _source("glygen_tool.py")
    assert "reported_n_glycosites" in source
    assert "reported_o_glycosites" in source
    assert '(item.get("total_n_glycosites") or 0)' not in source, (
        "the sum of two absent keys was the bug, not the fix"
    )
    assert "_first_number" in source, (
        "a count must come back null when the row does not carry it"
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


def test_the_clinical_trials_extractor_no_longer_deletes_its_evidence():
    """It did not omit these fields, it deleted them.

    `sourceVocabulary` names the MedDRA version a term comes from, and
    `assessmentType` separates a SYSTEMATIC_ASSESSMENT -- every participant
    checked for this event -- from a NON_SYSTEMATIC one, where a lower count
    may mean only that nobody looked. Comparing two arms across that
    difference is not valid. `numEvents` was deleted once a percentage had
    been computed from it, leaving a derived number with its input removed,
    and events are not participants: 5 events in 3 patients and 5 affected
    patients both arrived as "5".
    """
    source = _source("ctg_tool.py")
    assert 'del ae["sourceVocabulary"]' not in source
    assert 'del ae["assessmentType"]' not in source
    assert 'del group_stats["numEvents"]' not in source


def test_sgd_reads_the_interaction_direction_instead_of_assuming_it():
    """46% of rows were reported with bait and hit the wrong way round.

    SGD states the direction in `bait_hit`. On S000003219's 180 interactions,
    83 are "Hit-Bait", meaning locus1 is the hit -- and locus1 was labelled
    the bait unconditionally, which for a two-hybrid result inverts which
    protein was the probe.
    """
    source = _source("sgd_tool.py")
    assert 'bait_hit.strip().lower().startswith("hit")' in source, (
        "the direction must be read from bait_hit, not assumed from position"
    )
    assert "bait, hit = locus2, locus1" in source


def test_the_monarch_schemas_say_what_the_rows_hold():
    """Six of seven declared `{"type": "array"}` and nothing else.

    A schema that declares no properties is not a smaller problem than a
    dropped field; it is the reason a dropped field is invisible. Nothing
    static could show that `MonarchV3_get_associations` returned 9 of the 37
    fields Biolink puts on an association.
    """
    for tool in [
        "MonarchV3_get_entity",
        "MonarchV3_get_associations",
        "MonarchV3_search",
        "MonarchV3_get_mappings",
        "MonarchV3_phenotype_similarity_search",
    ]:
        schema = json.dumps(_config(tool).get("return_schema") or {})
        assert schema not in ('{"type": "array"}', '{"type": "object"}', "{}"), (
            f"{tool} still declares nothing about its rows"
        )
        assert '"properties"' in schema, f"{tool} declares no properties"


def test_sgd_says_which_strain_a_sequence_came_from():
    """ "Take S288C, falling back to the first" across 41 strains, silently.

    A caller comparing the returned coordinates to the reference genome could
    have been comparing against another isolate, with nothing in the response
    to say so.
    """
    source = _source("sgd_tool.py")
    assert '"strains_available"' in source
    assert '"is_reference_strain"' in source
