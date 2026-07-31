"""Regression guard for Fix-R29-1 in clingen_tool.py:
ClinGen_get_variant_classifications fetched the entire ~22MB, ~10k-row
Evidence Repository TSV (classifications/all) with no server-side gene/
variant filter and filtered client-side. Confirmed live this routinely
took 2-5+ minutes and sometimes hung past a 300s client timeout, even for
a gene with zero curated variants -- reproduced independently by 5
separate persona sessions across rounds 28 and 29 (PAH, BRCA1, DMD,
CACNA1C, PTPN22, PKD1). The classifications endpoint (no /all) supports
real server-side gene=/variant= filtering and responds in ~1-2s. The
upstream variant= param resolves to the variant's whole gene rather than
that one variant (confirmed live: variant=CA114360 returned 25 PAH rows),
so a client-side exact-match narrows it back down.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.clingen_tool import ClinGenTool

pytestmark = pytest.mark.unit

_PAH_ITEM = {
    "caid": "CAR:CA114360",
    "variationId": "586",
    "gene": {"label": "PAH"},
    "condition": {"label": "phenylketonuria", "@id": "MONDO:0009861"},
    "hgvs": ["NM_000277.2:c.1A>G", "NM_000277.2(PAH):c.1A>G (p.Met1Val)"],
    "guidelines": [
        {
            "outcome": {"label": "Pathogenic"},
            "agents": [{"affiliation": "Phenylketonuria VCEP"}],
        }
    ],
}

_OTHER_PAH_ITEM = {
    "caid": "CAR:CA229778",
    "variationId": "102844",
    "gene": {"label": "PAH"},
    "condition": {"label": "phenylketonuria", "@id": "MONDO:0009861"},
    "hgvs": ["NM_000277.2:c.806delT", "NM_000277.2(PAH):c.806delT (p.Ile269Thrfs)"],
    "guidelines": [
        {
            "outcome": {"label": "Pathogenic"},
            "agents": [{"affiliation": "Phenylketonuria VCEP"}],
        }
    ],
}


def _tool():
    return ClinGenTool(
        {"fields": {"operation": "get_variant_classifications"}, "parameter": {}}
    )


def _resp(payload):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = payload
    return r


class TestQueriesFilteredEndpoint:
    def test_gene_query_hits_classifications_not_all(self):
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp({"variantInterpretations": [_PAH_ITEM]}),
        ) as mock_get:
            result = tool.run({"gene": "PAH"})

        called_url = mock_get.call_args.args[0]
        assert called_url == "https://erepo.clinicalgenome.org/evrepo/api/classifications"
        assert "/all" not in called_url
        assert mock_get.call_args.kwargs["params"] == {"gene": "PAH"}
        assert result["status"] == "success"
        assert result["total"] == 1
        assert result["data"][0]["HGNC Gene Symbol"] == "PAH"
        assert result["data"][0]["Variation"] == "NM_000277.2(PAH):c.1A>G (p.Met1Val)"

    def test_empty_result_for_uncurated_gene(self):
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp({"variantInterpretations": []}),
        ):
            result = tool.run({"gene": "PTPN22"})

        assert result["status"] == "success"
        assert result["data"] == []
        assert result["total"] == 0
        assert "PTPN22" in result["note"]


class TestRequiresGeneOrVariant:
    def test_no_gene_or_variant_returns_error_without_calling_api(self):
        # Consolidation-time finding: calling classifications with neither
        # gene nor variant is just as unbounded as classifications/all --
        # confirmed live (30s timeout, no response) -- so this must be
        # rejected before any request is made, not just classifications/all.
        tool = _tool()
        with patch("tooluniverse.clingen_tool.requests.get") as mock_get:
            result = tool.run({})

        assert result["status"] == "error"
        assert "gene" in result["error"]
        mock_get.assert_not_called()

    def test_variant_only_is_accepted(self):
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp({"variantInterpretations": [_PAH_ITEM]}),
        ):
            result = tool.run({"variant": "CA114360"})

        assert result["status"] == "success"

    def test_empty_result_for_uncurated_variant_does_not_say_none(self):
        """Fix (PR #339 review): the empty-result guard was widened from
        `if not data and gene:` to `if not data:` to also cover variant-only
        queries, but the note text still hardcoded `for {gene}` -- a
        variant-only query with zero results printed "...for None." since
        `gene` is unset in that branch."""
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp({"variantInterpretations": []}),
        ):
            result = tool.run({"variant": "CA9999999999"})

        assert result["status"] == "success"
        assert result["data"] == []
        assert "None" not in result["note"]
        assert "CA9999999999" in result["note"]


class TestVariantFilterPrecision:
    def test_variant_query_narrowed_to_exact_match(self):
        # The upstream API resolves variant= to the whole gene (confirmed
        # live) -- the tool must narrow back down to the exact variant.
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp(
                {"variantInterpretations": [_PAH_ITEM, _OTHER_PAH_ITEM]}
            ),
        ):
            result = tool.run({"variant": "CA114360"})

        assert result["total"] == 1
        assert result["data"][0]["ClinVar Variation Id"] == "586"
