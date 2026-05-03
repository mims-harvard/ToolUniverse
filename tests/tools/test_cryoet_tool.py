"""
Tests for CryoET Data Portal tool.

Tests the CryoET GraphQL API integration for:
- Listing datasets with and without filters
- Getting a specific dataset by ID
- Listing runs in a dataset
- Listing tomograms for a run
- Listing annotations for a run
- Edge cases: missing params, invalid IDs, empty results
"""

import json
import pytest
from pathlib import Path


@pytest.fixture(scope="module")
def tool_config():
    """Load tool config from JSON."""
    config_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "tooluniverse"
        / "data"
        / "cryoet_tools.json"
    )
    with open(config_path) as f:
        tools = json.load(f)
    return {t["name"]: t for t in tools}


@pytest.fixture(scope="module")
def cryoet_tool_cls():
    """Import and return the CryoETTool class."""
    from tooluniverse.cryoet_tool import CryoETTool  # noqa: F401 (triggers @register_tool)
    from tooluniverse.tool_registry import get_tool_registry
    registry = get_tool_registry()
    return registry["CryoETTool"]


class TestCryoETToolDirect:
    """Level 1: Direct class tests against the live CryoET GraphQL API."""

    # ------------------------------------------------------------------ #
    # list_datasets
    # ------------------------------------------------------------------ #

    def test_list_datasets_no_filter(self, tool_config, cryoet_tool_cls):
        """list_datasets with no filter returns default number of datasets."""
        config = tool_config["CryoET_list_datasets"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "list_datasets", "limit": 3})

        assert result["status"] == "success"
        data = result["data"]
        assert data["count"] == 3
        assert len(data["datasets"]) == 3
        first = data["datasets"][0]
        assert "id" in first
        assert "title" in first
        assert "organismName" in first

    def test_list_datasets_organism_filter(self, tool_config, cryoet_tool_cls):
        """list_datasets filters by organism name correctly."""
        config = tool_config["CryoET_list_datasets"]
        tool = cryoet_tool_cls(config)
        result = tool.run(
            {"operation": "list_datasets", "organism_name": "Homo sapiens", "limit": 3}
        )

        assert result["status"] == "success"
        data = result["data"]
        assert data["count"] > 0
        for ds in data["datasets"]:
            assert "Homo" in ds.get("organismName", ""), (
                f"Expected 'Homo' in organism name, got: {ds.get('organismName')}"
            )

    def test_list_datasets_nonexistent_organism_returns_empty(self, tool_config, cryoet_tool_cls):
        """list_datasets returns empty list for organism that doesn't exist."""
        config = tool_config["CryoET_list_datasets"]
        tool = cryoet_tool_cls(config)
        result = tool.run(
            {
                "operation": "list_datasets",
                "organism_name": "NonExistentOrganism_XYZ_99999",
                "limit": 5,
            }
        )

        assert result["status"] == "success"
        data = result["data"]
        assert data["count"] == 0
        assert data["datasets"] == []

    def test_list_datasets_pagination_offset(self, tool_config, cryoet_tool_cls):
        """list_datasets with offset returns different datasets."""
        config = tool_config["CryoET_list_datasets"]
        tool = cryoet_tool_cls(config)
        page1 = tool.run({"operation": "list_datasets", "limit": 3, "offset": 0})
        page2 = tool.run({"operation": "list_datasets", "limit": 3, "offset": 3})

        assert page1["status"] == "success"
        assert page2["status"] == "success"
        ids1 = {ds["id"] for ds in page1["data"]["datasets"]}
        ids2 = {ds["id"] for ds in page2["data"]["datasets"]}
        assert ids1.isdisjoint(ids2), "Paginated pages should not share dataset IDs"

    def test_list_datasets_large_limit(self, tool_config, cryoet_tool_cls):
        """list_datasets handles a large limit value without crashing."""
        config = tool_config["CryoET_list_datasets"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "list_datasets", "limit": 100})

        assert result["status"] == "success"
        data = result["data"]
        assert data["count"] == len(data["datasets"])

    # ------------------------------------------------------------------ #
    # get_dataset
    # ------------------------------------------------------------------ #

    def test_get_dataset_known_id(self, tool_config, cryoet_tool_cls):
        """get_dataset returns full metadata for dataset 10053."""
        config = tool_config["CryoET_get_dataset"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "get_dataset", "dataset_id": 10053})

        assert result["status"] == "success"
        ds = result["data"]["dataset"]
        assert ds["id"] == 10053
        assert "title" in ds
        assert "organismName" in ds
        assert "s3Prefix" in ds

    def test_get_dataset_invalid_id(self, tool_config, cryoet_tool_cls):
        """get_dataset returns error for an ID that doesn't exist."""
        config = tool_config["CryoET_get_dataset"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "get_dataset", "dataset_id": 999999})

        assert result["status"] == "error"
        assert "not found" in result["error"].lower() or "999999" in result["error"]

    def test_get_dataset_missing_id_param(self, tool_config, cryoet_tool_cls):
        """get_dataset returns error when dataset_id is omitted."""
        config = tool_config["CryoET_get_dataset"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "get_dataset"})

        assert result["status"] == "error"
        assert "dataset_id" in result["error"].lower() or "required" in result["error"].lower()

    # ------------------------------------------------------------------ #
    # list_runs
    # ------------------------------------------------------------------ #

    def test_list_runs_known_dataset(self, tool_config, cryoet_tool_cls):
        """list_runs returns runs for dataset 10053."""
        config = tool_config["CryoET_list_runs"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "list_runs", "dataset_id": 10053, "limit": 5})

        assert result["status"] == "success"
        data = result["data"]
        assert data["dataset_id"] == 10053
        assert data["count"] > 0
        run = data["runs"][0]
        assert "id" in run
        assert "name" in run

    def test_list_runs_missing_dataset_id(self, tool_config, cryoet_tool_cls):
        """list_runs returns error when dataset_id is missing."""
        config = tool_config["CryoET_list_runs"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "list_runs"})

        assert result["status"] == "error"

    def test_list_runs_invalid_dataset_id_returns_empty(self, tool_config, cryoet_tool_cls):
        """list_runs returns empty list for a dataset ID that has no runs."""
        config = tool_config["CryoET_list_runs"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "list_runs", "dataset_id": 0})

        assert result["status"] == "success"
        assert result["data"]["count"] == 0

    # ------------------------------------------------------------------ #
    # list_tomograms
    # ------------------------------------------------------------------ #

    def test_list_tomograms_known_run(self, tool_config, cryoet_tool_cls):
        """list_tomograms returns tomograms for run 3430."""
        config = tool_config["CryoET_list_tomograms"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "list_tomograms", "run_id": 3430})

        assert result["status"] == "success"
        data = result["data"]
        assert data["run_id"] == 3430
        assert data["count"] > 0
        tomo = data["tomograms"][0]
        assert "id" in tomo
        assert "voxelSpacing" in tomo
        assert "isPortalStandard" in tomo

    def test_list_tomograms_missing_run_id(self, tool_config, cryoet_tool_cls):
        """list_tomograms returns error when run_id is missing."""
        config = tool_config["CryoET_list_tomograms"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "list_tomograms"})

        assert result["status"] == "error"

    def test_list_tomograms_invalid_run_id_returns_empty(self, tool_config, cryoet_tool_cls):
        """list_tomograms returns empty list for a run ID that doesn't exist."""
        config = tool_config["CryoET_list_tomograms"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "list_tomograms", "run_id": 0})

        assert result["status"] == "success"
        assert result["data"]["count"] == 0

    # ------------------------------------------------------------------ #
    # list_annotations
    # ------------------------------------------------------------------ #

    def test_list_annotations_known_run(self, tool_config, cryoet_tool_cls):
        """list_annotations returns annotations for run 3430."""
        config = tool_config["CryoET_list_annotations"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "list_annotations", "run_id": 3430})

        assert result["status"] == "success"
        data = result["data"]
        assert data["run_id"] == 3430
        assert data["count"] > 0
        ann = data["annotations"][0]
        assert "id" in ann
        assert "objectName" in ann

    def test_list_annotations_curator_recommended_filter(self, tool_config, cryoet_tool_cls):
        """list_annotations with curator_recommended_only=True only returns curated annotations."""
        config = tool_config["CryoET_list_annotations"]
        tool = cryoet_tool_cls(config)
        result = tool.run(
            {
                "operation": "list_annotations",
                "run_id": 3430,
                "curator_recommended_only": True,
            }
        )

        assert result["status"] == "success"
        # All returned annotations must be curator recommended
        for ann in result["data"].get("annotations", []):
            assert ann.get("isCuratorRecommended") is True

    def test_list_annotations_missing_run_id(self, tool_config, cryoet_tool_cls):
        """list_annotations returns error when run_id is missing."""
        config = tool_config["CryoET_list_annotations"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "list_annotations"})

        assert result["status"] == "error"

    # ------------------------------------------------------------------ #
    # unknown operation
    # ------------------------------------------------------------------ #

    def test_unknown_operation(self, tool_config, cryoet_tool_cls):
        """An unknown operation string returns a descriptive error."""
        config = tool_config["CryoET_list_datasets"]
        tool = cryoet_tool_cls(config)
        result = tool.run({"operation": "do_something_random"})

        assert result["status"] == "error"
        assert "Unknown operation" in result["error"] or "do_something_random" in result["error"]


