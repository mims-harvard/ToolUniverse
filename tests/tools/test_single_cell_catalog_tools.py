"""Unit tests for the single-cell catalog tools.

Covers the Broad Single Cell Portal, UCSC Cell Browser, and CellTypist
model catalog tools. Network-dependent assertions are kept loose so the
suite does not fail when upstream catalogs grow or are reorganized.
"""

import pytest
from tooluniverse import ToolUniverse


EXPECTED_TOOLS = [
    "SCP_search_studies",
    "SCP_list_studies",
    "SCP_get_study",
    "UCSCCellBrowser_search_datasets",
    "UCSCCellBrowser_get_dataset",
    "UCSCCellBrowser_list_facets",
    "CellTypist_search_models",
    "CellTypist_get_model",
]


@pytest.fixture(scope="module")
def tu():
    """Create a ToolUniverse instance with all tools loaded."""
    instance = ToolUniverse()
    instance.load_tools()
    return instance


class TestRegistration:
    """The three-step registration must produce every wrapper."""

    def test_tools_load(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        missing = [n for n in EXPECTED_TOOLS if n not in names]
        assert not missing, f"Tools failed to register: {missing}"

    def test_tool_names_within_mcp_limit(self):
        too_long = [n for n in EXPECTED_TOOLS if len(n) > 55]
        assert not too_long, f"Tool names exceed 55 chars: {too_long}"


class TestSingleCellPortal:
    """Broad Institute Single Cell Portal."""

    def test_search_studies(self, tu):
        result = tu.tools.SCP_search_studies(query="lung", limit=3)
        assert result["status"] == "success"
        assert len(result["data"]) <= 3
        assert all(s["accession"].startswith("SCP") for s in result["data"])

    def test_list_studies_sorted_by_cell_count(self, tu):
        result = tu.tools.SCP_list_studies(limit=5)
        assert result["status"] == "success"
        counts = [s["cell_count"] or 0 for s in result["data"]]
        assert counts == sorted(counts, reverse=True)

    def test_min_cells_filter(self, tu):
        threshold = 100000
        result = tu.tools.SCP_list_studies(min_cells=threshold, limit=5)
        assert result["status"] == "success"
        assert all((s["cell_count"] or 0) >= threshold for s in result["data"])

    def test_get_study_returns_full_description(self, tu):
        result = tu.tools.SCP_get_study(accession="SCP1")
        assert result["status"] == "success"
        assert result["data"]["accession"] == "SCP1"
        # get_study must not truncate, unlike the list/search operations
        assert not result["data"]["description"].endswith("...")

    def test_unknown_accession_returns_error(self, tu):
        result = tu.tools.SCP_get_study(accession="SCP_DOES_NOT_EXIST")
        assert result["status"] == "error"
        assert "accession" in result["error"].lower()


class TestUCSCCellBrowser:
    """UCSC Cell Browser."""

    def test_search_datasets_filters(self, tu):
        result = tu.tools.UCSCCellBrowser_search_datasets(
            organism="Human", body_part="brain", limit=5
        )
        assert result["status"] == "success"
        for dataset in result["data"]:
            assert any("human" in o.lower() for o in dataset["organisms"])
            assert any("brain" in b.lower() for b in dataset["body_parts"])

    def test_get_dataset_normalizes_parents(self, tu):
        result = tu.tools.UCSCCellBrowser_get_dataset(name="organoid-22q11")
        assert result["status"] == "success"
        # Upstream returns [name, label] pairs; the tool must emit objects
        for parent in result["data"]["parents"]:
            assert isinstance(parent, dict)
            assert set(parent) == {"name", "label"}

    def test_list_facets_counts_descend(self, tu):
        result = tu.tools.UCSCCellBrowser_list_facets(facet="organisms")
        assert result["status"] == "success"
        counts = [f["dataset_count"] for f in result["data"]]
        assert counts == sorted(counts, reverse=True)

    def test_unknown_dataset_returns_error(self, tu):
        result = tu.tools.UCSCCellBrowser_get_dataset(name="no-such-dataset-xyz")
        assert result["status"] == "error"


class TestCellTypistCatalog:
    """CellTypist pre-trained model catalog."""

    def test_search_models(self, tu):
        result = tu.tools.CellTypist_search_models(keyword="immune", limit=5)
        assert result["status"] == "success"
        assert result["data"]
        for model in result["data"]:
            assert model["filename"].endswith(".pkl")

    def test_min_celltypes_filter(self, tu):
        result = tu.tools.CellTypist_search_models(min_celltypes=50, limit=5)
        assert result["status"] == "success"
        assert all(int(m["n_celltypes"]) >= 50 for m in result["data"])

    def test_get_model(self, tu):
        result = tu.tools.CellTypist_get_model(filename="Immune_All_Low.pkl")
        assert result["status"] == "success"
        assert result["data"]["filename"] == "Immune_All_Low.pkl"
        assert result["data"]["download_url"].startswith("https://")

    def test_unknown_model_lists_alternatives(self, tu):
        result = tu.tools.CellTypist_get_model(filename="NotAModel.pkl")
        assert result["status"] == "error"
        assert ".pkl" in result["error"]


class TestErrorHandling:
    """run() must never raise; it returns error dicts instead."""

    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("SCP_search_studies", {"query": ""}),
            ("SCP_get_study", {"accession": "NOPE"}),
            ("UCSCCellBrowser_get_dataset", {"name": "nope-xyz"}),
            ("CellTypist_get_model", {"filename": "nope.pkl"}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
