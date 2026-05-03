# Network Pharmacology - Tool Parameter Reference

Verified tool signatures, response structures, and troubleshooting.

---

## Compound Identification Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `OpenTargets_get_drug_chembId_by_generic_name` | `drugName: str` | `{data: {search: {hits: [{id, name, description}]}}}` |
| `OpenTargets_get_drug_id_description_by_name` | `drugName: str` | `{data: {search: {hits: [{id, name, description}]}}}` |
| `drugbank_get_drug_basic_info_by_drug_name_or_id` | `query: str`, `case_sensitive: bool`, `exact_match: bool`, `limit: int` (ALL required) | `{status, data: {drug_name, drugbank_id, ...}}` |
| `PubChem_get_CID_by_compound_name` | `name: str` | `{IdentifierList: {CID: [int]}}` |
| `PubChem_get_compound_properties_by_CID` | `cid: int` | `{CID, MolecularWeight, ConnectivitySMILES, IUPACName}` |
| `ChEMBL_search_drugs` | `query: str`, `limit: int` | `{status, data: {drugs: [...]}}` |

## Target Identification Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `OpenTargets_get_target_id_description_by_name` | `targetName: str` | `{data: {search: {hits: [{id, name, description}]}}}` |
| `ensembl_lookup_gene` | `gene_id: str`, `species: str` (REQUIRED, e.g., "homo_sapiens") | `{status, data: {display_name, biotype, ...}}` |
| `MyGene_query_genes` | `query: str` | Gene info with cross-references |
| `Pharos_get_target` | `target_name: str` | Target with development level |

## Disease Identification Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `OpenTargets_get_disease_id_description_by_name` | `diseaseName: str` | `{data: {search: {hits: [{id, name, description}]}}}` |
| `OpenTargets_get_disease_description_by_efoId` | `efoId: str` | `{data: {disease: {id, name, description}}}` |
| `OpenTargets_get_disease_ids_by_efoId` | `efoId: str` | Disease cross-references |

## Network Edge Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `STRING_get_interaction_partners` | `protein_ids: list[str]`, `species: int` (9606), `limit: int` | `{status, data: [{stringId_A, stringId_B, preferredName_A, preferredName_B, score}]}` |
| `STRING_get_network` | `protein_ids: list[str]`, `species: int` | Network data |
| `STRING_functional_enrichment` | `protein_ids: list[str]`, `species: int` | Enrichment results |
| `STRING_ppi_enrichment` | `protein_ids: list[str]`, `species: int` | PPI enrichment statistics |
| `OpenTargets_get_target_interactions_by_ensemblID` | `ensemblId: str`, `size: int` | `{data: {target: {interactions: {count, rows: [{intA, targetA, intB, targetB, score}]}}}}` |
| `intact_search_interactions` | `query: str`, `max: int` | Interaction data |
| `humanbase_ppi_analysis` | `gene_list: list`, `tissue: str`, `max_node: int`, `interaction: str`, `string_mode: str` (ALL required) | Tissue-specific PPI |

## Drug-Target Edge Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` | `chemblId: str` | `{data: {drug: {mechanismsOfAction: {rows: [{mechanismOfAction, actionType, targets}]}}}}` |
| `OpenTargets_get_associated_targets_by_drug_chemblId` | `chemblId: str`, `size: int` | `{data: {drug: {linkedTargets: {count, rows}}}}` |
| `drugbank_get_targets_by_drug_name_or_drugbank_id` | `query, case_sensitive, exact_match, limit` (ALL required) | `{status, data: {targets: [{id, name, organism, actions}]}}` |
| `DGIdb_get_drug_gene_interactions` | `genes: list[str]` | `{data: {genes: {nodes: [{name, interactions}]}}}` |
| `CTD_get_chemical_gene_interactions` | `input_terms: str` | `{data: [{ChemicalName, GeneSymbol, InteractionActions}]}` |
| `ChEMBL_get_target_activities` | `target_chembl_id__exact: str` | Activity data with pchembl_value |

## Target-Disease Edge Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `OpenTargets_get_associated_targets_by_disease_efoId` | `efoId: str`, `limit: int` | `{data: {disease: {associatedTargets: {count, rows: [{target: {id, approvedSymbol}, score}]}}}}` |
| `OpenTargets_target_disease_evidence` | `efoId: str`, `ensemblId: str` (BOTH required) | Evidence data across datasources |
| `CTD_get_gene_diseases` | `input_terms: str` | `{data: [{GeneName, DiseaseName, DirectEvidence}]}` |
| `GWAS_search_associations_by_gene` | `gene_name: str` | GWAS association data |

## Drug-Disease Edge Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `OpenTargets_get_drug_indications_by_chemblId` | `chemblId: str`, `size: int` | `{data: {drug: {indications: {rows: [{disease, maxPhaseForIndication}]}}}}` |
| `OpenTargets_get_associated_diseases_by_drug_chemblId` | `chemblId: str`, `size: int` | `{data: {drug: {linkedDiseases: {count, rows}}}}` |
| `CTD_get_chemical_diseases` | `input_terms: str` | `{data: [{ChemicalName, DiseaseName, DirectEvidence}]}` |
| `search_clinical_trials` | `query_term: str` (REQUIRED), `condition: str`, `pageSize: int` | `{studies: [{NCT ID, brief_title, ...}]}` |

