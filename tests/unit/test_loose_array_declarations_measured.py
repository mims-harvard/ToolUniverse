"""Arrays whose declarations said nothing about their contents, measured.

1,011 array declarations across 595 tools either carry no `items` at all (795)
or `items: {"type": "object"}` with no properties (216). Each accepts anything,
so nothing inside one can fail validation -- the same defect as the 74 vacuous
envelope schemas earlier in this branch, one level down.

This is the first batch: ten tools on public APIs, measured over 134 calls.
Each array's contents were observed and the declaration written from what came
back, never from what the field is named or what the upstream docs imply.

The rules the measurement was turned into declarations by, which are the
interesting part:

  * an array with no observed items is left alone -- nothing is claimed
  * object items need at least 5 observations before their shape is declared
  * scalar items need at least 3: `items: {"type": "string"}` claims the
    elements are never anything else, and one element cannot carry that. Seven
    ENCODE accession lists were declared and then withdrawn on this rule once
    it was written down, which is the point of writing it down
  * `required` only for fields present in 100% of at least 20 observed items
  * a field that was null in every observation is OMITTED, not declared "null"

That last one is the lesson of the commit three back. Declaring a field `"null"`
claims it can never hold anything, and eleven entries is not enough to support
that: em_3d_reconstruction's num_class_averages was declared null on such a
sample and 3,934 of the PDB's 37,607 electron-microscopy entries populate it.
An undeclared property makes no claim at all, which is the honest position when
33 bio.tools records show nothing but null for `credit.fundrefid`.

Corrected after this batch was first pushed, which is the part worth reading.
That version declared 49 arrays and left 47 alone, every one of the 47 recorded
as "empty on every input". 23 of those 47 were reachable; 73 are declared now
and 24 are left.

ENCODE answers the question directly -- its index takes `field=*` and reports
how many records carry a field, the same trick RCSB's search API allowed
earlier in this branch. Asking it:

    File       aliases               1,227,220 records
    File       quality_metrics         264,016
    File       dbxrefs                 130,508
    File       flowcell_details        106,424
    Biosample  applied_modifications    12,702
    Experiment documents                16,873
    Experiment related_files                 1

Every one of ENCODE's 23 was populated, and ten sampled accessions had reached
none of them. Measuring the records the index named declares 22 of the 23 and
leaves related_files alone on a reason worth having: the archive holds exactly
one record carrying it.

The wording was the fault. "Empty on every input" is true of a field nothing in
the archive populates and of a field 1.2 million records populate, and it reads
the same either way. Each entry below now says which, and where an index
answered, it says what the index said.

Two other things the correction turned up. `articles->*->authors` is a loose
array this batch created: declaring `articles` gave it an `authors` field typed
`array` with nothing inside, one level deeper than anything the original scan
counted -- so 1,011 is not a countdown, and each batch has to re-scan after
applying. And the wider ENCODE inputs exposed three over-narrow fields in
ENCODE_get_file with nothing to do with arrays -- assay_term_name (26 strings
and 23 lists over 50 files), biosample_ontology (46 strings, 1 list) and
target -- all declared plain strings.

ChannelsDB is handled as one item type rather than twelve. Its twelve channel
arrays hold the same thing: 53 channels across the 8 that were non-empty, every
one carrying the same seven fields. Declaring them per array would have typed
the array with 21 observations and left the one with a single observation
alone, for no reason other than which PDB entries happened to be sampled.

Verified by corrupting one declared field inside each array on a live payload:
43 of the 45 arrays reachable that way went from accepted to rejected. The two
that did not were the corruption landing on `function.cmd` and `link.note`, the
fields deliberately left undeclared; corrupting `function.input` and `link.url`
instead rejects both.
"""

import json
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _tool(stem, name):
    for entry in json.loads((DATA / f"{stem}.json").read_text()):
        if entry.get("name") == name:
            return entry
    raise AssertionError(f"{name} not in {stem}.json")


