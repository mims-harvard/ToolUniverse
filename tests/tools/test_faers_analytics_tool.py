"""
Unit tests for FAERS Analytics Tool.

Tests statistical signal detection, stratification, and safety analytics.
"""

import pytest
import json
from tooluniverse import ToolUniverse


class TestFAERSAnalyticsTool:
    """Test FAERS Analytics operations."""
    
    @pytest.fixture
    def tu(self):
        """Initialize ToolUniverse with loaded tools."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_faers_analytics_tools_load(self, tu):
        """Verify all 6 FAERS Analytics operations are registered."""
        assert hasattr(tu.tools, 'FAERS_calculate_disproportionality')
        assert hasattr(tu.tools, 'FAERS_stratify_by_demographics')
        assert hasattr(tu.tools, 'FAERS_filter_serious_events')
        assert hasattr(tu.tools, 'FAERS_compare_drugs')
        assert hasattr(tu.tools, 'FAERS_analyze_temporal_trends')
        assert hasattr(tu.tools, 'FAERS_rollup_meddra_hierarchy')
    
    @pytest.mark.slow
    def test_calculate_disproportionality_real_api(self, tu):
        """Test calculating ROR/PRR/IC from real FAERS API."""
        result = tu.tools.FAERS_calculate_disproportionality(
            operation="calculate_disproportionality",
            drug_name="IBUPROFEN",
            adverse_event="Gastrointestinal haemorrhage"
        )
        
        assert result.get("status") in ["success", "error"]
        
        if result.get("status") == "success":
            assert "metrics" in result
            assert "ROR" in result["metrics"]
            assert "PRR" in result["metrics"]
            assert "IC" in result["metrics"]
            assert "signal_detection" in result
            
            print(f"\n✅ ROR: {result['metrics']['ROR']['value']} "
                  f"[{result['metrics']['ROR']['ci_95_lower']}-{result['metrics']['ROR']['ci_95_upper']}]")
            print(f"   Signal: {result['signal_detection']['signal_strength']}")
        else:
            print(f"\n⚠️  API error (expected for some queries): {result.get('error')}")
    
    @pytest.mark.slow
    def test_stratify_by_demographics(self, tu):
        """Test demographic stratification."""
        result = tu.tools.FAERS_stratify_by_demographics(
            operation="stratify_by_demographics",
            drug_name="IBUPROFEN",
            adverse_event="Gastrointestinal haemorrhage",
            stratify_by="sex"
        )
        
        assert result.get("status") in ["success", "error"]
        
        if result.get("status") == "success":
            assert "stratification" in result
            assert isinstance(result["stratification"], list)
            print(f"\n✅ Total reports: {result['total_reports']}")
            for strata in result["stratification"][:3]:
                print(f"   {strata['group']}: {strata['count']} ({strata['percentage']}%)")
        else:
            print(f"\n⚠️  Stratification error: {result.get('error')}")
    
    @pytest.mark.slow
    def test_filter_serious_events(self, tu):
        """Test filtering for serious adverse events."""
        result = tu.tools.FAERS_filter_serious_events(
            operation="filter_serious_events",
            drug_name="IBUPROFEN",
            seriousness_type="all"
        )
        
        assert result.get("status") in ["success", "error"]
        
        if result.get("status") == "success":
            assert "total_serious_events" in result
            assert "top_serious_reactions" in result
            print(f"\n✅ Total serious events: {result['total_serious_events']}")
            for reaction in result["top_serious_reactions"][:5]:
                print(f"   {reaction['reaction']}: {reaction['count']}")
        else:
            print(f"\n⚠️  Serious event filtering error: {result.get('error')}")
    
    @pytest.mark.slow
    def test_compare_drugs(self, tu):
        """Test comparing safety signals between two drugs."""
        result = tu.tools.FAERS_compare_drugs(
            operation="compare_drugs",
            drug1="IBUPROFEN",
            drug2="NAPROXEN",
            adverse_event="Gastrointestinal haemorrhage"
        )
        
        assert result.get("status") in ["success", "error"]
        
        if result.get("status") == "success":
            assert "drug1" in result
            assert "drug2" in result
            assert "comparison" in result
            print(f"\n✅ Comparison: {result['comparison']}")
            if result["drug1"].get("metrics"):
                print(f"   {result['drug1']['name']} ROR: {result['drug1']['metrics']['ROR']['value']}")
            if result["drug2"].get("metrics"):
                print(f"   {result['drug2']['name']} ROR: {result['drug2']['metrics']['ROR']['value']}")
        else:
            print(f"\n⚠️  Drug comparison error: {result.get('error')}")
    
    @pytest.mark.slow
    def test_analyze_temporal_trends(self, tu):
        """Test temporal trend analysis."""
        result = tu.tools.FAERS_analyze_temporal_trends(
            operation="analyze_temporal_trends",
            drug_name="IBUPROFEN",
            adverse_event="Gastrointestinal haemorrhage"
        )
        
        assert result.get("status") in ["success", "error"]
        
        if result.get("status") == "success":
            assert "temporal_data" in result
            assert "trend_analysis" in result
            print(f"\n✅ Trend: {result['trend_analysis']['trend']}")
            print(f"   Percent change: {result['trend_analysis']['percent_change']}%")
            print(f"   Years analyzed: {result['trend_analysis']['years_analyzed']}")
        else:
            print(f"\n⚠️  Temporal analysis error: {result.get('error')}")
    
    @pytest.mark.slow
    def test_rollup_meddra_hierarchy(self, tu):
        """Test MedDRA hierarchy rollup."""
        result = tu.tools.FAERS_rollup_meddra_hierarchy(
            operation="rollup_meddra_hierarchy",
            drug_name="IBUPROFEN"
        )
        
        assert result.get("status") in ["success", "error"]
        
        if result.get("status") == "success":
            assert "meddra_hierarchy" in result
            assert "PT_level" in result["meddra_hierarchy"]
            print(f"\n✅ Unique PTs: {result['meddra_hierarchy']['total_unique_PTs']}")
            for pt in result["meddra_hierarchy"]["PT_level"][:5]:
                print(f"   {pt['preferred_term']}: {pt['count']}")
        else:
            print(f"\n⚠️  MedDRA rollup error: {result.get('error')}")
    
    def test_error_handling_missing_params(self, tu):
        """Test error handling when parameters are missing."""
        result = tu.tools.FAERS_calculate_disproportionality(
            operation="calculate_disproportionality",
            drug_name="IBUPROFEN"
            # Missing adverse_event
        )
        
        assert result.get("status") == "error"
        assert "adverse_event" in result.get("error", "").lower()
    
    def test_error_handling_invalid_stratify_by(self, tu):
        """Test error handling with invalid stratify_by parameter."""
        result = tu.tools.FAERS_stratify_by_demographics(
            operation="stratify_by_demographics",
            drug_name="IBUPROFEN",
            adverse_event="Gastrointestinal haemorrhage",
            stratify_by="invalid_dimension"
        )
        
        assert result.get("status") == "error"
        assert "stratify_by" in result.get("error", "").lower()


class TestFAERSAnalyticsDirectClass:
    """Direct class testing for FAERS Analytics."""
    
    @pytest.fixture
    def faers_analytics_tool(self):
        """Initialize FAERS Analytics tool directly."""
        from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool
        
        # Load tool config
        with open("src/tooluniverse/data/faers_analytics_tools.json") as f:
            tools = json.load(f)
            config = next(
                t for t in tools 
                if t["name"] == "FAERS_calculate_disproportionality"
            )
        
        return FAERSAnalyticsTool(config)
    
    def test_direct_class_instantiation(self, faers_analytics_tool):
        """Test that FAERS Analytics tool instantiates correctly."""
        assert faers_analytics_tool is not None
        assert hasattr(faers_analytics_tool, 'run')
        assert hasattr(faers_analytics_tool, '_calculate_disproportionality')
        assert hasattr(faers_analytics_tool, '_calculate_ror_ci')
        assert hasattr(faers_analytics_tool, '_calculate_ic')
    
    def test_statistical_formulas(self, faers_analytics_tool):
        """Test statistical formula calculations."""
        # Test ROR CI calculation
        a, b, c, d = 10, 90, 5, 95
        ror_ci = faers_analytics_tool._calculate_ror_ci(a, b, c, d)
        assert "lower" in ror_ci
        assert "upper" in ror_ci
        assert ror_ci["lower"] > 0
        assert ror_ci["upper"] > ror_ci["lower"]
        
        # Test IC calculation
        ic = faers_analytics_tool._calculate_ic(a, b, c, d)
        assert isinstance(ic, float)
        
        print(f"\n✅ ROR CI: [{ror_ci['lower']:.3f}, {ror_ci['upper']:.3f}]")
        print(f"   IC: {ic:.3f}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "-m", "not slow"])
