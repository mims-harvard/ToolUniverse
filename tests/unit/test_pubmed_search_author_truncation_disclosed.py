"""PubMed_search_articles must disclose when it truncated the author list.

Regression for Fix-R28B. ``_fetch_summaries`` cuts every author list to the
first 5 names to bound the payload, but reported nothing about the cut. An
article that genuinely has 5 authors and an article whose 9 authors were
trimmed to 5 were therefore byte-indistinguishable in the response, so a caller
assembling a bibliography silently produced a wrong author list.

Verified live before the fix: PMID 41541570 really has 5 authors while PMID
34202135 has 9 (efetch and esummary agree; the sibling PubMed_get_article
returns all 9). The full count is present in the very same esummary payload the
truncation is applied to, so `author_count` is read from real upstream data, not
invented.

The fix is additive: `authors` still holds the first 5 names, and
`author_count` / `authors_truncated` are new sibling keys following the
`intervention_count` / `interventions_truncated` house style already used by
ClinicalTrials_search_studies.

All assertions run against synthetic esummary payloads -- no network.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import tooluniverse  # noqa: E402
from tooluniverse.pubmed_tool import PubMedRESTTool  # noqa: E402

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"


def _tool():
    return PubMedRESTTool(
        {
            "name": "PubMed_search_articles",
            "type": "PubMedRESTTool",
            "fields": {
                "db": "pubmed",
                "retmode": "json",
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            },
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
    )


def _record(pmid, author_names):
    return {
        "uid": pmid,
        "pubdate": "2021 Jun 25",
        "title": "Re-Irradiation for Head and Neck Cancer",
        "authors": [{"name": n} for n in author_names],
        "fulljournalname": "Cancers",
        "pubtype": ["Journal Article"],
        "elocationid": "",
        "articleids": [],
    }


def _summarize(records):
    """Run synthetic esummary records through _fetch_summaries."""
    tool = _tool()
    uids = [r["uid"] for r in records]
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "result": {"uids": uids, **{r["uid"]: r for r in records}}
    }

    with (
        patch.object(tool, "_enforce_rate_limit"),
        patch("tooluniverse.pubmed_tool.request_with_retry", return_value=resp),
    ):
        result = tool._fetch_summaries(uids)

    assert result["status"] == "success"
    return result["data"]


# The exact pair from the live reproduction: same query, same page, one
# complete list and one truncated list that used to look identical.
FIVE_AUTHORS = ["Bornedal S", "Lee J", "Melhus T", "Embring A", "Onjukka E"]
NINE_AUTHORS = [
    "Embring A",
    "Onjukka E",
    "Mercke C",
    "Lax I",
    "Berglund A",
    "Bornedal S",
    "Wennberg B",
    "Dalqvist E",
    "Friesland S",
]


def test_truncated_and_complete_five_author_lists_are_distinguishable():
    """The whole point: two five-name arrays, only one of which is complete."""
    complete, truncated = _summarize(
        [_record("41541570", FIVE_AUTHORS), _record("34202135", NINE_AUTHORS)]
    )

    # Both still show exactly five names -- the payload bound is unchanged.
    assert complete["authors"] == FIVE_AUTHORS
    assert truncated["authors"] == NINE_AUTHORS[:5]
    assert len(complete["authors"]) == len(truncated["authors"]) == 5

    # ...but they are no longer indistinguishable.
    assert complete["author_count"] == 5
    assert complete["authors_truncated"] is False
    assert truncated["author_count"] == 9
    assert truncated["authors_truncated"] is True


def test_author_count_is_the_upstream_total_not_the_shown_length():
    article = _summarize([_record("1", [f"Author {i}" for i in range(19)])])[0]

    assert len(article["authors"]) == 5
    assert article["author_count"] == 19
    assert article["authors_truncated"] is True


def test_short_author_lists_are_marked_complete():
    article = _summarize(
        [_record("25059767", ["Benhaim C", "Lapeyre M", "Thariat J"])]
    )[0]

    assert article["authors"] == ["Benhaim C", "Lapeyre M", "Thariat J"]
    assert article["author_count"] == 3
    assert article["authors_truncated"] is False


def test_record_with_no_authors_reports_zero_and_not_truncated():
    """Book/collective records carry no `authors` key at all."""
    record = _record("13678080", [])
    del record["authors"]

    article = _summarize([record])[0]

    assert article["authors"] == []
    assert article["author_count"] == 0
    assert article["authors_truncated"] is False


def test_existing_article_fields_are_untouched():
    """The change is additive -- nothing previously returned was removed."""
    article = _summarize([_record("34202135", NINE_AUTHORS)])[0]

    for key in (
        "pmid",
        "title",
        "authors",
        "journal",
        "pub_date",
        "pub_year",
        "doi",
        "pmcid",
        "article_type",
        "url",
        "doi_url",
        "pmc_url",
    ):
        assert key in article, f"previously-returned key {key!r} disappeared"


def test_config_documents_the_new_disclosure_fields():
    configs = json.loads((DATA_DIR / "pubmed_tools.json").read_text())
    search = next(c for c in configs if c["name"] == "PubMed_search_articles")
    props = search["return_schema"]["oneOf"][0]["items"]["properties"]

    assert props["author_count"]["type"] == "integer"
    assert props["authors_truncated"]["type"] == "boolean"
    # `authors` must warn that it is a truncated view.
    assert "truncated" in props["authors"]["description"].lower()
