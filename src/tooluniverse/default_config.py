"""Default tool configuration files mapping.

Separated from __init__.py to avoid circular imports.
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
    "literature_search": os.path.join(
        current_dir, "data", "literature_search_tools.json"
    ),
    "arxiv": os.path.join(current_dir, "data", "arxiv_tools.json"),
    "crossref": os.path.join(current_dir, "data", "crossref_tools.json"),
    "simbad": os.path.join(current_dir, "data", "simbad_tools.json"),
    "dblp": os.path.join(current_dir, "data", "dblp_tools.json"),
    "pubmed": os.path.join(current_dir, "data", "pubmed_tools.json"),
    "ncbi_nucleotide": os.path.join(current_dir, "data", "ncbi_nucleotide_tools.json"),
    "ncbi_sra": os.path.join(current_dir, "data", "ncbi_sra_tools.json"),
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
    "fda_orange_book": os.path.join(current_dir, "data", "fda_orange_book_tools.json"),
    "faers_analytics": os.path.join(current_dir, "data", "faers_analytics_tools.json"),
    "cdc": os.path.join(current_dir, "data", "cdc_tools.json"),
    "nhanes": os.path.join(current_dir, "data", "nhanes_tools.json"),
    "health_disparities": os.path.join(
        current_dir, "data", "health_disparities_tools.json"
    ),
    "hpa": os.path.join(current_dir, "data", "hpa_tools.json"),
    "reactome": os.path.join(current_dir, "data", "reactome_tools.json"),
    "pubchem": os.path.join(current_dir, "data", "pubchem_tools.json"),
    "medlineplus": os.path.join(current_dir, "data", "medlineplus_tools.json"),
    "rxnorm": os.path.join(current_dir, "data", "rxnorm_tools.json"),
    "loinc": os.path.join(current_dir, "data", "loinc_tools.json"),
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
    "biostudies": os.path.join(current_dir, "data", "biostudies_tools.json"),
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
    "sasbdb": os.path.join(current_dir, "data", "sasbdb_tools.json"),
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
    "icd": os.path.join(current_dir, "data", "icd_tools.json"),
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
    # Single-cell RNA-seq data
    "cellxgene_census": os.path.join(
        current_dir, "data", "cellxgene_census_tools.json"
    ),
    # Chromatin and epigenetics data
    "chipatlas": os.path.join(current_dir, "data", "chipatlas_tools.json"),
    # 4DN Data Portal - 3D genome organization
    "fourdn": os.path.join(current_dir, "data", "fourdn_tools.json"),
    # GTEx Portal API V2 - Tissue-specific gene expression and eQTLs
    "gtex_v2": os.path.join(current_dir, "data", "gtex_v2_tools.json"),
    # Rfam Database API - RNA families (v15.1, January 2026)
    "rfam": os.path.join(current_dir, "data", "rfam_tools.json"),
    # BiGG Models API - Genome-scale metabolic models
    "bigg_models": os.path.join(current_dir, "data", "bigg_models_tools.json"),
    # Protein-Protein Interaction (PPI) tools - STRING and BioGRID
    "ppi": os.path.join(current_dir, "data", "ppi_tools.json"),
    # BioGRID - Genetic and Protein Interactions, Chemical-Protein, PTMs
    "biogrid": os.path.join(current_dir, "data", "biogrid_tools.json"),
    # NVIDIA NIM Healthcare APIs - Structure prediction, molecular docking, genomics
    "nvidia_nim": os.path.join(current_dir, "data", "nvidia_nim_tools.json"),
    # COSMIC - Catalogue of Somatic Mutations in Cancer
    "cosmic": os.path.join(current_dir, "data", "cosmic_tools.json"),
    # OncoKB - Precision Oncology Knowledge Base
    "oncokb": os.path.join(current_dir, "data", "oncokb_tools.json"),
    # OMIM - Online Mendelian Inheritance in Man
    "omim": os.path.join(current_dir, "data", "omim_tools.json"),
    # Orphanet - Rare Disease Encyclopedia
    "orphanet": os.path.join(current_dir, "data", "orphanet_tools.json"),
    # DisGeNET - Gene-Disease Associations
    "disgenet": os.path.join(current_dir, "data", "disgenet_tools.json"),
    # BindingDB - Protein-Ligand Binding Affinities
    "bindingdb": os.path.join(current_dir, "data", "bindingdb_tools.json"),
    # GPCRdb - G Protein-Coupled Receptor Database
    "gpcrdb": os.path.join(current_dir, "data", "gpcrdb_tools.json"),
    # BRENDA - Enzyme Kinetics Database
    "brenda": os.path.join(current_dir, "data", "brenda_tools.json"),
    # SAbDab - Structural Antibody Database
    "sabdab": os.path.join(current_dir, "data", "sabdab_tools.json"),
    # IMGT - International ImMunoGeneTics Information System
    "imgt": os.path.join(current_dir, "data", "imgt_tools.json"),
    # HMDB - Human Metabolome Database
    "hmdb": os.path.join(current_dir, "data", "hmdb_tools.json"),
    # MetaCyc - Metabolic Pathway Database
    "metacyc": os.path.join(current_dir, "data", "metacyc_tools.json"),
    # ZINC - Virtual Screening Library
    "zinc": os.path.join(current_dir, "data", "zinc_tools.json"),
    # Enamine - Make-on-Demand Compounds
    "enamine": os.path.join(current_dir, "data", "enamine_tools.json"),
    # eMolecules - Vendor Aggregator
    "emolecules": os.path.join(current_dir, "data", "emolecules_tools.json"),
    # Pharos/TCRD - NIH IDG Understudied Proteins Database
    "pharos": os.path.join(current_dir, "data", "pharos_tools.json"),
    # AlphaMissense - DeepMind Pathogenicity Predictions
    "alphamissense": os.path.join(current_dir, "data", "alphamissense_tools.json"),
    # CADD - Combined Annotation Dependent Depletion
    "cadd": os.path.join(current_dir, "data", "cadd_tools.json"),
    # DepMap - Cancer Dependency Map (Sanger Cell Model Passports)
    "depmap": os.path.join(current_dir, "data", "depmap_tools.json"),
    # InterProScan - Protein Domain/Family Prediction
    "interproscan": os.path.join(current_dir, "data", "interproscan_tools.json"),
    # EVE - Evolutionary Variant Effect Predictions
    "eve": os.path.join(current_dir, "data", "eve_tools.json"),
    # Thera-SAbDab - Therapeutic Structural Antibody Database
    "therasabdab": os.path.join(current_dir, "data", "therasabdab_tools.json"),
    # DeepGO - Protein Function Prediction
    "deepgo": os.path.join(current_dir, "data", "deepgo_tools.json"),
    # ClinGen - Gene-Disease Validity, Dosage Sensitivity, Actionability
    "clingen": os.path.join(current_dir, "data", "clingen_tools.json"),
    # SpliceAI - Deep Learning Splice Prediction
    "spliceai": os.path.join(current_dir, "data", "spliceai_tools.json"),
    # IMPC - International Mouse Phenotyping Consortium (mouse KO phenotypes)
    "impc": os.path.join(current_dir, "data", "impc_tools.json"),
    # Complex Portal - Curated protein complexes (includes CORUM mammalian complexes)
    "complex_portal": os.path.join(current_dir, "data", "complex_portal_tools.json"),
    # Expression Atlas - EBI GXA baseline + differential gene expression
    "expression_atlas": os.path.join(
        current_dir, "data", "expression_atlas_tools.json"
    ),
    # ProteinsPlus - Protein-ligand docking and binding site analysis
    "proteinsplus": os.path.join(current_dir, "data", "proteinsplus_tools.json"),
    # SwissDock - Molecular docking with AutoDock Vina and Attracting Cavities
    "swissdock": os.path.join(current_dir, "data", "swissdock_tools.json"),
    # LIPID MAPS - Lipid Structure Database (lipidomics)
    "lipidmaps": os.path.join(current_dir, "data", "lipidmaps_tools.json"),
    # USDA FoodData Central - Food composition and nutrient database
    "fooddata_central": os.path.join(
        current_dir, "data", "fooddata_central_tools.json"
    ),
    # CTD - Comparative Toxicogenomics Database (chemical-gene-disease interactions)
    "ctd": os.path.join(current_dir, "data", "ctd_tools.json"),
    # NeuroMorpho - Neuronal morphology database (neuron reconstructions, morphometrics)
    "neuromorpho": os.path.join(current_dir, "data", "neuromorpho_tools.json"),
    # Allen Brain Atlas - Brain gene expression and structure data
    "allen_brain": os.path.join(current_dir, "data", "allen_brain_tools.json"),
    # GlyGen - Glycoinformatics (glycan structures, glycoproteins, glycosylation sites)
    "glygen": os.path.join(current_dir, "data", "glygen_tools.json"),
    # MGnify Expanded - Metagenomics genome catalog, biomes, study details
    "mgnify_expanded": os.path.join(current_dir, "data", "mgnify_expanded_tools.json"),
    # SGD - Saccharomyces Genome Database (yeast genes, phenotypes, interactions)
    "sgd": os.path.join(current_dir, "data", "sgd_tools.json"),
    # NCBI Datasets API v2 - Gene info, orthologs, taxonomy, genome metadata
    "ncbi_datasets": os.path.join(current_dir, "data", "ncbi_datasets_tools.json"),
    # EBI Taxonomy - Taxonomic classification, lineage, name resolution
    "ebi_taxonomy": os.path.join(current_dir, "data", "ebi_taxonomy_tools.json"),
    # Alliance of Genome Resources - Cross-species gene data from 7 model organisms
    "alliance_genome": os.path.join(current_dir, "data", "alliance_genome_tools.json"),
    # Open Targets Genetics - GWAS variant annotation, credible sets, L2G predictions
    "opentarget_genetics": os.path.join(
        current_dir, "data", "opentarget_genetics_tools.json"
    ),
    # HGNC - HUGO Gene Nomenclature Committee (authoritative human gene naming)
    "hgnc": os.path.join(current_dir, "data", "hgnc_tools.json"),
    # BV-BRC - Bacterial and Viral Bioinformatics Resource Center (pathogen genomics, AMR)
    "bvbrc": os.path.join(current_dir, "data", "bvbrc_tools.json"),
    # BioImage Archive - EBI biological imaging data (microscopy, cryo-EM, fluorescence)
    "bioimage_archive": os.path.join(
        current_dir, "data", "bioimage_archive_tools.json"
    ),
    # Plant Reactome - Gramene plant metabolic and regulatory pathways (140+ species)
    "plant_reactome": os.path.join(current_dir, "data", "plant_reactome_tools.json"),
    # Ensembl VEP - Variant Effect Predictor (HGVS, rsID annotation, variant recoding)
    "ensembl_vep": os.path.join(current_dir, "data", "ensembl_vep_tools.json"),
    # ITIS - Integrated Taxonomic Information System (US taxonomy, hierarchy, common names)
    "itis": os.path.join(current_dir, "data", "itis_tools.json"),
    # QuickGO - EBI Gene Ontology annotation browser (annotations, term details, hierarchy)
    "quickgo": os.path.join(current_dir, "data", "quickgo_tools.json"),
    # Bgee - Comparative gene expression across 29+ animal species (RNA-Seq, Affymetrix, EST)
    "bgee": os.path.join(current_dir, "data", "bgee_tools.json"),
    # OMA - Orthologous MAtrix Browser (orthology across 2,600+ genomes, HOGs, OMA Groups)
    "oma": os.path.join(current_dir, "data", "oma_tools.json"),
    # CATH - Protein Structure Classification (Class, Architecture, Topology, Homologous superfamily)
    "cath": os.path.join(current_dir, "data", "cath_tools.json"),
    # MeSH - Medical Subject Headings (NLM controlled vocabulary for PubMed indexing)
    "mesh": os.path.join(current_dir, "data", "mesh_tools.json"),
    # JLCSearch - Electronic components search (resistors, capacitors, MCUs, ICs, LEDs, diodes)
    "jlcsearch": os.path.join(current_dir, "data", "jlcsearch_tools.json"),
    # Mouser Electronics - Major distributor API (pricing, availability, specs, datasheets)
    "mouser": os.path.join(current_dir, "data", "mouser_tools.json"),
    # Digi-Key Electronics - Major distributor API (product search, details, categories)
    "digikey": os.path.join(current_dir, "data", "digikey_tools.json"),
    # HPO - Human Phenotype Ontology (phenotype terms, hierarchy, clinical genetics)
    "hpo": os.path.join(current_dir, "data", "hpo_tools.json"),
    # Reactome Analysis Service - Pathway enrichment/overrepresentation analysis
    "reactome_analysis": os.path.join(
        current_dir, "data", "reactome_analysis_tools.json"
    ),
    # Rhea - Expert-curated biochemical reactions (SIB, linked to ChEBI and EC)
    "rhea": os.path.join(current_dir, "data", "rhea_tools.json"),
    # PubChem BioAssay - Biological screening data (drug discovery, toxicology)
    "pubchem_bioassay": os.path.join(
        current_dir, "data", "pubchem_bioassay_tools.json"
    ),
    # ENA Portal API - European Nucleotide Archive search (studies, samples, sequences)
    "ena_portal": os.path.join(current_dir, "data", "ena_portal_tools.json"),
    # PomBase - Fission yeast (S. pombe) genome database (gene info, phenotypes, domains)
    "pombase": os.path.join(current_dir, "data", "pombase_tools.json"),
    # EBI BioSamples - Biological sample metadata hub (60M+ samples, cross-archive)
    "biosamples": os.path.join(current_dir, "data", "biosamples_tools.json"),
    # GNPS - Mass spectrometry spectral library (metabolomics, natural products)
    "gnps": os.path.join(current_dir, "data", "gnps_tools.json"),
    # WormBase - C. elegans genome database (gene info, phenotypes, expression)
    "wormbase": os.path.join(current_dir, "data", "wormbase_tools.json"),
    # SWISS-MODEL Repository - Pre-computed protein homology models (ExPASy/SIB)
    "swissmodel": os.path.join(current_dir, "data", "swissmodel_tools.json"),
    # ProteomeXchange - Proteomics data consortium (PRIDE, MassIVE, jPOST)
    "proteomexchange": os.path.join(current_dir, "data", "proteomexchange_tools.json"),
    # PDBe Search - PDB structure search via EBI Solr (full-text, compounds, organisms)
    "pdbe_search": os.path.join(current_dir, "data", "pdbe_search_tools.json"),
    # Nextstrain - Pathogen phylogenetics and molecular epidemiology tracking
    "nextstrain": os.path.join(current_dir, "data", "nextstrain_tools.json"),
    # UCSC Genome Browser - Genome sequences, gene search, annotation tracks (220+ genomes)
    "ucsc_genome": os.path.join(current_dir, "data", "ucsc_genome_tools.json"),
    # ChEBI - Chemical Entities of Biological Interest (EBI chemical ontology, 195K+ compounds)
    "chebi": os.path.join(current_dir, "data", "chebi_tools.json"),
    # UniChem - EBI unified chemical cross-referencing across 40+ databases
    "unichem": os.path.join(current_dir, "data", "unichem_tools.json"),
    # PANTHER - Protein classification, gene enrichment, and ortholog analysis (144 organisms)
    "panther": os.path.join(current_dir, "data", "panther_tools.json"),
    # Ensembl LD - Linkage disequilibrium from 1000 Genomes (population genetics)
    "ensembl_ld": os.path.join(current_dir, "data", "ensembl_ld_tools.json"),
    # Ensembl Regulation - TF binding motifs, constrained elements, binding matrices
    "ensembl_regulation": os.path.join(
        current_dir, "data", "ensembl_regulation_tools.json"
    ),
    # Ensembl Phenotypes - Gene/region/variant phenotype associations (GWAS, ClinVar, OMIM)
    "ensembl_phenotype": os.path.join(
        current_dir, "data", "ensembl_phenotype_tools.json"
    ),
    # Europe PMC Annotations - Text-mined entities from articles (chemicals, organisms, GO)
    "europepmc_annotations": os.path.join(
        current_dir, "data", "europepmc_annotations_tools.json"
    ),
    # WFGY ProblemMap - LLM/RAG failure triage prompt bundle (local, no API call)
    "wfgy_promptbundle": os.path.join(
        current_dir, "data", "wfgy_promptbundle_tools.json"
    ),
    # UniProt ID Mapping - Cross-database identifier conversion (100+ databases)
    "uniprot_idmapping": os.path.join(
        current_dir, "data", "uniprot_idmapping_tools.json"
    ),
    # Open Tree of Life - Phylogenetic tree of life (name resolution, taxonomy, MRCA, subtrees)
    "opentree": os.path.join(current_dir, "data", "opentree_tools.json"),
    # iNaturalist - Citizen science biodiversity observations (taxa, observations, species counts)
    "inaturalist": os.path.join(current_dir, "data", "inaturalist_tools.json"),
    # NCI Thesaurus - National Cancer Institute terminology (cancer diseases, drugs, genes)
    "nci_thesaurus": os.path.join(current_dir, "data", "nci_thesaurus_tools.json"),
    # ClinGen Allele Registry - Standardized allele IDs (HGVS normalization, cross-references)
    "clingen_ar": os.path.join(current_dir, "data", "clingen_ar_tools.json"),
    # NDEx - Network Data Exchange (biological network repository, PPI, signaling, regulatory networks)
    "ndex": os.path.join(current_dir, "data", "ndex_tools.json"),
    # Gene Ontology API - GO term details, gene functional annotations, gene-function associations
    "go_api": os.path.join(current_dir, "data", "go_api_tools.json"),
    # Ensembl Compara - Comparative genomics (orthologues, paralogues, gene trees)
    "ensembl_compara": os.path.join(current_dir, "data", "ensembl_compara_tools.json"),
    # Monarch Initiative V3 - Cross-species gene-disease-phenotype associations
    "monarch_v3": os.path.join(current_dir, "data", "monarch_v3_tools.json"),
    # EBI Proteins API Extended - Mutagenesis experiments and PTM proteomics evidence
    "ebi_proteins_ext": os.path.join(
        current_dir, "data", "ebi_proteins_ext_tools.json"
    ),
    # PDBe-KB Graph API - Aggregated structural knowledge base (ligand sites, PPI interfaces, stats)
    "pdbe_kb": os.path.join(current_dir, "data", "pdbe_kb_tools.json"),
    # UniProt Reference Datasets - Diseases, keywords, and proteomes controlled vocabularies
    "uniprot_ref": os.path.join(current_dir, "data", "uniprot_ref_tools.json"),
    # Disease Ontology - Standardized human disease classification (DO terms, hierarchy, cross-refs)
    "disease_ontology": os.path.join(
        current_dir, "data", "disease_ontology_tools.json"
    ),
    # RCSB PDB Data API - Direct REST access to PDB entry details, assemblies, non-polymer entities
    "rcsb_data": os.path.join(current_dir, "data", "rcsb_data_tools.json"),
    # EBI Proteins Features - Domain/site annotations, molecule processing, secondary structure
    "ebi_proteins_features": os.path.join(
        current_dir, "data", "ebi_proteins_features_tools.json"
    ),
    # InterPro Extended - Reverse lookup: find proteins containing a specific domain
    "interpro_ext": os.path.join(current_dir, "data", "interpro_ext_tools.json"),
    # STRING Extended - Per-protein functional annotations (GO, KEGG, disease, tissue)
    "string_ext": os.path.join(current_dir, "data", "string_ext_tools.json"),
    # Ensembl Info - Genome assembly metadata and species catalog
    "ensembl_info": os.path.join(current_dir, "data", "ensembl_info_tools.json"),
    # Epigenomics - Histone marks, DNA methylation, chromatin accessibility, regulatory elements
    "epigenomics": os.path.join(current_dir, "data", "epigenomics_tools.json"),
    # 3D Beacons - Aggregated 3D structure models from PDBe, AlphaFold, SWISS-MODEL, PED
    "three_d_beacons": os.path.join(current_dir, "data", "three_d_beacons_tools.json"),
    # Reactome Content Service - Pathway search, contained events, enhanced details
    "reactome_content": os.path.join(
        current_dir, "data", "reactome_content_tools.json"
    ),
    # InterPro Entry - Protein-to-domain mappings and keyword-based entry search
    "interpro_entry": os.path.join(current_dir, "data", "interpro_entry_tools.json"),
    # Ensembl Sequence - Region DNA and ID-based protein/cDNA sequence retrieval
    "ensembl_sequence": os.path.join(
        current_dir, "data", "ensembl_sequence_tools.json"
    ),
    # MyDisease.info - BioThings disease annotation aggregator (MONDO, DO, CTD, HPO, DisGeNET)
    "mydisease": os.path.join(current_dir, "data", "mydisease_tools.json"),
    # EBI OxO - Ontology cross-reference mappings across biomedical databases
    "oxo": os.path.join(current_dir, "data", "oxo_tools.json"),
    # InterPro Domain Architecture - Protein domain positions, structure mapping, clan members
    "interpro_domain_arch": os.path.join(
        current_dir, "data", "interpro_domain_arch_tools.json"
    ),
    # WikiPathways Extended - Gene lists from pathways and gene-to-pathway lookups
    "wikipathways_ext": os.path.join(
        current_dir, "data", "wikipathways_ext_tools.json"
    ),
    # EBI Gene Expression Atlas (GxA) - Baseline/differential gene expression experiments
    "gxa": os.path.join(current_dir, "data", "gxa_tools.json"),
    # CellxGene Discovery - Single-cell RNA-seq dataset/collection browsing
    "cellxgene_discovery": os.path.join(
        current_dir, "data", "cellxgene_discovery_tools.json"
    ),
    # Ensembl Archive - Stable ID versioning and history tracking
    "ensembl_archive": os.path.join(current_dir, "data", "ensembl_archive_tools.json"),
    # KEGG Extended - Gene-pathway links, pathway gene lists, compound details
    "kegg_ext": os.path.join(current_dir, "data", "kegg_ext_tools.json"),
    # Ensembl Map - Coordinate system conversion and assembly mapping
    "ensembl_map": os.path.join(current_dir, "data", "ensembl_map_tools.json"),
    # Ensembl Overlap - Features overlapping a genomic region (genes, variants, regulatory)
    "ensembl_overlap": os.path.join(current_dir, "data", "ensembl_overlap_tools.json"),
    # Ensembl Xrefs - External database cross-references for genes and proteins
    "ensembl_xrefs": os.path.join(current_dir, "data", "ensembl_xrefs_tools.json"),
    # Ensembl Variation Extended - Population genetics, linkage disequilibrium, haplotypes
    "ensembl_variation_ext": os.path.join(
        current_dir, "data", "ensembl_variation_ext_tools.json"
    ),
    # EBI Proteins Coordinates - Protein 3D structural coordinates
    "ebi_proteins_coordinates": os.path.join(
        current_dir, "data", "ebi_proteins_coordinates_tools.json"
    ),
    # EBI Proteins Epitope - Immunological epitope annotations
    "ebi_proteins_epitope": os.path.join(
        current_dir, "data", "ebi_proteins_epitope_tools.json"
    ),
    # EBI Proteins Interactions - Protein-protein interaction evidence
    "ebi_proteins_interactions": os.path.join(
        current_dir, "data", "ebi_proteins_interactions_tools.json"
    ),
    # PDBe Compound - Small molecule compound summaries and cross-references
    "pdbe_compound": os.path.join(current_dir, "data", "pdbe_compound_tools.json"),
    # PDBe Ligands - Structure-level ligand lists and residue details
    "pdbe_ligands": os.path.join(current_dir, "data", "pdbe_ligands_tools.json"),
    # PDBe SIFTS - Structure-to-sequence mappings (UniProt, Pfam, CATH, EC)
    "pdbe_sifts": os.path.join(current_dir, "data", "pdbe_sifts_tools.json"),
    # PDBe Validation - Experimental validation reports (R-factor, clashscore, geometry)
    "pdbe_validation": os.path.join(current_dir, "data", "pdbe_validation_tools.json"),
    # RCSB Advanced Search - Complex multi-attribute PDB queries
    "rcsb_advanced_search": os.path.join(
        current_dir, "data", "rcsb_advanced_search_tools.json"
    ),
    # RCSB GraphQL - Flexible PDB data retrieval via GraphQL schema
    "rcsb_graphql": os.path.join(current_dir, "data", "rcsb_graphql_tools.json"),
    # Reactome Interactors - Protein interaction data from IntAct/ChEMBL
    "reactome_interactors": os.path.join(
        current_dir, "data", "reactome_interactors_tools.json"
    ),
    # UniParc - UniProt Archive cross-references across sequence databases
    "uniparc": os.path.join(current_dir, "data", "uniparc_tools.json"),
    # UniProt Locations - Subcellular location controlled vocabulary
    "uniprot_locations": os.path.join(
        current_dir, "data", "uniprot_locations_tools.json"
    ),
    # UniProt Taxonomy - Taxonomy nodes and lineage data from UniProt
    "uniprot_taxonomy": os.path.join(
        current_dir, "data", "uniprot_taxonomy_tools.json"
    ),
    # UniRef - UniProt Reference Clusters (100/90/50 identity clusters)
    "uniref": os.path.join(current_dir, "data", "uniref_tools.json"),
    # ClinGen Dosage Sensitivity - Haploinsufficiency and triplosensitivity scores
    "clingen_dosage": os.path.join(
        current_dir, "data", "clingen_dosage_api_tools.json"
    ),
    # Dfam - Repetitive DNA element database (transposons, SINEs, LINEs)
    "dfam": os.path.join(current_dir, "data", "dfam_tools.json"),
    # DisProt - Intrinsically disordered protein regions database
    "disprot": os.path.join(current_dir, "data", "disprot_tools.json"),
    # Genome Nexus - Cancer variant annotation aggregator (VEP, COSMIC, ClinVar)
    "genome_nexus": os.path.join(current_dir, "data", "genome_nexus_tools.json"),
    # g:Profiler - Functional enrichment, gene ID conversion, ortholog mapping
    "gprofiler": os.path.join(current_dir, "data", "gprofiler_tools.json"),
    # Harmonizome - Aggregated gene-attribute associations from 114 datasets
    "harmonizome": os.path.join(current_dir, "data", "harmonizome_tools.json"),
    # MobiDB - Intrinsic disorder and mobility annotations for proteins
    "mobidb": os.path.join(current_dir, "data", "mobidb_tools.json"),
    # OmniPath - Signaling network (ligand-receptor, enzyme-substrate, complexes)
    "omnipath": os.path.join(current_dir, "data", "omnipath_tools.json"),
    # OrthoDB - Hierarchical orthology database (orthologs, paralogs across 1,300+ species)
    "orthodb": os.path.join(current_dir, "data", "orthodb_tools.json"),
    # SynBioHub - Synthetic biology parts and designs repository (SBOL standard)
    "synbiohub": os.path.join(current_dir, "data", "synbiohub_tools.json"),
    # BioPortal - NCBO ontology browser and annotation service
    "bioportal": os.path.join(current_dir, "data", "bioportal_tools.json"),
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
