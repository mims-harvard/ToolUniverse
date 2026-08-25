"""SCREEN cCRE proximality.

The API's `info.isproximal` comes back false for every element, so forwarding it
verbatim made `is_proximal` useless: filtering on it returned nothing anywhere,
which reads as "no proximal elements at this locus" rather than "this field is
unset". SCREEN already encodes proximality in the element class.
"""

import pytest

from tooluniverse.screen_ccre_tool import _is_proximal


@pytest.mark.parametrize("element_type", ["PLS", "pELS"])
def test_proximal_classes_are_proximal(element_type):
    """PLS (promoter-like) and pELS (proximal enhancer-like) are TSS-proximal."""
    assert _is_proximal(element_type, None) is True
    assert _is_proximal(element_type, False) is True


@pytest.mark.parametrize("element_type", ["dELS", "CTCF-only", "DNase-H3K4me3"])
def test_distal_and_other_classes_are_not_proximal(element_type):
    assert _is_proximal(element_type, None) is False
    assert _is_proximal(element_type, False) is False


def test_api_true_is_honoured():
    """If the API ever populates the field, a true value wins."""
    assert _is_proximal("dELS", True) is True


def test_missing_element_type_is_not_proximal():
    for value in (None, "", "unknown"):
        assert _is_proximal(value, None) is False