## Pathway Analysis Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `ReactomeAnalysis_pathway_enrichment` | `identifiers: str` (space-separated, NOT array) | `{data: {pathways: [{pathway_id, name, p_value, fdr, entities_found}]}}` |
| `enrichr_gene_enrichment_analysis` | `gene_list: list[str]`, `libs: list[str]` (REQUIRED) | Enrichment per library |
| `drugbank_get_pathways_reactions_by_drug_or_id` | `query, case_sensitive, exact_match, limit` | Pathway data |

## Safety Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `FAERS_calculate_disproportionality` | `operation: str`, `drug_name: str`, `adverse_event: str` | `{metrics: {PRR, ROR, IC}, signal_detection}` |
| `FAERS_filter_serious_events` | `operation: str`, `drug_name: str`, `seriousness_type: str` | Serious event data |
| `FAERS_count_death_related_by_drug` | `medicinalproduct: str` | `[{term, count}]` |
| `OpenTargets_get_drug_adverse_events_by_chemblId` | `chemblId: str` | `{data: {drug: {adverseEvents: {count, rows}}}}` |
| `OpenTargets_get_drug_warnings_by_chemblId` | `chemblId: str` | Drug warning data |
| `OpenTargets_get_target_safety_profile_by_ensemblID` | `ensemblId: str` | Target safety data |
| `gnomad_get_gene_constraints` | `gene_symbol: str` | Gene constraint (pLI, LOEUF) |
| `FDA_get_warnings_and_cautions_by_drug_name` | `drug_name: str` | FDA warning text |

## Literature Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `PubMed_search_articles` | `query: str`, `max_results: int` | list of `{pmid, title, authors, journal, pub_date}` |
| `EuropePMC_search_articles` | `query: str`, `limit: int` | Article list |
| `OpenTargets_get_publications_by_drug_chemblId` | `chemblId: str`, `size: int` | Publication data |

---

## Response Format Notes

- **DrugBank tools**: ALL require `query`, `case_sensitive`, `exact_match`, `limit` (4 params, ALL required).
- **FAERS analytics tools** (disproportionality, compare, filter, stratify, rollup, trends): ALL require `operation` parameter.
- **FAERS count tools** (count_death, count_reactions, etc.): Use `medicinalproduct` NOT `drug_name`.
- **OpenTargets tools**: Return nested `{data: {entity: {field: ...}}}` structure.
- **PubMed_search_articles**: Returns plain **list** of dicts, NOT `{articles: [...]}`.
- **PubChem CID lookup**: Returns `{IdentifierList: {CID: [...]}}` (NO data wrapper).
- **ReactomeAnalysis_pathway_enrichment**: Takes space-separated `identifiers` string, NOT array.
- **ensembl_lookup_gene**: REQUIRES `species='homo_sapiens'` parameter.
- **STRING tools**: Return `{status: "success", data: [...]}`.
- **CTD tools**: Return `{data: [...]}` with potentially large result sets.

---

## Fallback Strategies

| Phase | Primary Tool | Fallback 1 | Fallback 2 |
|-------|-------------|-----------|-----------|
| Compound ID | OpenTargets drug lookup | ChEMBL search | PubChem CID lookup |
| Target ID | OpenTargets target lookup | ensembl_lookup_gene | MyGene_query_genes |
| Disease ID | OpenTargets disease lookup | ols_search_efo_terms | CTD_get_chemical_diseases |
| Drug targets | OpenTargets drug mechanisms | DrugBank targets | DGIdb interactions |
| Disease targets | OpenTargets disease targets | CTD gene-diseases | GWAS associations |
| PPI network | STRING interactions | OpenTargets interactions | IntAct interactions |
| Pathways | ReactomeAnalysis enrichment | enrichr enrichment | STRING functional enrichment |
| Clinical trials | search_clinical_trials | clinical_trials_search | PubMed clinical |
| Safety | FAERS + FDA | OpenTargets AEs | DrugBank safety |
| Literature | PubMed search | EuropePMC search | OpenTargets publications |

---

## Troubleshooting

**"Disease not found"**:
- Try disease synonyms (e.g., "Alzheimer's disease" vs "Alzheimer disease")
- Use EFO/MONDO ID directly if known
- Search with `OpenTargets_multi_entity_search_by_query_string(queryString=...)` for broader matching
- Try parent disease category

**"No drugs found for target"**:
- Target may be Tdark (no chemical tools) - check with Pharos
- Expand to target family or pathway
- Search DGIdb which aggregates multiple sources
- Check chemical probes as starting points

**"No PPI data"**:
- Try different protein identifiers (gene symbol, UniProt, Ensembl protein)
- Use multiple PPI databases (STRING + IntAct + OpenTargets)
- Lower confidence threshold in STRING
- Use pathway co-membership as proxy for interaction

**"Network proximity not significant"**:
- Drug targets may be functionally distant from disease module
- Try expanding disease gene set (increase limit)
- Consider indirect mechanisms via shared pathways
- Report honestly - not all drug-disease pairs have network support

**"DrugBank parameter errors"**:
- ALL DrugBank tools require 4 params: `query`, `case_sensitive`, `exact_match`, `limit`
- Use `case_sensitive=False`, `exact_match=True` for exact drug name matching
- Use `exact_match=False` for broader searches

**"FAERS operation errors"**:
- Analytics tools (disproportionality, compare, filter, stratify) need `operation` param
- Count tools use `medicinalproduct` NOT `drug_name`
- Check FAERS tool name carefully to determine which pattern
