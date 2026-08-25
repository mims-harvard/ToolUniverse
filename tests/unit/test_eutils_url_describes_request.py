"""Regression guard for Fix-R57-3: the shared NCBI E-utilities base published a
``url`` that described no request.

The query lives in ``params=``, so echoing the endpoint constant produced a
string identical for every call and an error when replayed. Confirmed live for
four tools across three modules, all routed through
``NCBIEUtilsTool._make_request``:

    geo_search_datasets     -> url ".../eutils/esearch.fcgi"
    geo_get_dataset_info    -> url ".../eutils/esummary.fcgi"
    dbsnp_search_by_gene    -> url ".../eutils/esearch.fcgi"
    NCBI_search_nucleotide  -> url ".../eutils/esearch.fcgi"

and ``curl .../eutils/esearch.fcgi`` returns
``<ERROR>Empty term and query_key - nothing todo</ERROR>``.

Same class as the ClinVar fix in round 56. E-utilities takes no credentials on
these paths, so publishing the resolved URI leaks nothing; a repo-wide grep for
``api_key`` across ncbi_eutils/geo/dbsnp/ncbi_sra/ncbi_nucleotide finds none.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.ncbi_eutils_tool import NCBIEUtilsTool

pytestmark = pytest.mark.unit

SENT = (
    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    "?db=gds&retmode=json&term=psoriasis+keratinocyte"
)
BARE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


def _tool():
    tool = NCBIEUtilsTool({"name": "eutils", "type": "NCBIEUtilsTool"})
    tool.min_interval = 0  # keep the rate limiter out of the test's runtime
    return tool


def _resp(url=SENT, status=200):
    r = MagicMock()
    r.url = url
    r.status_code = status
    r.headers = {"content-type": "application/json"}
    r.json.return_value = {"esearchresult": {"idlist": ["1"]}}
    r.raise_for_status.return_value = None
    return r


class TestPublishedUrlDescribesTheRequest:
    def test_success_publishes_the_uri_that_was_sent(self):
        tool = _tool()
        with patch.object(tool.session, "get", return_value=_resp()):
            result = tool._make_request("/esearch.fcgi", {"db": "gds"})

        assert result["status"] == "success"
        assert result["url"] == SENT
        assert result["url"] != BARE

    def test_http_error_publishes_the_uri_that_was_sent(self):
        error = requests.exceptions.HTTPError("400")
        error.response = _resp(status=400)
        tool = _tool()
        with patch.object(tool.session, "get", side_effect=error):
            result = tool._make_request("/esearch.fcgi", {"db": "gds"})

        assert result["status"] == "error"
        assert result["url"] == SENT

    def test_request_exception_publishes_the_uri_that_was_sent(self):
        error = requests.exceptions.ConnectionError("boom")
        error.request = MagicMock(url=SENT)
        tool = _tool()
        with patch.object(tool.session, "get", side_effect=error):
            result = tool._make_request("/esearch.fcgi", {"db": "gds"})

        assert result["status"] == "error"
        assert result["url"] == SENT

    def test_a_stub_without_a_string_url_falls_back_to_the_endpoint(self):
        """A MagicMock's `.url` is a MagicMock; it must never reach the payload."""
        response = _resp()
        response.url = MagicMock()
        tool = _tool()
        with patch.object(tool.session, "get", return_value=response):
            result = tool._make_request("/esearch.fcgi", {"db": "gds"})

        assert result["url"] == BARE

    def test_the_query_is_visible_in_the_published_url(self):
        """The point of the fix: two different queries must be distinguishable."""
        tool = _tool()
        urls = []
        for term in ("psoriasis", "dermatitis"):
            sent = f"{BARE}?db=gds&term={term}"
            with patch.object(tool.session, "get", return_value=_resp(url=sent)):
                urls.append(tool._make_request("/esearch.fcgi", {"term": term})["url"])

        assert urls[0] != urls[1]
        assert "psoriasis" in urls[0] and "dermatitis" in urls[1]
