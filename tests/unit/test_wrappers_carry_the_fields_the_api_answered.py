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
    # Round six.
    (
        "mavedb_tool.py",
        "clinvarLinks",
        "the link from a ClinVar control to the measured score, read from a key that is not there",
    ),
    (
        "mavedb_tool.py",
        "def _publication",
        "the paper's title, journal, year and authors beside the PubMed number",
    ),
    (
        "mavedb_tool.py",
        "uniprotIdFromMappedMetadata",
        "the target's UniProt accession, which was read from a key a target sequence does not have",
    ),
    (
        "mavedb_tool.py",
        "scoreCalibrations",
        "the score ranges that map onto ACMG evidence strengths",
    ),
    (
        "mavedb_tool.py",
        "scoreDistribution",
        "the range and histogram the caller needs to pick a threshold",
    ),
    (
        "mavedb_tool.py",
        "def _keywords",
        "the controlled keywords an experiment is indexed under",
    ),
    (
        "wormbase_tool.py",
        "alleleSymbol",
        "which allele a phenotype belongs to; the annotation's subject is not the gene",
    ),
    (
        "wormbase_tool.py",
        "def _reference",
        "the PMID behind an annotation, where only Alliance's own curie came back",
    ),
    (
        "wormbase_tool.py",
        "phenotypesOrTraits",
        "the phenotype a genetic interaction was scored by, which is the result",
    ),
    (
        "wormbase_tool.py",
        "predictionMethodsNotCalled",
        "the methods that ran and did not call an ortholog",
    ),
    (
        "wormbase_tool.py",
        "def _perturbation",
        "which allele or RNAi a genetic interaction was measured with",
    ),
    (
        "wormbase_tool.py",
        "nb_annotations",
        "how many disease annotations the gene has, against a ribbon of all categories",
    ),
    (
        "wormbase_tool.py",
        "detectionMethod",
        "how an interaction was detected, without which the pair is not a result",
    ),
    (
        "usda_plants_tool.py",
        "def _plant_identity",
        "which plant a symbol resolved to, from a profile every one of these tools fetched",
    ),
    (
        "usda_plants_tool.py",
        'profile.get("Ancestors")',
        "the classification, nine ranks of it, from a plant profile tool",
    ),
    (
        "usda_plants_tool.py",
        'profile.get("MapCoordinates")',
        "where the plant occurs, where fips_distribution is null on most records",
    ),
    (
        "usda_plants_tool.py",
        'profile.get("AcceptedSymbol")',
        "where a symbol resolves when USDA names an accepted taxon separately",
    ),
    (
        "cancer_prognosis_tool.py",
        "_study_counts",
        "samples per modality, where max() of three of them was the whole answer",
    ),
    (
        "cancer_prognosis_tool.py",
        "referenceGenome",
        "whether a study's coordinates are hg19 or hg38",
    ),
    (
        "cancer_prognosis_tool.py",
        'p.get("datatype")',
        "whether expression values are Z-scores, which was being inferred from the profile id",
    ),
    (
        "fda_orange_book_tool.py",
        "def _identifiers",
        "the NDC and SPL codes an approval is joined to a claim or a label by",
    ),
    (
        "fda_orange_book_tool.py",
        "reference_standard",
        "which product generics are tested against, and which product a TE code is for",
    ),
    # Round nine.
    (
        "ncbi_datasets_tool.py",
        "_gene_ontology",
        "122 GO terms on a gene record, with their evidence codes and PMIDs",
    ),
    (
        "ncbi_datasets_tool.py",
        "genetic_code",
        "which translation tables a taxon uses, nuclear and mitochondrial",
    ),
    (
        "clingen_tool.py",
        'item.get("warnings")',
        "a curator's stated disagreement with ClinVar about a pathogenicity call",
    ),
    (
        "ewas_atlas_tool.py",
        "posToTss",
        "how far a CpG probe sits from a transcript's start site",
    ),
    (
        "pheweb_phewas_tool.py",
        'p.get("num_samples")',
        "the n behind a quantitative-trait association, where there are no cases to count",
    ),
    (
        "pheweb_phewas_tool.py",
        "resolved_variant",
        "what an rsID resolved to, from the Ensembl record the resolution fetched",
    ),
    (
        "efo_tool.py",
        "term_replaced_by",
        "what an obsolete term was replaced by, where the tool said only that it is obsolete",
    ),
    # Round ten.
    (
        "rgd_tool.py",
        'ann.get("objectSymbol")',
        "what an annotation is on, from 1,114 rows that named only the term",
    ),
    (
        "rgd_tool.py",
        'q.get("peakRgdId")',
        "the peak and flanking markers that define where a QTL is",
    ),
    (
        "rgd_tool.py",
        'r.get("diseases")',
        "the diseases a gene hit is associated with, which is why RGD is searched",
    ),
    (
        "rgd_strain_tool.py",
        'rec.get("lastStatus")',
        "whether a strain can still be obtained",
    ),
    (
        "impc_tool.py",
        'gene_data.get("allele_name"',
        "which alleles IMPC phenotyped, beside the phenotype status",
    ),
    (
        "progenetix_tool.py",
        "pathological_tnm_findings",
        "all three TNM findings, where the first label was reported as the staging",
    ),
    (
        "progenetix_tool.py",
        's.get("cohorts")',
        "which study a sample in a CNV search came from",
    ),
    (
        "metabolite_tool.py",
        'entry.get("mesh_chemical_id")',
        "which CTD chemical a metabolite name was matched to",
    ),
    (
        "metabolite_tool.py",
        "terms_tried",
        "which name variants were tried, so an empty answer is not read as no associations",
    ),
    # Round twelve.
    (
        "uniprot_tool.py",
        'entry.get("entryType")',
        "reviewed against unreviewed, the biggest quality distinction in UniProt",
    ),
    (
        "uniprot_ref_tool.py",
        "taxonLineage",
        "where a proteome's organism sits in the tree, 30 ranks of it",
    ),
    (
        "uniprot_ref_tool.py",
        'r.get("citations")',
        "the papers describing a proteome, with their 2,840 author names",
    ),
    (
        "quickgo_tool.py",
        "id_to_term",
        "what a GO term means, from the record the name backfill already fetched",
    ),
    (
        "reactome_content_tool.py",
        'entry.get("summation")',
        "the paragraph describing a pathway, answered for all 30 search hits",
    ),
    (
        "reactome_content_tool.py",
        "orthologousEvent",
        "the same reaction inferred in other species",
    ),
    (
        "pfam_tool.py",
        "entry_integrated",
        "the InterPro entry a Pfam family is integrated into",
    ),
    (
        "openfda_adv_tool.py",
        'openfda.get("rxcui")',
        "the RxNorm concept that resolves TYLENOL and acetaminophen to one drug",
    ),
    (
        "clingen_ar_tool.py",
        'ta.get("geneSymbol")',
        "the gene the allele is in, which the tool's own example promises",
    ),
    (
        "clingen_ar_tool.py",
        '"MANE"',
        "the MANE Select transcript, the representation the registry normalises to",
    ),
    (
        "clingen_ar_tool.py",
        '_ID_KEYS = ("rs", "alleleId", "variationId"',
        "the dbSNP rsID, read from `id`, a key the dbSNP record does not send",
    ),
    (
        "epmc_annotations_tool.py",
        '"tags": tags',
        "both ends of a relationship annotation, where only tags[0] was read",
    ),
    (
        "epmc_annotations_tool.py",
        'ann.get("section")',
        "whether a gene was mentioned in the Methods or in the Results",
    ),
    (
        "epmc_annotations_tool.py",
        'ann.get("provider")',
        "which text-mining pipeline made the claim",
    ),
    (
        "drugcentral_tool.py",
        'dc.get("pharmacology_class")',
        "the drug's FDA Established Pharmacologic Class, from a drug-information tool",
    ),
    (
        "drugcentral_tool.py",
        'rec.get("llr_threshold")',
        "the threshold an llr is a signal against; one without the other says nothing",
    ),
    (
        "drugcentral_tool.py",
        'u.get("swissprot_entry")',
        "the Swiss-Prot entry name of a target the tool exists to name",
    ),
    (
        "bgee_tool.py",
        'call.get("fdr")',
        "the FDR behind a present/absent expression call",
    ),
    (
        "bgee_tool.py",
        'match.get("match")',
        "which synonym a SYNONYM match matched",
    ),
    (
        "medlineplus_tool.py",
        '"db-key-list"',
        "the OMIM, NCBI Gene, GTR and ICD-10-CM codes for the page",
    ),
    (
        "medlineplus_tool.py",
        'gene_summary.get("gene-symbol"',
        "the gene symbol, where `name` is the protein name",
    ),
    (
        "ebi_proteins_features_tool.py",
        'f.get("ligand")',
        "what binds at a BINDING site, from the category whose name is 'binding sites'",
    ),
    (
        "ebi_proteins_features_tool.py",
        'f.get("ftId")',
        "the UniProt feature id a processed chain is cited by",
    ),
    (
        "chebi_tool.py",
        'struct_data.get("standard_inchi", None)',
        "the InChI, where only its hash was returned",
    ),
    (
        "chebi_tool.py",
        'raw.get("roles_classification")',
        "the role classification, which is half of what ChEBI is for",
    ),
    (
        "chebi_tool.py",
        'rec.get("accession_number")',
        "the CAS number and the registry, citation and xref accessions beside it",
    ),
    (
        "ols_tool.py",
        'item.get("exact_synonyms")',
        "the synonyms every OLS search hit carries",
    ),
    (
        "ols_tool.py",
        'alias="importsFrom"',
        "which ontologies an ontology depends on",
    ),
    (
        "ols_tool.py",
        '"is_obsolete": (term_data or {}).get("isObsolete")',
        "whether the term the similar ones are similar to has been retired",
    ),
    (
        "itis_tool.py",
        '_rows(data.get("synonymList"), "synonyms")',
        "the synonyms, which are the reason to consult a taxonomic authority",
    ),
    (
        "itis_tool.py",
        '_rows(data.get("acceptedNameList"), "acceptedNames")',
        "the name that replaced an invalid one, and the reason it was rejected",
    ),
    (
        "itis_tool.py",
        '"credibility_rating"',
        "the Taxonomic Work Group's verdict on the record",
    ),
    (
        "gbif_taxonomy_tool.py",
        '"kingdomKey"',
        "the rank keys, the handles for walking a tree the tool exists to walk",
    ),
    (
        "gbif_taxonomy_tool.py",
        '"issues"',
        "GBIF's own data-quality flags on the usage record",
    ),
    (
        "gbif_taxonomy_tool.py",
        'rec.get("preferred")',
        "which of a taxon's common names GBIF marks as the one to show",
    ),
    (
        "hubmap_tool.py",
        'person.get("orcid_id")',
        "the contributor ORCID, read from `orcid`, a key HuBMAP does not send",
    ),
    (
        "hubmap_tool.py",
        "organ_donor_data",
        "what the donor was -- age, sex, race -- at the end of a provenance chain",
    ),
    (
        "hubmap_tool.py",
        'org.get("laterality")',
        "which side a paired organ is, legible only inside the term string",
    ),
    (
        "rxclass_tool.py",
        'by_name.get("Relation")',
        "DIRECT against INDIRECT membership, which are not the same claim",
    ),
    (
        "ebi_proteins_coordinates_tool.py",
        'gc.get("feature")',
        "the 1,514 annotations per transcript the mapping response already carried",
    ),
    (
        "ebi_proteins_coordinates_tool.py",
        'genomic_loc.get("assemblyName")',
        "which assembly the genome positions are against",
    ),
    (
        "ebi_proteins_interactions_tool.py",
        'row.get("dbReference")',
        "the OMIM id of a disease the tool listed by name only",
    ),
    (
        "swissmodel_tool.py",
        's.get("ligand_chains")',
        "what is bound in the model, where the protein partners were reported",
    ),
    (
        "swissmodel_tool.py",
        's.get("oligo-state")',
        "whether the model is a monomer or an oligomer",
    ),
    (
        "hubmap_sample_tool.py",
        'metadata.get("living_donor_data")',
        "a living donor's attributes, which organ_donor_data does not hold",
    ),
    (
        "hubmap_sample_tool.py",
        'src.get("descendants")',
        "which datasets were made from the sample",
    ),
    (
        "nasa_osdr_tool.py",
        'metadata.get("study protocol description")',
        "the methods of a study whose tool promises its full metadata",
    ),
    (
        "nasa_osdr_tool.py",
        'source.get("Data Source Type")',
        "which repository a search row actually came from",
    ),
    (
        "uniprot_idmapping_tool.py",
        'item.get("to", False)',
        "whether a database can be mapped TO, where only FROM was reported",
    ),
    (
        "uniprot_idmapping_tool.py",
        'item.get("uriLink")',
        "how to resolve a mapped id, which is what mapping it was for",
    ),
    (
        "uniprot_idmapping_tool.py",
        '"unreviewed" not in entry_type.lower()',
        "Swiss-Prot against TrEMBL, tested on the string that is not a substring",
    ),
    (
        "uniprot_tool.py",
        '"unreviewed" not in entry_type.lower()',
        "the same test, where the substring form called every TrEMBL entry reviewed",
    ),
    (
        "gwas_sumstats_tool.py",
        'entry.get("summaryStatistics")',
        "whether a study has summary statistics, from a tool named after them",
    ),
    (
        "gwas_sumstats_tool.py",
        'entry.get("initialSampleDescription")',
        "the discovery sample, which is what a GWAS result means",
    ),
    (
        "ctg_tool.py",
        '_outcomes("secondaryOutcomes")',
        "the 39 secondary outcomes of a trial that reported 4 primary ones",
    ),
    (
        "ctg_tool.py",
        'item.get("armGroupLabels")',
        "which arms an intervention was given in",
    ),
    (
        "fooddata_central_tool.py",
        'n.get("derivationDescription")',
        "whether a nutrient value was measured or calculated",
    ),
    (
        "cellxgene_discovery_tool.py",
        'collection.get("publisher_metadata")',
        "the paper a collection belongs to, so it can be cited",
    ),
    (
        "cellxgene_discovery_tool.py",
        "def _ontology_terms",
        "which tissues a collection covers, which its sibling handler reads",
    ),
    (
        "nci_evs_tool.py",
        'c.get("conceptStatus")',
        "whether a terminology concept has been retired",
    ),
    (
        "nextstrain_tool.py",
        "def _coloring_values",
        "the values a build covers for a coloring, where only the key was given",
    ),
    (
        "orcid_tool.py",
        's.get("external-ids")',
        "a review's own external ids, where only its group's were read",
    ),
    (
        "orcid_tool.py",
        "def _source_name",
        "who deposited an ORCID assertion",
    ),
    (
        "fda_orange_book_tool.py",
        "_submission_summary(result.get(\"submissions\"))",
        "when an application was approved, in a row that answers whether a generic exists",
    ),
    (
        "expression_atlas_tool.py",
        'exp.get("experimentalFactors")',
        "which variables a baseline experiment measured across",
    ),
    (
        "hubmap_sample_tool.py",
        "def _donor_demographic_codes",
        "the SNOMED codes behind a donor's attributes",
    ),
    (
        "ddbj_tool.py",
        "def _xref_type_counts",
        "what a cross-reference count was counting",
    ),
    (
        "timer_tool.py",
        "def _get_study_sample_count",
        "how many samples the study has, against the 100 the estimate used",
    ),
    (
        "open_genes_tool.py",
        "def _evidence_digest",
        "what 57 longevity-association records say, where only '57' was reported",
    ),
    (
        "cath_tool.py",
        "def _go_terms",
        "a domain's GO annotations, which its sibling handler returns",
    ),
    (
        "cath_tool.py",
        'data.get("pdb_segments")',
        "the residue ranges that define the domain",
    ),
    (
        "humanbase_tool.py",
        "def _top_evidence_datasets",
        "which experiments support an interaction, where only a count was printed",
    ),
    (
        "cbioportal_tool.py",
        '"alteration_type": profile.get("molecularAlterationType")',
        "which molecular profile the mutations came from",
    ),
    (
        "orphanet_tool.py",
        'gene_info.get("Synonym")',
        "a gene's other symbols, which is how the answer is matched elsewhere",
    ),
    (
        "uniprot_ref_tool.py",
        '"taxon_lineage_nodes"',
        "the taxon ids of a lineage returned as bare names",
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
    ("MaveDB_get_score_set", "score_calibrations"),
    ("MaveDB_get_score_set", "score_distribution"),
    ("MaveDB_get_score_set", "dataset_columns"),
    ("MaveDB_get_score_set", "experiment"),
    ("MaveDB_get_clinical_controls", "variant_links"),
    ("MaveDB_search_experiments", "keywords"),
    ("MaveDB_search_experiments", "method"),
    ("MaveDB_search_score_sets", "target_gene_details"),
    ("WormBase_get_phenotypes", "subjects"),
    ("WormBase_get_phenotypes", "reference_details"),
    ("WormBase_get_phenotypes", "annotation_types"),
    ("WormBase_get_expression", "annotations"),
    ("WormBase_get_orthologs", "methods_not_called"),
    ("WormBase_get_interactions", "detection_method"),
    ("WormBase_get_interactions", "phenotypes_or_traits"),
    ("WormBase_get_human_diseases", "annotated_disease_count"),
    ("WormBase_get_human_diseases", "has_annotations"),
    ("USDA_plants_get_profile", "ancestors"),
    ("USDA_plants_get_profile", "map_coordinates"),
    ("USDA_plants_get_profile", "available_data"),
    ("USDA_plants_get_profile", "synonym_note"),
    ("USDA_plants_search_by_name", "accepted_symbol"),
    ("CancerPrognosis_search_studies", "sample_counts"),
    ("CancerPrognosis_search_studies", "reference_genome"),
    ("CancerPrognosis_search_studies", "cancer_type_name"),
    ("CancerPrognosis_get_study_summary", "datatype"),
    ("CancerPrognosis_get_gene_expression", "profile_datatype"),
    ("FDA_OrangeBook_get_approval_history", "products"),
    ("FDA_OrangeBook_get_approval_history", "identifiers"),
    ("FDA_OrangeBook_get_te_code", "dosage_form"),
    ("FDA_OrangeBook_search_drug", "identifiers"),
    ("NCBIDatasets_get_gene", "gene_ontology"),
    ("NCBIDatasets_get_gene", "summary"),
    ("NCBIDatasets_get_taxonomy", "genetic_code"),
    ("NCBIDatasets_get_orthologs", "gene_ontology_counts"),
    ("ClinGen_get_variant_classifications", "Warnings"),
    ("ClinGen_get_variant_classifications", "Guidelines"),
    ("EWASAtlas_search_by_gene", "transcripts"),
    ("EWASAtlas_get_study", "sd_age"),
    ("BioBankJapan_phewas_by_variant", "num_samples"),
    ("Genebass_gene_burden_phewas", "n_cases"),
    ("Genebass_gene_burden_phewas", "pval_skato"),
    ("ols_get_efo_term", "term_replaced_by"),
    ("ols_list_ontologies", "languages"),
    ("RGD_get_annotations", "object_symbol"),
    ("RGD_get_annotations", "reference_rgd_id"),
    ("RGD_get_qtls_in_region", "peak_rgd_id"),
    ("RGD_search_genes", "diseases"),
    ("RGD_get_orthologs", "refseq_status"),
    ("RGD_search_strains", "last_status"),
    ("IMPC_get_phenotypes_by_gene", "statistical_method"),
    ("IMPC_get_gene_summary", "allele_names"),
    ("IMPC_search_genes", "marker_type"),
    ("Progenetix_search_biosamples", "pathological_tnm_findings"),
    ("Progenetix_list_cohorts", "reference"),
    ("HMDB_get_diseases", "mesh_chemical_id"),
    ("HMDB_get_diseases", "ctd_terms_tried"),
    ("UniProt_search", "reviewed"),
    ("UniProt_search", "feature_types"),
    ("UniProt_search", "cross_reference_databases"),
    ("UniProtRef_get_proteome", "citations"),
    ("UniProtRef_get_proteome", "busco"),
    ("UniProtRef_search_keywords", "gene_ontologies"),
    ("QuickGO_annotations_by_goterm", "reference"),
    ("QuickGO_get_term_detail", "children"),
    ("ReactomeContent_search", "summation"),
    ("Pfam_get_protein_annotations", "protein_accession"),
    ("Pfam_get_family_proteins", "source_database"),
    ("FAERS_search_adverse_event_reports", "rxcui"),
    ("ClinGenAR_lookup_allele", "gene_symbol"),
    ("ClinGenAR_lookup_allele", "protein_effect"),
    ("ClinGenAR_lookup_allele", "mane_select_transcript"),
    ("ClinGenAR_lookup_allele", "transcript_alleles_truncated"),
    ("ClinGenAR_get_external_records", "record_count"),
    ("ClinGenAR_lookup_by_external_id", "transcript_alleles"),
    ("EPMC_get_text_mined_annotations", "tags"),
    ("EPMC_get_text_mined_annotations", "providers"),
    ("EPMC_get_article_genes", "mentions"),
    ("EPMC_get_article_genes", "returned_entities"),
    ("DrugCentral_get_drug", "pharmacologic_classes"),
    ("DrugCentral_get_drug", "adverse_event_signals_truncated"),
    ("DrugCentral_get_drug", "dosages"),
    ("DrugCentral_get_targets", "swissprot_entries"),
    ("DrugCentral_search", "cross_references"),
    ("Bgee_get_gene_expression", "fdr"),
    ("Bgee_search_genes", "matched_text"),
    ("Bgee_list_species", "parent_taxon_id"),
    ("MedlinePlus_get_genetics_condition_by_name", "cross_references"),
    ("MedlinePlus_get_genetics_gene_by_name", "gene_symbol"),
    ("MedlinePlus_connect_lookup_by_code", "resolved_query"),
    ("EBIProteins_get_domains_sites", "ligand"),
    ("EBIProteins_get_molecule_processing", "feature_id"),
    ("ChEBI_get_compound", "inchi"),
    ("ChEBI_get_compound", "roles"),
    ("ChEBI_get_compound", "cas_numbers"),
    ("ChEBI_get_compound", "synonym_details"),
    ("ChEBI_search", "smiles"),
    ("ChEBI_get_ontology_parents", "name"),
    ("ols_search_terms", "related_synonyms"),
    ("ols_get_ontology_info", "importsFrom"),
    ("ols_find_similar_terms", "source_term"),
    ("ITIS_get_full_record", "accepted_names"),
    ("ITIS_get_full_record", "synonyms_truncated"),
    ("ITIS_get_full_record", "jurisdictional_origins"),
    ("ITIS_get_hierarchy", "parent_name"),
    ("GBIF_get_taxon_children", "kingdomKey"),
    ("GBIF_get_taxon_children", "issues"),
    ("GBIF_get_vernacular_names", "preferred"),
    ("HuBMAP_list_organs", "laterality"),
    ("HuBMAP_list_organs", "category_term"),
    ("HuBMAP_get_dataset_provenance", "donor_attributes"),
    ("RxClass_get_class_members", "relation"),
    ("RxClass_find_classes", "classUrl"),
    ("RxClass_get_disease_relations", "relaSource"),
    ("EBIProteins_get_coordinate_mapping", "feature_type_counts"),
    ("EBIProteins_get_coordinate_mapping", "assembly_name"),
    ("EBIProteins_get_proteins_by_genomic_loc", "features_truncated"),
    ("EBIProteins_get_interaction_details", "disease_records"),
    ("EBIProteins_get_interaction_details", "subcellular_location_records"),
    ("EBIProteins_get_interaction_details", "intact_id_a"),
    ("SwissModel_get_models", "ligands"),
    ("SwissModel_get_models", "oligo_state"),
    ("SwissModel_get_summary", "models_with_ligands"),
    ("HuBMAP_get_sample", "descendant_count"),
    ("HuBMAP_get_sample", "donor_demographics"),
    ("OSDR_get_study", "protocol_descriptions"),
    ("OSDR_get_study", "investigator"),
    ("OSDR_search_studies", "data_source_type"),
    ("OSDR_list_files", "organization"),
    ("UniProtIDMap_list_databases", "to_supported"),
    ("UniProtIDMap_list_databases", "uri_template"),
    ("UniProtIDMap_gene_to_uniprot", "reviewed"),
    ("GWASSumStats_get_trait_studies", "summary_statistics"),
    ("GWASSumStats_get_trait_studies", "initial_sample_description"),
    ("GWASSumStats_list_studies", "discovery_sample_ancestry"),
    ("ClinicalTrials_get_study", "secondary_outcomes"),
    ("ClinicalTrials_get_study", "other_outcome_count"),
    ("ClinicalTrials_search_studies", "primary_outcome_measures"),
    ("ClinicalTrials_search_studies", "arm_count"),
    ("FoodDataCentral_search_foods", "derivation_description"),
    ("CxGDisc_list_collections", "publication"),
    ("CxGDisc_list_collections", "tissue_count"),
    ("CxGDisc_list_collections", "datasets_with_cell_count"),
    ("NCIEVS_search_terminology", "concept_status"),
    ("Nextstrain_get_dataset", "colorings"),
    ("ORCID_get_peer_reviews", "subgroup_external_ids"),
    ("ORCID_get_peer_reviews", "visibility"),
    ("FDA_OrangeBook_check_generic_availability", "original_approval_date"),
    ("FDA_OrangeBook_search_drug", "submission_count"),
    ("ExpressionAtlas_get_baseline", "experimental_factors"),
    ("ExpressionAtlas_get_baseline", "technology_type"),
    ("HuBMAP_get_sample", "donor_demographics_coded"),
    ("HuBMAP_search_donors", "demographics_coded"),
    ("DDBJ_get_entry", "cross_reference_types"),
    ("TIMER2_immune_estimation", "study_sample_total"),
    ("TIMER2_immune_estimation", "sampling"),
    ("TIMER2_immune_estimation", "n_paired_samples"),
    ("OpenGenes_get_gene", "evidence_summary"),
    ("OpenGenes_get_gene", "aging_mechanisms"),
    ("CATH_get_domain_summary", "go_terms"),
    ("CATH_get_domain_summary", "pdb_segments"),
    ("Orphanet_get_genes", "Synonyms"),
    ("Orphanet_get_genes", "ExternalReferences"),
    ("UniProtRef_search_proteomes", "taxon_lineage_nodes"),
    ("UniProtRef_search_proteomes", "component_names"),
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


def test_a_uniprot_search_hit_says_whether_it_is_reviewed():
    """Swiss-Prot or TrEMBL is the biggest quality distinction in UniProt.

    `entryType` is "UniProtKB reviewed (Swiss-Prot)" or "UniProtKB unreviewed
    (TrEMBL)" on every entry of every search, and the row carried six fields
    that did not include it -- so a curated human entry and an unreviewed
    machine annotation came back looking identical. The annotation score and
    the protein-existence evidence level, the other two quality signals on
    the same entry, went with it.
    """
    source = _source("uniprot_tool.py")
    assert 'entry.get("entryType")' in source
    assert '"reviewed"' in source
    assert 'entry.get("annotationScore")' in source


def test_an_impc_phenotype_hit_says_how_it_was_called():
    """A phenotype hit is a statistical result.

    Which pipeline ran it, which test produced the p-value and which IMPC
    data release it comes from were all in the Solr `fields` the tool itself
    asked for, and the row dropped them -- so "preweaning lethality,
    incomplete penetrance, p=1e-6" arrived with no way to tell a
    Supplied-as-data call from a Fisher exact one.
    """
    source = _source("impc_tool.py")
    assert source.count('doc.get("statistical_method")') >= 2
    assert 'doc.get("pipeline_name")' in source
    assert 'doc.get("resource_name")' in source


def test_an_obsolete_efo_term_says_what_replaced_it():
    """EFO:0000400 is "obsolete_diabetes mellitus" and MONDO_0005015 replaced it.

    The tool reported `is_obsolete: true` and stopped there, from a record
    that names the replacement in `annotation.term_replaced_by` -- so a caller
    looking up diabetes got a dead term and no pointer to the live one.
    """
    source = _source("efo_tool.py")
    assert 'annotation.get("term_replaced_by")' in source
    assert 'annotation.get("has_alternative_id")' in source


def test_a_burden_p_value_comes_with_its_sample_size():
    """4,529 Genebass associations, and not one of them said n.

    The case and control counts are on the phenotype catalogue the tool
    already fetches to get each phenotype's description, and only the
    description was kept. A burden p-value with no n cannot be read.
    """
    source = _source("pheweb_phewas_tool.py")
    assert 'p.get("n_cases")' in source
    assert 'record.get("description")' in source, (
        "the catalogue join is what carries them"
    )
    # And a quantitative trait's n, which is not a case count at all.
    assert 'p.get("num_samples")' in source


def test_a_te_code_names_the_product_it_applies_to():
    """"AB" for the 80 mg tablet says nothing about the oral solution.

    Therapeutic equivalence is a property of a product -- a dosage form, a
    route and a strength -- and the row carried the brand name, the code and
    the application number, leaving the caller to assume one TE code covered
    every form the brand is sold in.
    """
    source = _source("fda_orange_book_tool.py")
    assert '"dosage_form": product.get("dosage_form")' in source
    assert '"active_ingredients": product.get(' in source


def test_cbioportal_sample_counts_are_not_one_number():
    """`max()` of three counts, and no way to tell which one it was.

    BRCA TCGA has 1,108 samples, 982 sequenced, 1,080 with CNA, 1,100 with
    RNA-seq v2, 529 with microarray, 316 with HM27 methylation and 892 with
    RPPA. A study that can answer an expression question may not be able to
    answer a methylation one, and `sample_count` could not tell them apart.
    """
    source = _source("cancer_prognosis_tool.py")
    assert "_study_counts" in source
    assert "methylationHm27SampleCount" in source
    assert "rppaSampleCount" in source


def test_usda_says_when_a_symbol_was_a_synonym():
    """USDA redirects a synonym to the accepted taxon in silence.

    `symbol=AGRE2` answers the profile of ELRE4, Elymus repens -- and the
    symbol asked for and the symbol answered sat in two different parts of
    the response, data and metadata, with nothing stating the substitution.
    Four sibling tools paid for the same profile only to turn a symbol into a
    numeric id and then threw it away, so a wetland or invasive answer named
    neither the species nor the swap.
    """
    source = _source("usda_plants_tool.py")
    assert "def _plant_identity" in source
    assert "is a synonym; USDA PLANTS answered" in source
    # The resolver hands back the profile it already paid for.
    assert "return profile.get(\"Id\"), symbol, None, profile" in source


def test_wormbase_phenotypes_name_the_allele_they_belong_to():
    """A phenotype annotation's subject is the allele, not the gene.

    unc-26's "aldicarb resistant" is the phenotype of allele m2
    (WB:WBVar00088530); `inferredGene` is how it maps back to the gene. The
    tool reported the statement against the gene with no allele named, so two
    alleles with different phenotypes arrived as one undifferentiated list.
    """
    source = _source("wormbase_tool.py")
    assert 'subject_of.get("alleleSymbol")' in source or (
        '_text(subject_of.get("alleleSymbol"))' in source
    )
    assert 'a.get("inferredGene")' in source


def test_wormbase_disease_ribbon_counts_this_genes_annotations():
    """`disease_count` is the same for every gene: it counts ribbon categories.

    The ribbon answers two things and only one was read. `categories` is the
    Disease Ontology skeleton, every top-level category whether or not the
    gene has an annotation in it, and `subjects` carries this gene's counts
    per group. unc-26 has two disease annotations and was reported with five
    "diseases", none of them marked as the ones it actually has.
    """
    source = _source("wormbase_tool.py")
    assert "nb_annotations" in source
    assert '"has_annotations"' in source
    assert '"annotated_disease_count"' in source


def test_mavedb_clinical_controls_link_to_the_score_sets_own_variants():
    """The endpoint exists to connect a ClinVar call to a measured score.

    A clinical control answers "ClinVar calls 65709 in BRCA2 Pathogenic, by
    expert panel". The link to the score set's own variant arrives under
    `clinvarLinks` and was read from `mappedVariants`, which the response does
    not carry -- so `mapped_variant_urns` was empty on all 2,122 controls of
    urn:mavedb:00001263-a-2 and the one thing the caller came for was absent.
    """
    source = _source("mavedb_tool.py")
    assert 'entry.get("clinvarLinks")' in source
    assert 'entry.get("mappedVariants")' in source, (
        "keep the old spelling as a fallback rather than swapping one guess "
        "for another"
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


def test_a_clingen_allele_names_its_gene_and_protein_change():
    """The tool's own description promises 'CA000387 (TP53 p.Arg248Gln)'.

    Both of those live only on `transcriptAlleles`, which the wrapper never
    read: it returned the CA id, the community standard title and the first
    genomic HGVS. CA000387 has 65 transcript alleles and the MANE Select one
    is the representation the registry exists to normalise to, so it is
    surfaced whatever its position in the list, the rest are capped, and the
    cap is disclosed.
    """
    source = _source("clingen_ar_tool.py")
    assert "TRANSCRIPTS_PER_ALLELE" in source
    assert '"mane_select_transcript": mane' in source
    assert '"transcript_alleles_truncated": len(rows) > TRANSCRIPTS_PER_ALLELE' in source
    schema = json.dumps(_config("ClinGenAR_lookup_allele").get("return_schema") or {})
    assert '"mane_refseq_hgvs"' in schema


def test_a_clingen_external_record_has_an_id_under_the_name_it_uses():
    """`rec.get("id")` returned None for the databases that matter most.

    dbSNP sends `rs`, ClinVar alleles send `alleleId` and ClinVar variations
    send `variationId`; none of them sends `id`. So a tool whose description
    promises "dbSNP rsIDs" answered `{"id": null, "url": ".../snp/113488022"}`
    -- the rsID only inside a URL -- and dropped the ClinVar preferred name,
    the 30 RCV accessions and the gnomAD variant string with it.
    """
    source = _source("clingen_ar_tool.py")
    assert '_ID_KEYS = ("rs", "alleleId", "variationId"' in source
    assert 'f"rs{rec[key]}" if key == "rs" else str(rec[key])' in source


def test_an_epmc_relationship_annotation_keeps_both_ends():
    """A Gene Disease Relationship has two tags, and tags[0] is one of them.

    Open Targets contributes relationship annotations to Europe PMC whose
    `tags` carry the gene and the disease together: on PMID 33332779 one of
    them is interleukin-6 receptor *and* pneumonia *and* Covid-19. The
    wrapper read `tags[0]`, so the relationship arrived as its subject with
    the object silently gone -- and 17 of that article's 347 annotations are
    of that shape.
    """
    source = _source("epmc_annotations_tool.py")
    assert "def _tags(" in source
    assert '"tags": tags' in source
    assert '"tag_count"' in source
    schema = json.dumps(
        _config("EPMC_get_text_mined_annotations").get("return_schema") or {}
    )
    assert '"mentions_truncated"' in schema


def test_a_drugcentral_signal_comes_with_the_threshold_it_is_measured_against():
    """An llr of 44808 means nothing without llr_threshold of 9.445.

    DrugCentral ships a FAERS disproportionality row per MedDRA term -- 1,534
    for metformin, the strongest of them lactic acidosis -- and the whole
    section was dropped from a tool whose description promises "comprehensive
    drug data". Rows are ranked by llr, capped, and the cut is disclosed; the
    pair is reported together with is_signal, and the metadata says a signal
    is a reporting association and not causation.
    """
    source = _source("drugcentral_tool.py")
    assert "SIGNALS_PER_DRUG" in source
    assert '"is_signal"' in source
    assert "not evidence of causation" in source
    assert '"adverse_event_signals_truncated"' in source


def test_a_bgee_expression_call_reports_its_fdr():
    """`quality: "gold"` is the summary of the FDR, not the FDR.

    All 145 calls for TP53 carry `fdr` and all 145 lost it, while the
    qualitative grade derived from it was kept. The gene the response was
    answered for was dropped too, so a wrong gene id and a gene with no calls
    were the same empty answer.
    """
    source = _source("bgee_tool.py")
    assert 'call.get("fdr")' in source
    assert '"cluster_index": call.get("clusterIndex")' in source
    assert '"gene": {' in source


def test_an_itis_invalid_name_says_what_replaced_it():
    """"invalid" without the accepted name is half an answer.

    TSN 944513 is reported `usage_rating: "invalid"`, and the same response
    says it is a "junior synonym" of Homo sapiens, TSN 180092 -- both in
    `acceptedNameList` and `unacceptReason`, neither of which was read. The
    record also held 29 synonyms, 7 jurisdictional origins (Native in Alaska,
    and so on), the Taxonomic Work Group's credibility verdict, and the
    publications and experts the tool's own docstring promises as "authority
    references".
    """
    source = _source("itis_tool.py")
    assert '_rows(data.get("acceptedNameList"), "acceptedNames")' in source
    assert '"unaccept_reason"' in source
    assert '"synonyms_truncated"' in source
    assert "SYNONYMS_PER_RECORD" in source
    schema = json.dumps(_config("ITIS_get_full_record").get("return_schema") or {})
    assert '"unaccept_reason"' in schema


def test_a_hubmap_contributor_orcid_is_not_null():
    """`person.get("orcid")` against an API that sends `orcid_id`.

    Every contributor on HBM626.FHJD.938 has an ORCID and every one of them
    came back null -- the shape where a key the API does not send is read and
    the absence looks like missing data upstream.
    """
    source = _source("hubmap_tool.py")
    assert 'person.get("orcid") or person.get("orcid_id")' in source


def test_a_hubmap_provenance_chain_says_what_the_donor_was():
    """The chain ends at a Donor whose attributes were not reported.

    The lineage row carried seven keys, none of them the donor's age, sex or
    race -- which `metadata.organ_donor_data` holds in the same response, as
    UMLS-coded assertions. Walking Dataset -> Sample -> Donor and then not
    saying who the donor was is most of the question left unanswered.
    """
    source = _source("hubmap_tool.py")
    assert "def _donor_attributes" in source
    assert "organ_donor_data" in source
    assert '"spatial_annotations": _ccf_annotations(entity)' in source


def test_an_rxclass_member_says_whether_it_is_a_direct_member():
    """DIRECT and INDIRECT membership are different claims.

    RxClass states it per member in `nodeAttr`, along with the source's own id
    for the member -- M01AE07 for suprofen under ATC M01AE -- and the row
    reported rxcui, name and tty, so a member of a descendant class was
    indistinguishable from a member of the class asked about.
    """
    source = _source("rxclass_tool.py")
    assert 'by_name.get("Relation")' in source
    assert 'by_name.get("SourceId")' in source


def test_a_chebi_compound_reports_its_cas_number_and_its_roles():
    """Aspirin's 50-78-2 was in the response and was not returned.

    `database_accessions` holds four sections -- CAS, registry numbers, 68
    PubMed citations and the manual cross-references -- and none was read.
    Nor was `roles_classification`, which is 36 entries for aspirin and is the
    half of ChEBI that is an ontology rather than a structure database. The
    synonym list also flattened a ChEMBL BRAND NAME and an IUPAC NAME into one
    undifferentiated list of strings.
    """
    source = _source("chebi_tool.py")
    assert "def _accessions" in source
    assert "def _roles" in source
    assert '"synonym_details": synonym_detail_page' in source
    schema = json.dumps(_config("ChEBI_get_compound").get("return_schema") or {})
    assert '"cas_numbers_total"' in schema


def test_an_ols_search_hit_carries_the_definition_it_arrived_with():
    """A term search answering a label and an id costs a call per hit.

    Every /api/search doc carries `description`, `exact_synonyms`,
    `related_synonyms`, `type` and `ontology_prefix`, and the row model had
    six fields that included none of them. The definition is also where OLS
    records a merge: ZFA:0009046's says CL:0000804 and CL:0000812 were merged
    into CL:0000084.
    """
    source = _source("ols_tool.py")
    assert 'item.get("exact_synonyms")' in source
    assert "def _as_string_list" in source
    schema = json.dumps(_config("ols_search_terms").get("return_schema") or {})
    assert '"related_synonyms"' in schema
    assert '"items"' in schema, "the terms array declared nothing about its rows"


def test_a_gbif_tree_walker_returns_the_keys_to_walk_with():
    """Seven rank names, no rank keys, on a tool for navigating a tree.

    `_slim_usage` projected onto 19 of the 38 fields a name-usage record
    carries: the kingdom/phylum/class/order/family/genus/species names were
    in and the matching `...Key` values were out, so following the lineage
    needed a name search per step. `issues` -- GBIF's own quality flags, e.g.
    NAME_PARENT_MISMATCH -- and the dataset the record came from were dropped
    too.
    """
    source = _source("gbif_taxonomy_tool.py")
    for key in ("kingdomKey", "phylumKey", "classKey", "orderKey", "familyKey",
                "genusKey", "speciesKey", "issues", "datasetKey"):
        assert f'"{key}"' in source, f"_slim_usage still drops {key}"


def test_a_binding_site_names_what_binds_there():
    """EGFR 718-726 binds ATP, CHEBI:30616, and said only 718-726.

    Four of P00533's eleven DOMAINS_AND_SITES features carry a `ligand`, and
    the category's own description is "binding sites, DNA binding regions,
    motifs, regions". The MOLECULE_PROCESSING features lost `ftId` the same
    way -- PRO_0000015819 is the insulin B chain, and it is how a processed
    chain is cited.
    """
    source = _source("ebi_proteins_features_tool.py")
    assert 'f.get("ligand")' in source
    assert 'f.get("ftId")' in source
    schema = json.dumps(
        _config("EBIProteins_get_domains_sites").get("return_schema") or {}
    )
    assert '"ligand"' in schema


def test_an_intronic_clingen_coordinate_keeps_its_offset():
    """`start: 1258` is not where the variant is when the offset is 3918.

    For an intronic variant the registry gives the position as an exon
    boundary plus an offset into the intron and a direction: 12 of the
    transcript alleles on the page for rs113488022 read start 1258 with
    startIntronOffset 3918 in the '-' direction, i.e. 1258-3918. Reporting
    1258 alone is not a field omitted, it is a different position asserted --
    an exonic one.
    """
    source = _source("clingen_ar_tool.py")
    assert 'coord.get("startIntronOffset")' in source
    assert 'coord.get("startIntronDirection")' in source
    assert '"is_intronic"' in source
    schema = json.dumps(_config("ClinGenAR_lookup_allele").get("return_schema") or {})
    assert '"start_intron_offset"' in schema


def test_both_ebi_interaction_tools_return_the_intact_ids():
    """One handler returned them and its sibling over the same endpoint did not.

    `interactor1` and `interactor2` are the IntAct interactor ids, without
    which a row cannot be followed into IntAct. A substring anchor is no use
    here -- the name was already in the file once, in the handler that did
    read it -- so this counts both reads.
    """
    source = _source("ebi_proteins_interactions_tool.py")
    assert source.count('interaction.get("interactor1")') == 2, (
        "get_interactions reads the IntAct ids and get_interaction_details "
        "must read them too"
    )
    assert source.count('interaction.get("interactor2")') == 2



def test_a_coordinate_mapping_returns_the_annotations_it_mapped():
    """16,654 features came back for TP53 and none reached the caller.

    `/coordinates/{acc}` attaches UniProt's whole feature table to each
    transcript mapping, already projected onto the genome -- 1,514 on TP53's
    first transcript, 1,363 of them sequence variants with their VAR ids and
    their genome positions. The tool paged the exons carefully and never
    looked at the features. It also dropped `assemblyName`, so the genome
    positions it did return came without the assembly they are against.
    """
    source = _source("ebi_proteins_coordinates_tool.py")
    assert "FEATURES_PER_MAPPING" in source
    assert "def _feature_page" in source
    assert 'genomic_loc.get("assemblyName")' in source
    schema = json.dumps(
        _config("EBIProteins_get_coordinate_mapping").get("return_schema") or {}
    )
    assert '"feature_type_counts"' in schema


def test_an_ebi_disease_annotation_keeps_its_omim_id_and_its_text():
    """`diseaseId or acronym` and discard the rest dropped three things.

    The OMIM id is in `dbReference`, the definition in `description`, and one
    of TP53's nine disease records has no diseaseId at all -- it is the
    free-text disease involvement paragraph, so the name list dropped it
    entirely rather than listing it without a name.
    """
    source = _source("ebi_proteins_interactions_tool.py")
    assert "def _disease_rows" in source
    assert 'row.get("dbReference")' in source
    assert "def _location_rows" in source
    # The name lists stay, so a caller reading `diseases` still works.
    assert '"diseases": sorted(diseases)' in source


def test_a_swiss_model_structure_names_what_is_bound_in_it():
    """266 of P04637's 325 models carry a ligand and said nothing about it.

    The flattener reported `in_complex_with` protein partners and dropped
    `ligand_chains` -- zinc and magnesium on the p53 models -- along with
    `oligo-state`, which is the only thing that distinguishes a monomer from
    a 4-mer when there are no protein partners. The summary built its own
    narrower dict than the model list, so it was missing them twice over.
    """
    source = _source("swissmodel_tool.py")
    assert 's.get("ligand_chains")' in source
    assert 's.get("oligo-state")' in source
    assert 'summary["best_model"] = self._flatten_structure(best)' in source


def test_a_living_donor_has_demographics_too():
    """Reading only organ_donor_data returned {} for every living donor.

    HuBMAP stores a deceased donor's attributes under
    `metadata.organ_donor_data` and a living donor's under
    `metadata.living_donor_data`, and the normaliser knew only the first --
    so `demographics` came back empty with nothing to say why.
    """
    source = _source("hubmap_sample_tool.py")
    assert 'metadata.get("living_donor_data")' in source


def test_an_osdr_study_returns_its_protocols():
    """"Full metadata for one OSDR study" without the methods.

    OSD-1 lists eight protocols with their types and their full descriptions,
    and all three fields were dropped, along with the investigator, the
    funding agency and the grant number. `assays` and `files` on that
    endpoint hold only a REST_URL each, so the link is what there is to
    report -- counting the object gave 1 for every study.
    """
    source = _source("nasa_osdr_tool.py")
    assert 'metadata.get("study protocol description")' in source
    assert "def _person" in source
    assert '"assays_url"' in source


def test_an_id_mapping_database_says_both_directions():
    """Mapping has two directions and the listing reported one.

    All 95 databases say whether they can be mapped `from` and `to`, and only
    `from` was read -- so a caller choosing a target database had nothing to
    choose on. 90 of them also carry the URI template that resolves an id in
    that database, which is what having a mapped id is for.
    """
    source = _source("uniprot_idmapping_tool.py")
    assert 'item.get("to", False)' in source
    assert 'item.get("uriLink")' in source


def test_a_gwas_study_says_whether_it_has_summary_statistics():
    """The tool is named after summary statistics and did not report them.

    `summaryStatistics` is the FTP path to the deposited statistics, or the
    literal "NA" when there are none, and the study record dropped it along
    with the discovery sample ("2,095 European ancestry exposed individuals"
    against "42,907 ... unexposed"), the per-ancestry counts, the genotyping
    platform, the paper's title and the gene-environment flag.
    """
    source = _source("gwas_sumstats_tool.py")
    assert 'entry.get("summaryStatistics")' in source
    assert '"has_summary_statistics"' in source
    assert 'entry.get("discoverySampleAncestry")' in source
    schema = json.dumps(
        _config("GWASSumStats_get_trait_studies").get("return_schema") or {}
    )
    assert '"summary_statistics"' in schema
    # The row used to be declared as study_accession and nothing else.
    assert '"reported_trait"' in schema


def test_a_trial_returns_its_secondary_outcomes():
    """NCT04280705 has 4 primary outcomes and 39 secondary ones.

    `ClinicalTrials_get_study` begins "get full details" and read
    primaryOutcomes alone -- while the ClinicalTrialsDetailsTool handler in
    the same module has always read both, and had otherOutcomes commented out
    with no reason given. The description, which enumerated "primary
    outcome", is corrected with the fix rather than left to justify it.
    """
    source = _source("ctg_tool.py")
    assert '_outcomes("secondaryOutcomes")' in source
    assert '_outcomes("otherOutcomes")' in source
    assert "OUTCOMES_PER_SEARCH_ROW" in source
    description = _config("ClinicalTrials_get_study")["description"]
    assert "primary, secondary and other" in description


def test_a_nutrient_value_says_how_it_was_obtained():
    """"Calculated from value per serving size measure" is not a measurement.

    Every nutrient row carried name, value and unit, and the derivation code
    that separates an analysed value from a calculated or imputed one was
    dropped -- along with the USDA nutrient number, which is the identifier a
    name is not.
    """
    source = _source("fooddata_central_tool.py")
    assert 'n.get("derivationDescription")' in source
    assert 'n.get("nutrientNumber")' in source


def test_a_cellxgene_collection_can_be_cited_and_is_not_zero_cells():
    """Two defects in one row.

    `publisher_metadata` carries the journal, the date and the 12 authors of
    the retina atlas, and the row reported the DOI and a contact name, so a
    collection could not be cited from a listing. And `total_cells` was
    `sum(ds.get("cell_count", 0) ...)` over datasets that the listing
    endpoint gives no cell_count for, so it was 0 for every collection --
    which reads as "no cells" rather than "the listing does not say".
    """
    source = _source("cellxgene_discovery_tool.py")
    assert "def _publication" in source
    assert "total_cells = sum(counted) if counted else None" in source
    assert '"datasets_with_cell_count"' in source


def test_an_availability_answer_says_when_the_generic_was_approved():
    """"A generic exists" and "a generic was approved in 2015" differ.

    Drugs@FDA sends the whole submission history with every search result --
    284 rows across one availability check -- and the row the search builds
    dropped it, so neither the availability answer nor the search carried an
    approval date. ADVIL's first ANDA, ANDA206581, was approved 2015-08-03.
    The summary is computed once in the search row and carried down, and the
    full history stays the sibling tool's job, which the output now names.
    """
    source = _source("fda_orange_book_tool.py")
    assert "def _submission_summary" in source
    assert '_submission_summary(result.get("submissions"))' in source
    assert "_SUBMISSION_SUMMARY_KEYS" in source
    assert "submission_history_tool" in source


def test_a_nextstrain_coloring_is_more_than_its_key():
    """"gt" is genotype and "num_date" is date, and the response says so.

    Each coloring carries its own `title` and `type`, and a categorical one
    carries the values the build covers -- zika's `country` has 36 -- paired
    with the colour used to draw it. The summary reported the keys and called
    the list complete, which it was, of the keys.
    """
    source = _source("nextstrain_tool.py")
    assert "def _coloring_values" in source
    assert "COLORING_VALUES_PER_DIMENSION" in source
    schema = json.dumps(_config("Nextstrain_get_dataset").get("return_schema") or {})
    assert '"value_count"' in schema


def test_an_immune_estimate_pairs_by_sample_not_by_position():
    """The correlation was over two lists, not over patients.

    `_immune_estimation` grouped expression records by gene and appended the
    values in response order, then correlated `marker_vals[:n]` against
    `target_vals[:n]` with `n = min(len(a), len(b))` -- two lists built from
    separate groupings, paired by position.

    Measured on brca_tcga: all six markers return a value for every one of
    the first 100 samples in the same order, so the positional pairing was
    in fact correct for that request -- by coincidence, not by construction.
    cBioPortal documents no ordering guarantee for /molecular-data/fetch,
    one missing value would shift every later position, and
    `min(len(a), len(b))` would truncate rather than align. Because the
    sample id was dropped, nothing in the output could show whether the
    pairing had held.

    The sibling handler `_gene_correlation` in this module has always built
    per-sample maps and intersected them ("paired samples only"); this one
    now does too, and reports how many samples the r is over. The field the
    fix needed is the one the sweep flagged as dropped: `sampleId`, on all
    600 records.
    """
    source = _source("timer_tool.py")
    # A substring anchor is no use: `_gene_correlation` already read the
    # sample id, so the name was in the file before the fix. Count it.
    assert source.count('rec.get("sampleId")') == 2
    assert "set(marker_by_sample) & set(target_by_sample)" in source
    assert '"n_paired_samples": len(common)' in source


def test_an_immune_estimate_says_it_used_a_hundred_of_a_thousand_samples():
    """`n_samples: 100` was the cap, and the study has over a thousand.

    The mean and median are over whatever 100 samples cBioPortal lists
    first -- not a random sample -- and nothing in the answer said so. The
    cut is now a parameter with a stated default, the study's own sample
    count is fetched and reported, and the ordering is spelled out.
    """
    source = _source("timer_tool.py")
    assert "SAMPLES_PER_ESTIMATE" in source
    assert "def _get_study_sample_count" in source
    assert "not a random sample" in source


def test_open_genes_says_how_a_gene_is_implicated_not_just_how_often():
    """"Use to assess whether and HOW a gene is implicated in aging", and 57.

    `researches` holds the evidence records -- 57 longevity associations and
    14 lifespan studies for GHR -- and `_evidence_counts` reduced each list
    to its length. No other tool in the family returns the records, so the
    longevity effects, the intervention results, the change types, the model
    organisms and the DOIs were unreachable. The digest reports the distinct
    values per evidence type beside the counts, which answers "how" without
    copying hundreds of records.
    """
    source = _source("open_genes_tool.py")
    assert "def _evidence_digest" in source
    assert "_EVIDENCE_DIGEST_FIELDS" in source
    assert '"evidence_counts"' in source, "the counts stay"
    schema = json.dumps(_config("OpenGenes_get_gene").get("return_schema") or {})
    # The success branch used to declare no properties at all.
    assert '"aging_mechanisms"' in schema
    assert '"evidence_summary"' in schema


def test_a_cath_domain_summary_carries_its_function_and_its_boundaries():
    """A domain is its segments, and its summary dropped both.

    `go_terms` -- with the evidence code that qualifies each and the aspect it
    belongs to -- and `ec_terms` are the functional annotation, and
    `pdb_segments` are the residue ranges that make the domain a domain. The
    summary reported a residue COUNT and the CATH classification. The sibling
    handler `_get_funfam` has always returned `go_terms`.
    """
    source = _source("cath_tool.py")
    assert "def _go_terms" in source
    assert 'data.get("pdb_segments")' in source
    assert 'data.get("ec_terms")' in source
    assert source.count('"go_terms"') >= 2, "both handlers must carry them"



def test_a_spearman_p_value_is_not_rounded_to_zero():
    """`round(p, 6)` reports every p below 5e-7 as 0.0.

    A Spearman r of 0.71 between CD19 and PDCD1 over 100 BRCA tumours has
    p = 1.1e-16, and the tool said `p_value: 0.0` -- a claim no test can
    make. Six SIGNIFICANT figures keeps 1.1e-16 and still shortens
    0.0314159265 to 0.0314159.
    """
    source = _source("timer_tool.py")
    assert "def _p_value" in source
    assert "round(float(pval), 6)" not in source, (
        "decimal rounding flattens a small p-value to zero"
    )


def test_an_interaction_names_the_experiments_behind_it():
    """"Evidence Datasets: complete 466" and not one of their names.

    HumanBase answers 466 datasets for BRCA1-TP53 and 479 for TP53-MDM2,
    each with the database it is (IntAct, BioGRID), the kind of evidence it
    provides and the posterior it contributed. The report fetched all of
    them, counted them, and printed the count -- so "evidence" was a number.
    The strongest are named now, by posterior, with the remainder disclosed.
    """
    source = _source("humanbase_tool.py")
    assert "def _top_evidence_datasets" in source
    assert "EVIDENCE_DATASETS_NAMED" in source


def test_cbioportal_says_which_mutation_profile_it_read():
    """"Mutations" and "Mutations (uncalled)" are different profiles.

    The resolver matched a profile by alteration type, took its id and
    discarded the record -- the name, the datatype (MAF) and the description
    that says the calls came from whole-exome sequencing. An empty mutation
    result means different things in a called and an uncalled profile. It
    also falls back to a naming-convention guess when no profile matches,
    and the caller could not tell a matched id from a guessed one.

    The record goes out through an out-parameter: three tests assert on the
    scalar return of _get_mutation_profile_id. The new fields are on the
    response envelope, which this tool's return_schema does not describe --
    it declares the inner mutation array -- so they are guarded here rather
    than by a schema row.
    """
    source = _source("cbioportal_tool.py")
    assert 'found["resolution"] = "matched"' in source
    assert 'found["resolution"] = "guessed"' in source
    assert '"molecular_profile_resolution": profile_found.get("resolution")' in source

