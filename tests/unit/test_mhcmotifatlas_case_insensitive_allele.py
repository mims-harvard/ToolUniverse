"""Regression guard for Fix-R21B-3: MHCMotifAtlasTool matched allele codes
with exact, case-sensitive string equality against the atlas's own
uppercase-only TSV files, so a well-formed but lowercase allele (e.g.
"a0201") silently matched zero rows -- confirmed live -- even though the
tool's own error message's example format doesn't mention case matters.

Fixed by uppercasing the input allele before matching, consistent with how
mhc_class is already normalized.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.mhcmotifatlas_tool import MHCMotifAtlasTool

pytestmark = pytest.mark.unit

_CLASS_I_TSV = "Allele\tPeptide\nA0201\tALFTKVLENV\nA0201\tGILGFVFTL\nB0702\tRANDOMPEP\n"
_CLASS_II_TSV = "Allele\tPeptide\tCore\nDRB1_01_01\tAAAAAKAAKYGLVPGVGVAPG\tYGLVPGVGV\n"


def _tool():
    return MHCMotifAtlasTool({"name": "mhcmotif_test"})


def _resp(text):
    r = MagicMock()
    r.status_code = 200
    r.text = text
    return r


def test_lowercase_class_i_allele_matches():
    tool = _tool()
    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry",
        return_value=_resp(_CLASS_I_TSV),
    ):
        result = tool.run({"allele": "a0201", "mhc_class": "I", "limit": 10})

    assert result["status"] == "success"
    assert result["data"]["allele"] == "A0201"
    assert len(result["data"]["peptides"]) == 2


def test_lowercase_class_ii_allele_matches():
    tool = _tool()
    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry",
        return_value=_resp(_CLASS_II_TSV),
    ):
        result = tool.run({"allele": "drb1_01_01", "mhc_class": "II", "limit": 10})

    assert result["status"] == "success"
    assert result["data"]["allele"] == "DRB1_01_01"
    assert result["data"]["peptides"][0]["core"] == "YGLVPGVGV"


def test_uppercase_allele_still_works_no_regression():
    tool = _tool()
    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry",
        return_value=_resp(_CLASS_I_TSV),
    ):
        result = tool.run({"allele": "B0702", "mhc_class": "I", "limit": 10})

    assert result["status"] == "success"
    assert len(result["data"]["peptides"]) == 1


def test_genuinely_unknown_allele_still_errors():
    tool = _tool()
    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry",
        return_value=_resp(_CLASS_I_TSV),
    ):
        result = tool.run({"allele": "Z9999", "mhc_class": "I", "limit": 10})

    assert result["status"] == "error"
    assert "No ligands found" in result["error"]
