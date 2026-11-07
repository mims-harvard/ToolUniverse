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
