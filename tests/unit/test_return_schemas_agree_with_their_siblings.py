"""A schema that contradicts its own sibling is a sampling artifact, not a contract.

#843 widened the `type: "null"` declarations whose real type could be measured
and left 166 that came back null in every example, because nothing measured
says what those hold. Which of the 166 are latent failures and which are
accurate is answerable without guessing, by a question the tree can ask itself:
does another tool in the same file give the same field a real type?

16 did, on 2026-11-01. Five of them were correct and the check is what showed
that:

    odphp          Query->Age/Pregnant/Sex/TopicId/Type -- each tool types the
                   echoed request fields it has a parameter for and nulls the
                   ones it cannot supply. Internally consistent.
    ebi_proteins   features->*->description -- 0 non-null across 233 PTM
                   features on P04637, P31749 and P00533. PTM features carry
                   no description; mutagenesis features do.

The rest were real, and every correction below was measured against the live
API, not inferred from the sibling:

    OncoKB         highestResistanceLevel was `null` in annotate_mutations,
                   annotate_variant and annotate_copy_number while
                   get_gene_info said `string`. ROS1 G2032R in NSCLC -- the
                   crizotinib-resistance mutation, and ROS1 is one of the three
                   genes in OncoKB's token-free demo dataset -- answers
                   "LEVEL_R2".
    CPIC           CYP2C9 carries a functionmethods and a notesondiplotype
                   string; CYP2D6 and CYP2C19, the two test_examples, do not.
    rcsb_pdb       get_structure_validation_metrics_by_pdb_id declared both
                   R-factors `null` while get_core_refinement_statistics, fixed
                   in #843, already said ["number", "null"]. 4HHB answers
                   0.135. Widening one tool and leaving its sibling was the
                   hole this check found in that fix.

The same pass fixed the opposite error in the same fields. All five OncoKB
level fields measure `null,str` over 19 live demo calls, so a bare `"string"`
was as wrong as a bare `"null"`: BRAF V600E has no diagnostic level, ROS1
G2032R has no sensitive level at some tumour types. get_gene_info is left
alone -- it is a different endpoint whose levels are "1", "3A" and "" rather
than "LEVEL_1" and null.

Each tool also gained a test_example that reaches the non-null case, because
the schema and the example were generated from the same single response and so
the example could never contradict the schema. All five tools passed their own
examples before this change.

The rcsb example is worth stating precisely, because the first reading of it
was wrong. Its result carries no `status` key, so the runner never unwraps and
the schema's `data` property does apply: HEAD's schema rejects 0.135 when the
whole result is validated. The check was working. What hid the bug was the
example -- 1CRN is a 1981 entry that reports no R-factors, so the one input the
tool ships could only ever see null.

The schemas where the check really was touching nothing are a separate set, and
they are fixed in the following commit.
"""

import json
from pathlib import Path

import jsonschema
import pytest

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _load(stem):
    return json.loads((DATA / f"{stem}.json").read_text())


def _tool(stem, name):
    for entry in _load(stem):
        if entry.get("name") == name:
            return entry
    raise AssertionError(f"{name} not in {stem}.json")


def _subschema(schema, key, depth=0):
    """The declaration for *key*, found anywhere in *schema*."""
    if depth > 8 or not isinstance(schema, dict):
        return None
    for prop, decl in (schema.get("properties") or {}).items():
        if prop == key and isinstance(decl, dict) and "type" in decl:
            return decl
        found = _subschema(decl, key, depth + 1)
        if found is not None:
            return found
    if "items" in schema:
        found = _subschema(schema["items"], key, depth + 1)
        if found is not None:
            return found
    for keyword in ("oneOf", "anyOf", "allOf"):
        for branch in schema.get(keyword) or []:
            found = _subschema(branch, key, depth + 1)
            if found is not None:
                return found
    return None


def _types(schema, key):
    decl = _subschema(schema, key, 0)
    assert decl is not None, f"{key} not declared"
    declared = decl["type"]
    return set(declared) if isinstance(declared, list) else {declared}


# ---------------------------------------------------------------- OncoKB

