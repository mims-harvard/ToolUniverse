"""
Default tool configuration files mapping.

This module contains the default mapping of tool categories to their JSON configuration files.
It's separated from __init__.py to avoid circular imports.
"""

import os
import json
from pathlib import Path

# Get the current directory where this file is located
current_dir = os.path.dirname(os.path.abspath(__file__))

default_tool_files = {
    "special_tools": os.path.join(current_dir, "data", "special_tools.json"),
    "tool_finder": os.path.join(current_dir, "data", "finder_tools.json"),
    # 'tool_finder_llm': os.path.join(current_dir, 'data', 'tool_finder_llm_config.json'),
    "opentarget": os.path.join(current_dir, "data", "opentarget_tools.json"),
    "fda_drug_label": os.path.join(current_dir, "data", "fda_drug_labeling_tools.json"),
    "monarch": os.path.join(current_dir, "data", "monarch_tools.json"),
    "clinical_trials": os.path.join(
        current_dir, "data", "clinicaltrials_gov_tools.json"
    ),
    "fda_drug_adverse_event": os.path.join(
        current_dir, "data", "fda_drug_adverse_event_tools.json"
    ),
    "fda_drug_adverse_event_detail": os.path.join(
        current_dir, "data", "fda_drug_adverse_event_detail_tools.json"
    ),
    "ChEMBL": os.path.join(current_dir, "data", "chembl_tools.json"),
    "EuropePMC": os.path.join(current_dir, "data", "europe_pmc_tools.json"),
    "semantic_scholar": os.path.join(
        current_dir, "data", "semantic_scholar_tools.json"
    ),
    "pubtator": os.path.join(current_dir, "data", "pubtator_tools.json"),
    "EFO": os.path.join(current_dir, "data", "efo_tools.json"),
    "Enrichr": os.path.join(current_dir, "data", "enrichr_tools.json"),
    "HumanBase": os.path.join(current_dir, "data", "humanbase_tools.json"),
    "OpenAlex": os.path.join(current_dir, "data", "openalex_tools.json"),
    # Literature search tools
    "arxiv": os.path.join(current_dir, "data", "arxiv_tools.json"),
    "crossref": os.path.join(current_dir, "data", "crossref_tools.json"),
    "simbad": os.path.join(current_dir, "data", "simbad_tools.json"),
    "dblp": os.path.join(current_dir, "data", "dblp_tools.json"),
    "pubmed": os.path.join(current_dir, "data", "pubmed_tools.json"),
    "pubmed_search_mcp": os.path.join(current_dir, "data", "pubmed_search_tools.json"),
    "doaj": os.path.join(current_dir, "data", "doaj_tools.json"),
    "unpaywall": os.path.join(current_dir, "data", "unpaywall_tools.json"),
    "biorxiv": os.path.join(current_dir, "data", "biorxiv_tools.json"),
    "medrxiv": os.path.join(current_dir, "data", "medrxiv_tools.json"),
    "hal": os.path.join(current_dir, "data", "hal_tools.json"),
    "core": os.path.join(current_dir, "data", "core_tools.json"),
    "pmc": os.path.join(current_dir, "data", "pmc_tools.json"),
    "zenodo": os.path.join(current_dir, "data", "zenodo_tools.json"),
    "openaire": os.path.join(current_dir, "data", "openaire_tools.json"),
    "osf_preprints": os.path.join(current_dir, "data", "osf_preprints_tools.json"),
    "fatcat": os.path.join(current_dir, "data", "fatcat_tools.json"),
    "wikidata_sparql": os.path.join(current_dir, "data", "wikidata_sparql_tools.json"),
    "wikipedia": os.path.join(current_dir, "data", "wikipedia_tools.json"),
    "dbpedia": os.path.join(current_dir, "data", "dbpedia_tools.json"),
    "agents": os.path.join(current_dir, "data", "agentic_tools.json"),
    # Smolagents tool wrapper configs
    "smolagents": os.path.join(current_dir, "data", "smolagent_tools.json"),
    "tool_discovery_agents": os.path.join(
        current_dir, "data", "tool_discovery_agents.json"
    ),
    "web_search_tools": os.path.join(current_dir, "data", "web_search_tools.json"),
    "package_discovery_tools": os.path.join(
        current_dir, "data", "package_discovery_tools.json"
    ),
    "pypi_package_inspector_tools": os.path.join(
        current_dir, "data", "pypi_package_inspector_tools.json"
    ),
    "drug_discovery_agents": os.path.join(
        current_dir, "data", "drug_discovery_agents.json"
    ),
    "dataset": os.path.join(current_dir, "data", "dataset_tools.json"),
    # 'mcp_clients': os.path.join(current_dir, 'data', 'mcp_client_tools_example.json'),
    "mcp_auto_loader_txagent": os.path.join(
        current_dir, "data", "txagent_client_tools.json"
    ),
    "mcp_auto_loader_expert_feedback": os.path.join(
        current_dir, "data", "expert_feedback_tools.json"
    ),
    "adverse_event": os.path.join(current_dir, "data", "adverse_event_tools.json"),
    "dailymed": os.path.join(current_dir, "data", "dailymed_tools.json"),
    "hpa": os.path.join(current_dir, "data", "hpa_tools.json"),
    "reactome": os.path.join(current_dir, "data", "reactome_tools.json"),
    "pubchem": os.path.join(current_dir, "data", "pubchem_tools.json"),
    "medlineplus": os.path.join(current_dir, "data", "medlineplus_tools.json"),
    "rxnorm": os.path.join(current_dir, "data", "rxnorm_tools.json"),
    "uniprot": os.path.join(current_dir, "data", "uniprot_tools.json"),
    "cellosaurus": os.path.join(current_dir, "data", "cellosaurus_tools.json"),
    # 'software': os.path.join(current_dir, 'data', 'software_tools.json'),
    # Package tools - categorized software tools
    "software_bioinformatics": os.path.join(
        current_dir, "data", "packages", "bioinformatics_core_tools.json"
    ),
    "software_genomics": os.path.join(
        current_dir, "data", "packages", "genomics_tools.json"
    ),
    "software_single_cell": os.path.join(
        current_dir, "data", "packages", "single_cell_tools.json"
    ),
    "software_structural_biology": os.path.join(
        current_dir, "data", "packages", "structural_biology_tools.json"
    ),
    "software_cheminformatics": os.path.join(
        current_dir, "data", "packages", "cheminformatics_tools.json"
    ),
    "software_machine_learning": os.path.join(
        current_dir, "data", "packages", "machine_learning_tools.json"
    ),
    "software_visualization": os.path.join(
        current_dir, "data", "packages", "visualization_tools.json"
    ),
    # Scientific visualization tools
    "visualization_protein_3d": os.path.join(
        current_dir, "data", "protein_structure_3d_tools.json"
    ),
    "visualization_molecule_2d": os.path.join(
        current_dir, "data", "molecule_2d_tools.json"
    ),
    # New database tools
    "interpro": os.path.join(current_dir, "data", "interpro_tools.json"),
    "ebi_search": os.path.join(current_dir, "data", "ebi_search_tools.json"),
    "intact": os.path.join(current_dir, "data", "intact_tools.json"),
    "metabolights": os.path.join(current_dir, "data", "metabolights_tools.json"),
    "proteins_api": os.path.join(current_dir, "data", "proteins_api_tools.json"),
    "arrayexpress": os.path.join(current_dir, "data", "arrayexpress_tools.json"),
    "dbfetch": os.path.join(current_dir, "data", "dbfetch_tools.json"),
    "pdbe_api": os.path.join(current_dir, "data", "pdbe_api_tools.json"),
    "ena_browser": os.path.join(current_dir, "data", "ena_browser_tools.json"),
    "blast": os.path.join(current_dir, "data", "blast_tools.json"),
    "cbioportal": os.path.join(current_dir, "data", "cbioportal_tools.json"),
    "regulomedb": os.path.join(current_dir, "data", "regulomedb_tools.json"),
    "jaspar": os.path.join(current_dir, "data", "jaspar_tools.json"),
    "remap": os.path.join(current_dir, "data", "remap_tools.json"),
    "screen": os.path.join(current_dir, "data", "screen_tools.json"),
    "pride": os.path.join(current_dir, "data", "pride_tools.json"),
    "emdb": os.path.join(current_dir, "data", "emdb_tools.json"),
    "gtopdb": os.path.join(current_dir, "data", "gtopdb_tools.json"),
    "mpd": os.path.join(current_dir, "data", "mpd_tools.json"),
    "worms": os.path.join(current_dir, "data", "worms_tools.json"),
    "paleobiology": os.path.join(current_dir, "data", "paleobiology_tools.json"),
    "visualization_molecule_3d": os.path.join(
        current_dir, "data", "molecule_3d_tools.json"
    ),
    "software_scientific_computing": os.path.join(
        current_dir, "data", "packages", "scientific_computing_tools.json"
    ),
    "software_physics_astronomy": os.path.join(
        current_dir, "data", "packages", "physics_astronomy_tools.json"
    ),
    "software_earth_sciences": os.path.join(
        current_dir, "data", "packages", "earth_sciences_tools.json"
    ),
    "software_image_processing": os.path.join(
        current_dir, "data", "packages", "image_processing_tools.json"
    ),
    "software_neuroscience": os.path.join(
        current_dir, "data", "packages", "neuroscience_tools.json"
    ),
    "go": os.path.join(current_dir, "data", "gene_ontology_tools.json"),
    "compose": os.path.join(current_dir, "data", "compose_tools.json"),
    "python_executor": os.path.join(current_dir, "data", "python_executor_tools.json"),
    "idmap": os.path.join(current_dir, "data", "idmap_tools.json"),
    "disease_target_score": os.path.join(
        current_dir, "data", "disease_target_score_tools.json"
    ),
    "mcp_auto_loader_uspto_downloader": os.path.join(
        current_dir, "data", "uspto_downloader_tools.json"
    ),
    "uspto": os.path.join(current_dir, "data", "uspto_tools.json"),
    "xml": os.path.join(current_dir, "data", "xml_tools.json"),
    "mcp_auto_loader_boltz": os.path.join(
        current_dir, "data", "boltz_mcp_loader_tools.json"
    ),
    "url": os.path.join(current_dir, "data", "url_fetch_tools.json"),
    "file_download": os.path.join(current_dir, "data", "file_download_tools.json"),
    # 'langchain': os.path.join(current_dir, 'data', 'langchain_tools.json'),
    "rcsb_pdb": os.path.join(current_dir, "data", "rcsb_pdb_tools.json"),
    "rcsb_search": os.path.join(current_dir, "data", "rcsb_search_tools.json"),
    "tool_composition": os.path.join(
        current_dir, "data", "tool_composition_tools.json"
    ),
    "embedding": os.path.join(current_dir, "data", "embedding_tools.json"),
    "gwas": os.path.join(current_dir, "data", "gwas_tools.json"),
    "admetai": os.path.join(current_dir, "data", "admetai_tools.json"),
    # duplicate key removed
    "alphafold": os.path.join(current_dir, "data", "alphafold_tools.json"),
    "output_summarization": os.path.join(
        current_dir, "data", "output_summarization_tools.json"
    ),
    "odphp": os.path.join(current_dir, "data", "odphp_tools.json"),
    "who_gho": os.path.join(current_dir, "data", "who_gho_tools.json"),
    "umls": os.path.join(current_dir, "data", "umls_tools.json"),
    "euhealth": os.path.join(current_dir, "data", "euhealth_tools.json"),
    "markitdown": os.path.join(current_dir, "data", "markitdown_tools.json"),
    # Guideline and health policy tools
    "guidelines": os.path.join(current_dir, "data", "unified_guideline_tools.json"),
    # Database tools
    "kegg": os.path.join(current_dir, "data", "kegg_tools.json"),
    "ensembl": os.path.join(current_dir, "data", "ensembl_tools.json"),
    "clinvar": os.path.join(current_dir, "data", "clinvar_tools.json"),
    "geo": os.path.join(current_dir, "data", "geo_tools.json"),
    "dbsnp": os.path.join(current_dir, "data", "dbsnp_tools.json"),
    "gnomad": os.path.join(current_dir, "data", "gnomad_tools.json"),
    # Newly added database tools
    "gbif": os.path.join(current_dir, "data", "gbif_tools.json"),
    "obis": os.path.join(current_dir, "data", "obis_tools.json"),
    "wikipathways": os.path.join(current_dir, "data", "wikipathways_tools.json"),
    "rnacentral": os.path.join(current_dir, "data", "rnacentral_tools.json"),
    "encode": os.path.join(current_dir, "data", "encode_tools.json"),
    "gtex": os.path.join(current_dir, "data", "gtex_tools.json"),
    "mgnify": os.path.join(current_dir, "data", "mgnify_tools.json"),
    "gdc": os.path.join(current_dir, "data", "gdc_tools.json"),
    # Ontology tools
    "ols": os.path.join(current_dir, "data", "ols_tools.json"),
    "optimizer": os.path.join(current_dir, "data", "optimizer_tools.json"),
    # Compact mode core tools
    "compact_mode": os.path.join(current_dir, "data", "compact_mode_tools.json"),
    # New Life Science Tools
    "hca_tools": os.path.join(current_dir, "data", "hca_tools.json"),
    "clinical_trials_tools": os.path.join(
        current_dir, "data", "clinical_trials_tools.json"
    ),
    "iedb_tools": os.path.join(current_dir, "data", "iedb_tools.json"),
    "pathway_commons_tools": os.path.join(
        current_dir, "data", "pathway_commons_tools.json"
    ),
    "biomodels_tools": os.path.join(current_dir, "data", "biomodels_tools.json"),
    # BioThings APIs (MyGene, MyVariant, MyChem)
    "biothings": os.path.join(current_dir, "data", "biothings_tools.json"),
    # FDA Pharmacogenomic Biomarkers
    "fda_pharmacogenomic_biomarkers": os.path.join(
        current_dir, "data", "fda_pharmacogenomic_biomarkers_tools.json"
    ),
    # Metabolomics Workbench
    "metabolomics_workbench": os.path.join(
        current_dir, "data", "metabolomics_workbench_tools.json"
    ),
    # PharmGKB - Pharmacogenomics
    "pharmgkb": os.path.join(current_dir, "data", "pharmgkb_tools.json"),
    # DisGeNET - Gene-Disease Associations
    # DGIdb - Drug Gene Interactions
    "dgidb": os.path.join(current_dir, "data", "dgidb_tools.json"),
    # STITCH - Chemical-Protein Interactions
    "stitch": os.path.join(current_dir, "data", "stitch_tools.json"),
    # CIViC - Clinical Interpretation of Variants in Cancer
    "civic": os.path.join(current_dir, "data", "civic_tools.json"),
}

