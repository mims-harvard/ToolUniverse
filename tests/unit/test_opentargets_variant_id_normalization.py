"""Unit test: OpenTargets variant-id delimiter + not-found message.

Regression: OpenTargets_get_variant_info requires the underscore variant id
'chr_pos_ref_alt', but gnomad_search_variants / gnomad_get_variant_populations
emit the hyphen form 'chr-pos-ref-alt' (e.g. '19-44908684-T-C'). Feeding the
hyphen form straight through failed, and the shared OpenTargets hyphen->space
retry mangled it to '19 44908684 T C', producing a misleading "no entity ...
EFO to MONDO" (disease) error for a *variant* query. Now the id is normalized
to underscores before the query, and the not-found message is variant-specific.
"""
import pytest

from tooluniverse.graphql_tool import (
    OpentargetTool,
    _ot_entity_not_found_message,
)


@pytest.mark.unit
def test_hyphen_variant_id_normalized_to_underscore():
    assert (
        OpentargetTool._normalize_variant_id("19-44908684-T-C") == "19_44908684_T_C"
    )


@pytest.mark.unit
def test_underscore_variant_id_unchanged():
    assert (
        OpentargetTool._normalize_variant_id("19_44908684_T_C") == "19_44908684_T_C"
    )


@pytest.mark.unit
def test_non_coordinate_values_untouched():
    # rsIDs and other strings must not be rewritten.
    assert OpentargetTool._normalize_variant_id("rs429358") == "rs429358"
    # A hyphenated name that isn't a 4-part coordinate stays as-is.
    assert OpentargetTool._normalize_variant_id("BRCA2-related") == "BRCA2-related"
    # An indel coordinate (still 4 parts) normalizes.
    assert (
        OpentargetTool._normalize_variant_id("1-100-AT-A") == "1_100_AT_A"
    )


@pytest.mark.unit
def test_not_found_message_is_variant_specific_not_disease():
    msg = _ot_entity_not_found_message({"variantId": "1_999999999_A_T"})
    assert "variant" in msg.lower()
    assert "1_999999999_A_T" in msg
    # Must NOT wrongly blame disease EFO->MONDO remapping for a variant id.
    assert "EFO to MONDO" not in msg
