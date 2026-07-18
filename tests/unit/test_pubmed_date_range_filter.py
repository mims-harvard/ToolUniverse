"""Regression guard for Fix-R16E-1: NCBI's esearch silently ignores
mindate/maxdate entirely unless BOTH are present -- confirmed live that
mindate alone (an open-ended "from this date on" range) returned the exact
same unfiltered count as no date params at all, while mindate+maxdate
together correctly filtered. Also confirmed omitting datetype (even with
both dates set) silently changes NCBI's filter basis from publication date
to Entrez date. _build_params now backfills whichever bound is missing and
defaults datetype whenever any date bound is supplied.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.pubmed_tool import PubMedRESTTool

pytestmark = pytest.mark.unit


def _tool():
    return PubMedRESTTool(
        {
            "name": "PubMed_search_articles",
            "fields": {
                "db": "pubmed",
                "retmode": "json",
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            },
        }
    )


def test_mindate_alone_backfills_maxdate_and_datetype():
    tool = _tool()
    params = tool._build_params({"query": "diabetes", "mindate": "2024/01/01"})

    assert params["mindate"] == "2024/01/01"
    assert params["maxdate"] == "3000"
    assert params["datetype"] == "pdat"


def test_maxdate_alone_backfills_mindate_and_datetype():
    tool = _tool()
    params = tool._build_params({"query": "diabetes", "maxdate": "2010/12/31"})

    assert params["maxdate"] == "2010/12/31"
    assert params["mindate"] == "1000"
    assert params["datetype"] == "pdat"


def test_both_dates_present_are_not_overwritten():
    tool = _tool()
    params = tool._build_params(
        {
            "query": "diabetes",
            "mindate": "2020/01/01",
            "maxdate": "2022/01/01",
            "datetype": "edat",
        }
    )

    assert params["mindate"] == "2020/01/01"
    assert params["maxdate"] == "2022/01/01"
    assert params["datetype"] == "edat"


def test_no_date_params_means_no_date_params_added():
    tool = _tool()
    params = tool._build_params({"query": "diabetes"})

    assert "mindate" not in params
    assert "maxdate" not in params
    assert "datetype" not in params
