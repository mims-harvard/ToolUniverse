"""Offline regression tests: FDA_get_drug_label must read pre-PLR label sections.

Defect this covers
------------------
``_extract_label`` mapped its ``warnings_and_precautions`` response key from the
PLR section name only. openFDA carries a label in whichever format it was
submitted in, and the two formats share no section names, so for every pre-PLR
label the key came back null -- next to ``truncated: false``, an explicit
"nothing was cut". Live evidence, CLI::

    $ python -m tooluniverse.cli run FDA_get_drug_label '{"drug_name":"flumazenil"}'
    warnings_and_precautions: None
    truncated: false
    (no "warnings" key anywhere in the returned record)

Flumazenil is the benzodiazepine antidote and its WARNINGS section is the whole
reason the drug is dangerous::

    $ curl -G 'https://api.fda.gov/drug/label.json' \\
        --data-urlencode 'search=openfda.generic_name:"flumazenil"' --data 'limit=1'
    'warnings_and_cautions' in record: False
    'warnings' in record:              True
    "WARNINGS Risk of Seizures The reversal of benzodiazepine effects may be
     associated with the onset of seizures in certain high-risk populations ...
     Flumazenil is not recommended in cases of serious cyclic antidepressant
     poisoning ..."

The corpus-wide scale of this, and the fact that it follows the label's vintage
rather than the drug, is measured once in the note on ``_SECTION_FIELDS`` in
``src/tooluniverse/fda_label_tool.py``; it is not restated here.

``search=_exists_:warnings_and_precautions`` returns NOT_FOUND -- that name is
the printed heading, never an openFDA field -- so the original first lookup was
dead code and is gone.

Relationship to test_fda_label_plr_section_split
------------------------------------------------
That module pins the same upstream split for the ``openfda_tool`` family, which
takes the opposite approach on purpose: there the response keys ARE the openFDA
field names, so sibling content is attached under its own key and never
substituted, or provenance would be misrepresented. Here the response key
``warnings_and_precautions`` is format-neutral prose, not a field name, so
mapping either source section onto it is the correct behaviour. The returned
text keeps its own heading ("WARNINGS" vs "5 WARNINGS AND PRECAUTIONS"), so the
source stays visible in the content either way.

Hermeticity
-----------
``_extract_label`` is a pure function over an already-fetched openFDA record, so
these tests do no I/O at all rather than relying on a patch holding.
"""

import pytest

from tooluniverse.fda_label_tool import _SECTION_FIELDS, _extract_label

pytestmark = pytest.mark.unit

# Shape of a real pre-PLR record: WARNINGS + PRECAUTIONS, and none of the PLR
# section names. Trimmed from the live flumazenil label.
_PRE_PLR = {
    "id": "bd300433",
    "openfda": {"generic_name": ["FLUMAZENIL"]},
    "warnings": ["WARNINGS Risk of Seizures The reversal of benzodiazepine effects"],
    "precautions": ["PRECAUTIONS Return of Sedation Flumazenil may be expected"],
    "adverse_reactions": ["ADVERSE REACTIONS Deaths have occurred"],
}

# Shape of a real PLR record: the numbered PLR sections, no legacy sections.
_PLR = {
    "id": "aa11",
    "openfda": {"generic_name": ["APIXABAN"]},
    "warnings_and_cautions": ["5 WARNINGS AND PRECAUTIONS Apixaban can cause bleeding"],
    "drug_interactions": ["7 DRUG INTERACTIONS Apixaban is a substrate of CYP3A4"],
}

# 3,439 labels upstream carry both. The PLR section is the current one.
_BOTH = {
    "id": "bb22",
    "openfda": {"generic_name": ["MIXED"]},
    "warnings_and_cautions": ["PLR TEXT"],
    "warnings": ["LEGACY TEXT"],
}


def test_pre_plr_label_returns_its_warnings_section():
    record, truncated = _extract_label(_PRE_PLR)

    assert record["warnings_and_precautions"].startswith("WARNINGS Risk of Seizures")
    assert truncated == []


def test_pre_plr_label_returns_its_precautions_section():
    record, _ = _extract_label(_PRE_PLR)

    # Pre-PLR labels have no drug_interactions/use_in_specific_populations
    # section; that content is subheaded inside PRECAUTIONS.
    assert record["precautions"].startswith("PRECAUTIONS Return of Sedation")
    assert record["drug_interactions"] is None
    assert record["use_in_specific_populations"] is None


def test_plr_label_is_unchanged():
    record, _ = _extract_label(_PLR)

    assert record["warnings_and_precautions"].startswith("5 WARNINGS AND PRECAUTIONS")
    assert record["drug_interactions"].startswith("7 DRUG INTERACTIONS")
    # A PLR label has no legacy PRECAUTIONS section, and none is invented.
    assert record["precautions"] is None


def test_plr_section_wins_when_a_label_carries_both():
    record, _ = _extract_label(_BOTH)

    assert record["warnings_and_precautions"] == "PLR TEXT"


def test_recovered_sections_obey_the_truncation_budget():
    # A section that is only reachable via the new mapping must still be
    # disclosed when cut, or the fix would reintroduce silent loss by a
    # different route.
    record, truncated = _extract_label(_PRE_PLR, max_chars=10)

    # Order follows _SECTION_FIELDS here; _disclose_truncation sorts it later.
    assert set(truncated) == {
        "warnings_and_precautions",
        "precautions",
        "adverse_reactions",
    }
    assert len(record["warnings_and_precautions"]) < len(_PRE_PLR["warnings"][0])
    assert "precautions" in _SECTION_FIELDS