ONCOKB_LEVEL_FIELDS = [
    "highestSensitiveLevel",
    "highestResistanceLevel",
    "highestDiagnosticImplicationLevel",
    "highestPrognosticImplicationLevel",
    "highestFdaLevel",
]
# measured over 19 live demo.oncokb.org calls on 2026-11-01
MEASURED_LEVELS = {
    "highestSensitiveLevel": "LEVEL_1",
    "highestResistanceLevel": "LEVEL_R2",
    "highestDiagnosticImplicationLevel": "LEVEL_Dx2",
    "highestPrognosticImplicationLevel": "LEVEL_Px1",
    "highestFdaLevel": "LEVEL_Fda2",
}


@pytest.mark.parametrize(
    "tool",
    [
        "OncoKB_annotate_mutations",
        "OncoKB_annotate_variant",
        "OncoKB_annotate_copy_number",
    ],
)
@pytest.mark.parametrize("field", ONCOKB_LEVEL_FIELDS)
def test_oncokb_levels_are_a_string_or_null(tool, field):
    """Every level field measures both, so neither bare type is a contract."""
    declared = _types(_tool("oncokb_tools", tool)["return_schema"], field)
    assert declared == {"string", "null"}, f"{tool}.{field} declares {sorted(declared)}"


@pytest.mark.parametrize("field,value", sorted(MEASURED_LEVELS.items()))
def test_the_measured_level_values_validate(field, value):
    schema = _tool("oncokb_tools", "OncoKB_annotate_variant")["return_schema"]
    decl = _subschema(schema, field, 0)
    jsonschema.validate(value, decl)
    jsonschema.validate(None, decl)


def test_oncokb_get_gene_info_keeps_its_own_shape():
    """A different endpoint: levels are "1", "3A" and "", never "LEVEL_1"/null."""
    schema = _tool("oncokb_tools", "OncoKB_get_gene_info")["return_schema"]
    for field in ("highestSensitiveLevel", "highestResistanceLevel"):
        assert _types(schema, field) == {"string"}
    decl = _subschema(schema, "highestResistanceLevel", 0)
    jsonschema.validate("", decl)  # the measured empty-string case


def test_oncokb_copy_number_entrez_id_is_a_number():
    """Its only example, ERBB2, is absent from the demo dataset, so the schema
    was generated from a geneExist=False response. BRAF answers 673."""
    schema = _tool("oncokb_tools", "OncoKB_annotate_copy_number")["return_schema"]
    declared = _types(schema, "entrezGeneId")
    assert "null" in declared and declared & {"integer", "number"}
    jsonschema.validate(673, _subschema(schema, "entrezGeneId", 0))


# ------------------------------------------------------------------ CPIC

CYP2C9_FUNCTIONMETHODS = (
    "Methods:\nThe PubMed and PharmGKB databases were searched for the following terms"
)


@pytest.mark.parametrize("field", ["functionmethods", "notesondiplotype"])
def test_cpic_gene_notes_are_a_string_or_null(field):
    schema = _tool("cpic_tools", "CPIC_get_gene_info")["return_schema"]
    assert _types(schema, field) == {"string", "null"}
    jsonschema.validate(CYP2C9_FUNCTIONMETHODS, _subschema(schema, field, 0))
    jsonschema.validate(None, _subschema(schema, field, 0))


# -------------------------------------------------------------- rcsb_pdb


@pytest.mark.parametrize("field", ["ls_R_factor_R_work", "ls_R_factor_R_free"])
def test_both_rcsb_tools_agree_on_the_r_factors(field):
    """get_core_refinement_statistics was fixed in #843; its sibling was not."""
    for tool in (
        "get_structure_validation_metrics_by_pdb_id",
        "get_core_refinement_statistics",
    ):
        declared = _types(_tool("rcsb_pdb_tools", tool)["return_schema"], field)
        assert declared == {"number", "null"}, (
            f"{tool}.{field} declares {sorted(declared)}"
        )


def test_the_validation_metrics_envelope_accepts_4hhb():
    """Measured: {"data": {"entries": [{"refine": [{"R_free": null,
    "R_work": 0.135}], ...}]}}. Validated against the envelope, because the
    runner's unwrap makes this schema vacuous -- see the census below."""
    schema = _tool("rcsb_pdb_tools", "get_structure_validation_metrics_by_pdb_id")[
        "return_schema"
    ]
    jsonschema.validate(
        {
            "data": {
                "entries": [
                    {
                        "rcsb_id": "4HHB",
                        "refine": [
                            {"ls_R_factor_R_free": None, "ls_R_factor_R_work": 0.135}
                        ],
                        "pdbx_vrpt_summary_geometry": [{"clashscore": 142.32}],
                    }
                ]
            }
        },
        schema,
    )


