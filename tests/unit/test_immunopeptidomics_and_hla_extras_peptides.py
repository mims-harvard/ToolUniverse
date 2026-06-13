"""Offline unit tests for immunopeptidomics-and-hla-extras peptide tools.

Covers:
- HLALigandAtlasTool (HLALigandAtlas_get_benign_peptides, get_donors)
- MHCMotifAtlasTool (MHCMotifAtlas_get_allele_ligands)

The HTTP layer (http_utils.request_with_retry as imported into each tool
module) is mocked so the tests are deterministic and network-free.
"""

import gzip
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

# Make sure src/ is importable when run directly.
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tooluniverse.hlaligandatlas_tool import HLALigandAtlasTool  # noqa: E402
from tooluniverse.mhcmotifatlas_tool import MHCMotifAtlasTool  # noqa: E402


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class _FakeResp:
    def __init__(self, status_code=200, content=b"", text=""):
        self.status_code = status_code
        self.content = content
        self.text = text


_AGG_TSV = (
    "peptide_sequence_id\tpeptide_sequence\thla_class\tdonor_alleles\ttissues\n"
    "1\tLLPKKTESHHKAKGK\tHLA-II\tn/DRB1*01:01,w/DRB5*01:01\tAdrenal gland,Lung,Spleen\n"
    "2\tKVFGGTVHKK\tHLA-I\tn/A*11:01\tLung,Kidney\n"
    "3\tAAAAAAAAA\tHLA-I\tn/B*07:02\tBrain\n"
)

_DONORS_TSV = (
    "donor\thla_allele\n"
    "AUT01-DN13\tA*11:01\n"
    "OVA01-DN281\tA*11:01\n"
    "AUT01-DN05\tB*07:02\n"
)

_CLASSI_PEPTIDES = (
    "Allele\tPeptide\n"
    "A0101\tALDGRETD\n"
    "A0101\tYTDIINIFLY\n"
    "B0702\tAPRTLVYLL\n"
)

_CLASSII_PEPTIDES = (
    "Allele\tPeptide\tCore\n"
    "DRB1_01_01\tAAAAAKAAKYGLVPGVGVAPG\tYGLVPGVGV\n"
    "DRB1_01_01\tAAAKAAQFGLVPGVGVAP\tFGLVPGVGV\n"
)

_CLASSI_SEQUENCES = (
    "Allele\tSequence\n"
    "A0101\tSHSMRYFFTSVSRPGRGEPRFIAVGYVDDT\n"
    "B0702\tSHSMRYFYTSVSRPGRGEPRFISVGYVDDT\n"
)


def _gz(text):
    return gzip.compress(text.encode("utf-8"))


# --------------------------------------------------------------------------- #
# HLALigandAtlasTool - benign peptides
# --------------------------------------------------------------------------- #
def test_hla_benign_peptide_exact_match_success():
    tool = HLALigandAtlasTool({"fields": {"operation": "get_benign_peptides"}})
    with patch(
        "tooluniverse.hlaligandatlas_tool.request_with_retry",
        return_value=_FakeResp(content=_gz(_AGG_TSV)),
    ):
        out = tool.run({"peptide": "LLPKKTESHHKAKGK"})

    assert out["status"] == "success"
    peps = out["data"]["peptides"]
    assert len(peps) == 1
    row = peps[0]
    assert row["peptide_sequence_id"] == "1"
    assert row["peptide_sequence"] == "LLPKKTESHHKAKGK"
    assert row["hla_class"] == "HLA-II"
    assert "n/DRB1*01:01" in row["donor_alleles"]
    assert "Lung" in row["tissues"]
    assert out["metadata"]["returned"] == 1


def test_hla_benign_class_and_tissue_filter():
    tool = HLALigandAtlasTool({"fields": {"operation": "get_benign_peptides"}})
    with patch(
        "tooluniverse.hlaligandatlas_tool.request_with_retry",
        return_value=_FakeResp(content=_gz(_AGG_TSV)),
    ):
        out = tool.run({"hla_class": "HLA-I", "tissue": "lung", "limit": 10})

    assert out["status"] == "success"
    peps = out["data"]["peptides"]
    # Only row 2 is HLA-I AND in Lung (row 3 is HLA-I but Brain only).
    assert [p["peptide_sequence"] for p in peps] == ["KVFGGTVHKK"]
    assert all("Lung" in p["tissues"] for p in peps)


def test_hla_benign_invalid_class_error():
    tool = HLALigandAtlasTool({"fields": {"operation": "get_benign_peptides"}})
    out = tool.run({"hla_class": "HLA-X"})
    assert out["status"] == "error"
    assert "hla_class" in out["error"]


def test_hla_benign_http_error_path():
    tool = HLALigandAtlasTool({"fields": {"operation": "get_benign_peptides"}})
    with patch(
        "tooluniverse.hlaligandatlas_tool.request_with_retry",
        return_value=_FakeResp(status_code=502),
    ):
        out = tool.run({"peptide": "LLPKKTESHHKAKGK"})
    assert out["status"] == "error"
    assert "502" in out["error"]


def test_hla_benign_request_exception_no_raise():
    tool = HLALigandAtlasTool({"fields": {"operation": "get_benign_peptides"}})
    with patch(
        "tooluniverse.hlaligandatlas_tool.request_with_retry",
        side_effect=RuntimeError("boom"),
    ):
        out = tool.run({"peptide": "LLPKKTESHHKAKGK"})
    assert out["status"] == "error"
    assert "boom" in out["error"]


