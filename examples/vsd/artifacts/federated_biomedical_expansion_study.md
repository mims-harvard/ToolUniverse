# Federated Biomedical Source Evaluation

## Scope

Can a single reviewed-source scan create a locally loadable evidence panel that links cancer genes, protein models, pathways, tissue-reference identifiers, experimental cell lines, regulatory associations, and sequencing panels without editing ToolUniverse's built-in registry?

This study demonstrates technical retrieval and provenance across public research APIs. It does not establish clinical validity, causal inference, diagnostic utility, or treatment recommendations.

## Source Portfolio

- Reviewed service sources: `20`
- Contracts successfully inspected: `20`
- Distinct operations inspected: `1,142`
- Structurally draftable operations: `533`
- Inert net-new previews: `533`
- Gaps on existing ToolUniverse hosts: `475`
- Candidates from previously uncovered hosts: `58`
- Increment beyond the previous scanner portfolio: `518`
- Combined unique operation identities: `3,559`

| Source | Operations | Previews | Existing-host gaps | New-host candidates | Blocked |
|---|---:|---:|---:|---:|---:|
| `alphafold` | 5 | 5 | 0 | 5 | 0 |
| `biotools` | 56 | 1 | 1 | 0 | 55 |
| `cbioportal` | 152 | 57 | 57 | 0 | 95 |
| `cellosaurus` | 3 | 3 | 3 | 0 | 0 |
| `ebi_eqtl` | 33 | 10 | 10 | 0 | 23 |
| `ena_browser` | 34 | 5 | 5 | 0 | 29 |
| `gtex` | 57 | 56 | 56 | 0 | 1 |
| `hmmer` | 20 | 14 | 14 | 0 | 6 |
| `interpro_matches` | 2 | 1 | 1 | 0 | 1 |
| `mgnify` | 40 | 21 | 21 | 0 | 19 |
| `monarch` | 31 | 25 | 0 | 25 | 6 |
| `ncbi_datasets` | 107 | 20 | 0 | 20 | 87 |
| `ols` | 113 | 91 | 91 | 0 | 22 |
| `omicsdi` | 36 | 30 | 30 | 0 | 6 |
| `pdbe_download` | 28 | 14 | 14 | 0 | 14 |
| `pdbe_graph` | 193 | 148 | 148 | 0 | 45 |
| `pride` | 36 | 24 | 24 | 0 | 12 |
| `rcsb_search` | 7 | 0 | 0 | 0 | 7 |
| `reactome` | 83 | 8 | 0 | 8 | 75 |
| `workflowhub` | 106 | 0 | 0 | 0 | 106 |

## Scientific Evaluation

The evaluation linked three cancer models to seven independently generated research operations. Each accepted tool passed all three disease-context cases before approval, publication, and explicit loading into a fresh runtime.

- Accepted tools: `7`
- Pre-publication verification calls: `21`
- Post-publication runtime calls: `21`
- Candidates rejected on live drift: `3`

| Tool | Source | Scientific contribution |
|---|---|---|
| `VSDFederatedAlphaFoldCancerProteins` | `alphafold` | Retrieves the current AlphaFold model inventory for the scenario protein. |
| `VSDFederatedMonarchCancerGenes` | `monarch` | Normalizes each cancer gene to a Monarch entity with symbol and cross-resource identity. |
| `VSDFederatedReactomeCancerPathways` | `reactome` | Adds the reviewed human pathway most directly connected to each scenario mechanism. |
| `VSDFederatedGTExCancerGeneReferences` | `gtex` | Resolves the symbol to its GTEx GENCODE identifier and genomic coordinates before expression analysis. |
| `VSDFederatedCellosaurusCancerModels` | `cellosaurus` | Connects each experimental model to a stable Cellosaurus accession and a controlled cancer diagnosis. |
| `VSDFederatedEQTLGeneAssociations` | `ebi_eqtl` | Adds measured regulatory variants, effect estimates, and p-values for the same cancer gene. |
| `VSDFederatedCBioCancerGenePanels` | `cbioportal` | Retrieves a defined cBioPortal sequencing panel and its gene inventory for workflow-level membership assessment. |

## Scenario Evidence

### TP53: Human Papillomavirus-Related Endocervical Adenocarcinoma

