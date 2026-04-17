"""Tests for DSAPITool -- request construction and response parsing."""

import pytest


class TestDSAPIRequestConstruction:
    @pytest.fixture
    def tool(self, monkeypatch):
        monkeypatch.setenv("USPTO_API_KEY", "test-key-for-unit-tests")
        from tooluniverse.dsapi_tool import DSAPITool

        config = {
            "name": "test_dsapi_tool",
            "api_endpoint": "patent/oa/enriched_cited_reference_metadata/v3/records",
        }
        return DSAPITool(config)

    def test_query_mapped_to_criteria(self, tool, monkeypatch):
        captured = {}

        def fake_post(url, **kwargs):
            captured["data"] = kwargs.get("data", {})

            class FakeResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                def json(self):
                    return {"response": {"numFound": 0, "start": 0, "docs": []}}

            return FakeResponse()

        monkeypatch.setattr(tool.session, "post", fake_post)
        tool.run({"query": "patentApplicationNumber:14966067"})
        assert captured["data"]["criteria"] == "patentApplicationNumber:14966067"

    def test_pagination_mapped_correctly(self, tool, monkeypatch):
        captured = {}

        def fake_post(url, **kwargs):
            captured["data"] = kwargs.get("data", {})

            class FakeResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                def json(self):
                    return {"response": {"numFound": 0, "start": 5, "docs": []}}

            return FakeResponse()

        monkeypatch.setattr(tool.session, "post", fake_post)
        tool.run({"query": "test", "offset": 5, "limit": 10})
        assert captured["data"]["start"] == 5
        assert captured["data"]["rows"] == 10

    def test_default_pagination(self, tool, monkeypatch):
        captured = {}

        def fake_post(url, **kwargs):
            captured["data"] = kwargs.get("data", {})

            class FakeResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                def json(self):
                    return {"response": {"numFound": 0, "start": 0, "docs": []}}

            return FakeResponse()

        monkeypatch.setattr(tool.session, "post", fake_post)
        tool.run({"query": "test"})
        assert captured["data"]["start"] == 0
        assert captured["data"]["rows"] == 25

    def test_success_response_unwraps_correctly(self, tool, monkeypatch):
        fake_docs = [{"id": "abc", "citationCategoryCode": "X"}]

        def fake_post(url, **kwargs):
            class FakeResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                def json(self):
                    return {"response": {"numFound": 1, "start": 0, "docs": fake_docs}}

            return FakeResponse()

        monkeypatch.setattr(tool.session, "post", fake_post)
        result = tool.run({"query": "test"})
        assert result["status"] == "success"
        assert result["data"]["numFound"] == 1
        assert result["data"]["docs"] == fake_docs

    def test_missing_query_returns_error(self, tool):
        result = tool.run({})
        assert result["status"] == "error"