class TestCryoETToolViaRegistry:
    """Level 2: Tests through ToolUniverse registration system."""

    @pytest.fixture(scope="class")
    def tu(self):
        """Load ToolUniverse with all tools."""
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        """All 5 CryoET tools are registered in ToolUniverse."""
        expected = [
            "CryoET_list_datasets",
            "CryoET_get_dataset",
            "CryoET_list_runs",
            "CryoET_list_tomograms",
            "CryoET_list_annotations",
        ]
        for name in expected:
            assert name in tu.all_tool_dict, f"Tool '{name}' not found in registry"

    def test_list_datasets_via_registry(self, tu):
        """CryoET_list_datasets works through ToolUniverse.run_one_function."""
        result = tu.run_one_function(
            {
                "name": "CryoET_list_datasets",
                "arguments": {
                    "operation": "list_datasets",
                    "organism_name": "Homo sapiens",
                    "limit": 3,
                },
            }
        )
        assert result["status"] == "success"
        assert result["data"]["count"] == 3

    def test_get_dataset_via_registry(self, tu):
        """CryoET_get_dataset works through ToolUniverse.run_one_function."""
        result = tu.run_one_function(
            {
                "name": "CryoET_get_dataset",
                "arguments": {"operation": "get_dataset", "dataset_id": 10053},
            }
        )
        assert result["status"] == "success"
        assert result["data"]["dataset"]["id"] == 10053

    def test_list_runs_via_registry(self, tu):
        """CryoET_list_runs works through ToolUniverse.run_one_function."""
        result = tu.run_one_function(
            {
                "name": "CryoET_list_runs",
                "arguments": {"operation": "list_runs", "dataset_id": 10053, "limit": 5},
            }
        )
        assert result["status"] == "success"
        assert result["data"]["count"] > 0

    def test_list_tomograms_via_registry(self, tu):
        """CryoET_list_tomograms works through ToolUniverse.run_one_function."""
        result = tu.run_one_function(
            {
                "name": "CryoET_list_tomograms",
                "arguments": {"operation": "list_tomograms", "run_id": 3430},
            }
        )
        assert result["status"] == "success"
        assert result["data"]["count"] > 0

    def test_list_annotations_via_registry(self, tu):
        """CryoET_list_annotations works through ToolUniverse.run_one_function."""
        result = tu.run_one_function(
            {
                "name": "CryoET_list_annotations",
                "arguments": {"operation": "list_annotations", "run_id": 3430, "limit": 5},
            }
        )
        assert result["status"] == "success"
        assert result["data"]["count"] > 0

    def test_chained_workflow(self, tu):
        """Real-world workflow: list datasets -> get dataset -> list runs -> list tomograms -> list annotations."""
        # Step 1: Find a Coxiella dataset
        ds_result = tu.run_one_function(
            {
                "name": "CryoET_list_datasets",
                "arguments": {
                    "operation": "list_datasets",
                    "organism_name": "Coxiella",
                    "limit": 1,
                },
            }
        )
        assert ds_result["status"] == "success"
        assert len(ds_result["data"]["datasets"]) > 0
        dataset_id = ds_result["data"]["datasets"][0]["id"]

        # Step 2: Get full dataset details
        detail = tu.run_one_function(
            {
                "name": "CryoET_get_dataset",
                "arguments": {"operation": "get_dataset", "dataset_id": dataset_id},
            }
        )
        assert detail["status"] == "success"
        assert detail["data"]["dataset"]["id"] == dataset_id

        # Step 3: List runs
        runs = tu.run_one_function(
            {
                "name": "CryoET_list_runs",
                "arguments": {
                    "operation": "list_runs",
                    "dataset_id": dataset_id,
                    "limit": 1,
                },
            }
        )
        assert runs["status"] == "success"
        assert runs["data"]["count"] > 0
        run_id = runs["data"]["runs"][0]["id"]

        # Step 4: List tomograms for first run
        tomos = tu.run_one_function(
            {
                "name": "CryoET_list_tomograms",
                "arguments": {"operation": "list_tomograms", "run_id": run_id},
            }
        )
        assert tomos["status"] == "success"

        # Step 5: List annotations for first run
        anns = tu.run_one_function(
            {
                "name": "CryoET_list_annotations",
                "arguments": {"operation": "list_annotations", "run_id": run_id},
            }
        )
        assert anns["status"] == "success"


