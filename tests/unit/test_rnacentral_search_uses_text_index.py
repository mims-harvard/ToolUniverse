"""RNAcentral_search returned the same records for every query.

The tool called ``/api/v1/rna/?query=<text>``. That endpoint has no text search: it
ignores ``query`` and lists the same first page for MALAT1, let-7, U6 and even
"zzzzqqq". Keyword searches now use EBI Search's RNAcentral index; only an
accession (URS...) is fetched from the RNAcentral API.
"""

import sys
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.rnacentral_tool import RNAcentralSearchTool

pytestmark = pytest.mark.unit

EBI_HIT = {
    "hitCount": 2871,
    "entries": [
        {
            "id": "URS0002A146E4_9606",
            "fields": {
                "description": ["Homo sapiens (human) MALAT1"],
                "rna_type": ["lncRNA"],
                "length": ["7472"],
            },
        },
        {"id": "URS0000D5CD72_9606", "fields": {}},
    ],
}


def _run(arguments, payload):
    urls = []

    def fake_get(url, headers=None, timeout=30):
        urls.append(url)
        return payload

    with patch("tooluniverse.rnacentral_tool._http_get", side_effect=fake_get):
        return RNAcentralSearchTool().run(arguments), urls


def test_keyword_search_goes_to_the_ebi_text_index_with_the_query():
    result, urls = _run({"query": "MALAT1", "page_size": 5}, EBI_HIT)
    (url,) = urls
    assert url.startswith("https://www.ebi.ac.uk/ebisearch/ws/rest/rnacentral?")
    params = parse_qs(urlparse(url).query)
    assert params["query"] == ["MALAT1"] and params["size"] == ["5"]
    assert result["endpoint"] == "ebisearch"
    assert result["data"]["count"] == 2871


def test_results_keep_the_documented_shape():
    result, _ = _run({"query": "MALAT1"}, EBI_HIT)
    first, second = result["data"]["results"]
    assert first == {
        "rnacentral_id": "URS0002A146E4_9606",
        "url": "https://rnacentral.org/api/v1/rna/URS0002A146E4/9606",
        "description": "Homo sapiens (human) MALAT1",
        "rna_type": "lncRNA",
        "length": 7472,
    }
    assert second["description"] == "" and second["length"] is None


def test_accession_is_fetched_from_the_rnacentral_record_endpoint():
    record = {"rnacentral_id": "URS0000D5CD72_9606", "length": 8709}
    result, urls = _run({"query": "urs0000d5cd72_9606"}, record)
    assert urls == ["https://rnacentral.org/api/v1/rna/URS0000D5CD72/9606"]
    assert result["data"]["results"] == [record] and result["data"]["count"] == 1


def test_no_hits_is_an_empty_success_not_unrelated_records():
    result, _ = _run({"query": "zzzzqqq"}, {"hitCount": 0, "entries": []})
    assert result["status"] == "success"
    assert result["data"]["results"] == [] and result["data"]["count"] == 0


def test_blank_query_is_an_error_and_makes_no_request():
    result, urls = _run({"query": "  "}, {})
    assert result["status"] == "error" and urls == []
