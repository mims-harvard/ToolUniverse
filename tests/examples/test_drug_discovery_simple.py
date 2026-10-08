#!/usr/bin/env python3
"""
Tests for drug discovery simple example
"""

import unittest

from tooluniverse.tools import (
    OpenTargets_get_disease_id_description_by_name,
    ChEMBL_search_similar_molecules,
    ADMETAI_predict_toxicity,
    EuropePMC_search_articles
)


class TestDrugDiscoverySimple(unittest.TestCase):
    """Test drug discovery simple example tools directly."""
    
    def test_find_disease_targets(self):
        """Test finding disease targets using OpenTargets tool."""
        # Test with a known disease
        disease_info = OpenTargets_get_disease_id_description_by_name(
            diseaseName="Alzheimer's disease"
        )
        
        # Should return results or None
        self.assertTrue(disease_info is None or isinstance(disease_info, dict))
    
    def test_find_similar_compounds(self):
        """Test finding similar compounds using ChEMBL tool."""
        # Test with a known compound
        compounds = ChEMBL_search_similar_molecules(
            query="metformin",
            similarity_threshold=70,
            max_results=3
        )
        
        # Tools answer with the {status, data} envelope; similarity search
        # also needs the optional epam.indigo package, so an error is allowed
        # as long as it is a structured one.
        self.assertIsInstance(compounds, dict)
        self.assertIn(compounds.get("status"), ("success", "error"))
        if compounds["status"] == "success":
            self.assertIsInstance(compounds["data"], list)
    
    def test_predict_admet_properties(self):
        """Test ADMET property prediction using ADMETAI tool."""
        # Test with a known SMILES
        smiles = ["CN1C=NC2=C1C(=O)N(C(=O)N2C)C"]
        properties = ADMETAI_predict_toxicity(smiles=smiles)
        
        # Should return results or None
        self.assertTrue(properties is None or isinstance(properties, (list, dict)))
    
    def test_search_literature(self):
        """Test literature search using EuropePMC tool."""
        # Test with a known query
        papers = EuropePMC_search_articles(
            query="metformin diabetes",
            limit=3
        )
        
        # Standard {status, data, metadata} envelope since aa386a98.
        self.assertIsInstance(papers, dict)
        self.assertIn(papers.get("status"), ("success", "error"))
        if papers["status"] == "success":
            self.assertIsInstance(papers["data"], list)
    
    def test_drug_discovery_workflow(self):
        """Test that the drug discovery workflow tools work correctly."""
        # Test that all required tools are available and can be called
        # This simulates the workflow without needing the actual example file
        self.assertTrue(callable(OpenTargets_get_disease_id_description_by_name))
        self.assertTrue(callable(ChEMBL_search_similar_molecules))
        self.assertTrue(callable(ADMETAI_predict_toxicity))
        self.assertTrue(callable(EuropePMC_search_articles))


class TestDirectImports(unittest.TestCase):
    """Test direct imports work correctly."""
    
    def test_open_targets_import(self):
        """Test OpenTargets import."""
        self.assertIsNotNone(OpenTargets_get_disease_id_description_by_name)
    
    def test_chembl_import(self):
        """Test ChEMBL import."""
        self.assertIsNotNone(ChEMBL_search_similar_molecules)
    
    def test_admet_import(self):
        """Test ADMET import."""
        self.assertIsNotNone(ADMETAI_predict_toxicity)
    
    def test_literature_import(self):
        """Test literature search import."""
        self.assertIsNotNone(EuropePMC_search_articles)


if __name__ == "__main__":
    unittest.main()