"""Tests for PatentResolverTool -- patent number normalization."""

import pytest


class TestNormalizePatentNumber:
    @pytest.fixture
    def normalize(self):
        from tooluniverse.patent_resolver_tool import _normalize_patent_number

        return _normalize_patent_number

    def test_grant_with_country_and_kind_code(self, normalize):
        num, kind = normalize("US9629826B2")
        assert num == "9629826"
        assert kind == "grant"

    def test_grant_with_spaces_and_commas(self, normalize):
        num, kind = normalize("US 9,629,826 B2")
        assert num == "9629826"
        assert kind == "grant"

    def test_bare_grant_number(self, normalize):
        num, kind = normalize("9629826")
        assert num == "9629826"
        assert kind == "grant"

    def test_application_number_with_slash(self, normalize):
        num, kind = normalize("14/966,067")
        assert num == "14966067"
        assert kind == "application"

    def test_publication_number(self, normalize):
        num, kind = normalize("US20160106718A1")
        assert num == "US20160106718A1"
        assert kind == "publication"

    def test_eight_digit_ambiguous(self, normalize):
        num, kind = normalize("14966067")
        assert num == "14966067"
        assert kind == "ambiguous"

    def test_grant_b1_kind_code(self, normalize):
        num, kind = normalize("US10844125B1")
        assert num == "10844125"
        assert kind == "grant"

    def test_strips_whitespace(self, normalize):
        num, kind = normalize("  US9629826B2  ")
        assert num == "9629826"
        assert kind == "grant"