def _node(schema, path):
    """The declaration at a '->' path, looking through oneOf/anyOf/allOf."""

    def step(node, seg):
        if not isinstance(node, dict):
            return None
        found = (
            node.get("items") if seg == "*" else (node.get("properties") or {}).get(seg)
        )
        if found is not None:
            return found
        for keyword in ("oneOf", "anyOf", "allOf"):
            for branch in node.get(keyword) or []:
                found = step(branch, seg)
                if found is not None:
                    return found
        return None

    node = schema
    for seg in path.split("->"):
        node = step(node, seg)
        if node is None:
            return None
    return node


# Generated from the measurement; each row carries the sample behind it.
DECLARED_OBJECT_ITEMS = [
    (
        "biotools_registry_tools",
        "BioTools_get_tool",
        "credit",
        ["email", "name", "orcidid", "typeEntity", "typeRole", "url"],
        ["email", "name", "orcidid", "typeEntity", "typeRole", "url"],
        33,
    ),
    (
        "biotools_registry_tools",
        "BioTools_get_tool",
        "documentation",
        ["note", "type", "url"],
        ["note", "type", "url"],
        20,
    ),
    (
        "biotools_registry_tools",
        "BioTools_get_tool",
        "download",
        ["note", "type", "url", "version"],
        [],
        14,
    ),
    (
        "biotools_registry_tools",
        "BioTools_get_tool",
        "function",
        ["input", "note", "operation", "output"],
        [],
        19,
    ),
    ("biotools_registry_tools", "BioTools_get_tool", "link", ["type", "url"], [], 13),
    (
        "biotools_registry_tools",
        "BioTools_get_tool",
        "topic",
        ["term", "uri"],
        ["term", "uri"],
        34,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->CSATunnels_Caver",
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        53,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->CSATunnels_MOLE",
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        53,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->CofactorTunnels_MOLE",
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        53,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->ProcognateTunnels_Caver",
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        53,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->ProcognateTunnels_MOLE",
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        53,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->ReviewedChannels_Caver",
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        53,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->ReviewedChannels_MOLE",
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        53,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->TransmembranePores_MOLE",
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        ["Auto", "Cavity", "Id", "Layers", "Profile", "Properties", "Type"],
        53,
    ),
    (
        "clinicaltrials_gov_tools",
        "ClinicalTrials_get_study",
        "arms",
        ["description", "intervention_names", "label", "type"],
        ["description", "intervention_names", "label", "type"],
        38,
    ),
    (
        "clinicaltrials_gov_tools",
        "ClinicalTrials_get_study",
        "interventions",
        ["description", "name", "type"],
        [],
        19,
    ),
    (
        "clinicaltrials_gov_tools",
        "ClinicalTrials_get_study",
        "locations",
        ["city", "country", "facility", "status"],
        ["city", "country", "facility", "status"],
        295,
    ),
    (
        "clinicaltrials_gov_tools",
        "ClinicalTrials_get_study",
        "primary_outcomes",
        ["description", "measure", "time_frame"],
        ["description", "measure", "time_frame"],
        85,
    ),
    (
        "clinicaltrials_gov_tools",
        "ClinicalTrials_get_study",
        "references",
        ["citation", "pmid", "type"],
        ["citation", "type"],
        59,
    ),
    (
        "crossref_tools",
        "Crossref_get_work",
        "author",
        [
            "ORCID",
            "affiliation",
            "authenticated-orcid",
            "family",
            "given",
            "name",
            "role",
            "sequence",
            "suffix",
        ],
        ["affiliation", "role", "sequence"],
        351,
    ),
    (
        "crossref_tools",
        "Crossref_get_work",
        "funder",
        ["DOI", "award", "award-info", "doi-asserted-by", "id", "name"],
        [],
        17,
    ),
    (
        "crossref_tools",
        "Crossref_get_work",
        "license",
        ["URL", "content-version", "delay-in-days", "start"],
        ["URL", "content-version", "delay-in-days", "start"],
        20,
    ),
    (
        "crossref_tools",
        "Crossref_get_work",
        "reference",
        [
            "DOI",
            "article-title",
            "author",
            "doi-asserted-by",
            "first-page",
            "issue",
            "journal-title",
            "key",
            "series-title",
            "unstructured",
            "volume",
            "volume-title",
            "year",
        ],
        ["key"],
        738,
    ),
    (
        "dbaasp_tools",
        "DBAASP_get_peptide",
        "articles",
        [
            "additional",
            "authors",
            "id",
            "journal",
            "pages",
            "pubmed",
            "title",
            "volume",
            "year",
        ],
        [
            "additional",
            "authors",
            "id",
            "journal",
            "pages",
            "pubmed",
            "title",
            "volume",
            "year",
        ],
        27,
    ),
    (
        "dbaasp_tools",
        "DBAASP_get_peptide",
        "articles->*->authors",
        ["description", "name"],
        ["description", "name"],
        343,
    ),
    (
        "dbaasp_tools",
        "DBAASP_get_peptide",
        "hemoliticCytotoxicActivities",
        [
            "activity",
            "activityMeasureForLysisGroup",
            "activityMeasureForLysisValue",
            "concentration",
            "id",
            "ionicStrength",
            "note",
            "peptideId",
            "ph",
            "reference",
            "saltType",
            "targetCell",
            "unit",
        ],
        [],
        11,
    ),
    (
        "dbaasp_tools",
        "DBAASP_get_peptide",
        "smiles",
        [
            "description",
            "id",
            "lastUpdatedAt",
            "manuallyEdited",
            "pubChemCid",
            "pubChemCidUrl",
            "smiles",
            "smilesImageUrl",
        ],
        [
            "description",
            "id",
            "lastUpdatedAt",
            "manuallyEdited",
            "pubChemCid",
            "pubChemCidUrl",
            "smiles",
            "smilesImageUrl",
        ],
        27,
    ),
    (
        "dbaasp_tools",
        "DBAASP_get_peptide",
        "sourceGenes",
        ["dblink", "gene", "id", "kingdom", "note", "source", "subkingdom"],
        [],
        12,
    ),
    (
        "dbaasp_tools",
        "DBAASP_get_peptide",
        "targetActivities",
        [
            "activity",
            "activityMeasureGroup",
            "activityMeasureValue",
            "cfu",
            "cfuGroup",
            "concentration",
            "id",
            "ionicStrength",
            "medium",
            "note",
            "peptideId",
            "ph",
            "reference",
            "saltType",
            "targetSpecies",
            "unit",
        ],
        [
            "activity",
            "activityMeasureGroup",
            "activityMeasureValue",
            "cfu",
            "cfuGroup",
            "concentration",
            "id",
            "ionicStrength",
            "medium",
            "note",
            "peptideId",
            "ph",
            "reference",
            "saltType",
            "targetSpecies",
            "unit",
        ],
        163,
    ),
    ("dbaasp_tools", "DBAASP_get_peptide", "targetGroups", ["name"], ["name"], 46),
    (
        "dbaasp_tools",
        "DBAASP_get_peptide",
        "uniprots",
        ["description", "id", "proPeptide", "uniprotId", "uniprotUrl"],
        [],
        9,
    ),
    (
        "encode_tools",
        "ENCODE_get_file",
        "flowcell_details",
        ["barcode", "flowcell", "lane", "machine"],
        [],
        9,
    ),
]

