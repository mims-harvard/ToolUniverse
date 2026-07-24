"""Unit tests for metabolite stereochemistry-prefix stripping.

Regression for Feature-007F-03: `_strip_stereo("L-Lactic Acid")` used to
return "actic Acid" (it over-stripped "L-L"), so CTD never matched the
parent compound and Metabolite_get_diseases silently returned 0 diseases
for L-lactate and other stereoisomers whose name starts with a stereo
letter.
"""
import pytest

from tooluniverse.metabolite_tool import _strip_stereo


@pytest.mark.unit
@pytest.mark.parametrize(
    "name,expected",
    [
        # First letter of the compound is itself a stereo letter — must NOT be eaten.
        ("L-Lactic Acid", "Lactic Acid"),
        ("D-Lactic acid", "Lactic acid"),
        ("L-Leucine", "Leucine"),
        ("D-Ribose", "Ribose"),
        # Two genuine stereo descriptors are both stripped.
        ("Beta-D-Glucose", "Glucose"),
        ("cis-trans-Retinal", "Retinal"),
        # Single descriptor where the compound does not start with a stereo letter.
        ("L-Alanine", "Alanine"),
    ],
)
def test_strip_stereo_does_not_over_strip(name, expected):
    assert _strip_stereo(name) == expected


@pytest.mark.unit
def test_strip_stereo_returns_empty_when_no_prefix():
    # No leading stereo descriptor → returns "" (signals "no parent variant").
    assert _strip_stereo("Glucose") == ""
    assert _strip_stereo("Lactic Acid") == ""