# Auto-load any user-provided tools from ~/.tooluniverse/user_tools/
user_tools_dir = os.path.expanduser("~/.tooluniverse/data/user_tools")

if os.path.exists(user_tools_dir):
    for filename in os.listdir(user_tools_dir):
        if filename.endswith(".json"):
            key = f"user_{filename.replace('.json', '')}"
            default_tool_files[key] = os.path.join(user_tools_dir, filename)


def _get_hook_config_file_path():
    """
    Get the path to the hook configuration file.

    This function uses the same logic as HookManager._get_config_file_path()
    to ensure consistent path resolution across different installation scenarios.

    Returns
        Path: Path to the hook_config.json file
    """
    try:
        import importlib.resources as pkg_resources
    except ImportError:
        import importlib_resources as pkg_resources

    try:
        data_files = pkg_resources.files("tooluniverse.template")
        return data_files / "hook_config.json"
    except Exception:
        return Path(__file__).parent / "template" / "hook_config.json"


def get_default_hook_config():
    """
    Get default hook configuration from hook_config.json.

    This function loads the default hook configuration from the hook_config.json
    template file, providing a single source of truth for default hook settings.
    If the file cannot be loaded, it falls back to a minimal configuration.

    Returns
        dict: Default hook configuration with basic settings
    """
    try:
        config_file = _get_hook_config_file_path()
        content = (
            config_file.read_text(encoding="utf-8")
            if hasattr(config_file, "read_text")
            else Path(config_file).read_text(encoding="utf-8")
        )
        return json.loads(content)
    except Exception:
        # Fallback to minimal configuration if file cannot be loaded
        # This ensures the system continues to work even if the config file
        # is missing or corrupted
        return {
            "global_settings": {
                "default_timeout": 30,
                "max_hook_depth": 3,
                "enable_hook_caching": True,
                "hook_execution_order": "priority_desc",
            },
            "exclude_tools": [
                "Tool_RAG",
                "ToolFinderEmbedding",
                "ToolFinderLLM",
            ],
            "hook_type_defaults": {
                "SummarizationHook": {
                    "default_output_length_threshold": 5000,
                    "default_chunk_size": 32000,
                    "default_focus_areas": "key_findings_and_results",
                    "default_max_summary_length": 3000,
                },
                "FileSaveHook": {
                    "default_temp_dir": None,
                    "default_file_prefix": "tool_output",
                    "default_include_metadata": True,
                    "default_auto_cleanup": False,
                    "default_cleanup_age_hours": 24,
                },
            },
            "hooks": [
                {
                    "name": "default_summarization_hook",
                    "type": "SummarizationHook",
                    "enabled": True,
                    "priority": 1,
                    "conditions": {
                        "output_length": {"operator": ">", "threshold": 5000}
                    },
                    "hook_config": {
                        "composer_tool": "OutputSummarizationComposer",
                        "chunk_size": 32000,
                        "focus_areas": "key_findings_and_results",
                        "max_summary_length": 3000,
                    },
                }
            ],
            "tool_specific_hooks": {},
            "category_hooks": {},
        }
