"""SIDER_get_drug_side_effects must not invent a placebo rate.

The side-effect table on a SIDER drug page has three fixed leading columns --
``Side effect`` | ``Data for drug`` | ``Placebo`` -- followed by one cell per
source label. The parser used to ignore that layout and instead ran

    re.findall(r"([\\d.]+%\\s*-\\s*[\\d.]+%|[\\d.]+%)", row)

over the *whole* ``<tr>``, taking match[0] as the drug frequency and match[1] as
the placebo frequency. Two things in a row also contain percentages:

  * the trailing per-label anchors, whose tooltips read
    ``title="<b>Acitretin</b> : 65%"``, and
  * the MedDRA concept description in the side-effect cell, e.g.
    "Depression affects 15-25% of cancer patients."

So the second ``%`` in the row was never the placebo cell. The result was that
the drug's own rate got copied into ``placebo_frequency`` for every row that had
a rate at all -- 43/43 dapsone rows, 233/233 acitretin rows -- which reads as
"this drug causes the event at exactly the placebo rate", i.e. no drug effect.
It could also invent a drug frequency outright: varenicline / Depression is
labelled ``frequent`` upstream but was reported as ``25%``, a number scraped out
of the prose description of what depression is.

The fix reads each value from its own ``<td>``. An empty placebo cell -- the
common case, since most SIDER labels have no placebo arm -- yields None.

Second, unrelated-looking but same-file defect: ``_fetch_page`` collapsed every
non-200 status to None, so SIDER answering HTTP 500 ("Page unavailable") was
reported as "Drug page not found for ID 5538" -- a transient outage dressed up
as a stable absence, which no agent will retry.

All fixtures below are trimmed from the real pages; no network is used.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tooluniverse.sider_tool import SiderTool


CONFIG = {
    "type": "SiderTool",
    "name": "SIDER_get_drug_side_effects",
    "description": "Get side effects for a drug from SIDER",
    "parameter": {"type": "object", "properties": {}, "required": []},
}


def _page(rows_html):
    """A minimal SIDER drug page carrying the given side-effect rows."""
    return (
        "<h1>Acitretin</h1>\n"
        "<table>\n"
        "<tr><th>Side effect</th><th>Data for drug</th><th>Placebo</th>"
        '<th colspan="6">Labels</th></tr>\n' + rows_html + "\n</table>\n"
        "<h3 class='top'>Indications</h3>\n"
    )


# Trimmed verbatim from http://sideeffects.embl.de/drugs/41317/ (acitretin).
# Drug cell 65%, placebo cell EMPTY, and a trailing label tooltip that also
# says 65% -- the exact shape that produced the fabricated placebo rate.
ROW_EMPTY_PLACEBO = """<tr class="bg1">
<td class="nowrap">
<a href="/se/C0020557/" title="condition of elevated triglyceride concentration in the blood.">Hypertriglyceridaemia <small class='pull-right glyphicon glyphicon-info-sign'></small></a>
</td>
<td style="background-color: #F4573D; border-right: 2px solid #c1c9c7; color: black" class="nowrap">
65%
</td>
<td class="nowrap bg_grey fill fg_grey" style="outline: 2px solid black;">
</td>
<td style="border-left: 2px solid #c1c9c7; background-color: white" class="lCl1">
</td>
<td style="background-color: #F4573D" class="nowrap">
<a class="fill" style="color: #F4573D" href="/labels/bccancer/Acitretinmonograph_1Aug08/C0020557/" title="&lt;b&gt;Acitretin&lt;/b&gt; : 65%">x</a>
</td>
<td style="" class="nowrap bg_grey">
<a class="fill fg_grey" href="/labels/dpdonline/PdLVhg+tG2c=/C0020557/" title="&lt;b&gt;ACITRETIN&lt;/b&gt; : no frequency information">x</a>
</td>
</tr>"""

# Trimmed from http://sideeffects.embl.de/drugs/170361/ (varenicline): a row
# where SIDER really does report a placebo arm, in its own column.
ROW_REAL_PLACEBO = """<tr class="bg0">
<td class="nowrap">
<a href="/se/C0027497/" title="Sensation of unease and discomfort in the upper stomach.">Nausea <small class='pull-right glyphicon glyphicon-info-sign'></small></a>
</td>
<td style="background-color: #F4573D" class="nowrap">
16% - 30%
</td>
<td style="background-color: #F4F43D" class="nowrap">
10%
</td>
<td style="background-color: white" class="lCl1">
</td>
<td style="background-color: #F4573D" class="nowrap">
<a class="fill" href="/labels/fda/xyz/C0027497/" title="&lt;b&gt;Varenicline&lt;/b&gt; : 30%">x</a>
</td>
<td style="background-color: white" class="lCl3">
</td>
</tr>"""

# Also from varenicline: the drug column is the qualitative term "frequent",
# and the only percentage anywhere in the row lives inside the MedDRA concept
# description prose. The old parser reported frequency "25%" for this row.
ROW_QUALITATIVE_WITH_PCT_IN_PROSE = """<tr class="bg1">
<td class="nowrap">
<a href="/se/C0011570/" title="A mental condition marked by ongoing feelings of sadness. Depression affects 15-25% of cancer patients.">Depression <small class='pull-right glyphicon glyphicon-info-sign'></small></a>
</td>
<td style="background-color: #F4F43D; border-right: 2px solid #c1c9c7; color: black" class="nowrap">
frequent
</td>
<td class="nowrap bg_grey fill fg_grey" style="outline: 2px solid black;">
</td>
<td style="border-left: 2px solid #c1c9c7; background-color: white" class="lCl1">
</td>
<td style="background-color: white" class="lCl2">
</td>
<td style="background-color: white" class="lCl3">
</td>
</tr>"""

# Acitretin again: a hyphenated range written "1-10%" with a leading qualifier.
# The old percentage regex could only match the trailing "10%".
ROW_HYPHENATED_RANGE = """<tr class="bg0">
<td class="nowrap">
<a href="/se/C0018681/" title="Pain in the head.">Headache</a>
</td>
<td style="background-color: #F4F43D" class="nowrap">
postmarketing, 1-10%
</td>
<td class="nowrap bg_grey fill fg_grey">
</td>
<td style="background-color: white" class="lCl1">
</td>
</tr>"""


def _tool(status_code=200, body=""):
    """A SiderTool whose HTTP session is a stub -- no network is touched."""
    tool = SiderTool(dict(CONFIG))
    response = MagicMock()
    response.status_code = status_code
    response.text = body
    session = MagicMock()
    session.get.return_value = response
    tool.session = session
    return tool


def _side_effects(rows_html):
    tool = _tool(200, _page(rows_html))
    result = tool.run({"operation": "get_side_effects", "sider_drug_id": "41317"})
    assert result["status"] == "success", result
    return {e["side_effect_name"]: e for e in result["data"]["side_effects"]}


# --- (a) the regression: an empty placebo cell must be null, never a copy -----


def test_empty_placebo_cell_is_null_not_the_drugs_own_rate():
    """The headline bug: placebo_frequency == frequency for every row."""
    entry = _side_effects(ROW_EMPTY_PLACEBO)["Hypertriglyceridaemia"]
    assert entry["frequency"] == "65%"
    assert entry["placebo_frequency"] is None
    # Be explicit about what used to happen.
    assert entry["placebo_frequency"] != entry["frequency"]


def test_label_tooltip_percentage_is_not_mistaken_for_placebo():
    """The trailing anchor's title="<b>Acitretin</b> : 65%" is not a column."""
    entry = _side_effects(ROW_EMPTY_PLACEBO)["Hypertriglyceridaemia"]
    assert entry["placebo_frequency"] is None
    assert entry["meddra_code"] == "C0020557"


