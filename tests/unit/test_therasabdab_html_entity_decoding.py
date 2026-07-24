"""Round 84: TheraSAbDab_search_therapeutics/get_all_therapeutics/search_by_target
(all backed by `_parse_search_results`) left raw HTML entities in every parsed
cell -- `clean_html()` only special-cased `&nbsp;`, so any therapeutic whose
format/target/etc. contained an apostrophe, ampersand, or quote in the source
page rendered corrupted (e.g. "VH-VH-VH&#39;-VH&#39;&#39;-VH&#39;" instead of
"VH-VH-VH'-VH''-VH'"). Confirmed live: &amp; appears 22541 times and &#39;
326 times in the real page source. Fixed by using the standard `html.unescape`
instead of a single hardcoded replace.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.therasabdab_tool import TheraSAbDabTool

pytestmark = pytest.mark.unit


def _tool():
    return TheraSAbDabTool({"name": "TheraSAbDab_get_all_therapeutics"})


def _row(cells):
    tds = "".join(f"<td>{c}</td>" for c in cells)
    return f"<table><tr>{tds}</tr></table>"


def test_numeric_apostrophe_entity_decoded():
    tool = _tool()
    html = _row(
        [
            "brivekimig1",
            "Trispecific Single Domains (VH-VH-VH&#39;-VH&#39;&#39;-VH&#39;)",
            "Phase-II",
            "Active",
            "TNF/TNFRSF1A",
            "2023",
        ]
    )
    result = tool._parse_search_results(html)
    assert result[0]["format"] == "Trispecific Single Domains (VH-VH-VH'-VH''-VH')"


def test_ampersand_entity_decoded():
    tool = _tool()
    html = _row(
        ["dualab", "Fc&Fab fusion", "Approved", "Active", "CD3D&amp;CD3E", "2020"]
    )
    result = tool._parse_search_results(html)
    assert result[0]["format"] == "Fc&Fab fusion"
    assert result[0]["target"] == "CD3D&CD3E"


def test_nbsp_still_normalized_to_space():
    tool = _tool()
    html = _row(["someab", "Whole&nbsp;mAb", "Approved", "Active", "TNF", "2020"])
    result = tool._parse_search_results(html)
    assert result[0]["format"] == "Whole mAb"


def test_quote_entity_decoded():
    tool = _tool()
    html = _row(
        ["quoteab", '5&#39;-capped &quot;variant&quot;', "Approved", "Active", "TNF", "2020"]
    )
    result = tool._parse_search_results(html)
    assert result[0]["format"] == '5\'-capped "variant"'


def test_plain_text_without_entities_unaffected():
    tool = _tool()
    html = _row(["adalimumab", "Whole mAb", "Approved", "Active", "TNF/TNFA", "1999"])
    result = tool._parse_search_results(html)
    assert result[0]["format"] == "Whole mAb"
    assert result[0]["inn_name"] == "adalimumab"