# --------------------------------------------------------------------------- #
# HLALigandAtlasTool - donors
# --------------------------------------------------------------------------- #
def test_hla_donors_success():
    tool = HLALigandAtlasTool({"fields": {"operation": "get_donors"}})
    with patch(
        "tooluniverse.hlaligandatlas_tool.request_with_retry",
        return_value=_FakeResp(content=_gz(_DONORS_TSV)),
    ):
        out = tool.run({"allele": "A*11:01"})
    assert out["status"] == "success"
    donors = out["data"]["donors"]
    assert {d["donor"] for d in donors} == {"AUT01-DN13", "OVA01-DN281"}
    assert all(d["hla_allele"] == "A*11:01" for d in donors)


def test_hla_donors_plaintext_not_gzipped():
    # donors endpoint may serve plain text; _maybe_gunzip must handle it.
    tool = HLALigandAtlasTool({"fields": {"operation": "get_donors"}})
    with patch(
        "tooluniverse.hlaligandatlas_tool.request_with_retry",
        return_value=_FakeResp(content=_DONORS_TSV.encode("utf-8")),
    ):
        out = tool.run({"donor": "AUT01"})
    assert out["status"] == "success"
    assert {d["donor"] for d in out["data"]["donors"]} == {
        "AUT01-DN13",
        "AUT01-DN05",
    }


def test_hla_donors_http_error():
    tool = HLALigandAtlasTool({"fields": {"operation": "get_donors"}})
    with patch(
        "tooluniverse.hlaligandatlas_tool.request_with_retry",
        return_value=_FakeResp(status_code=404),
    ):
        out = tool.run({})
    assert out["status"] == "error"
    assert "404" in out["error"]


def test_hla_unknown_operation():
    tool = HLALigandAtlasTool({"fields": {"operation": "nonsense"}})
    out = tool.run({})
    assert out["status"] == "error"
    assert "Unknown operation" in out["error"]


# --------------------------------------------------------------------------- #
# MHCMotifAtlasTool
# --------------------------------------------------------------------------- #
def test_mhc_classI_ligands_success():
    tool = MHCMotifAtlasTool({})
    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry",
        return_value=_FakeResp(text=_CLASSI_PEPTIDES),
    ):
        out = tool.run({"allele": "A0101", "mhc_class": "I", "limit": 5})
    assert out["status"] == "success"
    assert out["data"]["allele"] == "A0101"
    assert out["data"]["mhc_class"] == "I"
    peps = [p["peptide"] for p in out["data"]["peptides"]]
    assert peps == ["ALDGRETD", "YTDIINIFLY"]
    assert out["data"]["sequence"] is None
    assert out["metadata"]["total_matches"] == 2
    assert out["metadata"]["has_core_column"] is False


def test_mhc_classII_ligands_with_core():
    tool = MHCMotifAtlasTool({})
    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry",
        return_value=_FakeResp(text=_CLASSII_PEPTIDES),
    ):
        out = tool.run({"allele": "DRB1_01_01", "mhc_class": "II"})
    assert out["status"] == "success"
    assert out["metadata"]["has_core_column"] is True
    first = out["data"]["peptides"][0]
    assert first["peptide"] == "AAAAAKAAKYGLVPGVGVAPG"
    assert first["core"] == "YGLVPGVGV"


def test_mhc_include_sequence():
    tool = MHCMotifAtlasTool({})

    def _fake(_session, _method, url, **_kwargs):
        if "sequences" in url:
            return _FakeResp(text=_CLASSI_SEQUENCES)
        return _FakeResp(text=_CLASSI_PEPTIDES)

    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry", side_effect=_fake
    ):
        out = tool.run(
            {"allele": "A0101", "mhc_class": "I", "include_sequence": True}
        )
    assert out["status"] == "success"
    assert out["data"]["sequence"] == "SHSMRYFFTSVSRPGRGEPRFIAVGYVDDT"


def test_mhc_class_normalization():
    tool = MHCMotifAtlasTool({})
    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry",
        return_value=_FakeResp(text=_CLASSI_PEPTIDES),
    ):
        out = tool.run({"allele": "A0101", "mhc_class": "MHC-I"})
    assert out["status"] == "success"
    assert out["data"]["mhc_class"] == "I"


def test_mhc_missing_allele_error():
    """MHC Motif Atlas returns an error envelope when no allele is supplied."""
    tool = MHCMotifAtlasTool({})
    out = tool.run({"mhc_class": "I"})
    assert out["status"] == "error"
    assert "allele" in out["error"]


def test_mhc_allele_not_found_error():
    """An allele with no ligands in the table yields a clean error envelope."""
    tool = MHCMotifAtlasTool({})
    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry",
        return_value=_FakeResp(text=_CLASSI_PEPTIDES),
    ):
        out = tool.run({"allele": "Z9999", "mhc_class": "I"})
    assert out["status"] == "error"
    assert "No ligands found" in out["error"]


def test_mhc_http_error_path():
    """A non-200 status yields an error envelope, not an exception."""
    tool = MHCMotifAtlasTool({})
    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry",
        return_value=_FakeResp(status_code=500),
    ):
        out = tool.run({"allele": "A0101", "mhc_class": "I"})
    assert out["status"] == "error"
    assert "500" in out["error"]


def test_mhc_request_exception_no_raise():
    """A transport exception is caught and returned as an error envelope."""
    tool = MHCMotifAtlasTool({})
    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry",
        side_effect=RuntimeError("network down"),
    ):
        out = tool.run({"allele": "A0101", "mhc_class": "I"})
    assert out["status"] == "error"
    assert "network down" in out["error"]


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
