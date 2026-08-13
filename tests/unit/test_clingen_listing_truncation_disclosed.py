"""Regression guard for Fix-R50: ClinGen listings capped `data` in silence.

`_get_gene_validity`, `_get_dosage_sensitivity` and the actionability listing
each published `data: curations[:100]` beside `total: len(curations)`, with no
flag, no `returned` count and no pagination parameter. Confirmed live:
`ClinGen_get_gene_validity {}` returned `total: 3659` directly above exactly
100 rows, on a tool whose description promises a "comprehensive list" -- a
total that disagrees with the rows printed next to it, which is precisely the
reading error the caller cannot detect without counting.

The cap itself is deliberate (the gene-validity CSV is thousands of rows); what
was missing is saying so.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.clingen_tool import ClinGenTool

pytestmark = pytest.mark.unit


def _csv(n_rows):
    header = (
        '"CLINGEN GENE VALIDITY CURATIONS","","",""\n'
        '"FILE CREATED: 2026-08-13","","",""\n'
        '"GENE SYMBOL","HGNC ID","DISEASE LABEL","CLASSIFICATION"\n'
    )
    rows = "".join(
        f'"GENE{i}","HGNC:{i}","disease {i}","Definitive"\n' for i in range(n_rows)
    )
    return header + rows


def _tool(operation):
    return ClinGenTool({"fields": {"operation": operation}, "parameter": {}})


def _run(operation, n_rows, arguments=None):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.text = _csv(n_rows)
    with patch("tooluniverse.clingen_tool.requests.get", return_value=response):
        return _tool(operation).run(arguments or {})


LISTINGS = ["get_gene_validity", "get_dosage_sensitivity"]


class TestTotalAndRowsAreReconcilable:
    @pytest.mark.parametrize("operation", LISTINGS)
    def test_returned_is_published_beside_total(self, operation):
        result = _run(operation, 3659)

        assert result["total"] == 3659
        assert result["returned"] == 100
        assert result["returned"] == len(result["data"])

    @pytest.mark.parametrize("operation", LISTINGS)
    def test_the_cap_is_flagged_not_left_to_be_counted(self, operation):
        result = _run(operation, 3659)

        assert result["data_truncated"] is True
        assert "100" in result["data_truncation_note"]

    @pytest.mark.parametrize("operation", LISTINGS)
    def test_the_note_points_at_a_way_to_narrow(self, operation):
        """A truncation flag without a remedy just relocates the dead end."""
        result = _run(operation, 3659)

        assert "`gene`" in result["data_truncation_note"]


class TestNoFalseTruncationClaim:
    @pytest.mark.parametrize("operation", LISTINGS)
    def test_a_complete_result_is_not_flagged_truncated(self, operation):
        result = _run(operation, 7)

        assert result["total"] == 7
        assert result["returned"] == 7
        assert "data_truncated" not in result
        assert "data_truncation_note" not in result

    @pytest.mark.parametrize("operation", LISTINGS)
    def test_exactly_at_the_cap_is_not_flagged_truncated(self, operation):
        """Off-by-one: 100 of 100 is complete, not truncated."""
        result = _run(operation, 100)

        assert result["total"] == 100
        assert result["returned"] == 100
        assert "data_truncated" not in result

    @pytest.mark.parametrize("operation", LISTINGS)
    def test_one_past_the_cap_is_flagged(self, operation):
        result = _run(operation, 101)

        assert result["total"] == 101
        assert result["returned"] == 100
        assert result["data_truncated"] is True

    def test_narrowing_by_gene_clears_the_flag(self, ):
        result = _run("get_gene_validity", 3659, {"gene": "GENE7"})

        assert result["total"] == 1
        assert "data_truncated" not in result
