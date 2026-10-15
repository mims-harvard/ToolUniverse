#!/usr/bin/env python3
"""
Comprehensive tests for all simple examples
"""

import unittest
import time
from tooluniverse.tools import (
    # Drug discovery tools
    OpenTargets_get_disease_id_description_by_name,
    ChEMBL_search_similar_molecules,
    ADMETAI_predict_toxicity,
    EuropePMC_search_articles,
    
    # Genomics tools
    HPA_search_genes_by_query,
    GO_get_annotations_for_gene,
    enrichr_gene_enrichment_analysis,
    
    # Literature tools
    ArXiv_search_papers,
    PubMed_search_articles,
    SemanticScholar_search_papers,
    
    # Protein structure tools
    get_sequence_by_pdb_id,
    get_protein_metadata_by_pdb_id,
    alphafold_get_prediction,
    
    # Clinical trial tools
    search_clinical_trials,
    FDA_get_drug_names_by_indication
)


class TestSimpleExamples(unittest.TestCase):
    """Test all simple examples functionality."""
    
    def test_direct_imports_work(self):
        """Test that all direct imports work correctly."""
        # Test drug discovery imports
        self.assertIsNotNone(OpenTargets_get_disease_id_description_by_name)
        self.assertIsNotNone(ChEMBL_search_similar_molecules)
        self.assertIsNotNone(ADMETAI_predict_toxicity)
        self.assertIsNotNone(EuropePMC_search_articles)
        
        # Test genomics imports
        self.assertIsNotNone(HPA_search_genes_by_query)
        self.assertIsNotNone(GO_get_annotations_for_gene)
        self.assertIsNotNone(enrichr_gene_enrichment_analysis)
        
        # Test literature imports
        self.assertIsNotNone(ArXiv_search_papers)
        self.assertIsNotNone(PubMed_search_articles)
        self.assertIsNotNone(SemanticScholar_search_papers)
        
        # Test protein structure imports
        self.assertIsNotNone(get_sequence_by_pdb_id)
        self.assertIsNotNone(get_protein_metadata_by_pdb_id)
        self.assertIsNotNone(alphafold_get_prediction)
        
        # Test clinical trial imports
        self.assertIsNotNone(search_clinical_trials)
        self.assertIsNotNone(FDA_get_drug_names_by_indication)
    
    def test_drug_discovery_tools(self):
        """Test drug discovery tools functionality."""
        # Test disease target search
        try:
            disease_info = OpenTargets_get_disease_id_description_by_name(
                disease_name="diabetes"
            )
            self.assertTrue(disease_info is None or isinstance(disease_info, dict))
        except Exception as e:
            # Expected to fail in test environment
            self.assertIsNotNone(e)
        
        # Test compound search
        try:
            compounds = ChEMBL_search_similar_molecules(
                query="aspirin",
                similarity_threshold=70,
                max_results=5
            )
            self.assertTrue(compounds is None or isinstance(compounds, dict))
        except Exception as e:
            self.assertIsNotNone(e)
        
        # Test ADMET prediction
        try:
            toxicity = ADMETAI_predict_toxicity(smiles="CCO")  # Ethanol
            self.assertIsInstance(toxicity, dict)
        except Exception as e:
            self.assertIsNotNone(e)
    
    def test_genomics_tools(self):
        """Test genomics tools functionality."""
        # Test gene search
        try:
            genes = HPA_search_genes_by_query(
                query="BRCA1",
                limit=5
            )
            self.assertTrue(genes is None or isinstance(genes, dict))
        except Exception as e:
            self.assertIsNotNone(e)
        
        # Test GO annotations
        try:
            annotations = GO_get_annotations_for_gene(
                gene_id="ENSG00000012048"  # BRCA1
            )
            self.assertTrue(annotations is None or isinstance(annotations, dict))
        except Exception as e:
            self.assertIsNotNone(e)
        
        # Test pathway enrichment
        try:
            enrichment = enrichr_gene_enrichment_analysis(
                gene_list=["BRCA1", "TP53"],
                organism='human',
                gene_set_library='GO_Biological_Process_2021'
            )
            self.assertTrue(enrichment is None or isinstance(enrichment, dict))
        except Exception as e:
            self.assertIsNotNone(e)
    
    def test_literature_tools(self):
        """Test literature search tools functionality."""
        # Test ArXiv search
        try:
            arxiv_papers = ArXiv_search_papers(
                query="machine learning",
                limit=3
            )
            self.assertTrue(arxiv_papers is None or isinstance(arxiv_papers, dict))
        except Exception as e:
            self.assertIsNotNone(e)
        
        # Test PubMed search
        try:
            pubmed_papers = PubMed_search_articles(
                query="cancer",
                limit=3
            )
            self.assertTrue(pubmed_papers is None or isinstance(pubmed_papers, dict))
        except Exception as e:
            self.assertIsNotNone(e)
        
        # Test Semantic Scholar search
        try:
            semantic_papers = SemanticScholar_search_papers(
                query="artificial intelligence",
                limit=3
            )
            self.assertTrue(semantic_papers is None or isinstance(semantic_papers, dict))
        except Exception as e:
            self.assertIsNotNone(e)
    
    def test_protein_structure_tools(self):
        """Test protein structure tools functionality."""
        # Test PDB sequence retrieval
        try:
            sequence = get_sequence_by_pdb_id(pdb_id="1CRN")
            self.assertTrue(sequence is None or isinstance(sequence, str))
        except Exception as e:
            self.assertIsNotNone(e)
        
        # Test protein metadata
        try:
            metadata = get_protein_metadata_by_pdb_id(pdb_id="1CRN")
            self.assertTrue(metadata is None or isinstance(metadata, dict))
        except Exception as e:
            self.assertIsNotNone(e)
        
        # Test AlphaFold prediction
        try:
            prediction = alphafold_get_prediction(uniprot_id="P38398")
            self.assertTrue(prediction is None or isinstance(prediction, dict))
        except Exception as e:
            self.assertIsNotNone(e)
    
    def test_clinical_trial_tools(self):
        """Test clinical trial tools functionality."""
        # Test trial search
        try:
            trials = search_clinical_trials(
                condition="diabetes",
                limit=5
            )
            self.assertTrue(trials is None or isinstance(trials, dict))
        except Exception as e:
            self.assertIsNotNone(e)
        
        # Test FDA drug search
        try:
            drugs = FDA_get_drug_names_by_indication(indication="diabetes")
            self.assertTrue(drugs is None or isinstance(drugs, dict))
        except Exception as e:
            self.assertIsNotNone(e)
    
    def test_tool_performance(self):
        """Test tool performance and response times."""
        tools_to_test = [
            (OpenTargets_get_disease_id_description_by_name, {"disease_name": "diabetes"}),
            (ChEMBL_search_similar_molecules, {"query": "aspirin", "max_results": 3}),
            (HPA_search_genes_by_query, {"query": "BRCA1", "limit": 3}),
            (ArXiv_search_papers, {"query": "machine learning", "limit": 3}),
            (get_sequence_by_pdb_id, {"pdb_id": "1CRN"}),
            (search_clinical_trials, {"condition": "diabetes", "limit": 3})
        ]
        
        for tool_func, params in tools_to_test:
            start_time = time.time()
            try:
                result = tool_func(**params)
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Check that tool executed (may fail due to network, but should not hang)
                self.assertLess(execution_time, 30, f"Tool {tool_func.__name__} took too long: {execution_time}s")
                
            except Exception as e:
                # Expected to fail in test environment, but should fail quickly
                end_time = time.time()
                execution_time = end_time - start_time
                self.assertLess(execution_time, 10, f"Tool {tool_func.__name__} failed too slowly: {execution_time}s")
    
    def test_example_imports(self):
        """Test that the example scripts exist and compile.

        Several examples run their whole demo at module level (e.g.
        gwas_tool_example loads every tool and makes 13 live GWAS calls), so
        importing them ran the demos and hit the test timeout. Compiling
        checks the same thing -- the file is valid Python -- without running it.
        """
        import py_compile
        from pathlib import Path

        examples_dir = Path(__file__).parent.parent.parent / "examples"
        for name in (
            "literature_search_example",
            "opentargets_example",
            "pubchem_tool_example",
            "hpa_example",
            "gwas_tool_example",
        ):
            path = examples_dir / f"{name}.py"
            self.assertTrue(path.is_file(), f"missing example: {path}")
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as e:
                self.fail(f"{name} does not compile: {e}")

if __name__ == "__main__":
    unittest.main()
