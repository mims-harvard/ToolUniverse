"""Tests for the DANDI Archive tool.

DANDI is the neurophysiology-recording counterpart to the already-wrapped
OpenNeuro (human MRI/EEG), with no overlap in data type. Tests assert a
real, known dataset survives the round trip: dandiset 000020 is a
documented mouse visual cortex patch-seq study with 1,040 subjects.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

MOUSE_VISUAL_CORTEX = "000020"


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
        assert "DANDI_search_datasets" in names
        assert "DANDI_get_dataset" in names
        assert "DANDI_list_assets" in names


class TestSearchDatasets:
    def test_finds_visual_cortex_datasets(self, tu):
        rows = data_of(
            tu.tools.DANDI_search_datasets(query="mouse visual cortex", limit=10)
        )
        assert rows
        assert all(r["dandiset_id"] for r in rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(tu.tools.DANDI_search_datasets(query="patch-seq", limit=3))
        assert len(rows) <= 3

    def test_unmatched_query(self, tu):
        result = tu.tools.DANDI_search_datasets(query="zzzznotarealdataset12345")
        assert result["status"] == "error"

    def test_missing_query(self, tu):
        assert tu.tools.DANDI_search_datasets(query="")["status"] == "error"


class TestGetDataset:
    def test_known_dataset_metadata(self, tu):
        data = data_of(tu.tools.DANDI_get_dataset(dandiset_id=MOUSE_VISUAL_CORTEX))
        assert "House mouse" in data["species"]
        assert "Neurodata Without Borders (NWB)" in data["data_standard"]
        assert data["number_of_subjects"] == 1040

    def test_unknown_dataset(self, tu):
        result = tu.tools.DANDI_get_dataset(dandiset_id="999999")
        assert result["status"] == "error"

    def test_missing_dandiset_id(self, tu):
        assert tu.tools.DANDI_get_dataset(dandiset_id="")["status"] == "error"


class TestListAssets:
    def test_known_dataset_has_nwb_files(self, tu):
        rows = data_of(
            tu.tools.DANDI_list_assets(dandiset_id=MOUSE_VISUAL_CORTEX, limit=10)
        )
        assert rows
        assert all(r["path"].endswith(".nwb") for r in rows)

    def test_limit_is_respected(self, tu):
        result = tu.tools.DANDI_list_assets(dandiset_id=MOUSE_VISUAL_CORTEX, limit=3)
        rows = data_of(result)
        assert len(rows) <= 3
        assert result["metadata"]["total_assets"] >= len(rows)

    def test_unknown_dataset(self, tu):
        result = tu.tools.DANDI_list_assets(dandiset_id="999999")
        assert result["status"] == "error"

    def test_missing_dandiset_id(self, tu):
        assert tu.tools.DANDI_list_assets(dandiset_id="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("DANDI_search_datasets", {"query": ""}),
            ("DANDI_get_dataset", {"dandiset_id": ""}),
            ("DANDI_get_dataset", {"dandiset_id": "999999"}),
            ("DANDI_list_assets", {"dandiset_id": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