DECLARED_SCALAR_ITEMS = [
    ("biotools_registry_tools", "BioTools_get_tool", "collectionID", "string", 22),
    ("biotools_registry_tools", "BioTools_get_tool", "version", "string", 40),
    (
        "clinicaltrials_gov_tools",
        "ClinicalTrials_get_study",
        "conditions",
        "string",
        23,
    ),
    ("clinicaltrials_gov_tools", "ClinicalTrials_get_study", "phases", "string", 10),
    ("crossref_tools", "Crossref_get_work", "container-title", "string", 10),
    ("crossref_tools", "Crossref_get_work", "title", "string", 10),
    ("encode_tools", "ENCODE_get_biosample", "alternate_accessions", "string", 7),
    ("encode_tools", "ENCODE_get_biosample", "applied_modifications", "string", 22),
    ("encode_tools", "ENCODE_get_biosample", "characterizations", "string", 5),
    ("encode_tools", "ENCODE_get_biosample", "genetic_modifications", "string", 10),
    ("encode_tools", "ENCODE_get_biosample", "internal_tags", "string", 7),
    (
        "encode_tools",
        "ENCODE_get_biosample",
        "model_organism_donor_modifications",
        "string",
        12,
    ),
    ("encode_tools", "ENCODE_get_biosample", "parent_of", "string", 11),
    ("encode_tools", "ENCODE_get_biosample", "references", "string", 7),
    ("encode_tools", "ENCODE_get_biosample", "treatments", "string", 10),
    ("encode_tools", "ENCODE_get_experiment", "alternate_accessions", "string", 7),
    ("encode_tools", "ENCODE_get_experiment", "category_slims", "string", 21),
    ("encode_tools", "ENCODE_get_experiment", "documents", "string", 42),
    ("encode_tools", "ENCODE_get_experiment", "objective_slims", "string", 19),
    ("encode_tools", "ENCODE_get_experiment", "revoked_files", "string", 8),
    ("encode_tools", "ENCODE_get_experiment", "superseded_by", "string", 5),
    ("encode_tools", "ENCODE_get_experiment", "supersedes", "string", 14),
    ("encode_tools", "ENCODE_get_experiment", "type_slims", "string", 7),
    ("encode_tools", "ENCODE_get_file", "aliases", "string", 19),
    ("encode_tools", "ENCODE_get_file", "alternate_accessions", "string", 9),
    ("encode_tools", "ENCODE_get_file", "dbxrefs", "string", 18),
    ("encode_tools", "ENCODE_get_file", "fastq_signature", "string", 5),
    ("encode_tools", "ENCODE_get_file", "quality_metrics", "string", 10),
    ("encode_tools", "ENCODE_get_file", "superseded_by", "string", 6),
    ("hgnc_tools", "HGNC_fetch_gene_by_symbol", "alias_symbol", "string", 48),
    ("hgnc_tools", "HGNC_fetch_gene_by_symbol", "ccds_id", "string", 62),
    ("hgnc_tools", "HGNC_fetch_gene_by_symbol", "gene_group", "string", 38),
    ("hgnc_tools", "HGNC_fetch_gene_by_symbol", "omim_id", "string", 20),
    ("hgnc_tools", "HGNC_fetch_gene_by_symbol", "prev_name", "string", 23),
    ("hgnc_tools", "HGNC_fetch_gene_by_symbol", "prev_symbol", "string", 20),
    ("hgnc_tools", "HGNC_fetch_gene_by_symbol", "refseq_accession", "string", 20),
    ("hgnc_tools", "HGNC_fetch_gene_by_symbol", "uniprot_ids", "string", 20),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->cities_tags",
        "string",
        3,
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->emb_codes_hierarchy",
        "string",
        6,
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->emb_codes_tags",
        "string",
        6,
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->sources->*->images",
        "string",
        17,
    ),
]

