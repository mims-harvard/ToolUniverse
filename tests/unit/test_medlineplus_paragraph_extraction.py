"""Regression guard for Fix-R26C-1 in MedlinePlusRESTTool._extract_text_content.

Confirmed live against MedlinePlus's XML-fallback response for FMR1.json
(xmltodict-parsed): a <html:p> paragraph containing a nested inline tag
(e.g. <html:i>FMR1</html:i>) parses to a dict whose "#text" has the tag's
own text dropped, leaving a double-space gap ("The  gene provides...").
A paragraph WITHOUT any nested tag parses as a bare string instead of a
dict, and the previous `isinstance(p, dict)` filter silently discarded it
entirely -- for FMR1 this dropped the whole middle paragraph of the
"function" description. Also covers the real-JSON path, where "html" is
a raw HTML string (e.g. "<p>The <i>FMR1</i> gene...</p>") and the previous
code only stripped <p>/</p>, leaving <i>/</i> as literal text.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.medlineplus_tool import MedlinePlusRESTTool

pytestmark = pytest.mark.unit


def _tool():
    return MedlinePlusRESTTool.__new__(MedlinePlusRESTTool)


class TestXmlFallbackParagraphExtraction:
    def test_inline_tag_text_reinserted_not_dropped(self):
        text_item = {
            "text": {
                "html": {
                    "html:p": [
                        {"html:i": "FMR1", "#text": "The  gene provides instructions."}
                    ]
                }
            }
        }
        result = _tool()._extract_text_content(text_item)
        assert result == "The FMR1 gene provides instructions."

    def test_bare_string_paragraph_not_dropped(self):
        # A paragraph with no nested inline tag parses as a plain string,
        # not a dict -- the old `isinstance(p, dict)` filter silently
        # discarded these entirely.
        text_item = {
            "text": {
                "html": {
                    "html:p": [
                        {"html:i": "FMR1", "#text": "The  gene provides FMRP."},
                        "Researchers believe FMRP acts as a shuttle.",
                    ]
                }
            }
        }
        result = _tool()._extract_text_content(text_item)
        assert "Researchers believe FMRP acts as a shuttle." in result
        assert result == (
            "The FMR1 gene provides FMRP.\nResearchers believe FMRP acts as a shuttle."
        )

    def test_single_paragraph_not_wrapped_in_list_still_works(self):
        text_item = {"text": {"html": {"html:p": "Just one paragraph."}}}
        result = _tool()._extract_text_content(text_item)
        assert result == "Just one paragraph."


class TestRealJsonHtmlStringExtraction:
    def test_inline_tags_stripped_not_left_literal(self):
        html = "<p>The <i>FMR1</i> gene provides instructions for making FMRP.</p>"
        text_item = {"text": {"html": html}}
        result = _tool()._extract_text_content(text_item)
        assert result == "The FMR1 gene provides instructions for making FMRP."
        assert "<i>" not in result

    def test_multiple_paragraphs_join_with_newline(self):
        html = "<p>First paragraph.</p><p>Second paragraph.</p>"
        text_item = {"text": {"html": html}}
        result = _tool()._extract_text_content(text_item)
        assert result == "First paragraph.\nSecond paragraph."
