# Target Intelligence Tool Reference

Complete reference of 225+ ToolUniverse tools for target research, organized by category.

## 1. Core Protein Information (UniProt)

| Tool | Parameters | Returns |
|------|------------|---------|
| `UniProt_get_entry_by_accession` | `accession` | Complete protein entry |
| `UniProt_get_function_by_accession` | `accession` | Functional annotations |
| `UniProt_get_recommended_name_by_accession` | `accession` | Official protein name |
| `UniProt_get_alternative_names_by_accession` | `accession` | Aliases and synonyms |
| `UniProt_get_organism_by_accession` | `accession` | Species info |
| `UniProt_get_subcellular_location_by_accession` | `accession` | Cellular localization |
| `UniProt_get_disease_variants_by_accession` | `accession` | Disease variants |
| `UniProt_get_ptm_processing_by_accession` | `accession` | PTMs, active sites |
| `UniProt_get_sequence_by_accession` | `accession` | Amino acid sequence |
| `UniProt_get_isoform_ids_by_accession` | `accession` | Splice isoforms |
| `UniProt_search` | `query`, `organism`, `limit`, `fields` | Search results |
| `UniProt_id_mapping` | `ids`, `from_db`, `to_db` | ID mappings |
| `UniProt_get_proteome` | `proteome_id` | Proteome info |
| `UniProt_get_uniref_cluster` | `cluster_id` | UniRef cluster |
| `UniProt_search_uniref` | `query`, `cluster_type`, `limit` | UniRef search |
| `UniProt_get_uniparc_entry` | `upi` | UniParc entry |
| `UniProt_search_uniparc` | `query`, `limit` | UniParc search |

### EBI Proteins API

| Tool | Parameters | Returns |
|------|------------|---------|
| `proteins_api_get_protein` | `accession`, `format` | Comprehensive protein info |
| `proteins_api_get_features` | `accession` | Protein features |
| `proteins_api_get_variants` | `accession` | Protein variants |
| `proteins_api_get_comments` | `accession` | Annotations/comments |
| `proteins_api_get_epitopes` | `accession` | Epitope data |
| `proteins_api_get_proteomics` | `accession` | Proteomics data |
| `proteins_api_get_xrefs` | `accession` | Cross-references |
| `proteins_api_get_publications` | `accession` | Related publications |
| `proteins_api_get_genome_mappings` | `accession` | Genome mappings |
| `proteins_api_search` | `query` | Search proteins |

## 2. Gene Information

### MyGene (BioThings)

| Tool | Parameters | Returns |
|------|------------|---------|
| `MyGene_get_gene_annotation` | `gene_id`, `fields` | Detailed gene annotation |
| `MyGene_query_genes` | `query`, `species`, `fields`, `size` | Gene search |
| `MyGene_batch_query` | `gene_ids`, `species`, `fields` | Batch gene query |

### Ensembl

| Tool | Parameters | Returns |
|------|------------|---------|
| `ensembl_lookup_gene` | `gene_id`, `species` | Gene lookup |
| `ensembl_get_sequence` | `id`, `type`, `species` | DNA/protein sequence |
| `ensembl_get_variants` | `region`, `species` | Variants in region |
| `ensembl_get_variation` | `id`, `species` | Variation details |
| `ensembl_get_variation_phenotypes` | `id`, `species` | Phenotype associations |
| `ensembl_get_xrefs` | `id`, `external_db` | Cross-references |
| `ensembl_get_xrefs_by_name` | `name`, `species` | Xrefs by gene name |
| `ensembl_get_regulatory_features` | `region`, `species` | Regulatory features |
| `ensembl_get_genetree` | `id`, `prune_species` | Gene tree |
| `ensembl_get_homology` | `species`, `symbol`, `target_species` | Orthologs/paralogs |
| `ensembl_get_alignment` | `species`, `region` | Genomic alignments |
| `ensembl_get_taxonomy` | `id` | Taxonomy info |
| `ensembl_vep_region` | `species`, `region`, `allele` | Variant effect prediction |

### Other Gene Resources

| Tool | Parameters | Returns |
|------|------------|---------|
| `kegg_get_gene_info` | `gene_id` | KEGG gene info |
| `kegg_find_genes` | `keyword`, `organism` | KEGG gene search |
| `cBioPortal_get_genes` | `keyword` | Cancer gene search |
| `civic_search_genes` | `gene_symbol` | CIViC gene info |
| `gnomad_get_gene` | `gene_symbol` | gnomAD gene data |
| `gnomad_search_variants_genes` | `query` | gnomAD gene search |
| `gnomad_get_gene_constraints` | `gene_symbol` | Constraint scores |

