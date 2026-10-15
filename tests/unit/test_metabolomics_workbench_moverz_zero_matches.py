"""MetabolomicsWorkbench_search_by_mz/_search_by_exact_mass returned a raw string for zero matches.

Metabolomics Workbench's moverz endpoint sends the shared TSV header row and
nothing else when a search has no matches (confirmed live: m/z 180.0634 with
adduct M+H and tolerance 0.0001), not an empty body. `_parse_tsv_text` treated
"header, no rows" the same as "not a table" and fell back to handing back the
raw header line as `data`, a str, instead of the `[]` every other zero-result
path in this tool returns -- silently changing the output's type depending on
how many matches there happened to be.
"""

import pytest

pytestmark = pytest.mark.unit

HEADER_ONLY = (
    "Input m/z\tMatched m/z\tDelta\tName\tSystematic name\tFormula\tIon\t"
    "Category\tMain class\tSub class\n"
)
WITH_ROWS = (
    "Input m/z\tMatched m/z\tDelta\tName\n"
    "180.0634\t180.0653\t.0019\t5,8-Dihydroxy-3,4-dihydrocarbostyril\n"
)


def _parse(text):
    from tooluniverse.metabolomics_workbench_tool import MetabolomicsWorkbenchTool

    return MetabolomicsWorkbenchTool._parse_tsv_text(text)


def test_header_only_body_parses_as_an_empty_list_not_a_string():
    assert _parse(HEADER_ONLY) == []


def test_header_with_rows_still_parses_normally():
    rows = _parse(WITH_ROWS)
    assert rows == [
        {
            "Input m/z": "180.0634",
            "Matched m/z": "180.0653",
            "Delta": ".0019",
            "Name": "5,8-Dihydroxy-3,4-dihydrocarbostyril",
        }
    ]


def test_non_tabular_text_is_still_rejected():
    assert _parse("not a table at all") is None
    assert _parse("") is None
