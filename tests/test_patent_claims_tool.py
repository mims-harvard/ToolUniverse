"""Tests for PatentClaimsTool --- XML claim parsing logic.

Tests the _parse_claims_from_xml helper with sample XML.
No network calls needed --- pure XML processing.
"""

import pytest

# Sample grant XML fragment (same structure as real USPTO grant XML)
SAMPLE_CLAIMS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<us-patent-grant>
<claims id="claims">
<claim id="CLM-00001" num="1">
<claim-text>1. A method of treating a disease comprising administering a compound.</claim-text>
</claim>
<claim id="CLM-00002" num="2">
<claim-text>2. The method of claim 1, wherein the compound is aspirin.</claim-text>
</claim>
<claim id="CLM-00003" num="3">
<claim-text>3. A system for analyzing data comprising a processor and a memory.</claim-text>
</claim>
</claims>
</us-patent-grant>
"""


class TestParseClaimsFromXml:
    @pytest.fixture
    def parse(self):
        from tooluniverse.patent_claims_tool import _parse_claims_from_xml

        return _parse_claims_from_xml

    def test_extracts_all_claims(self, parse):
        claims = parse(SAMPLE_CLAIMS_XML)
        assert len(claims) == 3

    def test_claim_numbers_are_sequential(self, parse):
        claims = parse(SAMPLE_CLAIMS_XML)
        numbers = [c["claim_number"] for c in claims]
        assert numbers == [1, 2, 3]

    def test_independent_claim_detected(self, parse):
        claims = parse(SAMPLE_CLAIMS_XML)
        assert claims[0]["is_independent"] is True
        assert claims[0]["dependent_on"] is None

    def test_dependent_claim_detected(self, parse):
        claims = parse(SAMPLE_CLAIMS_XML)
        assert claims[1]["is_independent"] is False
        assert claims[1]["dependent_on"] == 1

    def test_second_independent_claim(self, parse):
        claims = parse(SAMPLE_CLAIMS_XML)
        assert claims[2]["is_independent"] is True
        assert claims[2]["dependent_on"] is None

    def test_claim_text_is_full(self, parse):
        claims = parse(SAMPLE_CLAIMS_XML)
        assert "treating a disease" in claims[0]["claim_text"]

    def test_empty_xml_returns_empty_list(self, parse):
        claims = parse("<us-patent-grant></us-patent-grant>")
        assert claims == []

    def test_claim_id_preserved(self, parse):
        claims = parse(SAMPLE_CLAIMS_XML)
        assert claims[0]["claim_id"] == "CLM-00001"