# ------------------------------------------------- the regression examples

REACHES_THE_NON_NULL_CASE = [
    (
        "oncokb_tools",
        "OncoKB_annotate_mutations",
        {
            "gene": "ROS1",
            "variant": "G2032R",
            "tumor_type": "Non-Small Cell Lung Cancer",
        },
    ),
    (
        "oncokb_tools",
        "OncoKB_annotate_variant",
        {
            "gene": "ROS1",
            "variant": "G2032R",
            "tumor_type": "Non-Small Cell Lung Cancer",
        },
    ),
    (
        "oncokb_tools",
        "OncoKB_annotate_copy_number",
        {"gene": "BRAF", "copy_number_type": "AMPLIFICATION", "tumor_type": "Melanoma"},
    ),
    ("cpic_tools", "CPIC_get_gene_info", {"symbol": "CYP2C9"}),
    (
        "rcsb_pdb_tools",
        "get_structure_validation_metrics_by_pdb_id",
        {"pdb_id": "4HHB"},
    ),
]


@pytest.mark.parametrize("stem,tool,example", REACHES_THE_NON_NULL_CASE)
def test_an_example_reaches_the_non_null_case(stem, tool, example):
    """Without these the sweep can only ever see the response the schema was
    generated from. All five tools passed their own examples before the fix."""
    assert example in _tool(stem, tool).get("test_examples", [])


# ------------------------------------------------ the sibling contradiction

# Verified correct on 2026-11-01, so excluded from the rule rather than "fixed":
# odphp types the echoed request fields each tool has a parameter for and nulls
# the rest; EBI Proteins' PTM features carry no description (0 non-null across
# 233 features on P04637, P31749, P00533).
VERIFIED_CONSISTENT = {
    ("odphp_tools.json", "Query->Age"),
    ("odphp_tools.json", "Query->Keyword"),
    ("odphp_tools.json", "Query->Pregnant"),
    ("odphp_tools.json", "Query->Sex"),
    ("odphp_tools.json", "Query->TopicId"),
    ("odphp_tools.json", "Query->Type"),
    ("ebi_proteins_ext_tools.json", "features->*->description"),
    ("cpic_tools.json", "*->functionmethods"),
    ("cpic_tools.json", "*->notesondiplotype"),
}


def _declarations(stem):
    """{field path: {tool: declared type tuple}} for one tool file."""
    found = {}

    def walk(node, path, tool):
        if not isinstance(node, dict):
            return
        for prop, decl in (node.get("properties") or {}).items():
            here = f"{path}->{prop}" if path else prop
            if isinstance(decl, dict) and "type" in decl:
                declared = decl["type"]
                found.setdefault(here, {})[tool] = (
                    tuple(declared) if isinstance(declared, list) else (declared,)
                )
            walk(decl, here, tool)
        if "items" in node:
            walk(node["items"], f"{path}->*" if path else "*", tool)
        for keyword in ("oneOf", "anyOf", "allOf"):
            for branch in node.get(keyword) or []:
                walk(branch, path, tool)
        for decl in (node.get("patternProperties") or {}).values():
            walk(decl, f"{path}->~" if path else "~", tool)

    for entry in _load(stem):
        if isinstance(entry.get("return_schema"), dict):
            walk(entry["return_schema"], "", entry.get("name", "?"))
    return found


def test_no_field_is_null_in_one_tool_and_typed_in_its_sibling():
    offenders = []
    for path in sorted(DATA.glob("*_tools.json")):
        for field, by_tool in _declarations(path.stem).items():
            if (path.name, field) in VERIFIED_CONSISTENT:
                continue
            nulls = [t for t, d in by_tool.items() if d == ("null",)]
            typed = {t: d for t, d in by_tool.items() if set(d) - {"null"}}
            if nulls and typed:
                offenders.append(
                    f"{path.name} {field}: null in {sorted(nulls)}, "
                    f"typed in {sorted(typed)[0]}={list(next(iter(typed.values())))}"
                )
    assert not offenders, "\n".join(offenders)
