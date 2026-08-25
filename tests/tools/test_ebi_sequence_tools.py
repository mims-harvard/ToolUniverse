"""Unit tests for the EMBL-EBI Job Dispatcher sequence-analysis tools.

These submit real jobs and poll them, so each test takes several seconds.
Assertions check biological correctness where the answer is well known
(rhodopsin has seven transmembrane helices; haemoglobin alpha carries a
Globin domain), because a parser can return schema-valid nonsense.
"""

import pytest
from tooluniverse import ToolUniverse


EXPECTED_TOOLS = [
    "EBI_pairwise_align",
    "EBI_translate_sequence",
    "EBI_scan_pfam_domains",
    "EBI_predict_membrane_topology",
    "EBI_profile_search",
]

TRANSIENT = ("timed out", "Failed to connect", "did not finish", "HTTP 5")

# Bovine rhodopsin (P02699): the canonical seven-transmembrane receptor.
RHODOPSIN = (
    ">sp_P02699\n"
    "MNGTEGPNFYVPFSNKTGVVRSPFEAPQYYLAEPWQFSMLAAYMFLLIMLGFPINFLTLYVTVQHKKLRT"
    "PLNYILLNLAVADLFMVFGGFTTTLYTSLHGYFVFGPTGCNLEGFFATLGGEIALWSLVVLAIERYVVVC"
    "KPMSNFRFGENHAIMGVAFTWVMALACAAPPLVGWSRYIPEGMQCSCGIDYYTPHEETNNESFVIYMFVV"
    "HFIIPLIVIFFCYGQLVFTVKEAAAQQQESATTQKAEKEVTRMVIIMVIAFLICWLPYAGVAFYIFTHQG"
    "SDFGPIFMTIPAFFAKTSAVYNPVIYIMMNKQFRNCMVTTLCCGKNPLGDDEASTTVSKTETSQVAPA"
)

# Human haemoglobin subunit alpha (P69905) and beta (P68871).
HBA = (
    ">sp_P69905\n"
    "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNA"
    "VAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR"
)
HBB = (
    ">sp_P68871\n"
    "MVHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPKVKAHGKKVLG"
    "AFSDGLAHLDNLKGTFATLSELHCDKLHVDPENFRLLGNVLVCVLAHHFGKEFTPPVQAAYQKVVAGVANALAHKYH"
)

DNA = ">seq\nATGAAAACCGCATATATTGCGAAACAGCGCCAGATTAGCTTTGTGAAAAGCCATTTTAGC"


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


def data_of(result):
    """Return result['data'], skipping on a transient job failure."""
    if result.get("status") == "error":
        error = str(result.get("error", ""))
        if any(t in error for t in TRANSIENT):
            pytest.skip(f"EBI job did not complete: {error[:90]}")
        pytest.fail(f"unexpected error response: {error[:200]}")
    return result["data"]


class TestRegistration:
    def test_tools_load(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert not [n for n in EXPECTED_TOOLS if n not in names]

    def test_names_within_mcp_limit(self):
        assert not [n for n in EXPECTED_TOOLS if len(n) > 55]


class TestPairwiseAlign:
    def test_global_alignment_reports_identity(self, tu):
        data = data_of(
            tu.tools.EBI_pairwise_align(
                sequence_a=HBA, sequence_b=HBB, algorithm="needle"
            )
        )
        # Haemoglobin alpha and beta are homologous but distinct: ~40-50% id.
        assert 25 < data["identity_percent"] < 70
        assert data["score"] is not None
        assert data["alignment"]

    def test_local_alignment_supported(self, tu):
        data = data_of(
            tu.tools.EBI_pairwise_align(
                sequence_a=HBA, sequence_b=HBB, algorithm="matcher"
            )
        )
        assert data["algorithm"] == "matcher"

    def test_unknown_algorithm_lists_choices(self, tu):
        result = tu.tools.EBI_pairwise_align(
            sequence_a=HBA, sequence_b=HBB, algorithm="smithwaterman"
        )
        assert result["status"] == "error"
        assert "needle" in result["error"]

    def test_missing_second_sequence(self, tu):
        result = tu.tools.EBI_pairwise_align(sequence_a=HBA, sequence_b="")
        assert result["status"] == "error"


class TestTranslate:
    def test_dna_to_protein(self, tu):
        data = data_of(
            tu.tools.EBI_translate_sequence(sequence=DNA, mode="dna_to_protein",
                                            frame="1")
        )
        assert "MKTAYIAKQRQ" in data["result"].replace("\n", "")

    def test_six_frame_returns_multiple_records(self, tu):
        data = data_of(
            tu.tools.EBI_translate_sequence(sequence=DNA, mode="six_frame")
        )
        assert data["mode"] == "six_frame"
        assert data["result"]

    def test_unknown_mode(self, tu):
        result = tu.tools.EBI_translate_sequence(sequence=DNA, mode="rna_to_protein")
        assert result["status"] == "error"
        assert "dna_to_protein" in result["error"]


class TestPfamScan:
    def test_finds_globin_domain_in_haemoglobin(self, tu):
        domains = data_of(tu.tools.EBI_scan_pfam_domains(sequence=HBA))
        assert domains, "expected at least one Pfam domain"
        globin = [d for d in domains if d["hmm_name"] == "Globin"]
        assert globin, f"expected a Globin domain, got {[d['hmm_name'] for d in domains]}"
        hit = globin[0]
        assert hit["hmm_accession"].startswith("PF00042")
        assert hit["evalue"] < 1e-10
        assert hit["start"] and hit["end"] and hit["start"] < hit["end"]
        assert hit["significant"] is True


class TestPhobius:
    def test_rhodopsin_has_seven_transmembrane_helices(self, tu):
        data = data_of(tu.tools.EBI_predict_membrane_topology(sequence=RHODOPSIN))
        assert data["transmembrane_helix_count"] == 7
        assert data["has_signal_peptide"] is False
        assert any(f["feature"] == "TRANSMEM" for f in data["features"])

    def test_soluble_protein_has_no_helices(self, tu):
        data = data_of(tu.tools.EBI_predict_membrane_topology(sequence=HBA))
        assert data["transmembrane_helix_count"] == 0


class TestProfileSearch:
    def test_phmmer_against_swissprot(self, tu):
        data = data_of(
            tu.tools.EBI_profile_search(
                sequence=HBA, method="phmmer", database="swissprot"
            )
        )
        assert data["method"] == "phmmer"
        assert data["result"]

    def test_database_validated_per_method(self, tu):
        result = tu.tools.EBI_profile_search(
            sequence=HBA, method="phmmer", database="uniprotkb_swissprot"
        )
        assert result["status"] == "error"
        assert "swissprot" in result["error"]


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("EBI_pairwise_align", {"sequence_a": "", "sequence_b": ""}),
            ("EBI_translate_sequence", {"sequence": ""}),
            ("EBI_scan_pfam_domains", {"sequence": ""}),
            ("EBI_predict_membrane_topology", {"sequence": ""}),
            ("EBI_profile_search", {"sequence": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