class TestCryoETTestExamples:
    """Level 5: Verify test_examples from JSON config return real data."""

    @pytest.fixture(scope="class")
    def tool_configs(self):
        config_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "tooluniverse"
            / "data"
            / "cryoet_tools.json"
        )
        with open(config_path) as f:
            return json.load(f)

    @pytest.fixture(scope="class")
    def cryoet_cls(self):
        from tooluniverse.cryoet_tool import CryoETTool  # noqa: F401
        from tooluniverse.tool_registry import get_tool_registry
        return get_tool_registry()["CryoETTool"]

    def test_all_test_examples_succeed(self, tool_configs, cryoet_cls):
        """Every test_example in cryoet_tools.json returns status=success."""
        for tool_def in tool_configs:
            tool_name = tool_def["name"]
            examples = tool_def.get("test_examples", [])
            tool = cryoet_cls(tool_def)
            for i, example in enumerate(examples):
                result = tool.run(example)
                assert result.get("status") == "success", (
                    f"Tool '{tool_name}' example {i}: expected success, "
                    f"got {result.get('status')!r}. Error: {result.get('error')}"
                )
                assert "data" in result, (
                    f"Tool '{tool_name}' example {i}: expected 'data' key in result, "
                    f"got keys: {list(result.keys())}"
                )