def test_every_row_of_a_placebo_free_page_reports_null_placebo():
    entries = _side_effects(
        ROW_EMPTY_PLACEBO
        + "\n"
        + ROW_QUALITATIVE_WITH_PCT_IN_PROSE
        + "\n"
        + ROW_HYPHENATED_RANGE
    )
    assert len(entries) == 3
    assert all(e["placebo_frequency"] is None for e in entries.values()), entries


# --- (b) a genuine placebo value is still read, from its own column -----------


def test_real_placebo_value_is_read_from_the_placebo_column():
    entry = _side_effects(ROW_REAL_PLACEBO)["Nausea"]
    assert entry["frequency"] == "16% - 30%"
    assert entry["placebo_frequency"] == "10%"


def test_mixed_page_keeps_each_rows_own_placebo_state():
    entries = _side_effects(ROW_REAL_PLACEBO + "\n" + ROW_EMPTY_PLACEBO)
    assert entries["Nausea"]["placebo_frequency"] == "10%"
    assert entries["Hypertriglyceridaemia"]["placebo_frequency"] is None


# --- (c) the drug frequency itself comes from its own cell -------------------


def test_percentage_in_the_concept_description_is_not_a_frequency():
    """Varenicline/Depression was reported as 25%; upstream says "frequent"."""
    entry = _side_effects(ROW_QUALITATIVE_WITH_PCT_IN_PROSE)["Depression"]
    assert entry["frequency"] == "frequent"
    assert entry["placebo_frequency"] is None
    # The prose is still returned as the concept description -- it just must not
    # leak into either frequency field.
    assert "15-25%" in entry["description"]
    assert "%" not in entry["frequency"]


