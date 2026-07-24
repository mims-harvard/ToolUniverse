"""Unit test: ClinVar_search_variants must handle a dbSNP rsID query.

Regression: an rsID passed as `query` (e.g. rs4244285, the CYP2C19*2 variant)
was aliased to `condition` and searched as a DISEASE term ('rs4244285[dis]'),
silently returning 0 -- but ClinVar's free-text index matches a bare rsID
(term=rs4244285 -> 37 records). That false-empty broke the standard
pharmacogenomics chain rsID -> ClinVar clinical significance. rsIDs are now
routed to a bare-term search.
"""
from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def _term_for(arguments):
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        tool.run(arguments)
    return mock_request.call_args[0][1]["term"]


def test_rsid_query_becomes_bare_term_not_disease_field():
    term = _term_for({"query": "rs4244285"})
    assert "rs4244285" in term
    assert "[dis]" not in term  # must NOT be searched as a disease


def test_explicit_rsid_param_supported():
    term = _term_for({"rsid": "rs4244285"})
    assert "rs4244285" in term
    assert "[dis]" not in term


def test_rsid_combines_with_gene():
    term = _term_for({"gene": "CYP2C19", "rsid": "rs4244285"})
    assert "CYP2C19[gene]" in term
    assert "rs4244285" in term
    assert " AND " in term


def test_non_rsid_query_still_uses_disease_field():
    term = _term_for({"query": "Rett syndrome"})
    assert '"Rett syndrome"[dis]' in term


def test_case_insensitive_rsid_detection():
    term = _term_for({"query": "RS4244285"})
    assert "[dis]" not in term
    assert "RS4244285" in term
