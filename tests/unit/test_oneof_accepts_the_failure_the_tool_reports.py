"""A schema has to accept the failure its own tool reports.

The previous round closed 583 schemas whose `oneOf` matched an error envelope
on two branches. The same scan left 34 matching it on none: their oneOf is one
success shape against another, and the failure the tool really sends is
described nowhere. Those were called with a nonexistent identifier and the
payload recorded, which is how the list went from 34 to 30 -- four of them do
accept the shape they really emit, and it was the probe's envelope list that
did not cover it.

    euhealth x21, expression_anova, pharmacodb, monarch
                                  {status, error, error_details}   rejected
    SemanticScholar_search_papers  {status, error, retryable}       rejected
    UniProt function / location    {status, error, detail}          rejected
    WikiPathways_get_pathway       {status, error}                  rejected
    humanbase_ppi_analysis  {status, error, metadata, query, ...}   rejected

    FDA_get_drug_label             {status, error, suggestion}      accepted
    ProteinSimilarity x2           {status, error, stage}           accepted
    search_clinical_trials         a nonsense query still returns a result

humanbase is worth naming: it reports the error alongside `metadata`, `query`
and `unresolved_genes`, so it is a failure carrying context rather than a bare
envelope, and `biological_processes` is present and null. Its success branch
requires `graph`, which the failure lacks, so the error branch is still the only
one it reaches.

The `[]` case is separate and does not need an upstream failure at all. Four
tools pair two array branches, and an empty array satisfies any `items`, so a
search that legitimately finds nothing matched both branches and was invalid
against its own schema. Measured: PubMed_search_articles with a query that has
no hits returns `[]` and was rejected. `minItems: 1` on the secondary branch
leaves `[]` matching only the primary one, which is what an empty result is.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"

# The envelope each tool was measured sending, keyed by (file stem, tool).
MEASURED = {
    ("expression_anova_tools", "expression_anova_per_gene"): {
        "status": "error",
        "error": "x",
        "error_details": {"code": 500},
    },
    ("pharmacodb_tools", "PharmacoDB_get_drug_targets"): {
        "status": "error",
        "error": "x",
        "error_details": {"code": 500},
    },
    ("monarch_tools", "get_joint_associated_diseases_by_HPO_ID_list"): {
        "status": "error",
        "error": "x",
        "error_details": {"code": 500},
    },
    ("semantic_scholar_tools", "SemanticScholar_search_papers"): {
        "status": "error",
        "error": "x",
        "retryable": True,
    },
    ("uniprot_tools", "UniProt_get_function_by_accession"): {
        "status": "error",
        "error": "x",
        "detail": "x",
    },
    ("uniprot_tools", "UniProt_get_subcellular_location_by_accession"): {
        "status": "error",
        "error": "x",
        "detail": "x",
    },
    ("wikipathways_tools", "WikiPathways_get_pathway"): {
        "status": "error",
        "error": "x",
    },
    ("humanbase_tools", "humanbase_ppi_analysis"): {
        "status": "error",
        "error": "x",
        "biological_processes": None,
        "metadata": {},
        "query": {},
        "unresolved_genes": [],
    },
    ("pubmed_tools", "PubMed_search_articles"): {"status": "error", "error": "x"},
}

# The 21 euhealth tools all send the same shape.
EUHEALTH_ENVELOPE = {"status": "error", "error": "x", "error_details": {"code": 500}}

# Two array branches, where [] used to satisfy both.
EMPTY_RESULT_TOOLS = [
    ("pubmed_tools", "PubMed_search_articles"),
    ("semantic_scholar_tools", "SemanticScholar_search_papers"),
    ("uniprot_tools", "UniProt_get_function_by_accession"),
    ("uniprot_tools", "UniProt_get_subcellular_location_by_accession"),
]


def _entries(stem):
    return json.loads((DATA / f"{stem}.json").read_text())


def _tool(stem, name):
    for entry in _entries(stem):
        if entry.get("name") == name:
            return entry
    raise AssertionError(f"{name} not in {stem}.json")


def _matching(branches, instance):
    return [
        i
        for i, branch in enumerate(branches)
        if not list(Draft7Validator(branch).iter_errors(instance))
    ]


def _euhealth_tools():
    return [
        entry["name"]
        for entry in _entries("euhealth_tools")
        if isinstance(entry, dict)
        and isinstance((entry.get("return_schema") or {}).get("oneOf"), list)
    ]


CASES = sorted(MEASURED.items(), key=lambda kv: kv[0]) + [
    (("euhealth_tools", name), EUHEALTH_ENVELOPE) for name in _euhealth_tools()
]


def test_every_measured_tool_is_still_here():
    """30 were measured rejecting their own failure; a shrinking list would make
    the rest of this file pass by checking less."""
    assert len(CASES) == 30, [k for k, _ in CASES]


@pytest.mark.parametrize("key,envelope", CASES, ids=[f"{k[1]}" for k, _ in CASES])
def test_the_failure_the_tool_sends_matches_exactly_one_branch(key, envelope):
    stem, name = key
    schema = _tool(stem, name)["return_schema"]
    hits = _matching(schema["oneOf"], envelope)
    assert len(hits) == 1, (
        f"{name}: its own error envelope matches branches {hits}; "
        "none means the failure is undescribed, two means oneOf rejects it"
    )
    assert not list(Draft7Validator(schema).iter_errors(envelope)), (
        f"{name}: the whole schema still rejects the envelope it sends"
    )


@pytest.mark.parametrize(
    "stem,name", EMPTY_RESULT_TOOLS, ids=[n for _, n in EMPTY_RESULT_TOOLS]
)
def test_a_search_that_finds_nothing_is_valid(stem, name):
    """An empty array satisfies any `items`, so two array branches both accept
    [] unless one of them says it wants at least one element."""
    schema = _tool(stem, name)["return_schema"]
    hits = _matching(schema["oneOf"], [])
    assert len(hits) == 1, f"{name}: [] matches branches {hits}"
    assert not list(Draft7Validator(schema).iter_errors([]))


def _all_schemas():
    for path in sorted(DATA.glob("*.json")):
        try:
            entries = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            schema = entry.get("return_schema")
            if isinstance(schema, dict) and isinstance(schema.get("oneOf"), list):
                if len(schema["oneOf"]) > 1:
                    yield path.name, entry["name"], schema


ALL = list(_all_schemas())


def test_no_schema_lets_an_empty_array_match_two_branches():
    """The invariant behind the four, so a schema added later cannot bring it
    back. Only schemas that can describe an array at all are in scope: where a
    parent `type` already excludes a non-object, a branch overlap on [] changes
    no verdict -- expression_anova_per_gene is that case."""
    offenders = []
    for filename, tool, schema in ALL:
        if list(Draft7Validator(schema).iter_errors([])) and not _accepts_array(schema):
            continue
        if len(_matching(schema["oneOf"], [])) > 1:
            offenders.append((filename, tool))
    assert not offenders, "%d schemas reject an empty result: %s" % (
        len(offenders),
        offenders[:5],
    )


def _accepts_array(schema):
    declared = schema.get("type")
    if declared is None:
        return True
    return "array" in ([declared] if isinstance(declared, str) else declared)