# Still left alone -- the reason is the parameter, and it distinguishes
# "the index says a million records carry it and none were sampled" from
# "the index says one record in the archive carries it".
LEFT_ALONE = [
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->AlphaFillTunnels_Caver",
        0,
        "the /channels/pdb/ route this tool calls does not serve these groups; ChannelsDB has a separate /channels/alphafill/ route the tool never calls",
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->AlphaFillTunnels_MOLE",
        0,
        "the /channels/pdb/ route this tool calls does not serve these groups; ChannelsDB has a separate /channels/alphafill/ route the tool never calls",
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->CofactorTunnels_Caver",
        0,
        "the /channels/pdb/ route this tool calls does not serve these groups; ChannelsDB has a separate /channels/alphafill/ route the tool never calls",
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->TransmembranePores_Caver",
        0,
        "the /channels/pdb/ route this tool calls does not serve these groups; ChannelsDB has a separate /channels/alphafill/ route the tool never calls",
    ),
    (
        "dbaasp_tools",
        "DBAASP_get_peptide",
        "antibiofilmActivities",
        0,
        "0 items across 58 peptides",
    ),
    (
        "dbaasp_tools",
        "DBAASP_get_peptide",
        "pdbs",
        2,
        "2 items across 58 peptides",
    ),
    (
        "encode_tools",
        "ENCODE_get_experiment",
        "related_files",
        1,
        "the ENCODE index reports exactly 1 record in the archive carrying this field, and that record yields 1 item",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->added_countries_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->amino_acids_prev_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->amino_acids_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->checkers",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->data_quality_bugs_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->environment_impact_level_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->ingredients_that_may_be_from_palm_oil_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->main_countries_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->minerals_prev_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->minerals_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->nucleotides_prev_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->nucleotides_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->other_nutritional_substances_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->removed_countries_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->unknown_nutrients_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->vitamins_prev_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
    (
        "openfoodfacts_tools",
        "OpenFoodFacts_get_product",
        "product->vitamins_tags",
        0,
        "OpenFoodFacts reported 8,071 products carrying minerals_tags while its API was reachable, so this is about the inputs; the API returned 503 for the rest of the re-measurement and no product carrying these tags could be fetched through the tool",
    ),
]


