"""Batch two of the loose array declarations, and what the second pass changed.

The first batch measured ten tools over 134 calls. This is fourteen more over
286, and the interesting result is not the 87 declarations but what happened
when the same arrays were measured twice with different inputs.

Sixteen arrays that the first pass recorded as empty on every input were not
empty at all:

    MAGICapp *->files                        0 -> 526 items
    MAGICapp *->picos->*->references->*->referencePicos
                                             0 -> 491 items
    MAGICapp *->references->*->attachedFiles 0 -> 469 items
    MAGICapp *->images                       0 -> 21 items
    HOCOMOCO pwm                             0 -> 228 items
    DataCite attributes->sizes               1 -> 17 items
    DataCite attributes->formats             0 -> 6 items
    DataCite creators->*->nameIdentifiers    0 -> 15 items
    intact ligands                           0 -> 12 items
    BVBRC pmid                               2 -> 13 items
    NeuroMorpho *->sharedReconstructions     4 -> 11 items

MAGICapp is the clearest: nine of its arrays were empty across the first
fourteen guidelines and carry hundreds of items across the next twenty-six. On
the first pass's evidence they would have been written down as fields the
upstream does not populate. They are fields those fourteen guidelines did not
happen to use.

Two of the sixteen were not upstream's doing at all. HOCOMOCO's `pwm` is
returned only when `include_pwm` is set, which the tool's own second
test_example does and the first pass's inputs did not; and the DataCite DOIs
in the first pass were ones made up for the test, which 404. Both were bad
inputs on this side, which is the same mistake in a different coat: a field
looks absent, and the first explanation reached for is that upstream does not
send it.

So the measurements from the two passes are merged rather than one replacing
the other -- counts add, per-field presence adds, observed types union. Keeping
it additive is what makes `present == count` still mean "present in every item
observed", which the `required` rule rests on.

Eleven arrays are still left alone, each with its sample in the parameter.

Four faults turned up in the 286-call validation, none of them from this work
-- reverting the batch and running the same 286 cases gives the identical 277
pass and 9 fail. Three were one defect wearing three hats: BV-BRC, DataCite and
(in the previous commit) ChannelsDB all pair an open success branch with an
error branch under `oneOf`, which needs exactly one match, so a correct
{status, error} result satisfies both and fails. The same scan over every
return_schema finds 583 tools in that state, confirmed on four untouched tools
with real error results. Fixing all of them is not in this commit; the two in
front of it are, by requiring the identity keys measured present in every
successful payload.
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
        "datacite_tools",
        "DataCite_get_dataset",
        "attributes->creators->*->nameIdentifiers",
        ["nameIdentifier", "nameIdentifierScheme", "schemeUri"],
        [],
        15,
    ),
    (
        "datacite_tools",
        "DataCite_get_dataset",
        "attributes->dates",
        ["date", "dateType"],
        ["date", "dateType"],
        53,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->files",
        [
            "avStatus",
            "displayName",
            "fileExtension",
            "fileId",
            "fileLocation",
            "fileName",
            "fullPath",
            "referenceFileId",
            "referenceId",
            "uuid",
        ],
        [
            "avStatus",
            "displayName",
            "fileExtension",
            "fileId",
            "fileLocation",
            "fileName",
            "fullPath",
            "uuid",
        ],
        526,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->images",
        ["caption", "fileName", "imageId", "location", "sortOrder", "srcSet", "uuid"],
        ["caption", "fileName", "imageId", "location", "sortOrder", "srcSet", "uuid"],
        21,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->picos->*->picoCodes",
        ["code", "codeId", "name", "ontology", "picoId", "sectionId", "type"],
        [],
        12,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->picos->*->references->*->attachedFiles",
        [
            "avStatus",
            "displayName",
            "fileExtension",
            "fileId",
            "fileLocation",
            "fileName",
            "fullPath",
            "referenceFileId",
            "referenceId",
            "uuid",
        ],
        [
            "avStatus",
            "displayName",
            "fileExtension",
            "fileId",
            "fileLocation",
            "fileName",
            "fullPath",
            "referenceFileId",
            "referenceId",
            "uuid",
        ],
        468,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->picos->*->references->*->files",
        [
            "avStatus",
            "displayName",
            "fileExtension",
            "fileId",
            "fileLocation",
            "fileName",
            "fullPath",
            "referenceFileId",
            "referenceId",
            "uuid",
        ],
        [
            "avStatus",
            "displayName",
            "fileExtension",
            "fileId",
            "fileLocation",
            "fileName",
            "fullPath",
            "referenceFileId",
            "referenceId",
            "uuid",
        ],
        468,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->picos->*->references->*->referencePicos",
        [
            "comparator",
            "intervention",
            "picoId",
            "population",
            "referenceId",
            "referencePicoOutcomeContinuous",
            "referencePicoOutcomeDichotomous",
            "referencePicoOutcomeNarrative",
            "revManId",
            "setting",
        ],
        [
            "comparator",
            "intervention",
            "picoId",
            "population",
            "referenceId",
            "referencePicoOutcomeContinuous",
            "referencePicoOutcomeDichotomous",
            "referencePicoOutcomeNarrative",
            "revManId",
            "setting",
        ],
        491,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->references->*->attachedFiles",
        [
            "avStatus",
            "displayName",
            "fileExtension",
            "fileId",
            "fileLocation",
            "fileName",
            "fullPath",
            "referenceFileId",
            "referenceId",
            "uuid",
        ],
        [
            "avStatus",
            "displayName",
            "fileExtension",
            "fileId",
            "fileLocation",
            "fileName",
            "fullPath",
            "referenceFileId",
            "referenceId",
            "uuid",
        ],
        469,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->references->*->files",
        [
            "avStatus",
            "displayName",
            "fileExtension",
            "fileId",
            "fileLocation",
            "fileName",
            "fullPath",
            "referenceFileId",
            "referenceId",
            "uuid",
        ],
        [
            "avStatus",
            "displayName",
            "fileExtension",
            "fileId",
            "fileLocation",
            "fileName",
            "fullPath",
            "referenceFileId",
            "referenceId",
            "uuid",
        ],
        469,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->references->*->referencePicos",
        [
            "comparator",
            "intervention",
            "picoId",
            "population",
            "referenceId",
            "referencePicoOutcomeContinuous",
            "referencePicoOutcomeDichotomous",
            "referencePicoOutcomeNarrative",
            "revManId",
            "setting",
        ],
        [
            "comparator",
            "intervention",
            "picoId",
            "population",
            "referenceId",
            "referencePicoOutcomeContinuous",
            "referencePicoOutcomeDichotomous",
            "referencePicoOutcomeNarrative",
            "revManId",
            "setting",
        ],
        441,
    ),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "clinical_significance",
        [
            "accession",
            "accession_version",
            "allele_annotation_index",
            "allele_id",
            "citations",
            "clinical_significances",
            "collection_method",
            "create_date",
            "disease_ids",
            "disease_names",
            "gene_ids",
            "last_evaluated_date",
            "measure_set_id",
            "origins",
            "refsnp_id",
            "review_status",
            "significance",
            "update_date",
            "variant_identifiers",
        ],
        [
            "accession",
            "accession_version",
            "allele_annotation_index",
            "allele_id",
            "citations",
            "clinical_significances",
            "collection_method",
            "create_date",
            "disease_ids",
            "disease_names",
            "gene_ids",
            "measure_set_id",
            "origins",
            "refsnp_id",
            "review_status",
            "significance",
            "update_date",
            "variant_identifiers",
        ],
        91,
    ),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "genes",
        ["gene", "gene_id", "name"],
        [],
        8,
    ),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "grch38_placements",
        [
            "coordinate_system",
            "deleted_sequence",
            "inserted_sequence",
            "position",
            "seq_id",
            "spdi_position",
        ],
        [
            "coordinate_system",
            "deleted_sequence",
            "inserted_sequence",
            "position",
            "seq_id",
            "spdi_position",
        ],
        27,
    ),
    (
        "neuromorpho_tools",
        "NeuroMorpho_search_literature",
        "*->sharedReconstructions",
        ["nReconstructions", "sharedArticleId"],
        [],
        11,
    ),
    ("omicsdi_tools", "OmicsDI_get_dataset", "organisms", ["acc", "name"], [], 5),
    (
        "omicsdi_tools",
        "OmicsDI_get_dataset",
        "protocols",
        ["description", "name"],
        [],
        6,
    ),
    (
        "pride_tools",
        "PRIDE_get_project",
        "instruments",
        ["@type", "accession", "cvLabel", "name", "value"],
        ["@type", "accession", "cvLabel", "name"],
        32,
    ),
    (
        "pride_tools",
        "PRIDE_get_project",
        "labPIs",
        [
            "affiliation",
            "country",
            "email",
            "firstName",
            "id",
            "identifier",
            "lastName",
            "name",
            "orcid",
            "title",
        ],
        [
            "affiliation",
            "country",
            "email",
            "firstName",
            "id",
            "identifier",
            "lastName",
            "name",
            "orcid",
            "title",
        ],
        30,
    ),
    (
        "pride_tools",
        "PRIDE_get_project",
        "organismParts",
        ["@type", "accession", "cvLabel", "name", "value"],
        ["@type", "accession", "cvLabel", "name"],
        63,
    ),
    (
        "pride_tools",
        "PRIDE_get_project",
        "organisms",
        ["@type", "accession", "cvLabel", "name", "value"],
        ["@type", "accession", "cvLabel", "name"],
        34,
    ),
    (
        "pride_tools",
        "PRIDE_get_project",
        "submitters",
        [
            "affiliation",
            "country",
            "email",
            "firstName",
            "id",
            "identifier",
            "lastName",
            "name",
            "orcid",
            "title",
        ],
        [
            "affiliation",
            "country",
            "email",
            "firstName",
            "id",
            "identifier",
            "lastName",
            "name",
            "orcid",
            "title",
        ],
        30,
    ),
    (
        "protvar_tools",
        "ProtVar_get_function",
        "database_references",
        ["id", "properties", "type"],
        ["id", "properties", "type"],
        268,
    ),
    (
        "protvar_tools",
        "ProtVar_get_function",
        "gene_names",
        ["name", "synonyms"],
        ["name"],
        23,
    ),
    (
        "protvar_tools",
        "ProtVar_get_function",
        "interactions",
        ["a", "aresidues", "b", "bresidues", "pdbModel", "pdockq"],
        ["a", "aresidues", "b", "bresidues", "pdbModel", "pdockq"],
        425,
    ),
    (
        "protvar_tools",
        "ProtVar_get_function",
        "pockets",
        [
            "buriedness",
            "energyPerVol",
            "meanPlddt",
            "pocketId",
            "radGyration",
            "resid",
            "score",
            "structId",
        ],
        [
            "buriedness",
            "energyPerVol",
            "meanPlddt",
            "pocketId",
            "radGyration",
            "resid",
            "score",
            "structId",
        ],
        28,
    ),
    (
        "intact_tools",
        "intact_get_complex_details",
        "crossReferences",
        [
            "database",
            "dbMI",
            "dbdefinition",
            "description",
            "identifier",
            "qualifier",
            "qualifierDefinition",
            "qualifierMI",
            "qualifierUrl",
            "searchURL",
        ],
        [
            "database",
            "dbMI",
            "dbdefinition",
            "description",
            "identifier",
            "qualifier",
            "qualifierDefinition",
            "qualifierMI",
            "qualifierUrl",
            "searchURL",
        ],
        658,
    ),
    (
        "intact_tools",
        "intact_get_complex_details",
        "participants",
        [
            "bioRole",
            "bioRoleDefinition",
            "bioRoleMI",
            "description",
            "identifier",
            "identifierLink",
            "interactorAC",
            "interactorType",
            "interactorTypeDefinition",
            "interactorTypeMI",
            "linkedFeatures",
            "name",
            "otherFeatures",
            "stochiometry",
        ],
        [
            "bioRole",
            "bioRoleDefinition",
            "bioRoleMI",
            "description",
            "identifier",
            "identifierLink",
            "interactorAC",
            "interactorType",
            "interactorTypeDefinition",
            "interactorTypeMI",
            "linkedFeatures",
            "name",
            "otherFeatures",
            "stochiometry",
        ],
        289,
    ),
]

DECLARED_SCALAR_ITEMS = [
    ("bvbrc_tools", "BVBRC_get_protein_structure", "gene", "string", 23),
    ("bvbrc_tools", "BVBRC_get_protein_structure", "method", "string", 17),
    ("bvbrc_tools", "BVBRC_get_protein_structure", "organism_name", "string", 25),
    ("bvbrc_tools", "BVBRC_get_protein_structure", "pmid", "string", 13),
    ("bvbrc_tools", "BVBRC_get_protein_structure", "product", "string", 23),
    ("bvbrc_tools", "BVBRC_get_protein_structure", "taxon_id", "integer", 25),
    ("bvbrc_tools", "BVBRC_get_protein_structure", "uniprotkb_accession", "string", 28),
    (
        "datacite_tools",
        "DataCite_get_dataset",
        "attributes->creators->*->affiliation",
        "string",
        21,
    ),
    ("datacite_tools", "DataCite_get_dataset", "attributes->formats", "string", 6),
    ("datacite_tools", "DataCite_get_dataset", "attributes->sizes", "string", 17),
    ("hocomoco_tools", "HOCOMOCO_get_motif", "entrezgene_ids_human", "string", 28),
    ("hocomoco_tools", "HOCOMOCO_get_motif", "entrezgene_ids_mouse", "string", 26),
    ("hocomoco_tools", "HOCOMOCO_get_motif", "gene_synonyms_human", "string", 44),
    ("hocomoco_tools", "HOCOMOCO_get_motif", "gene_synonyms_mouse", "string", 58),
    ("hocomoco_tools", "HOCOMOCO_get_motif", "hgnc_ids", "string", 28),
    ("hocomoco_tools", "HOCOMOCO_get_motif", "previous_names", "string", 28),
    ("hocomoco_tools", "HOCOMOCO_get_motif", "pwm", "array", 228),
    (
        "immport_tools",
        "ImmPort_search_studies",
        "*->assay_method_counts",
        "string",
        121,
    ),
    ("immport_tools", "ImmPort_search_studies", "*->assay_methods", "string", 121),
    ("immport_tools", "ImmPort_search_studies", "*->biosample_types", "string", 127),
    (
        "immport_tools",
        "ImmPort_search_studies",
        "*->condition_or_disease",
        "string",
        84,
    ),
    ("immport_tools", "ImmPort_search_studies", "*->program_name", "string", 83),
    ("immport_tools", "ImmPort_search_studies", "*->pubmed_ids", "string", 87),
    ("immport_tools", "ImmPort_search_studies", "*->research_focus", "string", 74),
    ("immport_tools", "ImmPort_search_studies", "*->species", "string", 66),
    ("immport_tools", "ImmPort_search_studies", "*->study_pi", "string", 266),
    ("mobidb_tools", "MobiDB_get_protein", "curated_disorder->regions", "array", 12),
    ("mobidb_tools", "MobiDB_get_protein", "curated_lip->regions", "array", 8),
    (
        "mobidb_tools",
        "MobiDB_get_protein",
        "prediction_disorder->regions->*",
        "integer",
        32,
    ),
    (
        "mobidb_tools",
        "MobiDB_get_protein",
        "ptm_summary->entries->*->position",
        "integer",
        140,
    ),
    ("mobidb_tools", "MobiDB_get_protein", "ptm_summary->positions->*", "integer", 140),
    ("ncbi_variation_tools", "NCBIVariation_rsid_lookup", "citations", "integer", 3171),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "mane_select_ids",
        "string",
        8,
    ),
    ("neuromorpho_tools", "NeuroMorpho_get_literature", "authors", "string", 246),
    ("neuromorpho_tools", "NeuroMorpho_get_literature", "brainRegion", "string", 36),
    ("neuromorpho_tools", "NeuroMorpho_get_literature", "cellType", "string", 36),
    ("neuromorpho_tools", "NeuroMorpho_get_literature", "dataUsage", "string", 36),
    ("neuromorpho_tools", "NeuroMorpho_get_literature", "species", "string", 36),
    ("neuromorpho_tools", "NeuroMorpho_get_literature", "tracingSystem", "string", 36),
    (
        "neuromorpho_tools",
        "NeuroMorpho_search_literature",
        "*->authors",
        "string",
        1572,
    ),
    (
        "neuromorpho_tools",
        "NeuroMorpho_search_literature",
        "*->brainRegion",
        "string",
        212,
    ),
    (
        "neuromorpho_tools",
        "NeuroMorpho_search_literature",
        "*->cellType",
        "string",
        212,
    ),
    (
        "neuromorpho_tools",
        "NeuroMorpho_search_literature",
        "*->dataUsage",
        "string",
        214,
    ),
    ("neuromorpho_tools", "NeuroMorpho_search_literature", "*->species", "string", 212),
    (
        "neuromorpho_tools",
        "NeuroMorpho_search_literature",
        "*->tracingSystem",
        "string",
        212,
    ),
    ("omicsdi_tools", "OmicsDI_get_dataset", "diseases", "string", 9),
    ("omicsdi_tools", "OmicsDI_get_dataset", "instruments", "string", 3),
    ("omicsdi_tools", "OmicsDI_get_dataset", "keywords", "string", 28),
    ("omicsdi_tools", "OmicsDI_get_dataset", "omics_type", "string", 8),
    ("omicsdi_tools", "OmicsDI_get_dataset", "publicationIds", "string", 5),
    ("omicsdi_tools", "OmicsDI_get_dataset", "tissues", "string", 11),
    ("pride_tools", "PRIDE_get_project", "keywords", "string", 110),
    ("pride_tools", "PRIDE_search_proteomics", "*->diseases", "string", 2769),
    ("pride_tools", "PRIDE_search_proteomics", "*->instruments", "string", 452),
    ("pride_tools", "PRIDE_search_proteomics", "*->keywords", "string", 1372),
    ("pride_tools", "PRIDE_search_proteomics", "*->organisms", "string", 386),
    ("pride_tools", "PRIDE_search_proteomics", "*->projectTags", "string", 18),
    ("pride_tools", "PRIDE_search_proteomics", "*->submitters", "string", 300),
    ("intact_tools", "intact_get_complex_details", "ligands", "string", 12),
]

LEFT_ALONE = [
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->emrCodes",
        0,
        "empty on every input",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->interventions->codes",
        4,
        "only 4 observed, too few to type an object",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->picos->*->outcomes->nonPoolableOutcomes->*->extraReferences->*->attachedFiles",
        2,
        "only 2 observed, too few to type an object",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->picos->*->outcomes->practicalIssues",
        0,
        "empty on every input",
    ),
    (
        "neuromorpho_tools",
        "NeuroMorpho_get_literature",
        "sharedReconstructions",
        2,
        "only 2 observed, too few to type an object",
    ),
    (
        "pride_tools",
        "PRIDE_search_proteomics",
        "*->organismParts",
        0,
        "empty on every input",
    ),
    (
        "protvar_tools",
        "ProtVar_get_function",
        "foldx_predictions",
        0,
        "empty on every input",
    ),
    (
        "protvar_tools",
        "ProtVar_get_function",
        "m3d_predictions",
        0,
        "empty on every input",
    ),
    (
        "intact_tools",
        "intact_get_complex_details",
        "agonists",
        0,
        "empty on every input",
    ),
    (
        "intact_tools",
        "intact_get_complex_details",
        "antagonists",
        0,
        "empty on every input",
    ),
    (
        "intact_tools",
        "intact_get_complex_details",
        "comments",
        1,
        "only 1 observed, too few to claim the element type",
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
    """The reason is the parameter so a later pass can re-measure rather than
    guess -- and after what the second pass found, "empty on every input" is
    worth re-measuring rather than trusting."""
    node = _node(_tool(stem, tool)["return_schema"], path)
    assert node is not None, path
    items = node.get("items")
    assert items is None or items == {"type": "object"}, (
        f"{path} was left alone because: {why} (observed {count} items)"
    )


BRANCH_SEPARATED = [
    ("bvbrc_tools", "BVBRC_get_protein_structure", ["feature_id", "pdb_id"], 13),
    ("datacite_tools", "DataCite_get_dataset", ["attributes", "id", "type"], 12),
]


@pytest.mark.parametrize(
    "stem,tool,required,payloads",
    BRANCH_SEPARATED,
    ids=[t for _, t, _, _ in BRANCH_SEPARATED],
)
def test_the_success_branch_stops_matching_the_error_envelope(
    stem, tool, required, payloads
):
    """oneOf needs exactly one branch to match. With nothing required on the
    success branch, a correct {status, error} result satisfied both branches
    and failed validation -- only ever when the upstream call failed, which is
    why it went unnoticed. 583 tools are in that state; these two are fixed."""
    from jsonschema import Draft7Validator

    schema = _tool(stem, tool)["return_schema"]
    branches = schema["oneOf"]
    success = next(b for b in branches if "error" not in (b.get("properties") or {}))
    assert sorted(success["required"]) == sorted(required), (
        f"present in all {payloads} successful payloads measured"
    )
    envelope = {"status": "error", "error": "upstream said no"}
    matching = [
        i
        for i, b in enumerate(branches)
        if not list(Draft7Validator(b).iter_errors(envelope))
    ]
    assert len(matching) == 1, f"branches {matching} all accept the error envelope"
    assert not list(Draft7Validator(schema).iter_errors(envelope))


MEASURED_NULLABLE = [
    (
        "omicsdi_tools",
        "OmicsDI_get_dataset",
        "instruments",
        {"array", "null"},
        "a list for 6 of 8 datasets measured, null for 2",
    ),
    (
        "intact_tools",
        "intact_get_complex_details",
        "institutionURL",
        {"string", "null"},
        "null for CPX-200, 1 of the 56 complexes measured",
    ),
]


@pytest.mark.parametrize(
    "stem,tool,path,types,evidence",
    MEASURED_NULLABLE,
    ids=[p for _, _, p, _, _ in MEASURED_NULLABLE],
)
def test_a_field_that_returns_null_says_so(stem, tool, path, types, evidence):
    node = _node(_tool(stem, tool)["return_schema"], path)
    assert node is not None, path
    t = node.get("type")
    assert (set(t) if isinstance(t, list) else {t}) == types, evidence