## 3. Drug-Target Interactions

### DGIdb

| Tool | Parameters | Returns |
|------|------------|---------|
| `DGIdb_get_drug_gene_interactions` | `genes`, `interaction_sources`, `interaction_types` | Drug-gene interactions |
| `DGIdb_get_gene_druggability` | `genes` | Druggability categories |
| `DGIdb_get_gene_info` | `genes` | Gene info from DGIdb |
| `DGIdb_get_drug_info` | `drugs` | Drug info from DGIdb |

### ChEMBL

| Tool | Parameters | Returns |
|------|------------|---------|
| `ChEMBL_get_target` | `target_chembl_id`, `format` | Target details |
| `ChEMBL_search_targets` | `pref_name__contains`, `organism`, `target_type`, `limit` | Target search |
| `ChEMBL_get_target_activities` | `target_chembl_id__exact`, `limit` | Bioactivity data |
| `ChEMBL_get_target_assays` | `target_chembl_id__exact`, `limit` | Target assays |
| `ChEMBL_get_molecule_targets` | `molecule_chembl_id__exact`, `limit` | Molecule targets |
| `ChEMBL_search_binding_sites` | `target_chembl_id` | Binding sites |
| `ChEMBL_search_mechanisms` | `molecule_chembl_id`, `target_chembl_id` | Mechanisms of action |
| `ChEMBL_get_molecule` | `chembl_id`, `format` | Molecule details |
| `ChEMBL_search_molecules` | `pref_name__contains`, `limit` | Molecule search |
| `ChEMBL_get_assay` | `assay_chembl_id` | Assay details |
| `ChEMBL_search_activities` | `molecule_chembl_id`, `target_chembl_id`, `standard_type` | Activity search |

### DrugBank & GtoPdb

| Tool | Parameters | Returns |
|------|------------|---------|
| `drugbank_get_targets_by_drug_name_or_drugbank_id` | `query`, `exact_match`, `limit` | Drug targets |
| `drugbank_get_drug_name_and_description_by_target_name` | `target_name` | Drugs for target |
| `GtoPdb_get_target` | `target_id` | GtoPdb target info |
| `GtoPdb_get_targets` | `family_id` | List targets |
| `GtoPdb_search_ligands` | `target_id` | Target-ligand interactions |
| `GtoPdb_search_interactions` | `query` | Interaction search |

### STITCH

| Tool | Parameters | Returns |
|------|------------|---------|
| `STITCH_get_chemical_protein_interactions` | `identifiers`, `species`, `required_score`, `limit` | Chemical-protein links |
| `STITCH_get_interaction_partners` | `identifiers`, `species` | Interaction network |
| `STITCH_resolve_identifier` | `identifier`, `species` | ID resolution |

### GPCRdb (NEW - for GPCR Targets)

~35% of approved drugs target GPCRs. GPCRdb provides specialized data for G protein-coupled receptors.

| Tool | Parameters | Returns |
|------|------------|---------|
| `GPCRdb_get_protein` | `operation="get_protein"`, `protein` (entry name) | GPCR family, class, sequence info |
| `GPCRdb_list_proteins` | `operation="list_proteins"`, `family` (optional) | List GPCR families/proteins |
| `GPCRdb_get_structures` | `operation="get_structures"`, `protein`, `state` (optional) | Structures with receptor state (active/inactive) |
| `GPCRdb_get_ligands` | `operation="get_ligands"`, `protein` | Known ligands (agonists/antagonists) |
| `GPCRdb_get_mutations` | `operation="get_mutations"`, `protein` | Mutation effects on binding/signaling |

**Entry name format**: `{gene_lower}_human` (e.g., `adrb2_human`, `drd2_human`)

**Key advantages**:
- Active vs. inactive state structures
- Ballesteros-Weinstein residue numbering
- Curated ligand binding data
- Experimental mutation effects

### Pharos/TCRD (NEW - Target Development Level)

NIH's Illuminating the Druggable Genome (IDG) portal provides TDL classification.

