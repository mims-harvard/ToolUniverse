# Exhaustive Continuous Catalog Expansion Study

## Objective

Measure exhaustive candidate generation across a general OpenAPI directory and a biomedical API registry while preserving VSD's inert review boundary and exact ToolUniverse registry audit.

## Method

Each catalog was scanned through linked, bounded cycles until every compatible record had been attempted. Contracts, operations, and draft configuration hashes were deduplicated before aggregation. Scientific samples were selected only by generic vocabulary matching over catalog metadata; scanner logic contains no provider-specific scientific cases. The recorded run also preserves redundant attempts from partially filled final cycles so execution efficiency can be audited separately from deduplicated scientific results.

## Catalog populations

| Catalog | Records | Compatible | Processed | Cycles | Successful contracts | Failures | Draft-ready |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `apis_guru` | 2,529 | 1,521 | 1,521 | 21 | 1,452 | 123 | 2,225 |
| `smartapi` | 270 | 227 | 227 | 4 | 292 | 8 | 872 |

## Aggregate results

| Measure | Result |
| --- | ---: |
| Catalog records | 2,799 |
| Compatible records processed | 1,748 |
| Contract attempts | 1,875 |
| Redundant attempts in recorded run | 127 |
| Unique contracts inspected | 1,626 |
| Unique operations inventoried | 37,570 |
| Unique draft-ready candidates | 3,097 |
| Draft-ready provider hosts | 203 |
| Scientific draft-ready candidates | 309 |
| Blocked operations | 36,362 |
| Isolated contract failures | 131 |

Draft-ready means the static contract and existing VSD configuration generator accepted the operation. It does not mean that the upstream operation returned a scientifically valid response.
The recorded run made 127 redundant attempts while filling the final bounded batches. Unique contract, operation, and configuration hashes exclude those repetitions; the scanner selection logic now stops a partial final cycle instead of rotating processed records into it.

## Scientific candidates for downstream qualification

| Catalog | API | Operation | Request | Term matches |
| --- | --- | --- | --- | ---: |
| `smartapi` | Translator Annotation Service | `get_/{curieid}` | `GET biothings.transltr.io/annotator/{curieid}` | 6 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `genes_detail_get` | `GET ontology.api.hubmapconsortium.org/genes/{ids}/detail` | 4 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `genes_get` | `GET ontology.api.hubmapconsortium.org/genes/{ids}` | 4 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `genes_info_get` | `GET ontology.api.hubmapconsortium.org/genes-info` | 4 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `pathways_with_genes_get` | `GET ontology.api.hubmapconsortium.org/pathways/with-genes` | 4 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `protein_info_get` | `GET ontology.api.hubmapconsortium.org/proteins-info` | 4 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `proteins_get` | `GET ontology.api.hubmapconsortium.org/proteins/{id}` | 4 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `relationships_for_gene_target_symbol_get` | `GET ontology.api.hubmapconsortium.org/relationships/gene/{target_symbol}` | 4 |
| `smartapi` | Genetics Data Provider for NCATS Biomedical Translator Reasoners | `meta_knowledge_graph_get` | `GET genetics-kp.transltr.io/genetics_provider/trapi/v1.5/meta_knowledge_graph` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `annotations_get` | `GET ontology.api.hubmapconsortium.org/annotations` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `annotations_id_get` | `GET ontology.api.hubmapconsortium.org/annotations/{ids}` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `annotations_organ_levels_get` | `GET ontology.api.hubmapconsortium.org/annotations/organ-levels` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `annotations_organ_levels_id_get` | `GET ontology.api.hubmapconsortium.org/annotations/{ids}/organ-levels` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `annotations_organs_get` | `GET ontology.api.hubmapconsortium.org/annotations/organs` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `annotations_organs_id_get` | `GET ontology.api.hubmapconsortium.org/annotations/{ids}/organs` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `assayclass_get` | `GET ontology.api.hubmapconsortium.org/assayclasses` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `assayclass_name_get` | `GET ontology.api.hubmapconsortium.org/assayclasses/{class}` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `celltypes_detail_get` | `GET ontology.api.hubmapconsortium.org/celltypes/{ids}/detail` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `celltypes_get` | `GET ontology.api.hubmapconsortium.org/celltypes/{ids}` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `celltypes_info_get` | `GET ontology.api.hubmapconsortium.org/celltypes-info` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `datasettypes_dataset_type_code_get` | `GET ontology.api.hubmapconsortium.org/dataset-types/hierarchy/{dataset_type_code}` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `datasettypes_dataset_type_code_modality_code_analyte_code_get` | `GET ontology.api.hubmapconsortium.org/dataset-types/hierarchy/{dataset_type_code}/{modality_code}/{analyte_code}` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `datasettypes_dataset_type_code_modality_code_get` | `GET ontology.api.hubmapconsortium.org/dataset-types/hierarchy/{dataset_type_code}/{modality_code}` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `datasettypes_get` | `GET ontology.api.hubmapconsortium.org/dataset-types` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `datasettypes_hierarchy_get` | `GET ontology.api.hubmapconsortium.org/dataset-types/hierarchy` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `field_assays_get` | `GET ontology.api.hubmapconsortium.org/field-assays` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `field_assays_name_get` | `GET ontology.api.hubmapconsortium.org/field-assays/{name}` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `field_descriptions_get` | `GET ontology.api.hubmapconsortium.org/field-descriptions` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `field_descriptions_name_get` | `GET ontology.api.hubmapconsortium.org/field-descriptions/{name}` | 3 |
| `smartapi` | HuBMAP/SenNet Ontology API (hs-ontology-api) | `field_entities_get` | `GET ontology.api.hubmapconsortium.org/field-entities` | 3 |

## Interpretation

The study separates scale from validity. Exhaustive scanning measures how many exact operations can enter a governed review queue; selected scientific candidates must still pass representative live verification, explicit approval, fresh-runtime loading, and lifecycle monitoring.

## Boundary

The exhaustive scanner fetched catalog pages and contract documents but did not call provider operations. Draft-ready candidates remain unverified, unapproved, unpublished, unloaded, and non-executable.

Portfolio SHA-256: `10ce696555b9de42a2bdf1fa1c86ac746a8c631b8c0e4e9b2dff3d3c513e7bd8`.
