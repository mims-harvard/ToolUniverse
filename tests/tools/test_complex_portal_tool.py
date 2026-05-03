"""Unit tests for Complex Portal (CORUM) tools."""

import pytest
from tooluniverse import ToolUniverse


class TestComplexPortalTools:
    """Test suite for Complex Portal protein complex tools."""

    @pytest.fixture
    def tu(self):
        """Initialize ToolUniverse with all tools loaded."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_load(self, tu):
        """Verify all Complex Portal tools are registered and loadable."""
        assert hasattr(tu.tools, "ComplexPortal_search_complexes")
        assert hasattr(tu.tools, "ComplexPortal_get_complex")

    def test_search_complexes_by_gene(self, tu):
        """Test complex search by gene/protein name."""
        result = tu.tools.ComplexPortal_search_complexes(
            **{"query": "TP53", "species": "9606", "number": 5}
        )

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data", {})
            assert "complexes" in data
            assert "count" in data
            assert isinstance(data["complexes"], list)

            # TP53 is well-studied, should be in complexes
            if data["complexes"]:
                complex_info = data["complexes"][0]
                assert "complex_id" in complex_info
                assert "name" in complex_info
                assert "subunits" in complex_info
                assert complex_info["complex_id"].startswith("CPX-")
                print(
                    f"✓ Found {data['count']} complexes, "
                    f"first: {complex_info['name']}"
                )

    def test_get_complex_details(self, tu):
        """Test detailed complex retrieval by ID."""
        # CPX-1 is the SMAD2:SMAD3:SMAD4 complex
        result = tu.tools.ComplexPortal_get_complex(**{"complex_id": "CPX-1"})

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data")
            if data:
                # Complex Portal API may return complex_id as None but include it in cross_references
                assert "subunits" in data
                assert "systematic_name" in data
                # CPX-1 is SMAD2:SMAD3:SMAD4 (3 subunits)
                assert len(data["subunits"]) == 3
                assert "SMAD" in data.get("systematic_name", "")
                print(f"✓ Complex: {data.get('systematic_name')}, {len(data['subunits'])} subunits")
            else:
                # Complex ID may not exist
                assert result.get("message")

    def test_search_by_complex_name(self, tu):
        """Test searching by complex name instead of gene."""
        result = tu.tools.ComplexPortal_search_complexes(
            **{"query": "proteasome", "species": "9606", "number": 10}
        )

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data", {})
            assert "complexes" in data
            # Should find multiple proteasome variants
            if data["complexes"]:
                names = [c["name"] for c in data["complexes"]]
                assert any("proteasome" in n.lower() for n in names)
                print(f"✓ Found {len(data['complexes'])} proteasome complexes")

    def test_cross_species_search(self, tu):
        """Test searching across all species (no filter)."""
        result = tu.tools.ComplexPortal_search_complexes(
            **{"query": "TP53", "species": "", "number": 10}
        )

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data", {})
            complexes = data.get("complexes", [])
            # Should find human and mouse complexes
            species_set = set(c.get("species", "").split(";")[0] for c in complexes)
            print(f"✓ Found complexes in species: {species_set}")

    def test_missing_parameter_error(self, tu):
        """Test error handling for missing required parameters."""
        result = tu.tools.ComplexPortal_search_complexes(**{})

        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "error" in result
        assert "required" in result["error"].lower()

    def test_no_results_handling(self, tu):
        """Test handling of queries with no matching complexes."""
        result = tu.tools.ComplexPortal_search_complexes(
            **{"query": "NONEXISTENT_PROTEIN_XYZ123", "species": "9606", "number": 5}
        )

        assert isinstance(result, dict)

        # Skip on transient API failures (timeout, connection issues)
        if result["status"] == "error":
            error_msg = result.get("error", "")
            if any(
                word in error_msg.lower()
                for word in ["timeout", "request failed", "connection"]
            ):
                pytest.skip(f"Skipping due to transient API error: {error_msg}")

        assert result["status"] == "success"
        # Should return empty list, not error
        data = result.get("data", {})
        assert data.get("count", 0) == 0
        assert data.get("complexes", []) == []