@pytest.mark.parametrize(
    "stem,tool,path,fields,required,count",
    DECLARED_OBJECT_ITEMS,
    ids=[f"{t}:{p.split('->')[-1]}" for _, t, p, _, _, _ in DECLARED_OBJECT_ITEMS],
)
def test_an_object_array_declares_the_fields_its_items_were_seen_to_have(
    stem, tool, path, fields, required, count
):
    """Field list and required list both come from the `count` items observed,
    with always-null fields left out rather than declared null."""
    node = _node(_tool(stem, tool)["return_schema"], path)
    assert node is not None, path
    items = node.get("items")
    assert items is not None, f"{path} still declares no items"
    assert items["type"] == "object"
    assert sorted(items.get("properties") or {}) == fields
    assert sorted(items.get("required") or []) == sorted(required), (
        f"required is the fields present in all {count} observed items"
    )


@pytest.mark.parametrize(
    "stem,tool,path,itemtype,count",
    DECLARED_SCALAR_ITEMS,
    ids=[f"{t}:{p.split('->')[-1]}" for _, t, p, _, _ in DECLARED_SCALAR_ITEMS],
)
def test_a_scalar_array_declares_the_type_its_items_were_seen_to_have(
    stem, tool, path, itemtype, count
):
    node = _node(_tool(stem, tool)["return_schema"], path)
    assert node is not None, path
    items = node.get("items")
    assert items is not None, f"{path} still declares no items"
    assert items["type"] == itemtype, f"measured over {count} items"


@pytest.mark.parametrize(
    "stem,tool,path,count,why",
    LEFT_ALONE,
    ids=[f"{t}:{p.split('->')[-1]}" for _, t, p, _, _ in LEFT_ALONE],
)
def test_an_array_nothing_was_observed_in_stays_undeclared(
    stem, tool, path, count, why
):
    """Declaring an item shape nobody has seen would read as fixed and fail the
    first time the array is not empty. The reason each of these was left alone
    is the parameter, so a later pass can see what to re-measure rather than
    guess."""
    node = _node(_tool(stem, tool)["return_schema"], path)
    assert node is not None, path
    assert "items" not in node, (
        f"{path} was left alone because: {why} (observed {count} items)"
    )