| Evidence layer | Observation | Provider |
|---|---|---|
| `alphafold_models: Representative predicted structure` | `[{"globalMetricValue": 75.06, "latestVersion": 6, "modelEntityId": "AF-P04637-F1", "uniprotAccession": "P04637"}]` | `alphafold.ebi.ac.uk` |
| `monarch_gene: Normalized gene entity` | `{"category": "biolink:Gene", "id": "HGNC:11998", "name": "TP53", "symbol": "TP53"}` | `api-v3.monarchinitiative.org` |
| `reactome_pathway: Mechanistic pathway` | `{"displayName": "p53-Dependent G1 DNA Damage Response", "isInDisease": false, "speciesName": "Homo sapiens", "stId": "R-HSA-69563"}` | `reactome.org` |
| `gtex_gene_reference: GTEx reference gene` | `{"chromosome": "chr17", "end": 7687550, "entrezGeneId": 7157, "gencodeId": "ENSG00000141510.16", "geneSymbol": "TP53", "start": 7661779}` | `gtexportal.org` |
| `cellosaurus_model: Cell-line accession` | `{"type": "primary", "value": "CVCL_0030"}` | `api.cellosaurus.org` |
| `cellosaurus_model: Cell-line disease annotation` | `{"accession": "C27677", "database": "NCIt", "iri": "http://purl.obolibrary.org/obo/NCIT_C27677", "label": "Human papillomavirus-related endocervical adenocarcinoma"}` | `api.cellosaurus.org` |
| `eqtl_associations: Representative regulatory associations` | `[{"beta": -0.031020600348711014, "dataset_id": "QTD000605", "gene_id": "ENSG00000141510", "pvalue": 0.8880540132522583, "rsid": "rs57684686", "se": 0.22005000710487366, "study_id": "QTS000037", "variant": "chr17_6690403_G_A"}, {"beta": 0.5499770045280457, "dataset_id": "QTD000605", "gene_id": "ENSG00000141510", "pvalue": 0.11778099834918976, "rsid": "rs77...` | `www.ebi.ac.uk` |
| `cbio_gene_panel: Cancer sequencing panel` | `{"description": "Targeted (341 cancer genes) sequencing of various tumor types via MSK-IMPACT on Illumina HiSeq sequencers.", "genePanelId": "IMPACT341"}` | `www.cbioportal.org` |
| `cbio_gene_panel: Scenario gene in panel` | `[{"entrezGeneId": 7157, "hugoGeneSymbol": "TP53"}]` | `www.cbioportal.org` |

### BRCA1: Invasive Breast Carcinoma

| Evidence layer | Observation | Provider |
|---|---|---|
| `alphafold_models: Representative predicted structure` | `[{"globalMetricValue": 41.59, "latestVersion": 6, "modelEntityId": "AF-P38398-F1", "uniprotAccession": "P38398"}]` | `alphafold.ebi.ac.uk` |
| `monarch_gene: Normalized gene entity` | `{"category": "biolink:Gene", "id": "HGNC:1100", "name": "BRCA1", "symbol": "BRCA1"}` | `api-v3.monarchinitiative.org` |
| `reactome_pathway: Mechanistic pathway` | `{"displayName": "DNA Double-Strand Break Repair", "isInDisease": false, "speciesName": "Homo sapiens", "stId": "R-HSA-5693532"}` | `reactome.org` |
| `gtex_gene_reference: GTEx reference gene` | `{"chromosome": "chr17", "end": 43170245, "entrezGeneId": 672, "gencodeId": "ENSG00000012048.20", "geneSymbol": "BRCA1", "start": 43044295}` | `gtexportal.org` |
| `cellosaurus_model: Cell-line accession` | `{"type": "primary", "value": "CVCL_0031"}` | `api.cellosaurus.org` |
| `cellosaurus_model: Cell-line disease annotation` | `{"accession": "C4194", "database": "NCIt", "iri": "http://purl.obolibrary.org/obo/NCIT_C4194", "label": "Invasive breast carcinoma of no special type"}` | `api.cellosaurus.org` |
| `eqtl_associations: Representative regulatory associations` | `[{"beta": -0.0027977300342172384, "dataset_id": "QTD000394", "gene_id": "ENSG00000012048", "pvalue": 0.9909949898719788, "rsid": "rs57173345", "se": 0.24741299450397491, "study_id": "QTS000022", "variant": "chr17_42174076_T_G"}, {"beta": 0.07570499926805496, "dataset_id": "QTD000394", "gene_id": "ENSG00000012048", "pvalue": 0.7689549922943115, "rsid": "rs...` | `www.ebi.ac.uk` |
| `cbio_gene_panel: Cancer sequencing panel` | `{"description": "FoundationOne gene panel (317 genes)", "genePanelId": "FoundationOne"}` | `www.cbioportal.org` |
| `cbio_gene_panel: Scenario gene in panel` | `[{"entrezGeneId": 672, "hugoGeneSymbol": "BRCA1"}]` | `www.cbioportal.org` |

