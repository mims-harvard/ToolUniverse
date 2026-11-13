"""The sibling-section disclosure left out the one section it had a tool for.

A label tool returns one section, and `other_section_tools` exists so that a
caller who asked for the safe-handling warnings is told the same label also
carries, say, a boxed warning -- naming the tool that returns each. The set it
checks, `LABEL_DECISION_SECTIONS`, omitted `general_precautions`, which is
where the older labels put the content newer ones put under `precautions`:
dexamethasone has a general_precautions section and no precautions one, so the
disclosure said nothing about it.

Measured live on FDA_get_safe_handling_warnings_by_drug_name for
dexamethasone, before the fix: 12 sections disclosed, general_precautions not
among them, and 2 labels carrying it.
"""

import pytest

from tooluniverse.openfda_tool import (
    LABEL_DECISION_SECTIONS,
    LABEL_SECTION_TOOLS,
)

pytestmark = pytest.mark.unit


def test_general_precautions_is_checked_by_the_disclosure():
    assert "general_precautions" in LABEL_DECISION_SECTIONS


def test_every_section_with_a_tool_is_a_section_the_disclosure_checks():
    """The invariant the omission broke.

    `LABEL_SECTION_TOOLS` says which tool returns a section;
    `LABEL_DECISION_SECTIONS` says which sections the disclosure looks for. A
    section in the first and not the second has a tool nobody will be told to
    call.
    """
    missing = sorted(set(LABEL_SECTION_TOOLS) - set(LABEL_DECISION_SECTIONS))
    assert missing == [], (
        f"{missing} have a tool in LABEL_SECTION_TOOLS and are not in "
        "LABEL_DECISION_SECTIONS, so other_section_tools will never mention them"
    )
