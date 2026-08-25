"""Regression guard: gnomad_get_sv_by_gene / gnomad_get_sv_by_region used to
hardcode `structural_variants(dataset: gnomad_sv_r4)` while still exposing a
`reference_genome` enum of GRCh37/GRCh38. gnomad_sv_r4 is a GRCh38 callset, so
a GRCh37 request returned a GRCh37 gene span (or a GRCh37 region echo) next to
a GRCh38 SV list -- two coordinate systems mixed silently in one payload.
Confirmed live: RHD GRCh37 and GRCh38 returned byte-identical 162-SV lists, and
the GRCh37 region query returned CPX variants at pos 1769047, nowhere near the
requested 25598884-25656936 interval.

The SV dataset now follows the requested assembly via fields.derived_variables:
GRCh38 -> gnomad_sv_r4, GRCh37 -> gnomad_sv_r2_1.

That fix opened a follow-on gap: gnomad_get_sv_detail still hardcoded
`structural_variant(dataset: gnomad_sv_r4)` while telling callers to discover
IDs with the two tools above, so a GRCh37 caller got IDs the detail tool could
not resolve ("Variant not found"). SV variant IDs are dataset-specific and the
two formats are disjoint -- measured live over 4411 gnomad_sv_r2_1 IDs and
36151 gnomad_sv_r4 IDs, the r2_1 pattern `<TYPE>_<chrom>_<decimal>` matched
4411/4411 r2_1 IDs and 0/36151 r4 IDs (r4 IDs always carry a `chr` prefix).
gnomad_get_sv_detail now routes on that ID format via a `patterns` rule, so r4
IDs keep their previous dataset and behaviour exactly.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parent.parent.parent / "src/tooluniverse/data/gnomad_tools.json"
)
SV_TOOLS = ("gnomad_get_sv_by_gene", "gnomad_get_sv_by_region")


def _config(name):
    configs = json.loads(CONFIG_PATH.read_text())
    return next(c for c in configs if c["name"] == name)


@pytest.mark.parametrize("tool_name", SV_TOOLS)
def test_sv_dataset_is_not_hardcoded(tool_name):
    fields = _config(tool_name)["fields"]
    assert "gnomad_sv_r4)" not in fields["query_schema"]
    assert "structural_variants(dataset: $svDataset)" in fields["query_schema"]
    assert "$svDataset: StructuralVariantDatasetId!" in fields["query_schema"]

    rule = fields["derived_variables"]["svDataset"]
    assert rule["from"] == "reference_genome"
    assert rule["map"] == {"GRCh37": "gnomad_sv_r2_1", "GRCh38": "gnomad_sv_r4"}
    assert rule["default"] == "gnomad_sv_r4"


@pytest.mark.parametrize("tool_name", SV_TOOLS)
def test_sv_homozygote_count_is_nullable(tool_name):
    """gnomad_sv_r2_1 reports homozygote_count: null for multi-allelic CNVs."""
    schema = json.dumps(_config(tool_name)["return_schema"])
    variants = json.loads(schema)["oneOf"][0]["properties"]
    root = variants["gene"] if "gene" in variants else variants["region"]
    sv_props = root["properties"]["structural_variants"]["items"]["properties"]
    assert "null" in sv_props["homozygote_count"]["type"]
    assert "null" in sv_props["major_consequence"]["type"]


@pytest.mark.parametrize(
    "reference_genome,expected",
    [("GRCh37", "gnomad_sv_r2_1"), ("GRCh38", "gnomad_sv_r4"), (None, "gnomad_sv_r4")],
)
def test_derived_variable_follows_reference_genome(reference_genome, expected):
    from tooluniverse.gnomad_tool import gnomADGraphQLQueryTool

    tool = gnomADGraphQLQueryTool(_config("gnomad_get_sv_by_gene"))
    variables = dict(tool.default_variables)
    if reference_genome is not None:
        variables["referenceGenome"] = reference_genome
    tool._apply_derived_variables(variables)
    assert variables["svDataset"] == expected


def test_explicitly_supplied_derived_variable_wins():
    from tooluniverse.gnomad_tool import gnomADGraphQLQueryTool

    tool = gnomADGraphQLQueryTool(_config("gnomad_get_sv_by_gene"))
    variables = {"referenceGenome": "GRCh37", "svDataset": "gnomad_sv_r2_1_controls"}
    tool._apply_derived_variables(variables)
    assert variables["svDataset"] == "gnomad_sv_r2_1_controls"


def test_derived_variables_absent_is_a_no_op():
    """Tools without fields.derived_variables keep their previous behaviour."""
    from tooluniverse.gnomad_tool import gnomADGraphQLQueryTool

    tool = gnomADGraphQLQueryTool(_config("gnomad_get_region"))
    variables = {"referenceGenome": "GRCh38"}
    tool._apply_derived_variables(variables)
    assert variables == {"referenceGenome": "GRCh38"}


# --- gnomad_get_sv_detail: route the callset off the variant ID format -------

DETAIL_TOOL = "gnomad_get_sv_detail"


def test_sv_detail_dataset_is_not_hardcoded():
    fields = _config(DETAIL_TOOL)["fields"]
    assert "gnomad_sv_r4," not in fields["query_schema"]
    assert "structural_variant(dataset: $svDataset," in fields["query_schema"]
    assert "$svDataset: StructuralVariantDatasetId!" in fields["query_schema"]

    rule = fields["derived_variables"]["svDataset"]
    assert rule["from"] == "variant_id"
    assert rule["default"] == "gnomad_sv_r4"
    assert [p["value"] for p in rule["patterns"]] == ["gnomad_sv_r2_1"]


def test_sv_detail_dataset_override_is_optional_with_upstream_enum():
    """The override must never become required, and must match upstream."""
    parameter = _config(DETAIL_TOOL)["parameter"]
    assert parameter["required"] == ["variant_id"]
    assert parameter["properties"]["dataset"]["enum"] == [
        "gnomad_sv_r2_1",
        "gnomad_sv_r2_1_controls",
        "gnomad_sv_r2_1_non_neuro",
        "gnomad_sv_r4",
    ]
    # No JSON default: the fallback is the auto-detected callset, not a pin.
    assert "default" not in parameter["properties"]["dataset"]


@pytest.mark.parametrize(
    "variant_id,expected",
    [
        # r2_1 IDs: <TYPE>_<chrom>_<decimal>, no "chr" prefix.
        ("DEL_1_1937", "gnomad_sv_r2_1"),
        ("MCNV_1_28", "gnomad_sv_r2_1"),
        ("BND_1_1", "gnomad_sv_r2_1"),
        ("DEL_X_191243", "gnomad_sv_r2_1"),
        ("DUP_Y_54913", "gnomad_sv_r2_1"),
        ("CPX_22_1234", "gnomad_sv_r2_1"),
        # r4 IDs: <TYPE>_chr<chrom>_<hex>. Must keep today's dataset exactly.
        ("DEL_chr1_759a6e5b", "gnomad_sv_r4"),
        ("DEL_chr17_24e4872b", "gnomad_sv_r4"),
        ("DUP_chr22_abc12345", "gnomad_sv_r4"),
        ("BND_chrX_12345678", "gnomad_sv_r4"),
        # An all-decimal r4 suffix still routes to r4 via the "chr" prefix.
        ("DEL_chr1_12345678", "gnomad_sv_r4"),
        # Unrecognised shapes fall back to today's dataset, so a bad ID keeps
        # failing the same clean "Variant not found" way it does now.
        ("NOT_A_REAL_ID", "gnomad_sv_r4"),
        ("", "gnomad_sv_r4"),
    ],
)
def test_sv_detail_dataset_follows_variant_id_format(variant_id, expected):
    from tooluniverse.gnomad_tool import gnomADGraphQLQueryTool

    tool = gnomADGraphQLQueryTool(_config(DETAIL_TOOL))
    variables = {"variantId": variant_id}
    tool._apply_derived_variables(variables)
    assert variables["svDataset"] == expected


def test_sv_detail_explicit_dataset_wins_over_id_format():
    """The optional override beats auto-detection, for v2.1 subsets."""
    from tooluniverse.gnomad_tool import gnomADGraphQLQueryTool

    tool = gnomADGraphQLQueryTool(_config(DETAIL_TOOL))
    variables = {"variantId": "DEL_1_1937", "svDataset": "gnomad_sv_r2_1_controls"}
    tool._apply_derived_variables(variables)
    assert variables["svDataset"] == "gnomad_sv_r2_1_controls"


@pytest.mark.parametrize(
    "field",
    [
        # Measured null counts over 4595 gnomad_sv_r2_1 records spanning five
        # GRCh37 regions: 47 null for the hom/hemi counts (multi-allelic CNVs),
        # 879 null for the consequence fields, 3126 null for chrom2/pos2/end2.
        "homozygote_count",
        "hemizygote_count",
        "major_consequence",
        "consequence",
        "chrom2",
        "pos2",
        "end2",
        "ac_hom",
        "ac_hemi",
    ],
)
def test_sv_detail_nullable_fields(field):
    schema = _config(DETAIL_TOOL)["return_schema"]
    props = schema["oneOf"][0]["properties"]["structural_variant"]["properties"]
    assert "null" in props[field]["type"], field


def test_sv_detail_breakend_coordinates_accept_integers():
    """pos2/end2 used to be typed `null`-only; BND records carry integers."""
    schema = _config(DETAIL_TOOL)["return_schema"]
    props = schema["oneOf"][0]["properties"]["structural_variant"]["properties"]
    for field in ("pos2", "end2"):
        assert "integer" in props[field]["type"], field


def test_pattern_rules_do_not_disturb_map_based_rules():
    """The `patterns` extension must leave pure lookup-table rules untouched."""
    from tooluniverse.gnomad_tool import gnomADGraphQLQueryTool

    tool = gnomADGraphQLQueryTool(_config("gnomad_get_sv_by_gene"))
    assert "patterns" not in tool.derived_variables["svDataset"]
    variables = {"referenceGenome": "GRCh37"}
    tool._apply_derived_variables(variables)
    assert variables["svDataset"] == "gnomad_sv_r2_1"


def test_match_patterns_ignores_non_string_sources():
    from tooluniverse.gnomad_tool import gnomADGraphQLQueryTool

    patterns = [{"match": "^x", "value": "hit"}]
    assert gnomADGraphQLQueryTool._match_patterns(patterns, None) is None
    assert gnomADGraphQLQueryTool._match_patterns(patterns, 42) is None
    assert gnomADGraphQLQueryTool._match_patterns(None, "xyz") is None
    assert gnomADGraphQLQueryTool._match_patterns(patterns, "xyz") == "hit"