def test_hyphenated_range_is_not_truncated_to_its_upper_bound():
    entry = _side_effects(ROW_HYPHENATED_RANGE)["Headache"]
    assert entry["frequency"] == "postmarketing, 1-10%"
    assert entry["placebo_frequency"] is None


def test_side_effect_name_and_description_still_parse():
    entry = _side_effects(ROW_EMPTY_PLACEBO)["Hypertriglyceridaemia"]
    assert entry["meddra_code"] == "C0020557"
    assert "triglyceride" in entry["description"]


# --- (d) HTTP 5xx is an upstream outage, not a missing drug -------------------


def test_http_500_is_reported_as_a_retryable_server_error():
    """SIDER answers 500 with <title>Page unavailable</title> for /drugs/5538/."""
    tool = _tool(500, "<html><title>Page unavailable</title></html>")
    result = tool.run({"operation": "get_side_effects", "sider_drug_id": "5538"})
    assert result["status"] == "error"
    error = result["error"].lower()
    assert "500" in error
    assert "server error" in error
    assert "retried" in error or "retry" in error
    # The whole point: it must not claim the drug is absent from SIDER.
    assert "not found" not in error, result["error"]
    assert result["retryable"] is True
    assert result["http_status"] == 500


def test_http_503_is_also_retryable():
    tool = _tool(503, "")
    result = tool.run({"operation": "get_side_effects", "sider_drug_id": "5538"})
    assert result["status"] == "error"
    assert result["retryable"] is True
    assert "not found" not in result["error"].lower()


def test_http_500_on_the_search_endpoint_is_also_surfaced():
    """The same fix covers name lookups, which hit /searchBox/ first."""
    tool = _tool(500, "")
    result = tool.run({"operation": "get_side_effects", "drug_name": "isotretinoin"})
    assert result["status"] == "error"
    assert result["retryable"] is True
    assert "server error" in result["error"].lower()


# --- (e) a genuine 404 keeps its not-found wording ---------------------------


def test_http_404_still_reports_not_found():
    tool = _tool(404, "")
    result = tool.run({"operation": "get_side_effects", "sider_drug_id": "99999999"})
    assert result["status"] == "error"
    assert "not found" in result["error"].lower()
    assert "99999999" in result["error"]
    assert result.get("retryable") is not True


def test_http_404_on_indications_still_reports_not_found():
    tool = _tool(404, "")
    result = tool.run({"operation": "get_indications", "sider_drug_id": "99999999"})
    assert result["status"] == "error"
    assert "not found" in result["error"].lower()


def test_http_404_on_a_side_effect_page_still_reports_not_found():
    tool = _tool(404, "")
    result = tool.run(
        {"operation": "get_drugs_for_side_effect", "meddra_code": "C9999999"}
    )
    assert result["status"] == "error"
    assert "not found" in result["error"].lower()


# --- (f) shipped config documents the nullable placebo ------------------------


def _sider_config():
    path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "sider_tools.json"
    )
    return {t["name"]: t for t in json.loads(path.read_text())}


@pytest.mark.parametrize("field", ["frequency", "placebo_frequency"])
def test_return_schema_allows_null_frequencies(field):
    tool = _sider_config()["SIDER_get_drug_side_effects"]
    prop = tool["return_schema"]["properties"]["side_effects"]["items"]["properties"][
        field
    ]
    assert "null" in prop["type"], prop


def test_placebo_description_warns_that_null_is_not_zero():
    tool = _sider_config()["SIDER_get_drug_side_effects"]
    text = tool["return_schema"]["properties"]["side_effects"]["items"]["properties"][
        "placebo_frequency"
    ]["description"].lower()
    assert "null" in text
    assert "placebo" in text
    # It must say what null means, since null is now the majority answer.
    assert "zero" in text or "not" in text