| Tool | Parameters | Returns |
|------|------------|---------|
| `Pharos_get_target` | `gene` OR `uniprot` | TDL, family, novelty, description |
| `Pharos_search_targets` | `query`, `top` | Target list with TDL |
| `Pharos_get_tdl_summary` | - | TDL level descriptions |
| `Pharos_get_disease_targets` | `disease`, `top` | Targets for disease with TDL |

**TDL Classification**:
| Level | Description | Druggability |
|-------|-------------|--------------|
| **Tclin** | Approved drug targets | Highest |
| **Tchem** | Small molecule activities (IC50 < 30nM) | Good |
| **Tbio** | Biological annotations only | Moderate |
| **Tdark** | Understudied proteins | Unknown |

**Example**:
```python
result = tu.tools.Pharos_get_target(gene="EGFR")
# Returns: tdl="Tclin", fam="Kinase", novelty=0.2, publicationCount=45000
```

### DepMap (NEW - Target Essentiality)

CRISPR knockout essentiality data from cancer cell lines.

| Tool | Parameters | Returns |
|------|------------|---------|
| `DepMap_get_gene_dependencies` | `gene_symbol` | Gene essentiality data |
| `DepMap_get_cell_lines` | `tissue`, `cancer_type`, `page_size` | Cell line metadata |
| `DepMap_search_cell_lines` | `query` | Search cell lines |
| `DepMap_get_cell_line` | `model_id` OR `model_name` | Detailed cell line info |
| `DepMap_get_drug_response` | `drug_name` | Drug sensitivity data |

**Effect Score Interpretation**:
| Score | Meaning |
|-------|---------|
| < -1.0 | Strongly essential |
| -0.5 to -1.0 | Essential |
| -0.5 to 0 | Weakly essential |
| > 0 | Not essential |

**Example**:
```python
deps = tu.tools.DepMap_get_gene_dependencies(gene_symbol="KRAS")
# Returns: Gene info, note about essentiality

cells = tu.tools.DepMap_get_cell_lines(cancer_type="Lung Cancer", page_size=10)
# Returns: Cell line names, cancer types, MSI status
```

### InterProScan (NEW - Domain Prediction)

De novo domain/family prediction for novel sequences.

| Tool | Parameters | Returns |
|------|------------|---------|
| `InterProScan_scan_sequence` | `sequence`, `go_terms`, `pathways` | Domains, GO terms, pathways |
| `InterProScan_get_job_status` | `job_id` | Job status |
| `InterProScan_get_job_results` | `job_id` | Completed results |

**When to use**: Novel proteins, Tdark targets, custom sequences.

**Example**:
```python
# Submit sequence for analysis
result = tu.tools.InterProScan_scan_sequence(
    sequence="MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH...",
    go_terms=True,
    pathways=True
)
# Returns: job_id (if running) or domains/GO/pathways (if complete)

# Check job if still running
status = tu.tools.InterProScan_get_job_status(job_id="iprscan5-xxx")
results = tu.tools.InterProScan_get_job_results(job_id="iprscan5-xxx")
```

### BindingDB (NEW - Ligand Binding Data)

Experimental binding affinity data (Ki, IC50, Kd) for target-ligand pairs.

| Tool | Parameters | Returns |
|------|------------|---------|
| `BindingDB_get_ligands_by_uniprot` | `uniprot`, `affinity_cutoff` | Ligands with affinities |
| `BindingDB_get_ligands_by_uniprots` | `uniprots`, `affinity_cutoff` | Multi-target ligands |
| `BindingDB_get_ligands_by_pdb` | `pdb_ids`, `affinity_cutoff`, `sequence_identity` | Structure-based ligands |
| `BindingDB_get_targets_by_compound` | `smiles`, `similarity_cutoff` | Polypharmacology |

**Example**:
```python
# Get ligands for EGFR
ligands = tu.tools.BindingDB_get_ligands_by_uniprot(
    uniprot="P00533",
    affinity_cutoff=100  # Only potent ligands <100 nM
)
# Returns: SMILES, affinity_type (Ki/IC50/Kd), affinity value, PMID

# Find targets for a compound
targets = tu.tools.BindingDB_get_targets_by_compound(
    smiles="CC(=O)Nc1ccc(cc1)O",
    similarity_cutoff=0.85
)
# Returns: proteins with similar compound activities
```

**Affinity Interpretation**:
| Range | Level | Drug Potential |
|-------|-------|----------------|
| <1 nM | Ultra-potent | Clinical candidate |
| 1-30 nM | Tchem threshold | Drug-like |
| 30-100 nM | Potent | Good start |
| 100-1000 nM | Moderate | Needs optimization |

