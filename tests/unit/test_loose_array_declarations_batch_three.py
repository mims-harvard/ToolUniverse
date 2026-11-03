"""Batch three: the arrays that only became visible once the others were closed.

Declaring an object array's items names its fields, and a field that is itself
an array arrives undeclared. That is why the count does not fall by the number
fixed: 159 declarations last round closed 159 arrays and exposed 47 new ones.
This measures those 47 across 11 tools and 199 live results.

The samples are large where it matters, which is the whole point of the
exercise -- the fault being fixed is a declaration generated from one response:

    ChannelsDB  Channels->*->*->Profile                     5,059 items
    MAGICapp    *->picos->*->outcomes->*->...               2,955 items
    NCBIVariation clinical_significance->*->variant_identifiers  780 items
    NCBIVariation clinical_significance->*->citations            575 items

43 are declared and 17 are left alone, with the sample size and the reason in
the parameter rather than in a comment, so a later pass re-measures instead of
guessing. 11 of the 17 were empty on every input: that makes their element type
unknown, not unconstrained, and batch two's experience -- 16 arrays called
"empty on every input" by the first pass carried hundreds of items on the
second -- is the reason the reason is recorded.

Each of the 43 was proved to bite rather than assumed to: a value violating the
declared type was placed in a payload where that array is populated, and the
schema at HEAD accepted all 43 while this one accepts none.
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


DECLARED_OBJECT_ITEMS = [
    (
        "crossref_tools",
        "Crossref_get_work",
        "author->*->affiliation",
        ["name"],
        ["name"],
        79,
    ),
    (
        "crossref_tools",
        "Crossref_get_work",
        "author->*->role",
        ["role", "vocabulary"],
        ["role", "vocabulary"],
        351,
    ),
    (
        "crossref_tools",
        "Crossref_get_work",
        "funder->*->award-info",
        ["award-number"],
        [],
        5,
    ),
    (
        "crossref_tools",
        "Crossref_get_work",
        "funder->*->id",
        ["asserted-by", "id", "id-type"],
        [],
        16,
    ),
    (
        "biotools_registry_tools",
        "BioTools_get_tool",
        "function->*->input",
        ["data", "format"],
        ["data", "format"],
        26,
    ),
    (
        "biotools_registry_tools",
        "BioTools_get_tool",
        "function->*->operation",
        ["term", "uri"],
        ["term", "uri"],
        39,
    ),
    (
        "biotools_registry_tools",
        "BioTools_get_tool",
        "function->*->output",
        ["data", "format"],
        ["data", "format"],
        20,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->CSATunnels_Caver->*->Profile",
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        113,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->CSATunnels_MOLE->*->Profile",
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        2742,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->CofactorTunnels_MOLE->*->Profile",
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        5059,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->ProcognateTunnels_Caver->*->Profile",
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        51,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->ProcognateTunnels_MOLE->*->Profile",
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        1132,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->ReviewedChannels_Caver->*->Profile",
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        33,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->ReviewedChannels_MOLE->*->Profile",
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        326,
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->TransmembranePores_MOLE->*->Profile",
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        ["Charge", "Distance", "FreeRadius", "Radius", "T", "X", "Y", "Z"],
        441,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->picos->*->references->*->referencePicos->*->referencePicoOutcomeContinuous",
        [
            "absoluteDifference",
            "absoluteDifferenceDirection",
            "absoluteDifferenceHigh",
            "absoluteDifferenceHighDirection",
            "absoluteDifferenceLow",
            "absoluteDifferenceLowDirection",
            "absoluteDifferenceType",
            "outcome",
            "outcomeId",
            "referencePicoId",
            "revManId",
            "studyData",
        ],
        [
            "absoluteDifference",
            "absoluteDifferenceDirection",
            "absoluteDifferenceHigh",
            "absoluteDifferenceHighDirection",
            "absoluteDifferenceLow",
            "absoluteDifferenceLowDirection",
            "absoluteDifferenceType",
            "outcome",
            "outcomeId",
            "referencePicoId",
            "revManId",
            "studyData",
        ],
        2673,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->picos->*->references->*->referencePicos->*->referencePicoOutcomeDichotomous",
        [
            "absoluteDifference",
            "absoluteDifferenceDirection",
            "absoluteDifferenceHigh",
            "absoluteDifferenceHighDirection",
            "absoluteDifferenceLow",
            "absoluteDifferenceLowDirection",
            "comparatorEffect",
            "interventionEffect",
            "outcome",
            "outcomeId",
            "referencePicoId",
            "relativeEffect",
            "relativeEffectConfidenceHigh",
            "relativeEffectConfidenceLow",
            "relativeEffectType",
            "revManId",
            "studyData",
        ],
        [
            "absoluteDifference",
            "absoluteDifferenceDirection",
            "absoluteDifferenceHigh",
            "absoluteDifferenceHighDirection",
            "absoluteDifferenceLow",
            "absoluteDifferenceLowDirection",
            "comparatorEffect",
            "interventionEffect",
            "outcome",
            "outcomeId",
            "referencePicoId",
            "relativeEffect",
            "relativeEffectConfidenceHigh",
            "relativeEffectConfidenceLow",
            "relativeEffectType",
            "revManId",
            "studyData",
        ],
        2955,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->references->*->referencePicos->*->referencePicoOutcomeContinuous",
        [
            "absoluteDifference",
            "absoluteDifferenceDirection",
            "absoluteDifferenceHigh",
            "absoluteDifferenceHighDirection",
            "absoluteDifferenceLow",
            "absoluteDifferenceLowDirection",
            "absoluteDifferenceType",
            "outcome",
            "outcomeId",
            "referencePicoId",
            "revManId",
            "studyData",
        ],
        [
            "absoluteDifference",
            "absoluteDifferenceDirection",
            "absoluteDifferenceHigh",
            "absoluteDifferenceHighDirection",
            "absoluteDifferenceLow",
            "absoluteDifferenceLowDirection",
            "absoluteDifferenceType",
            "outcome",
            "outcomeId",
            "referencePicoId",
            "revManId",
            "studyData",
        ],
        2422,
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->references->*->referencePicos->*->referencePicoOutcomeDichotomous",
        [
            "absoluteDifference",
            "absoluteDifferenceDirection",
            "absoluteDifferenceHigh",
            "absoluteDifferenceHighDirection",
            "absoluteDifferenceLow",
            "absoluteDifferenceLowDirection",
            "comparatorEffect",
            "interventionEffect",
            "outcome",
            "outcomeId",
            "referencePicoId",
            "relativeEffect",
            "relativeEffectConfidenceHigh",
            "relativeEffectConfidenceLow",
            "relativeEffectType",
            "revManId",
            "studyData",
        ],
        [
            "absoluteDifference",
            "absoluteDifferenceDirection",
            "absoluteDifferenceHigh",
            "absoluteDifferenceHighDirection",
            "absoluteDifferenceLow",
            "absoluteDifferenceLowDirection",
            "comparatorEffect",
            "interventionEffect",
            "outcome",
            "outcomeId",
            "referencePicoId",
            "relativeEffect",
            "relativeEffectConfidenceHigh",
            "relativeEffectConfidenceLow",
            "relativeEffectType",
            "revManId",
            "studyData",
        ],
        1792,
    ),
    (
        "intact_tools",
        "intact_get_complex_details",
        "participants->*->linkedFeatures",
        [
            "crossReferences",
            "featureAc",
            "featureRole",
            "featureRoleDefinition",
            "featureRoleMI",
            "featureRoleUrl",
            "featureType",
            "featureTypeDefinition",
            "featureTypeMI",
            "featureTypeUrl",
            "linkedFeatures",
            "name",
            "participantId",
            "ranges",
        ],
        [
            "crossReferences",
            "featureAc",
            "featureRole",
            "featureRoleDefinition",
            "featureRoleMI",
            "featureRoleUrl",
            "featureType",
            "featureTypeDefinition",
            "featureTypeMI",
            "featureTypeUrl",
            "linkedFeatures",
            "name",
            "participantId",
            "ranges",
        ],
        118,
    ),
    (
        "intact_tools",
        "intact_get_complex_details",
        "participants->*->otherFeatures",
        [
            "crossReferences",
            "featureAc",
            "featureRole",
            "featureRoleDefinition",
            "featureRoleMI",
            "featureRoleUrl",
            "featureType",
            "featureTypeDefinition",
            "featureTypeMI",
            "featureTypeUrl",
            "linkedFeatures",
            "name",
            "participantId",
            "ranges",
        ],
        [],
        18,
    ),
    (
        "protvar_tools",
        "ProtVar_get_function",
        "gene_names->*->synonyms",
        ["value"],
        [],
        19,
    ),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "clinical_significance->*->disease_ids",
        ["accession", "organization"],
        ["accession", "organization"],
        414,
    ),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "clinical_significance->*->variant_identifiers",
        ["accession", "organization"],
        ["accession", "organization"],
        780,
    ),
]

DECLARED_SCALAR_ITEMS = [
    (
        "clinicaltrials_gov_tools",
        "ClinicalTrials_get_study",
        "arms->*->intervention_names",
        "string",
        50,
    ),
    (
        "crossref_tools",
        "Crossref_get_work",
        "funder->*->award",
        "string",
        5,
    ),
    (
        "biotools_registry_tools",
        "BioTools_get_tool",
        "credit->*->typeRole",
        "string",
        38,
    ),
    (
        "biotools_registry_tools",
        "BioTools_get_tool",
        "documentation->*->type",
        "string",
        20,
    ),
    (
        "biotools_registry_tools",
        "BioTools_get_tool",
        "link->*->type",
        "string",
        13,
    ),
    (
        "encode_tools",
        "ENCODE_get_file",
        "assay_term_name",
        "string",
        20,
    ),
    (
        "hocomoco_tools",
        "HOCOMOCO_get_motif",
        "pwm->*",
        "number",
        912,
    ),
    (
        "protvar_tools",
        "ProtVar_get_function",
        "interactions->*->aresidues",
        "integer",
        15296,
    ),
    (
        "protvar_tools",
        "ProtVar_get_function",
        "interactions->*->bresidues",
        "integer",
        16666,
    ),
    (
        "protvar_tools",
        "ProtVar_get_function",
        "pockets->*->resid",
        "integer",
        494,
    ),
    (
        "mobidb_tools",
        "MobiDB_get_protein",
        "curated_disorder->regions->*",
        "integer",
        24,
    ),
    (
        "mobidb_tools",
        "MobiDB_get_protein",
        "curated_lip->regions->*",
        "integer",
        16,
    ),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "clinical_significance->*->citations",
        "integer",
        575,
    ),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "clinical_significance->*->clinical_significances",
        "string",
        97,
    ),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "clinical_significance->*->collection_method",
        "string",
        104,
    ),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "clinical_significance->*->disease_names",
        "string",
        108,
    ),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "clinical_significance->*->gene_ids",
        "string",
        143,
    ),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "clinical_significance->*->origins",
        "string",
        107,
    ),
    (
        "ncbi_variation_tools",
        "NCBIVariation_rsid_lookup",
        "clinical_significance->*->significance",
        "string",
        97,
    ),
]

LEFT_ALONE = [
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->AlphaFillTunnels_Caver",
        0,
        "empty on every input",
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->AlphaFillTunnels_MOLE",
        0,
        "empty on every input",
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->CofactorTunnels_Caver",
        0,
        "empty on every input",
    ),
    (
        "channelsdb_tools",
        "ChannelsDB_get_channels_pdb",
        "Channels->TransmembranePores_Caver",
        0,
        "empty on every input",
    ),
    (
        "encode_tools",
        "ENCODE_get_file",
        "biosample_ontology",
        1,
        "only 1 observed, too few to claim the element type",
    ),
    (
        "encode_tools",
        "ENCODE_get_file",
        "target",
        0,
        "empty on every input",
    ),
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
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->picos->*->references->*->referencePicos->*->referencePicoOutcomeNarrative",
        0,
        "empty on every input",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->references->*->referencePicos->*->referencePicoOutcomeNarrative",
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
]


def test_the_measurement_is_the_size_it_says_it_is():
    """So a truncated list cannot make the rest of this file pass by covering
    less than it claims."""
    assert len(DECLARED_OBJECT_ITEMS) + len(DECLARED_SCALAR_ITEMS) == 43
    assert len(LEFT_ALONE) == 17


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
    assert sorted(items.get("required") or []) == required, (
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
def test_an_array_too_little_was_observed_in_stays_undeclared(
    stem, tool, path, count, why
):
    node = _node(_tool(stem, tool)["return_schema"], path)
    assert node is not None, path
    items = node.get("items")
    assert items is None or items == {"type": "object"}, (
        f"{path} was left alone because: {why} (observed {count} items)"
    )


def test_no_declaration_describes_its_own_measurement():
    """The applier used to put the measurement in the field's description, which
    is the slot that documents the field and which reaches the model as part of
    return_schema. 136 of those notes were removed and none may come back."""
    offenders = []
    for path in sorted(DATA.glob("*.json")):
        try:
            entries = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(entries, list):
            continue

        def walk(node, where):
            if isinstance(node, dict):
                text = node.get("description")
                if (
                    isinstance(text, str)
                    and "the declaration was an array with no items" in text
                ):
                    offenders.append((path.name, where))
                for key, value in node.items():
                    walk(value, where)
            elif isinstance(node, list):
                for value in node:
                    walk(value, where)

        for entry in entries:
            if isinstance(entry, dict) and "return_schema" in entry:
                walk(entry["return_schema"], entry.get("name"))
    assert not offenders, "%d descriptions describe the measurement: %s" % (
        len(offenders),
        offenders[:5],
    )
