"""Tests for the EGA (European Genome-phenome Archive) tool.

EGA accessions appear constantly in papers' data-availability statements
with no way to resolve them in ToolUniverse before this. The API's own
query-like parameters are completely non-functional under every name
tried (query, q, search, title, free_text_search all returned the
identical first record), so only exact-accession lookups are exposed.
Tests assert real, known metadata survives the round trip.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

BIPOLAR_STUDY = "EGAS00000000001"
CONTROL_DATASET = "EGAD00000000001"


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


def data_of(result):
    if result.get("status") == "error":
        error = str(result.get("error", ""))
        if any(t in error for t in TRANSIENT):
            pytest.skip(f"upstream temporarily unavailable: {error[:80]}")
        pytest.fail(f"unexpected error response: {error[:200]}")
    return result["data"]


class TestRegistration:
    def test_tools_load(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert "EGA_get_study" in names
        assert "EGA_get_dataset" in names
        assert "EGA_get_study_datasets" in names


class TestGetStudy:
    def test_known_study_metadata(self, tu):
        data = data_of(tu.tools.EGA_get_study(accession=BIPOLAR_STUDY))
        assert "Bipolar" in data["title"]
        assert data["accession_id"] == BIPOLAR_STUDY

    def test_unknown_study(self, tu):
        result = tu.tools.EGA_get_study(accession="NOTAREALACCESSION")
        assert result["status"] == "error"

    def test_missing_accession(self, tu):
        assert tu.tools.EGA_get_study(accession="")["status"] == "error"


class TestGetDataset:
    def test_known_dataset_metadata(self, tu):
        data = data_of(tu.tools.EGA_get_dataset(accession=CONTROL_DATASET))
        assert data["accession_id"] == CONTROL_DATASET
        assert data["access_type"] == "controlled"
        assert data["num_samples"] == 1504

    def test_unknown_dataset(self, tu):
        result = tu.tools.EGA_get_dataset(accession="NOTAREALACCESSION")
        assert result["status"] == "error"

    def test_missing_accession(self, tu):
        assert tu.tools.EGA_get_dataset(accession="")["status"] == "error"


class TestGetStudyDatasets:
    def test_bipolar_study_has_known_dataset(self, tu):
        rows = data_of(tu.tools.EGA_get_study_datasets(accession=BIPOLAR_STUDY))
        assert any(r["accession_id"] == CONTROL_DATASET for r in rows)

    def test_unknown_study(self, tu):
        result = tu.tools.EGA_get_study_datasets(accession="NOTAREALACCESSION")
        assert result["status"] == "error"

    def test_missing_accession(self, tu):
        assert tu.tools.EGA_get_study_datasets(accession="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("EGA_get_study", {"accession": ""}),
            ("EGA_get_study", {"accession": "NOTAREALACCESSION"}),
            ("EGA_get_dataset", {"accession": ""}),
            ("EGA_get_study_datasets", {"accession": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