### Human Protein Atlas (NEW - Expression)

Protein and RNA expression across tissues and cell lines.

| Tool | Parameters | Returns |
|------|------------|---------|
| `HPA_search_genes_by_query` | `search_query` | Gene info, Ensembl ID |
| `HPA_generic_search` | `search_query`, `columns` | Custom data fields |
| `HPA_get_comparative_expression_by_gene_and_cellline` | `gene_name`, `cell_line` | Cancer vs normal |

**Example**:
```python
# Search gene
gene = tu.tools.HPA_search_genes_by_query(search_query="EGFR")
# Returns: Gene name, Ensembl ID, synonyms

# Compare cancer cell line vs normal tissue
expr = tu.tools.HPA_get_comparative_expression_by_gene_and_cellline(
    gene_name="EGFR",
    cell_line="a549"  # Lung cancer
)
# Returns: expression comparison
```

**Supported Cell Lines**: a549, mcf7, hela, hepg2, pc3, jurkat, rh30, siha, u251, ishikawa

### PubChem BioAssay (NEW - Screening Data)

HTS screening data and dose-response curves.

| Tool | Parameters | Returns |
|------|------------|---------|
| `PubChem_search_assays_by_target_gene` | `gene_symbol` | AIDs for gene |
| `PubChem_get_assay_summary` | `aid` | Assay statistics |
| `PubChem_get_assay_targets` | `aid` | Target info |
| `PubChem_get_assay_active_compounds` | `aid` | Active CIDs |
| `PubChem_get_assay_dose_response` | `aid` | IC50/EC50 data |

**Example**:
```python
# Find assays for target
assays = tu.tools.PubChem_search_assays_by_target_gene(gene_symbol="EGFR")
# Returns: list of AIDs

# Get assay summary
summary = tu.tools.PubChem_get_assay_summary(aid=504526)
# Returns: active/inactive counts, target info

# Get active compounds
actives = tu.tools.PubChem_get_assay_active_compounds(aid=504526)
# Returns: CIDs of active compounds
```

## 4. Open Targets Platform

### Target-Centric

