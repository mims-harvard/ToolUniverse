"""Unit test: Alliance phenotype statements must be stripped of HTML markup.

Regression: ZFIN_get_gene_phenotypes (AllianceGenomeTool) passed the API's
phenotypeStatement through raw, so italicised gene symbols leaked literal tags
into the JSON, e.g. 'anatomical structure <i>acta1a</i> expression decreased
amount'. A caller rendering the field got the tags verbatim.
"""
import pytest

from tooluniverse.alliance_genome_tool import _strip_html


@pytest.mark.unit
def test_strip_italic_tags():
    assert (
        _strip_html(
            "anatomical structure <i>acta1a</i> expression decreased amount, abnormal"
        )
        == "anatomical structure acta1a expression decreased amount, abnormal"
    )


@pytest.mark.unit
def test_unescape_entities_and_strip():
    # Entity-encoded tags are unescaped then stripped (no markup survives).
    assert _strip_html("gene &lt;i&gt;x&lt;/i&gt; up") == "gene x up"
    assert _strip_html("a &amp; b <sup>2</sup>") == "a & b 2"


@pytest.mark.unit
def test_non_string_passthrough():
    assert _strip_html(None) is None
    assert _strip_html(123) == 123


@pytest.mark.unit
def test_plain_text_unchanged():
    assert _strip_html("no markup here") == "no markup here"
