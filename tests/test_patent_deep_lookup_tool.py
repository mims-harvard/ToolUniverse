"""Tests for PatentDeepLookupTool --- batch pipeline logic.

Tests the input validation and module selection WITHOUT hitting the API.
"""

import pytest


class TestDeepLookupInputValidation:
    @pytest.fixture
    def tool(self, monkeypatch):
        monkeypatch.setenv("USPTO_API_KEY", "test-key-for-unit-tests")
        from tooluniverse.patent_deep_lookup_tool import PatentDeepLookupTool

        config = {"name": "USPTO_patent_deep_lookup"}
        return PatentDeepLookupTool(config)

    def test_requires_patent_numbers_or_search_query(self, tool):
        """Must provide either patent_numbers or search_query."""
        result = tool.run({"include": ["metadata"]})
        assert result["status"] == "error"

    def test_rejects_empty_patent_numbers(self, tool):
        result = tool.run({"patent_numbers": [], "include": ["metadata"]})
        assert result["status"] == "error"

    def test_rejects_invalid_include_module(self, tool):
        result = tool.run(
            {
                "patent_numbers": ["US9629826B2"],
                "include": ["nonexistent_module"],
            }
        )
        assert result["status"] == "error"
        assert "nonexistent_module" in result["error"]

    def test_default_include_is_metadata(self, tool):
        """If include is not specified, default to ['metadata']."""
        assert tool._validate_include(None) == ["metadata"]

    def test_limit_capped_at_50(self, tool):
        """Maximum 50 patents per request to avoid rate limit abuse."""
        assert tool._apply_limit(100) == 50
        assert tool._apply_limit(10) == 10
        assert tool._apply_limit(None) == 10  # default

    def test_valid_include_modules(self, tool):
        """All valid module names should be accepted."""
        valid = [
            "metadata",
            "assignment",
            "claims",
            "transactions",
            "enriched_citations",
        ]
        for module in valid:
            assert tool._validate_include([module]) == [module]
