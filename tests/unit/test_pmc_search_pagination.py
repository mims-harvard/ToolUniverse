from tooluniverse.pmc_tool import PMCTool


class _Response:
    def __init__(self, *, payload=None, text=""):
        self._payload = payload
        self.text = text
        self.status_code = 200

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def test_pmc_forwards_offset_and_repeats_exact_page_envelope(monkeypatch):
    calls = []
    summary = """<eSummaryResult>
      <DocSum><Id>12</Id><Item Name="Title" Type="String">Paper 12</Item></DocSum>
      <DocSum><Id>13</Id><Item Name="Title" Type="String">Paper 13</Item></DocSum>
    </eSummaryResult>"""

    def fake_request(session, method, url, **kwargs):
        calls.append((url, kwargs.get("params", {})))
        if url.endswith("/esearch.fcgi"):
            return _Response(
                payload={
                    "esearchresult": {
                        "count": "5",
                        "idlist": ["12", "13"],
                    }
                }
            )
        return _Response(text=summary)

    monkeypatch.setattr("tooluniverse.pmc_tool.request_with_retry", fake_request)
    result = PMCTool({"name": "PMC_search_papers"})._search(
        "cancer", limit=2, offset=2
    )

    assert calls[0][1]["retstart"] == 2
    assert [row["pmc_id"] for row in result] == ["PMC12", "PMC13"]
    page = result[0]["search_pagination"]
    assert page == result[1]["search_pagination"]
    assert page["total_results"] == 5
    assert page["returned"] == 2
    assert page["has_more"] is True
    assert page["next_offset"] == 4


def test_pmc_tail_page_terminates(monkeypatch):
    summary = """<eSummaryResult>
      <DocSum><Id>14</Id><Item Name="Title" Type="String">Paper 14</Item></DocSum>
    </eSummaryResult>"""

    def fake_request(session, method, url, **kwargs):
        if url.endswith("/esearch.fcgi"):
            assert kwargs["params"]["retmax"] == 1
            return _Response(
                payload={"esearchresult": {"count": "10001", "idlist": ["14"]}}
            )
        return _Response(text=summary)

    monkeypatch.setattr("tooluniverse.pmc_tool.request_with_retry", fake_request)
    result = PMCTool({"name": "PMC_search_papers"})._search(
        "cancer", limit=3, offset=9998
    )

    page = result[0]["search_pagination"]
    assert page["returned"] == 1
    assert page["total_results"] == 10001
    assert page["retrievable_results"] == 9999
    assert page["has_more"] is False
    assert page["next_offset"] is None
    assert page["database_result_complete"] is False
    assert page["retrieval_limit_reached"] is True


def test_pmc_rejects_offset_beyond_upstream_window(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.pmc_tool.request_with_retry",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no request")),
    )

    result = PMCTool({"name": "PMC_search_papers"})._search(
        "cancer", limit=3, offset=9999
    )

    assert result[0]["retryable"] is False
    assert "9,999-result retrieval window" in result[0]["error"]
