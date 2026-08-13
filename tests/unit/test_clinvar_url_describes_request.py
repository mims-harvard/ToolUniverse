"""Regression guard for Fix-R56-3: ClinVar published a `url` that
described no request.

``ClinVar_get_clinical_significance {"variant_id": "977673"}`` returned
``url: "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"`` --
the bare endpoint, byte-identical for every variant and an error when
replayed. The query lived in ``params=``, which requests keeps out of the
pre-request URL string; ``response.url`` is the URL actually sent.

Confirmed live after the fix: variant 977673 and 393995 now yield
distinct, replayable URLs ending ``?db=clinvar&id=<variant>&retmode=json``.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.clinvar_tool import ClinVarRESTTool

pytestmark = pytest.mark.unit

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def _tool():
    return ClinVarRESTTool({"name": "clinvar_test", "type": "ClinVarRESTTool"})


def _resp(sent_url):
    r = MagicMock()
    r.status_code = 200
    r.url = sent_url
    r.headers = {"content-type": "application/json"}
    r.json.return_value = {"result": {}}
    r.text = ""
    r.raise_for_status.return_value = None
    return r


class TestPublishedUrl:
    def test_url_carries_the_query_actually_sent(self):
        tool = _tool()
        sent = f"{BASE}esummary.fcgi?db=clinvar&id=977673&retmode=json"

        with patch.object(tool.session, "get", return_value=_resp(sent)):
            result = tool._make_request(
                "esummary.fcgi",
                params={"db": "clinvar", "id": "977673", "retmode": "json"},
            )

        assert result["url"] == sent
        assert "id=977673" in result["url"]

    def test_two_variants_do_not_share_one_url(self):
        tool = _tool()
        urls = []
        for variant in ("977673", "393995"):
            sent = f"{BASE}esummary.fcgi?db=clinvar&id={variant}&retmode=json"
            with patch.object(tool.session, "get", return_value=_resp(sent)):
                urls.append(
                    tool._make_request(
                        "esummary.fcgi",
                        params={"db": "clinvar", "id": variant, "retmode": "json"},
                    )["url"]
                )

        assert urls[0] != urls[1]
