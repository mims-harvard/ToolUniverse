"""
Tests for COD (Crystallography Open Database) tools.

Tests the COD API integration for:
- Text search (query alias)
- Formula search
- Space group search (spacegroup alias)
- Element-based search
- Single structure retrieval (cod_id alias)
- Response field completeness
"""

import json
import pytest
from pathlib import Path


class TestCODToolDirect:
    """Level 1: Direct class testing."""

    @pytest.fixture
    def tool_config(self):
        """Load tool config from JSON."""
        config_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "tooluniverse"
            / "data"
            / "cod_crystal_tools.json"
        )
        with open(config_path) as f:
            tools = json.load(f)
        return {t["name"]: t for t in tools}

    def test_search_text(self, tool_config):
        """Test text search for aspirin."""
        from tooluniverse.cod_tool import CODTool

        config = tool_config["COD_search_structures"]
        tool = CODTool(config)
        result = tool.run({"text": "aspirin", "results": 3})

        assert result["status"] == "success"
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["file"] == "1515581"

    def test_search_query_alias(self, tool_config):
        """Test query alias resolves to text."""
        from tooluniverse.cod_tool import CODTool

        config = tool_config["COD_search_structures"]
        tool = CODTool(config)
        result = tool.run({"query": "aspirin", "max_results": 2})

        assert result["status"] == "success"
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        assert "C9 H8 O4" in data[0]["formula"]

    def test_search_formula(self, tool_config):
        """Test formula search."""
        from tooluniverse.cod_tool import CODTool

        config = tool_config["COD_search_structures"]
        tool = CODTool(config)
        result = tool.run({"formula": "C9 H8 O4", "results": 3})

        assert result["status"] == "success"
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        for entry in data:
            assert "C9 H8 O4" in entry["formula"]

    def test_search_spacegroup_alias(self, tool_config):
        """Test spacegroup alias resolves to sg."""
        from tooluniverse.cod_tool import CODTool

        config = tool_config["COD_search_structures"]
        tool = CODTool(config)
        result = tool.run({"spacegroup": "P 21/c", "max_results": 2})

        assert result["status"] == "success"
        assert isinstance(result["data"], list)

    def test_search_max_results_alias(self, tool_config):
        """Test max_results alias resolves to results."""
        from tooluniverse.cod_tool import CODTool

        config = tool_config["COD_search_structures"]
        tool = CODTool(config)
        result = tool.run({"text": "aspirin", "max_results": 2})

        assert result["status"] == "success"
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) <= 2

    def test_search_returns_expected_fields(self, tool_config):
        """Test that search results contain all expected fields."""
        from tooluniverse.cod_tool import CODTool

        config = tool_config["COD_search_structures"]
        tool = CODTool(config)
        result = tool.run({"text": "aspirin", "results": 1})

        assert result["status"] == "success"
        entry = result["data"][0]
        # Must have these fields
        assert "file" in entry
        assert "formula" in entry
        assert "sg" in entry
        assert "a" in entry
        assert "b" in entry
        assert "c" in entry
        assert "alpha" in entry
        assert "beta" in entry
        assert "gamma" in entry
        assert "vol" in entry

    def test_get_structure_by_id(self, tool_config):
        """Test getting structure by id."""
        from tooluniverse.cod_tool import CODTool

        config = tool_config["COD_get_structure"]
        tool = CODTool(config)
        result = tool.run({"id": "1515581"})

        assert result["status"] == "success"
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) == 1
        entry = data[0]
        assert entry["file"] == "1515581"
        assert "C9 H8 O4" in entry["formula"]

    def test_get_structure_cod_id_alias(self, tool_config):
        """Test cod_id alias resolves to id."""
        from tooluniverse.cod_tool import CODTool

        config = tool_config["COD_get_structure"]
        tool = CODTool(config)
        result = tool.run({"cod_id": "1515581"})

        assert result["status"] == "success"
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) == 1

    def test_get_structure_complete_fields(self, tool_config):
        """Test that structure retrieval returns all crystallographic fields."""
        from tooluniverse.cod_tool import CODTool

        config = tool_config["COD_get_structure"]
        tool = CODTool(config)
        result = tool.run({"id": "1515581"})

        entry = result["data"][0]
        # Unit cell parameters
        assert float(entry["a"]) > 0
        assert float(entry["b"]) > 0
        assert float(entry["c"]) > 0
        assert entry["alpha"] is not None
        assert entry["beta"] is not None
        assert entry["gamma"] is not None
        assert float(entry["vol"]) > 0
        # Z value
        assert entry["Z"] == "4"
        # R factors
        assert entry["Robs"] is not None
        # Journal reference
        assert entry["doi"] == "10.1039/c1sc00430a"
        assert entry["journal"] == "Chemical Science"
        assert entry["year"] == "2011"
        assert "Varughese" in entry["authors"]
        assert len(entry["title"]) > 10
        # Space group
        assert "21/c" in entry["sg"]

    def test_get_structure_hydroxyapatite(self, tool_config):
        """Test retrieval of a different structure (hydroxyapatite)."""
        from tooluniverse.cod_tool import CODTool

        config = tool_config["COD_get_structure"]
        tool = CODTool(config)
        result = tool.run({"cod_id": "2300273"})

        assert result["status"] == "success"
        entry = result["data"][0]
        assert "Ca" in entry["formula"]
        assert entry["sgNumber"] == "176"


class TestCODToolSDK:
    """Level 2: Python SDK wrapper testing."""

    def test_sdk_search(self):
        """Test SDK wrapper for search."""
        from tooluniverse.tools.COD_search_structures import COD_search_structures

        result = COD_search_structures(query="aspirin", max_results=2)
        assert result["status"] == "success"
        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0

    def test_sdk_get_structure(self):
        """Test SDK wrapper for get structure."""
        from tooluniverse.tools.COD_get_structure import COD_get_structure

        result = COD_get_structure(cod_id="1515581")
        assert result["status"] == "success"
        assert isinstance(result["data"], list)
        assert result["data"][0]["file"] == "1515581"
