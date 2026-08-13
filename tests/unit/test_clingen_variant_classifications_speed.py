"""Regression guard for Fix-R29-1 in clingen_tool.py:
ClinGen_get_variant_classifications fetched the entire ~22MB, ~10k-row
Evidence Repository TSV (classifications/all) with no server-side gene/
variant filter and filtered client-side. Confirmed live this routinely
took 2-5+ minutes and sometimes hung past a 300s client timeout, even for
a gene with zero curated variants -- reproduced independently by 5
separate persona sessions across rounds 28 and 29 (PAH, BRCA1, DMD,
CACNA1C, PTPN22, PKD1). The classifications endpoint (no /all) supports
real server-side filtering and responds in ~1-2s.

Fix-R50 corrects what "real server-side filtering" means here. Re-probed
live, the endpoint implements `gene`, `caid`, `hgvs` and `variationId` --
but NOT `variant`, which it accepts and ignores. The earlier reading
("variant= resolves to the variant's whole gene") was wrong: a bogus
`variant=ZZZNOTAVARIANT` returns the same first rows as sending no filter
at all, so the request was really an unfiltered listing of the whole
repository. Combined with an unstated `matchLimit` (which pages at 25),
that produced two defects this module now guards:

  * `total` counted one page, not the query -- PAH reported 25 against
    817 curated classifications, a 32x understatement
  * the client-side narrowing ran over an arbitrary 25-row page, so
    CAID CA16020993 (PAH c.1315+1G>T, classified Likely Pathogenic by
    the Phenylketonuria VCEP, row 401 of 817) was reported absent with
    the confident explanation "Not all genes have active VCEPs"
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
        assert mock_get.call_args.kwargs["params"] == {"gene": "PAH", "matchLimit": 5000}
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
    """Fix-R50: the variant filter has to be applied by the server.

    `variant=` is not an endpoint parameter, so the old client-side narrowing
    could only ever see whatever page the unfiltered listing happened to
    return. Each test below asserts the request names a parameter the endpoint
    actually implements -- reverting to `params["variant"] = variant` fails
    every one of them.
    """

    @staticmethod
    def _params_for(variant):
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp({"variantInterpretations": [_PAH_ITEM]}),
        ) as mock_get:
            _tool().run({"variant": variant})
        return mock_get.call_args.kwargs["params"]

    def test_caid_is_sent_as_caid(self):
        assert self._params_for("CA114360")["caid"] == "CA114360"

    def test_prefixed_caid_is_normalised(self):
        assert self._params_for("CAR:CA114360")["caid"] == "CA114360"

    def test_clinvar_variation_id_is_sent_as_variation_id(self):
        assert self._params_for("586")["variationId"] == "586"

    def test_hgvs_and_protein_change_are_sent_as_hgvs(self):
        assert self._params_for("NM_000277.3:c.1315+1G>T")["hgvs"] == (
            "NM_000277.3:c.1315+1G>T"
        )
        assert self._params_for("p.Arg408Trp")["hgvs"] == "p.Arg408Trp"

    def test_the_ignored_variant_param_is_never_sent(self):
        for variant in ("CA114360", "586", "p.Arg408Trp"):
            assert "variant" not in self._params_for(variant)

    def test_server_filtered_result_is_published_verbatim(self):
        """No client-side narrowing left: what the server matched is the answer."""
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp({"variantInterpretations": [_PAH_ITEM]}),
        ):
            result = tool.run({"variant": "CA114360"})

        assert result["total"] == 1
        assert result["data"][0]["ClinVar Variation Id"] == "586"


class TestTotalCountsTheQueryNotThePage:
    """The 32x understatement: `total` must describe the query, not one page."""

    @staticmethod
    def _many(n):
        return {
            "variantInterpretations": [
                dict(_PAH_ITEM, caid=f"CAR:CA{i}", variationId=str(i))
                for i in range(n)
            ]
        }

    def test_match_limit_is_stated_so_the_page_is_not_25(self):
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp(self._many(1)),
        ) as mock_get:
            tool.run({"gene": "PAH"})

        assert mock_get.call_args.kwargs["params"]["matchLimit"] == 5000

    def test_total_is_the_full_count_not_the_published_slice(self):
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp(self._many(817)),
        ):
            result = tool.run({"gene": "PAH"})

        assert result["total"] == 817
        assert result["returned"] == 100
        assert len(result["data"]) == 100

    def test_the_gap_between_total_and_rows_is_disclosed(self):
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp(self._many(817)),
        ):
            result = tool.run({"gene": "PAH"})

        assert result["truncated"] is True
        assert "817" not in result["truncation_note"]  # not a hardcoded number
        assert "100" in result["truncation_note"]

    def test_no_truncation_claim_when_everything_fits(self):
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp(self._many(3)),
        ):
            result = tool.run({"gene": "PAH"})

        assert result["total"] == 3
        assert result["returned"] == 3
        assert result["truncated"] is False
        assert "truncation_note" not in result

    def test_filling_the_request_cap_marks_total_a_lower_bound(self):
        """`hgvs` matches on substring, so a short fragment can fill the cap."""
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp(self._many(5000)),
        ):
            result = tool.run({"gene": "PAH"})

        assert result["truncated"] is True
        assert "lower bound" in result["truncation_note"]


class TestAbsentVariantIsNotBlamedOnTheGene:
    def test_missing_variant_note_does_not_claim_the_vcep_is_absent(self):
        """The old note explained a paging artefact with a false cause.

        CA16020993 is classified by the Phenylketonuria VCEP, yet a
        variant-only query answered "Not all genes have active VCEPs".
        """
        tool = _tool()
        with patch(
            "tooluniverse.clingen_tool.requests.get",
            return_value=_resp({"variantInterpretations": []}),
        ):
            result = tool.run({"variant": "CA16020993"})

        note = result["note"]
        assert "VCEP" not in note
        assert "caid" in note
        assert "server-side" in note
