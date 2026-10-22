"""Regression tests for ProtParam derived-classification provenance."""

from unittest.mock import patch

import pytest

from tooluniverse.protparam_tool import ProtParamTool, _DIWV, _instability_index


pytestmark = pytest.mark.unit


def _tool() -> ProtParamTool:
    return ProtParamTool({"name": "ProtParam_calculate"})


@pytest.mark.parametrize(
    ("index", "classification"),
    [(39.999, "stable"), (40.0, "unstable"), (40.001, "unstable")],
)
def test_stability_rule_includes_exact_boundary(index, classification):
    """The output publishes and follows the exact <40 versus >=40 rule."""
    with patch("tooluniverse.protparam_tool._instability_index", return_value=index):
        result = _tool().run({"sequence": "ACDEFGHIK"})

    assert result["status"] == "success"
    data = result["data"]
    interpretation = data["stability_interpretation"]
    assert data["stability_classification"] == classification
    assert interpretation["classification"] == classification
    assert interpretation["metric_value"] == index
    assert interpretation["threshold"] == 40.0
    assert interpretation["rule"] == (
        "stable if instability_index < 40; unstable if >= 40"
    )


def test_stability_label_is_explicitly_local_and_derived():
    """A heuristic label cannot look like a retrieved experimental fact."""
    result = _tool().run({"sequence": "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPS"})

    interpretation = result["data"]["stability_interpretation"]
    assert interpretation["derived"] is True
    assert interpretation["derived_by"] == "ToolUniverse"
    assert interpretation["metric"] == "instability_index"
    assert "heuristic" in interpretation["scope_note"]
    assert "not a retrieved experimental" in interpretation["scope_note"]
    assert "Guruprasad" in interpretation["method_basis"]


def test_complete_sparse_diwv_table_contains_all_nondefault_weights():
    """The sparse table has all 153 official non-1.0 dipeptide weights."""
    assert len(_DIWV) == 153
    assert _DIWV["AC"] == 44.94
    assert _DIWV["RR"] == 58.28
    assert _DIWV["YR"] == -15.91
    assert "AA" not in _DIWV  # Official default weight 1.0.


def test_uniprot_tp53_and_hba_instability_indices_match_reference_values():
    """Real UniProt sequences match values independently derived from Biopython."""
    tp53 = (
        "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGP"
        "DEAPRMPEAAPPVAPAPAAPTPAAPAPAPSWPLSSSVPSQKTYQGSYGFRLGFLHSGTAKSV"
        "TCTYSPALNKMFCQLAKTCPVQLWVDSTPPPGTRVRAMAIYKQSQHMTEVVRRCPHHERCSDS"
        "DGLAPPQHLIRVEGNLRVEYLDDRNTFRHSVVVPYEPPEVGSDCTTIHYNYMCNSSCMGGMNRR"
        "PILTIITLEDSSGNLLGRNSFEVRVCACPGRDRRTEEENLRKKGEPHHELPPGSTKRALPNNTSS"
        "SPQPKKKPLDGEYFTLQIRGRERFEMFRELNEALELKDAQAGKEPGGSRAHSSHLKSKKGQSTS"
        "RHKKLMFKTEGPDSD"
    )
    hba = (
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKV"
        "ADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLD"
        "KFLASVSTVLTSKYR"
    )

    assert len(tp53) == 393
    assert len(hba) == 142
    assert _instability_index(tp53) == 73.59
    assert _instability_index(hba) == 6.97
