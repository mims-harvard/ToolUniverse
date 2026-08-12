"""
Tests for tool name shortening functionality.

This module tests the automatic tool name shortening feature added for
MCP 64-character limit compatibility.
"""

import pytest
from tooluniverse.tool_name_utils import shorten_tool_name, ToolNameMapper


class TestShortenToolName:
    """Tests for the shorten_tool_name function."""
    
    def test_short_name_unchanged(self):
        """Test that short names are not modified."""
        name = "FDA_get_drug_name"
        shortened = shorten_tool_name(name, max_length=55)
        assert shortened == name
        assert len(shortened) <= 55
    
    def test_long_name_shortened(self):
        """Test that long names are shortened."""
        name = "FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name"
        shortened = shorten_tool_name(name, max_length=55)
        
        assert len(shortened) <= 55
        assert shortened.startswith("FDA_")
        assert shortened != name
    
    def test_preserves_category_prefix(self):
        """Test that category prefix (first word) is preserved."""
        names = [
            "FDA_get_very_long_information_about_something",
            "UniProt_get_extremely_detailed_function_information",
        ]
        
        for name in names:
            shortened = shorten_tool_name(name, max_length=55)
            category = name.split('_')[0]
            assert shortened.startswith(category + "_")
    
    def test_fits_within_limit(self):
        """Test that shortened names always fit within the limit."""
        long_names = [
            "FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name",
            "euhealthinfo_search_diabetes_mellitus_epidemiology_registry",
        ]
        
        for name in long_names:
            shortened = shorten_tool_name(name, max_length=55)
            assert len(shortened) <= 55


class TestToolNameMapper:
    """Tests for the ToolNameMapper class."""
    
    def test_bidirectional_mapping(self):
        """Test that names can be mapped both directions."""
        mapper = ToolNameMapper()
        original = "FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name"
        
        # Shorten
        shortened = mapper.get_shortened(original, max_length=55)
        assert len(shortened) <= 55
        
        # Resolve back
        resolved = mapper.get_original(shortened)
        assert resolved == original
    
    def test_collision_handling(self):
        """Test that collisions are handled with counters."""
        mapper = ToolNameMapper()
        
        # Create two names that might shorten to the same thing
        name1 = "test_get_info"
        name2 = "test_get_information"
        
        short1 = mapper.get_shortened(name1, max_length=20)
        short2 = mapper.get_shortened(name2, max_length=20)
        
        # If they collide, second should have suffix
        if short1 == short2[:len(short1)]:
            assert "_2" in short2 or short2 != short1
        
        # Both should resolve correctly
        assert mapper.get_original(short1) == name1
        assert mapper.get_original(short2) == name2
    
    def test_caching(self):
        """Test that repeated calls return the same shortened name."""
        mapper = ToolNameMapper()
        name = "FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name"
        
        short1 = mapper.get_shortened(name, max_length=55)
        short2 = mapper.get_shortened(name, max_length=55)
        
        assert short1 == short2


class TestMCPCompatibility:
    """Tests for MCP 64-character limit compatibility."""
    
    def test_smcp_integration(self):
        """Test that SMCP automatically enables name shortening."""
        try:
            from tooluniverse.smcp import SMCP
        except Exception as e:
            pytest.skip(f"SMCP not available: {e}")
        
        server = SMCP(
            name='tu',
            tool_categories=['fda_drug_label'],
            auto_expose_tools=False,
            search_enabled=False
        )
        
        # SMCP should automatically enable name shortening
        assert server.tooluniverse.name_mapper is not None


class TestShortenedNameResolution:
    """Round-tripping a shortened name back to the registered tool.

    MCP clients only ever see the shortened name -- it is what the server
    advertises -- and call back with it. `ToolNameMapper.resolve()` covers
    alias->primary and original->short but never short->original, and its
    short->original index is only populated for names the *same process* has
    shortened. A client talking to a separately-started server therefore sent a
    name the mapper had never seen, and every such call failed with
    "not found even after loading tools".
    """

    @staticmethod
    def _universe(names):
        """A ToolUniverse with a fake registry and no tool loading."""
        from tooluniverse.execute_function import ToolUniverse

        tu = ToolUniverse.__new__(ToolUniverse)
        from tooluniverse.tool_name_utils import ToolNameMapper

        tu.name_mapper = ToolNameMapper()
        tu._name_mapper_primed = False
        tu.MAX_TOOL_NAME_LENGTH = 45
        tu.all_tool_dict = {n: {"name": n} for n in names}
        return tu

    LONG = "OpenTargets_get_diseases_phenotypes_by_target_ensembl"

    def test_shortened_name_resolves_to_registered_name(self):
        tu = self._universe([self.LONG])
        short = shorten_tool_name(self.LONG, 45)
        assert short != self.LONG
        assert tu._resolve_tool_name(short) == self.LONG

    def test_priming_happens_before_speculative_shortening(self):
        """resolve() caches a short name as its own original on a miss; if that
        runs before priming, the real original collides and is pushed to a _2
        suffix, silently breaking exactly the names that need the round trip."""
        tu = self._universe([self.LONG])
        short = shorten_tool_name(self.LONG, 45)
        tu._resolve_tool_name(short)  # first call must not poison the cache
        assert tu._resolve_tool_name(short) == self.LONG

    def test_registered_name_is_returned_unchanged(self):
        tu = self._universe([self.LONG, "ChEMBL_search_mechanisms"])
        assert tu._resolve_tool_name("ChEMBL_search_mechanisms") == "ChEMBL_search_mechanisms"
        assert tu._resolve_tool_name(self.LONG) == self.LONG

    def test_unknown_name_is_returned_unchanged(self):
        tu = self._universe([self.LONG])
        assert tu._resolve_tool_name("NoSuchToolAtAll") == "NoSuchToolAtAll"

    def test_empty_name_is_returned_unchanged(self):
        assert self._universe([self.LONG])._resolve_tool_name("") == ""

    def test_priming_is_skipped_for_a_direct_hit(self):
        """The fast path must not pay for priming."""
        tu = self._universe(["ChEMBL_search_mechanisms"])
        tu._resolve_tool_name("ChEMBL_search_mechanisms")
        assert tu._name_mapper_primed is False

    def test_priming_runs_once(self):
        tu = self._universe([self.LONG])
        tu._resolve_tool_name("miss_one")
        assert tu._name_mapper_primed is True
        calls = []
        original = tu.name_mapper.get_shortened
        tu.name_mapper.get_shortened = lambda *a, **k: (calls.append(1), original(*a, **k))[1]
        tu._resolve_tool_name("miss_two")
        assert len(calls) <= 1  # resolve()'s own lookup only, no re-priming