### EGFR: Lung Adenocarcinoma

| Evidence layer | Observation | Provider |
|---|---|---|
| `alphafold_models: Representative predicted structure` | `[{"globalMetricValue": 75.94, "latestVersion": 6, "modelEntityId": "AF-P00533-F1", "uniprotAccession": "P00533"}]` | `alphafold.ebi.ac.uk` |
| `monarch_gene: Normalized gene entity` | `{"category": "biolink:Gene", "id": "HGNC:3236", "name": "EGFR", "symbol": "EGFR"}` | `api-v3.monarchinitiative.org` |
| `reactome_pathway: Mechanistic pathway` | `{"displayName": "Signaling by EGFR", "isInDisease": false, "speciesName": "Homo sapiens", "stId": "R-HSA-177929"}` | `reactome.org` |
| `gtex_gene_reference: GTEx reference gene` | `{"chromosome": "chr7", "end": 55211628, "entrezGeneId": 1956, "gencodeId": "ENSG00000146648.17", "geneSymbol": "EGFR", "start": 55019021}` | `gtexportal.org` |
| `cellosaurus_model: Cell-line accession` | `{"type": "primary", "value": "CVCL_0023"}` | `api.cellosaurus.org` |
| `cellosaurus_model: Cell-line disease annotation` | `{"accession": "C3512", "database": "NCIt", "iri": "http://purl.obolibrary.org/obo/NCIT_C3512", "label": "Lung adenocarcinoma"}` | `api.cellosaurus.org` |
| `eqtl_associations: Representative regulatory associations` | `[{"beta": -0.04925350099802017, "dataset_id": "QTD000397", "gene_id": "ENSG00000146648", "pvalue": 0.8095020055770874, "rsid": "rs7811334", "se": 0.20391100645065308, "study_id": "QTS000022", "variant": "chr7_54024714_T_C"}, {"beta": -0.10296399891376495, "dataset_id": "QTD000397", "gene_id": "ENSG00000146648", "pvalue": 0.4851979911327362, "rsid": "rs152...` | `www.ebi.ac.uk` |
| `cbio_gene_panel: Cancer sequencing panel` | `{"description": "DFCI-ONCOPANEL-3, Number of Genes - 447", "genePanelId": "DFCI-ONCOPANEL-3"}` | `www.cbioportal.org` |
| `cbio_gene_panel: Scenario gene in panel` | `[{"entrezGeneId": 1956, "hugoGeneSymbol": "EGFR"}]` | `www.cbioportal.org` |

## Qualification Decisions

| Candidate | Source | Decision |
|---|---|---|
| `VSDFederatedRejectedCBioGene` | `cbioportal` | Rejected during live response validation |
| `VSDFederatedRejectedPDBeEntities` | `pdbe_graph` | Rejected during live response validation |
| `VSDFederatedRejectedOmicsDIDatabases` | `omicsdi` | Rejected during live response validation |

## Operational Interpretation

The federated manifest converted reviewed contract sources into a bounded candidate portfolio and added 518 operation identities beyond the previous catalog scan. Seven selected gaps became locally loadable tools only after live verification and explicit review. Three schema-drifted candidates were rejected, demonstrating that source trust does not bypass operation-level evidence.

The 533 previews are candidates, not 533 approved tools. This evaluation supports seven selected tools with complete promotion evidence and records three explicit rejections; the built-in registry was not changed.

Study digest: `d8487760fe84a3d2a086d592763ffb8326225ea654d2bd305273063605a18924`
Source scan digest: `fc986e78d3a5b8cf26be0d2d50bee54b01b178d0be092bca71f9e65e2b272a49`
