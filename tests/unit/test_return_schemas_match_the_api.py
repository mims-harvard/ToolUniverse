"""A field declared `type: "null"` claims the API never sends a value there.

That is almost never an API contract. It is what a schema generated from one
response records when the field happened to be empty, and it is a trap that
springs the first time the field carries data: the tool is fine, the sweep says
SCHEMA ERROR. Nine of rcsb_pdb's results were that, on 2026-11-01:

    get_host_organism_by_pdb_id        'Escherichia coli' is not of type 'null'
    get_emdb_ids_by_pdb_id             ['EMD-2984'] is not of type 'null'
    get_core_refinement_statistics     27.66 is not of type 'null'
    ...

The corrections here were measured, not guessed: each tool's own test_examples
were run and the declaration widened to the type observed. A field that came
back null in every example was left alone, because nothing measured says what
it holds -- 166 field-level `type: "null"` declarations remain across the tree
and each is the same latent failure.

The same pass fixed the opposite error, a field declared non-null that the API
leaves empty (odphp Query->Keyword, Open Food Facts' Nutri-Score nutrients,
Carbon-A's md5, EBI Search's facet option values), and three fields typed from
the wrong sample: KLIFS resolution/quality_score are numbers, not strings, and
HPA's gene_synonym is an array of strings, as its four sibling tools already
said.

One of the ten was not a schema fault at all. NPAtlas declares origin_organism
"string or null" and the sweep reported the taxon object there; widening the
schema would have pinned two silent faults instead of fixing them. The search
endpoint sends `original_organism` and no `origin_organism`, so every
NPAtlas_search_compounds hit reported null, and the detail endpoint's
`origin_organism.taxon` is now an object where it was a string, so the
projection passed that object through. Fixed in the projection; the schema is
untouched.

One widening was reverted by measurement rather than kept: MyGene's
hits[].ensembl `{"type": "null"}` is a branch of a oneOf, not a field claim, and
widening it to ["object", "null"] made an object match both branches, so oneOf
rejected it. The schema was already right. 10 such null branches exist and none
of them is touched.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "tooluniverse" / "data"


def _tool(file_name, tool_name):
    tools = json.loads((DATA / file_name).read_text("utf-8"))
    return next(t for t in tools if t["name"] == tool_name)


def _at(node, *path):
    for part in path:
        if isinstance(part, int):
            node = node[part]
            continue
        # Step through a oneOf/anyOf to the branch that declares this field.
        for keyword in ("oneOf", "anyOf", "allOf"):
            if keyword in node:
                for branch in node[keyword]:
                    if part in branch or part in (branch.get("properties") or {}):
                        node = branch
                        break
        if part in node:
            node = node[part]
        else:
            node = node["properties"][part]
    return node


def _types(node):
    declared = node.get("type")
    return {declared} if isinstance(declared, str) else set(declared or ())


RCSB_FIELDS = [
    # (tool, path from the entry object, the type the API was observed to send)
    ("get_host_organism_by_pdb_id",
     ("polymer_entities", "items", "entity_src_gen", "items",
      "pdbx_host_org_scientific_name"), "string"),
    ("get_crystal_growth_conditions_by_pdb_id", ("exptl_crystal_grow",), "array"),
    ("get_crystallization_ph_by_pdb_id", ("exptl_crystal_grow",), "array"),
    ("get_emdb_ids_by_pdb_id",
     ("rcsb_entry_container_identifiers", "emdb_ids"), "array"),
    ("get_binding_affinity_by_pdb_id", ("rcsb_binding_affinity",), "array"),
    ("get_core_refinement_statistics",
     ("refine", "items", "ls_R_factor_R_work"), "number"),
    ("get_core_refinement_statistics",
     ("refine", "items", "ls_R_factor_R_free"), "number"),
    ("get_core_refinement_statistics",
     ("refine", "items", "pdbx_overall_phase_error"), "number"),
    ("get_target_cofactor_info",
     ("polymer_entities", "items", "rcsb_target_cofactors"), "array"),
    ("get_chem_comp_audit_info", ("nonpolymer_entities",), "array"),
    ("get_chem_comp_charge_and_ambiguity", ("nonpolymer_entities",), "array"),
]


@pytest.mark.parametrize(("tool_name", "path", "observed"), RCSB_FIELDS)
def test_rcsb_fields_declare_what_the_api_sends(tool_name, path, observed):
    tool = _tool("rcsb_pdb_tools.json", tool_name)
    entry = _at(tool["return_schema"], "data", "entries", "items")
    node = _at(entry, *path)

    assert observed in _types(node), f"{tool_name} {path}: {node.get('type')}"
    # Still nullable: these fields are genuinely absent for some entries.
    assert "null" in _types(node)


def test_gtex_subset_group_is_a_string():
    tool = _tool("gtex_v2_tools.json", "GTEx_get_gene_expression")
    node = _at(tool["return_schema"], "oneOf", 0, "items", "subsetGroup")

    assert _types(node) == {"string", "null"}


def test_klifs_resolution_and_quality_score_are_numbers():
    """Declared "string" while KLIFS sends 1.9 and 8 (and 7.6)."""
    for tool_name in ("KLIFS_get_structures", "KLIFS_get_structures_by_pdb"):
        items = _at(
            _tool("klifs_tools.json", tool_name)["return_schema"], "oneOf", 0, "items"
        )
        for field in ("resolution", "quality_score"):
            types = _types(_at(items, field))
            assert "number" in types, f"{tool_name}.{field}: {types}"
            assert "string" not in types, f"{tool_name}.{field}: {types}"


def test_hpa_gene_synonym_matches_its_sibling_tools():
    """Four HPA tools declare an array of strings; the fifth said "string"."""
    contextual = _tool(
        "hpa_tools.json", "HPA_get_contextual_biological_process_analysis"
    )
    node = _at(contextual["return_schema"], "data", "gene_synonym")

    assert node == {"type": "array", "items": {"type": "string"}}


def test_npatlas_reads_the_organism_from_both_record_shapes():
    """NPAtlas' schema was right and its projection had stopped matching it.

    `origin_organism` is declared "string or null" and the sweep reported the
    taxon object there. Widening the schema to accept the object would have
    pinned two silent faults:

    * ``/compounds/basicSearch`` sends ``original_organism`` and no
      ``origin_organism``, so every NPAtlas_search_compounds hit reported
      ``origin_organism: null``.
    * ``/compound/{npaid}``'s ``origin_organism.taxon`` is now an object where
      it used to be a string, so the projection handed that object through
      instead of falling back to the binomial.

    Fixed in the projection, which is where the fault was, so the schema is
    unchanged.
    """
    from tooluniverse.npatlas_tool import _organism_name

    # The search endpoint's shape.
    assert (
        _organism_name({"original_organism": "Penicillium sp. SF-5292"})
        == "Penicillium sp. SF-5292"
    )
    # The detail endpoint's shape today: taxon is an object, and the binomial
    # is more specific than the genus-level taxon name it resolved to.
    assert (
        _organism_name(
            {
                "origin_organism": {
                    "genus": "Curvularia",
                    "species": "geniculata",
                    "taxon": {"name": "Curvularia", "rank": "genus"},
                }
            }
        )
        == "Curvularia geniculata"
    )
    # The shape it used to send, which the old code handled and must keep.
    assert (
        _organism_name({"origin_organism": {"taxon": "Curvularia sp."}})
        == "Curvularia sp."
    )
    # Taxon object with no binomial beside it: fall back to its name.
    assert (
        _organism_name({"origin_organism": {"taxon": {"name": "Streptomyces"}}})
        == "Streptomyces"
    )
    # Nothing to report is still None, not "" and not a crash.
    assert _organism_name({}) is None
    assert _organism_name({"origin_organism": None}) is None
    assert _organism_name({"origin_organism": {"genus": "", "species": ""}}) is None


def test_npatlas_schema_still_says_string():
    """The guard against re-widening a schema whose tool was the problem."""
    tool = _tool("npatlas_tools.json", "NPAtlas_get_compound")
    node = _at(tool["return_schema"], "origin_organism")

    assert _types(node) == {"string", "null"}


@pytest.mark.parametrize(
    ("file_name", "tool_name", "path"),
    [
        ("odphp_tools.json", "odphp_topicsearch", ("Query", "Keyword")),
        (
            "carbon_a_benchmark_tools.json",
            "Carbon_A_get_benchmark_genome",
            ("data", "files", "items", "md5"),
        ),
    ],
)
def test_fields_the_api_leaves_empty_are_nullable(file_name, tool_name, path):
    node = _at(_tool(file_name, tool_name)["return_schema"], *path)

    assert "null" in _types(node), f"{tool_name} {path}: {node.get('type')}"


def test_mygene_ensembl_keeps_its_oneOf_null_branch():
    """Widening this branch made an object match both, so oneOf rejected it.

    The guard for a measured-looking fix that is actually wrong: a
    `{"type": "null"}` inside oneOf/anyOf is an alternative, not a claim that
    the field is always null.
    """
    tool = _tool("biothings_tools.json", "MyGene_query_genes")
    node = _at(tool["return_schema"], "hits", "items", "ensembl")
    branches = node.get("oneOf") or node.get("anyOf") or []

    assert {"type": "null"} in branches
