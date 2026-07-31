"""ENCODE searches answered a zero-result query with another species' data.

ENCODE returns HTTP 404 carrying a valid body ({"total": 0, "@graph": [],
"notification": "No results found"}) when a facet combination matches nothing.
``_encode_search`` treated that as a transport error, and callers reacted in one
of two wrong ways:

* the histone / chromatin-accessibility / RNA-seq searches retried with the
  organism filter deleted, so "H3K4me3 in human midbrain" -- which ENCODE does
  not have -- came back as four *Mus musculus* embryo experiments while
  metadata still said organism "Homo sapiens". The bogus-value control was
  arithmetic: Homo sapiens 431 + Mus musculus 97 = 528, exactly what a
  nonsense organism returned;
* five other searches surfaced the same 404 as "API HTTP error: 404", turning a
  legitimately empty answer into a fake outage.

Both symptoms come from the one misread status code.
"""

from unittest.mock import patch

import pytest

from tooluniverse.epigenomics_tool import EpigenomicsTool

_ORGANISM_KEY = "replicates.library.biosample.organism.scientific_name"


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


_EMPTY_404 = {"total": 0, "@graph": [], "notification": "No results found"}


def _make(endpoint):
    return EpigenomicsTool(
        {
            "name": f"ENCODE_{endpoint}",
            "type": "EpigenomicsTool",
            "fields": {"endpoint": endpoint},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def test_encode_search_reads_the_404_body_as_zero_results():
    tool = _make("histone_chipseq")
    with patch(
        "tooluniverse.epigenomics_tool._request_with_backoff",
        return_value=_FakeResponse(404, _EMPTY_404),
    ):
        raw = tool._encode_search({"type": "Experiment"})

    assert raw["total"] == 0
    assert raw["@graph"] == []


def test_a_real_404_without_a_body_still_raises():
    tool = _make("histone_chipseq")
    with patch(
        "tooluniverse.epigenomics_tool._request_with_backoff",
        return_value=_FakeResponse(404, None),
    ):
        with pytest.raises(RuntimeError):
            tool._encode_search({"type": "Experiment"})


@pytest.mark.parametrize(
    "endpoint,arguments",
    [
        (
            "histone_chipseq",
            {"histone_mark": "H3K4me3", "biosample_term_name": "midbrain"},
        ),
        (
            "chromatin_accessibility",
            {"biosample_term_name": "midbrain"},
        ),
    ],
)
def test_empty_result_never_retries_without_the_organism_filter(endpoint, arguments):
    tool = _make(endpoint)
    calls = []

    def fake_request(url, params=None, **kwargs):
        calls.append(dict(params or {}))
        return _FakeResponse(404, _EMPTY_404)

    with patch(
        "tooluniverse.epigenomics_tool._request_with_backoff",
        side_effect=fake_request,
    ):
        result = tool.run(dict(arguments, organism="Homo sapiens", limit=4))

    assert len(calls) == 1, "the organism filter must not be dropped and retried"
    assert calls[0][_ORGANISM_KEY] == "Homo sapiens"

    assert result["status"] == "success"
    assert result["metadata"]["total"] == 0
    assert result["metadata"]["organism"] == "Homo sapiens"
    assert result["data"] == []


def test_empty_result_is_not_reported_as_an_api_outage():
    tool = _make("encode_microrna")
    with patch(
        "tooluniverse.epigenomics_tool._request_with_backoff",
        return_value=_FakeResponse(404, _EMPTY_404),
    ):
        result = tool.run({"biosample_term_name": "liver", "limit": 2})

    assert result["status"] == "success"
    assert "404" not in str(result)
    assert result["data"]["total"] == 0


def test_non_empty_results_still_flow_through():
    tool = _make("histone_chipseq")
    payload = {
        "total": 1,
        "@graph": [
            {
                "accession": "ENCSR914QOK",
                "target": {"label": "H3K27me3"},
                "lab": {"title": "Some Lab"},
                "biosample_summary": "Homo sapiens K562",
            }
        ],
    }
    with patch(
        "tooluniverse.epigenomics_tool._request_with_backoff",
        return_value=_FakeResponse(200, payload),
    ):
        result = tool.run(
            {"histone_mark": "H3K27me3", "biosample_term_name": "K562", "limit": 5}
        )

    assert result["status"] == "success"
    accessions = [e["accession"] for e in result["data"]["experiments"]]
    assert accessions == ["ENCSR914QOK"]
