"""Regression guard for Fix-R78B-1: ClinVar_search_variants had no way to
search by protein change / HGVS notation (only gene/condition/variant_id/
clinical_significance), so an exact-match lookup for a specific known
variant could only be done by browsing gene-level rows (capped at 100) and
filtering client-side -- which silently misses well-known but old/low-ID
records once a gene has more ClinVar entries than the fetch cap (confirmed
live for HBB's canonical sickle-cell record, VCV 15333, one of the best-known
pathogenic variants in human genetics; see test_compound_variant_tool.py for
the full cross-tool bug this caused). ClinVar eSearch DOES support a real
[Variant name] field tag (confirmed live via raw NCBI E-utils), so this adds
it as a proper "variant_name" parameter.

Fix-R3-07 update: each candidate is now emitted as a QUOTED Entrez term, and
an HGVS-prefixed name additionally contributes its prefix-stripped spelling,
because coding notation ("c.1905+1G>A") only matches with the prefix kept
while protein notation ("p.Glu342Lys") only matches with it removed.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def test_variant_name_single_string_builds_field_tag():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        result = tool.run({"gene": "HBB", "variant_name": "Glu6Val"})

    assert result["status"] == "success"
    term = mock_request.call_args[0][1]["term"]
    assert "HBB[gene]" in term
    assert '"Glu6Val"[Variant name]' in term
    assert "AND" in term


def test_variant_name_list_combines_with_or():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        tool.run({"gene": "HBB", "variant_name": ["Glu7Val", "Glu6Val"]})

    term = mock_request.call_args[0][1]["term"]
    assert '"Glu7Val"[Variant name]' in term
    assert '"Glu6Val"[Variant name]' in term
    assert " OR " in term
    # both candidates must be inside one parenthesized OR group, ANDed with gene
    assert '("Glu7Val"[Variant name] OR "Glu6Val"[Variant name])' in term


def test_variant_name_alone_is_a_valid_search_no_gene_required():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        result = tool.run({"variant_name": "V600E"})

    assert result["status"] == "success"
    assert '"V600E"[Variant name]' in mock_request.call_args[0][1]["term"]


def test_variant_name_is_a_recognized_parameter_not_flagged_as_unrecognized():
    tool = _tool()
    result = tool.run({"variant_name_typo": "V600E"})
    assert result["status"] == "error"
    # the typo'd param is flagged as unrecognized, and the correct spelling
    # is offered as a valid search parameter in the same error message
    assert "Unrecognized parameter(s): variant_name_typo" in result["error"]
    assert "variant_name" in result["error"]


def test_empty_or_blank_variant_name_entries_are_dropped():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        tool.run({"gene": "HBB", "variant_name": ["", "  ", "Glu6Val"]})

    term = mock_request.call_args[0][1]["term"]
    assert '"Glu6Val"[Variant name]' in term
    assert "OR" not in term  # only one real candidate survived, no OR needed


def test_variant_is_aliased_to_variant_name_when_gene_also_present():
    """Fix: `variant` (the intuitive name; schema calls it `variant_name`) was
    silently dropped whenever a valid param like `gene` was also present, so
    {"gene":"KRAS","variant":"G12C"} returned ALL KRAS variants instead of the
    G12C ones -- a dangerous silent full-gene dump. `variant` is now aliased to
    `variant_name` so the natural query filters correctly."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        result = tool.run({"gene": "KRAS", "variant": "G12C"})

    assert result["status"] == "success"
    term = mock_request.call_args[0][1]["term"]
    assert "KRAS[gene]" in term
    assert '"G12C"[Variant name]' in term  # the variant filter is actually applied


def test_variant_alias_not_flagged_as_unrecognized_when_alone():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        result = tool.run({"variant": "G12C"})

    assert result["status"] == "success"
    assert '"G12C"[Variant name]' in mock_request.call_args[0][1]["term"]


def test_explicit_variant_name_takes_precedence_over_variant_alias():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        tool.run({"gene": "KRAS", "variant_name": "G12D", "variant": "G12C"})

    term = mock_request.call_args[0][1]["term"]
    assert '"G12D"[Variant name]' in term
    assert "G12C" not in term
