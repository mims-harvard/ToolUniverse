"""Regression guard for Fix-R6C-1: ClinVar_search_variants's
clinical_significance filter used "clinsig <value>"[Filter], which only
indexes single-word clinsig values. Confirmed live that "clinsig risk
factor"[Filter] and "clinsig likely pathogenic"[Filter] both silently
returned 0 results even though matching variants exist (e.g. HFE C282Y,
classification "Pathogenic/Pathogenic, low penetrance; risk factor").
ClinVar separately indexes compound values via clinsig_<value>[prop]
(underscore-joined). The query now ORs both forms.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def test_compound_clinsig_ors_filter_and_prop_forms():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        tool.run({"gene": "HFE", "clinical_significance": "risk factor"})

    term = mock_request.call_args[0][1]["term"]
    assert '"clinsig risk factor"[Filter]' in term
    assert "clinsig_risk_factor[prop]" in term
    assert " OR " in term


def test_single_word_clinsig_still_ors_both_forms():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        tool.run({"gene": "HFE", "clinical_significance": "Pathogenic"})

    term = mock_request.call_args[0][1]["term"]
    assert '"clinsig pathogenic"[Filter]' in term
    assert "clinsig_pathogenic[prop]" in term