| Tool | Parameters | Returns |
|------|------------|---------|
| `OpenTargets_get_target_id_description_by_name` | `targetName` | Target ID lookup |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblID` | Drugs for target |
| `OpenTargets_get_diseases_phenotypes_by_target_ensembl` | `ensemblID` | Diseases for target |
| `OpenTargets_get_target_safety_profile_by_ensemblID` | `ensemblID` | Safety info |
| `OpenTargets_get_target_tractability_by_ensemblID` | `ensemblID` | Tractability |
| `OpenTargets_get_target_interactions_by_ensemblID` | `ensemblID` | PPI via Open Targets |
| `OpenTargets_get_target_gene_ontology_by_ensemblID` | `ensemblID` | GO terms |
| `OpenTargets_get_target_synonyms_by_ensemblID` | `ensemblID` | Target synonyms |
| `OpenTargets_get_target_classes_by_ensemblID` | `ensemblID` | Classifications |
| `OpenTargets_get_target_constraint_info_by_ensemblID` | `ensemblID` | Constraint data |
| `OpenTargets_get_target_genomic_location_by_ensemblID` | `ensemblID` | Genomic location |
| `OpenTargets_get_target_subcell_locations_by_ensembl_ID` | `ensemblID` | Subcellular location |
| `OpenTargets_get_target_homologues_by_ensemblID` | `ensemblID` | Homologs |
| `OpenTargets_get_target_enabling_packages_by_ensemblID` | `ensemblID` | TEP info |
| `OpenTargets_get_chemical_probes_by_target_ensemblID` | `ensemblID` | Chemical probes |
| `OpenTargets_get_biological_mouse_models_by_ensemblID` | `ensemblID` | Mouse models |
| `OpenTargets_get_publications_by_target_ensemblID` | `ensemblID` | Publications |
| `OpenTargets_get_similar_entities_by_target_ensemblID` | `ensemblID` | Similar targets |

### Disease-Target Evidence

| Tool | Parameters | Returns |
|------|------------|---------|
| `OpenTargets_get_associated_targets_by_disease_efoId` | `efoId` | Targets for disease |
| `OpenTargets_target_disease_evidence` | `ensemblID`, `efoId` | Evidence details |
| `disease_target_score` | `efoId`, `datasourceId` | Disease-target scores |

## 5. Protein Structure

### RCSB PDB

| Tool | Parameters | Returns |
|------|------------|---------|
| `get_protein_metadata_by_pdb_id` | `pdb_id` | Basic metadata |
| `get_protein_classification_by_pdb_id` | `pdb_id` | Protein classification |
| `get_sequence_by_pdb_id` | `pdb_id` | PDB sequence |
| `get_binding_affinity_by_pdb_id` | `pdb_id` | Binding affinity data |
| `get_target_cofactor_info` | `pdb_id` | Cofactor info |
| `get_polymer_entity_annotations` | `entity_id` | Polymer annotations |
| `get_uniprot_accession_by_entity_id` | `entity_id` | UniProt from PDB |
| `get_gene_name_by_entity_id` | `entity_id` | Gene name from PDB |
| `PDB_search_similar_structures` | `pdb_id` | Similar structures |
| `get_polymer_entity_ids_by_pdb_id` | `pdb_id` | Polymer entity IDs |
| `get_source_organism_by_pdb_id` | `pdb_id` | Source organism |
| `get_citation_info_by_pdb_id` | `pdb_id` | Citation info |
| `get_mutation_annotations_by_pdb_id` | `pdb_id` | Mutation annotations |
| `get_assembly_info_by_pdb_id` | `pdb_id` | Biological assembly |
| `get_taxonomy_by_pdb_id` | `pdb_id` | Taxonomy |
| `get_crystallographic_properties_by_pdb_id` | `pdb_id` | Crystal properties |
| `get_structure_validation_metrics_by_pdb_id` | `pdb_id` | Validation metrics |
| `get_ligand_smiles_by_chem_comp_id` | `chem_comp_id` | Ligand SMILES |
| `visualize_protein_structure_3d` | `pdb_id` | 3D visualization |

### PDBe

| Tool | Parameters | Returns |
|------|------------|---------|
| `pdbe_get_entry_summary` | `pdb_id` | Entry summary |
| `pdbe_get_entry_quality` | `pdb_id` | Quality metrics |
| `pdbe_get_entry_publications` | `pdb_id` | Publications |
| `pdbe_get_entry_assemblies` | `pdb_id` | Biological assemblies |
| `pdbe_get_entry_secondary_structure` | `pdb_id` | Secondary structure |
| `pdbe_get_entry_molecules` | `pdb_id` | Molecule info |
| `pdbe_get_entry_status` | `pdb_id` | Entry status |
| `pdbe_get_entry_experiment` | `pdb_id` | Experimental details |

### AlphaFold

| Tool | Parameters | Returns |
|------|------------|---------|
| `alphafold_get_prediction` | `qualifier` (UniProt) | Full 3D predictions |
| `alphafold_get_summary` | `qualifier` | Summary/metadata |
| `alphafold_get_annotations` | `qualifier` | Annotations |

### EMDB

| Tool | Parameters | Returns |
|------|------------|---------|
| `EMDB_search_structures` | `query` | EM structure search |
| `EMDB_get_structure` | `emdb_id` | EM structure details |

## 6. Protein-Protein Interactions

### STRING

| Tool | Parameters | Returns |
|------|------------|---------|
| `STRING_get_protein_interactions` | `protein_ids`, `species`, `confidence_score`, `network_type`, `limit` | PPI network |

### IntAct

| Tool | Parameters | Returns |
|------|------------|---------|
| `intact_get_interactions` | `identifier`, `format` | Interactions |
| `intact_search_interactions` | `query`, `first`, `max` | Interaction search |
| `intact_get_interactor` | `identifier`, `format` | Interactor details |
| `intact_get_interaction_network` | `identifier`, `depth` | Interaction network |
| `intact_get_interaction_details` | `interaction_id` | Interaction details |
| `intact_get_interactions_by_organism` | `taxid`, `size` | Organism interactions |
| `intact_get_interactions_by_complex` | `complex_id` | Complex interactions |
| `intact_get_complex_details` | `complex_ac` | Complex details |

### Other PPI Sources

| Tool | Parameters | Returns |
|------|------------|---------|
| `BioGRID_get_interactions` | `gene_names`, `organism`, `interaction_type`, `limit` | BioGRID PPI |
| `HPA_get_protein_interactions_by_gene` | `gene_symbol` | HPA interactions |
| `humanbase_ppi_analysis` | `genes`, `tissue` | HumanBase PPI |
| `Reactome_get_interactor` | `id` | Reactome interactors |
| `pc_get_interactions` | `source`, `target` | Pathway Commons |

## 7. Functional Annotations

### Gene Ontology

| Tool | Parameters | Returns |
|------|------------|---------|
| `GO_get_annotations_for_gene` | `gene_id` | GO annotations |
| `GO_get_genes_for_term` | `go_id`, `taxon`, `rows` | Genes for GO term |
| `GO_search_terms` | `query` | GO term search |
| `GO_get_term_details` | `id` | GO term details |
| `GO_get_term_by_id` | `id` | GO term info |
| `OpenTargets_get_gene_ontology_terms_by_goID` | `goId` | GO term via OT |

### InterPro & Pfam

| Tool | Parameters | Returns |
|------|------------|---------|
| `InterPro_get_protein_domains` | `protein_id` | Domain annotations |
| `InterPro_search_domains` | `query`, `page_size` | Domain search |
| `InterPro_get_domain_details` | `accession` | Domain details |

### Gene Set Enrichment

| Tool | Parameters | Returns |
|------|------------|---------|
| `enrichr_gene_enrichment_analysis` | `genes`, `gene_set_library` | Enrichment analysis |

## 8. Pathways

### Reactome

| Tool | Parameters | Returns |
|------|------------|---------|
| `Reactome_map_uniprot_to_pathways` | `id` (UniProt) | Pathways for protein |
| `Reactome_map_uniprot_to_reactions` | `id` | Reactions for protein |
| `Reactome_get_pathway` | `stId` | Pathway details |
| `Reactome_get_pathway_reactions` | `stId` | Pathway reactions |
| `Reactome_get_pathway_hierarchy` | `stId` | Parent pathways |
| `Reactome_list_top_pathways` | `species` | Top-level pathways |
| `Reactome_get_participants` | `stId` | Reaction participants |
| `Reactome_get_reaction` | `stId` | Reaction details |
| `Reactome_get_complex` | `stId` | Complex details |
| `Reactome_list_species` | - | All species |
| `Reactome_query_by_ids` | `ids`, `species` | ID query |
| `Reactome_get_events_hierarchy` | `species` | Full hierarchy |
| `Reactome_get_diseases` | - | Disease pathways |

### KEGG

| Tool | Parameters | Returns |
|------|------------|---------|
| `kegg_get_pathway_info` | `pathway_id` | Pathway details |
| `kegg_search_pathway` | `keyword`, `org` | Pathway search |
| `kegg_list_organisms` | - | All organisms |

### WikiPathways

| Tool | Parameters | Returns |
|------|------------|---------|
| `WikiPathways_get_pathway` | `wpid`, `format` | Pathway content |
| `WikiPathways_search` | `query`, `organism` | Pathway search |

### Pathway Commons

| Tool | Parameters | Returns |
|------|------------|---------|
| `pc_search_pathways` | `query` | Pathway search |

## 9. Gene Expression

### GTEx

| Tool | Parameters | Returns |
|------|------------|---------|
| `GTEx_get_gene_expression` | `gencode_id`, `tissue_site_detail_id` | Expression data |
| `GTEx_get_median_gene_expression` | `gencode_id` | Median by tissue |
| `GTEx_get_top_expressed_genes` | `tissue_id` | Top genes in tissue |
| `GTEx_get_expression_summary` | `gencode_id` | Expression summary |
| `GTEx_get_eqtl_genes` | `tissue_id` | eQTL genes |
| `GTEx_get_single_tissue_eqtls` | `gencode_id`, `tissue_id` | Single tissue eQTL |
| `GTEx_get_multi_tissue_eqtls` | `gencode_id` | Multi-tissue eQTL |
| `GTEx_calculate_eqtl` | `gencode_id`, `variant_id` | Calculate eQTL |

### Human Protein Atlas (HPA)

| Tool | Parameters | Returns |
|------|------------|---------|
| `HPA_search_genes_by_query` | `search_query` | Gene search |
| `HPA_get_gene_basic_info_by_ensembl_id` | `ensembl_id` | Basic gene info |
| `HPA_get_comprehensive_gene_details_by_ensembl_id` | `ensembl_id` | Comprehensive details |
| `HPA_get_rna_expression_in_specific_tissues` | `ensembl_id`, `tissue` | Tissue RNA expression |
| `HPA_get_rna_expression_by_source` | `ensembl_id` | Expression by source |
| `HPA_get_subcellular_location` | `ensembl_id` | Subcellular location |
| `HPA_get_disease_expression_by_gene_tissue_disease` | `ensembl_id`, `tissue`, `disease` | Disease expression |
| `HPA_get_cancer_prognostics_by_gene` | `gene_symbol` | Cancer prognostics |
| `HPA_get_biological_processes_by_gene` | `gene_symbol` | Biological processes |

### Single-Cell

| Tool | Parameters | Returns |
|------|------------|---------|
| `CELLxGENE_get_expression_data` | `gene_id`, `dataset_id` | Single-cell expression |
| `CELLxGENE_get_gene_metadata` | `gene_id` | Gene metadata |

## 10. Variants & Mutations

### ClinVar

| Tool | Parameters | Returns |
|------|------------|---------|
| `clinvar_search_variants` | `gene`, `condition`, `variant_id`, `max_results` | Variant search |
| `clinvar_get_variant_details` | `variant_id` | Variant details |
| `clinvar_get_clinical_significance` | `variant_id` | Clinical significance |

### dbSNP

| Tool | Parameters | Returns |
|------|------------|---------|
| `dbsnp_get_variant_by_rsid` | `rsid` | dbSNP variant |
| `dbsnp_search_by_gene` | `gene_symbol` | dbSNP by gene |
| `dbsnp_get_frequencies` | `rsid` | Allele frequencies |

### gnomAD

| Tool | Parameters | Returns |
|------|------------|---------|
| `gnomad_get_variant` | `variant_id` | gnomAD variant |
| `gnomad_search_variants` | `query` | Variant search |
| `gnomad_get_region` | `chrom`, `start`, `stop` | Variants in region |

### CIViC

| Tool | Parameters | Returns |
|------|------------|---------|
| `civic_get_variant` | `variant_id` | CIViC variant |
| `civic_get_variants_by_gene` | `gene_symbol` | Variants for gene |
| `civic_search_variants` | `query` | Variant search |

### Other Variant Sources

| Tool | Parameters | Returns |
|------|------------|---------|
| `MyVariant_get_variant_annotation` | `variant_id` | MyVariant annotation |
| `MyVariant_query_variants` | `query` | Variant query |
| `PharmGKB_search_variants` | `query` | PharmGKB variants |
| `cBioPortal_get_mutations` | `gene_symbol`, `study_id` | Cancer mutations |
| `RegulomeDB_query_variant` | `variant_id` | Regulatory annotation |
| `gwas_search_snps` | `query` | GWAS SNPs |
| `gwas_get_snp_by_id` | `snp_id` | GWAS SNP details |
| `gwas_get_snps_for_gene` | `gene_symbol` | GWAS SNPs for gene |

## 11. Literature

### PubMed

| Tool | Parameters | Returns |
|------|------------|---------|
| `PubMed_search_articles` | `query`, `limit`, `api_key` | Article search |
| `PubMed_get_article` | `pmid`, `api_key` | Article metadata |
| `PubMed_get_related` | `pmid`, `limit` | Related articles |
| `PubMed_get_cited_by` | `pmid`, `limit` | Citing articles |
| `PubMed_get_links` | `pmid` | External links |

### Europe PMC

| Tool | Parameters | Returns |
|------|------------|---------|
| `EuropePMC_search_articles` | `query`, `limit` | Article search |
| `EuropePMC_get_citations` | `source`, `article_id` | Citations |
| `EuropePMC_get_references` | `source`, `article_id` | References |

### Other Literature

| Tool | Parameters | Returns |
|------|------------|---------|
| `PMC_search_papers` | `query` | PMC full-text search |
| `PubTator3_LiteratureSearch` | `query` | PubTator with NER |
| `PubTator3_EntityAutocomplete` | `query` | Entity autocomplete |
| `openalex_search_works` | `query` | OpenAlex publications |
| `openalex_literature_search` | `query` | Literature search |

## 12. Pharmacogenomics

### PharmGKB

| Tool | Parameters | Returns |
|------|------------|---------|
| `PharmGKB_get_gene_details` | `gene_symbol` | Gene info |
| `PharmGKB_search_genes` | `query` | Gene search |
| `PharmGKB_get_drug_details` | `drug_name` | Drug details |
| `PharmGKB_search_drugs` | `query` | Drug search |
| `PharmGKB_get_clinical_annotations` | `gene_symbol` | Clinical annotations |
| `PharmGKB_get_dosing_guidelines` | `gene_symbol` | Dosing guidelines |
| `OpenTargets_drug_pharmacogenomics_data` | `chemblId` | OT pharmacogenomics |
| `fda_pharmacogenomic_biomarkers` | - | FDA biomarkers |

## 13. Disease Associations

| Tool | Parameters | Returns |
|------|------------|---------|
| `OpenTargets_get_disease_ids_by_name` | `diseaseName` | Disease ID lookup |
| `OpenTargets_get_disease_description_by_efoId` | `efoId` | Disease description |
| `OpenTargets_get_associated_drugs_by_disease_efoId` | `efoId` | Drugs for disease |
| `OpenTargets_get_publications_by_disease_efoId` | `efoId` | Disease publications |
| `OpenTargets_get_disease_therapeutic_areas_by_efoId` | `efoId` | Therapeutic areas |
| `gwas_search_studies` | `query` | GWAS studies |
| `gwas_get_studies_for_trait` | `trait` | Studies for trait |
| `gwas_search_associations` | `query` | GWAS associations |
| `gwas_get_associations_for_trait` | `trait` | Associations for trait |
| `GtoPdb_list_diseases` | - | GtoPdb diseases |
| `GtoPdb_get_disease` | `disease_id` | Disease details |
| `Reactome_get_diseases` | - | Reactome diseases |
| `OSL_get_efo_id_by_disease_name` | `disease_name` | EFO ID lookup |

### DisGeNET (NEW - Gene-Disease Associations)

DisGeNET integrates gene-disease associations from curated repositories, GWAS catalogs, animal models, and literature. **Requires**: `DISGENET_API_KEY`

| Tool | Parameters | Returns |
|------|------------|---------|
| `DisGeNET_search_gene` | `operation="search_gene"`, `gene` (symbol/ID), `limit` | Diseases associated with gene |
| `DisGeNET_search_disease` | `operation="search_disease"`, `disease` (name/UMLS CUI), `limit` | Genes associated with disease |
| `DisGeNET_get_gda` | `operation="get_gda"`, `gene`, `disease`, `min_score` | Gene-disease association details |
| `DisGeNET_get_vda` | `operation="get_vda"`, `variant` (rsID), `limit` | Variant-disease associations |
| `DisGeNET_get_disease_genes` | `operation="get_disease_genes"`, `disease`, `limit` | All genes for a disease |

**Key metrics**:
- **GDA Score**: 0-1 confidence score for gene-disease association
- **Evidence Index**: Number and diversity of sources
- **Disease Specificity Index**: How specific is gene to this disease
- **Disease Pleiotropy Index**: How many diseases gene is linked to

**Interpretation**:
- Score ≥0.7: Strong association (consider T2 evidence)
- Score 0.4-0.7: Moderate association
- Score <0.4: Weak/limited evidence

## 14. ID Conversion & Cross-References

| Tool | Parameters | Returns |
|------|------------|---------|
| `UniProt_id_mapping` | `ids`, `from_db`, `to_db` | ID conversion |
| `OpenTargets_map_any_disease_id_to_all_other_ids` | `diseaseId` | Disease ID mapping |
| `ebi_cross_reference_search` | `identifier`, `source` | EBI cross-refs |
| `Reactome_query_by_ids` | `ids` | Reactome ID lookup |

## Common ID Mapping Combinations

| From | To | Tool Call |
|------|----|----|
| Gene Symbol → UniProt | `UniProt_search(query='gene:EGFR AND organism_id:9606')` |
| UniProt → Ensembl | `UniProt_id_mapping(ids=['P00533'], from_db='UniProtKB_AC-ID', to_db='Ensembl')` |
| Ensembl → UniProt | `UniProt_id_mapping(ids=['ENSG00000146648'], from_db='Ensembl', to_db='UniProtKB')` |
| UniProt → PDB | Extract from UniProt entry cross-references |
| Gene Symbol → Entrez | `MyGene_query_genes(query='symbol:EGFR', species='human')` |
| UniProt → ChEMBL Target | `ChEMBL_search_targets(pref_name__contains='EGFR', organism='Homo sapiens')` |
