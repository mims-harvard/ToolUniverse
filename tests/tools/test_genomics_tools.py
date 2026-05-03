#!/usr/bin/env python3
"""
Tests for genomics tools integration.
Tests both original GWAS tools and new genomics tools.
"""

import unittest
import sys
import os
import json
from pathlib import Path
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tooluniverse import ToolUniverse
import tooluniverse as _tu_pkg


@pytest.mark.network
class TestGenomicsToolsIntegration(unittest.TestCase):
    """Test genomics tools integration with ToolUniverse."""

    @classmethod
    def setUpClass(cls):
        """Set up test class with ToolUniverse instance."""
        cls.tu = ToolUniverse()

        # Load original GWAS tools
        cls.tu.load_tools(tool_type=["gwas"])

        # Load and register new genomics tools
        config_path = Path(_tu_pkg.__file__).parent / "data" / "genomics_tools.json"
        if not config_path.exists():
            raise unittest.SkipTest(f"genomics_tools.json not found at {config_path}")
        with open(config_path, 'r') as f:
            genomics_configs = json.load(f)
        
        from tooluniverse.ensembl_tool import EnsemblTool
        from tooluniverse.clinvar_tool import ClinVarTool
        from tooluniverse.dbsnp_tool import DbSnpTool
        from tooluniverse.ucsc_tool import UCSCTool
        from tooluniverse.gnomad_tool import GnomadTool
        from tooluniverse.genomics_gene_search_tool import GWASGeneSearch
        
        tools = [
            (EnsemblTool, "EnsemblTool"),
            (ClinVarTool, "ClinVarTool"),
            (DbSnpTool, "DbSnpTool"),
            (UCSCTool, "UCSCTool"),
            (GnomadTool, "GnomadTool"),
            (GWASGeneSearch, "GWASGeneSearch")
        ]
        
        for tool_class, tool_type in tools:
            config = next((c for c in genomics_configs if c["type"] == tool_type), None)
            if config:
                cls.tu.register_custom_tool(tool_class, tool_config=config)

    @classmethod
    def tearDownClass(cls):
        """Clean up test class."""
        if hasattr(cls, 'tu') and cls.tu:
            cls.tu.close()
    
    def test_original_gwas_tools_loaded(self):
        """Test that original GWAS tools are loaded."""
        gwas_tools = [key for key in self.tu.all_tool_dict.keys() if 'gwas' in key.lower()]
        self.assertGreater(len(gwas_tools), 0, "No GWAS tools loaded")
        self.assertIn('gwas_search_associations', gwas_tools)
        self.assertIn('gwas_search_studies', gwas_tools)
        self.assertIn('gwas_get_snps_for_gene', gwas_tools)
    
    def test_new_genomics_tools_loaded(self):
        """Test that new genomics tools are loaded."""
        genomics_tools = [
            'Ensembl_lookup_gene_by_symbol',
            'ClinVar_search_variants',
            'dbSNP_get_variant_by_rsid',
            'UCSC_get_genes_by_region',
            'gnomAD_query_variant',
            'GWAS_search_associations_by_gene'
        ]
        
        for tool in genomics_tools:
            self.assertIn(tool, self.tu.all_tool_dict, f"Tool {tool} not loaded")
    
    def test_ensembl_gene_lookup(self):
        """Test Ensembl gene lookup functionality."""
        result = self.tu.run_one_function({
            "name": "Ensembl_lookup_gene_by_symbol",
            "arguments": {"symbol": "BRCA1"}
        })
        
        self.assertIsInstance(result, dict)
        self.assertNotIn('error', result)
        self.assertIn('id', result)
        self.assertEqual(result['symbol'], 'BRCA1')
        self.assertEqual(result['id'], 'ENSG00000012048')
        self.assertEqual(result['seq_region_name'], '17')
    
    def test_dbsnp_variant_lookup(self):
        """Test dbSNP variant lookup functionality."""
        result = self.tu.run_one_function({
            "name": "dbSNP_get_variant_by_rsid",
            "arguments": {"rsid": "rs699"}
        })
        
        self.assertIsInstance(result, dict)
        self.assertNotIn('error', result)
        self.assertIn('refsnp_id', result)
        self.assertEqual(result['refsnp_id'], 'rs699')
        self.assertEqual(result['chrom'], 'chr1')
    
    def test_gnomad_variant_query(self):
        """Test gnomAD variant query functionality."""
        result = self.tu.run_one_function({
            "name": "gnomAD_query_variant",
            "arguments": {"variant_id": "1-230710048-A-G"}
        })
        
        self.assertIsInstance(result, dict)
        self.assertNotIn('error', result)
        self.assertIn('variantId', result)
        self.assertEqual(result['variantId'], '1-230710048-A-G')
        self.assertIn('genome', result)
    
    def test_original_gwas_association_search(self):
        """Test original GWAS association search functionality."""
        result = self.tu.run_one_function({
            "name": "gwas_search_associations",
            "arguments": {
                "efo_trait": "breast cancer",
                "size": 2
            }
        })
        
        self.assertIsInstance(result, dict)
        self.assertNotIn('error', result)
        self.assertIn('data', result)
        self.assertIsInstance(result['data'], list)


if __name__ == "__main__":
    unittest.main()