---
name: tooluniverse-plant-genomics
description: Research plant genes, pathways, and species using PlantReactome, Ensembl Plants, POWO, UniProt, KEGG, and literature tools. Covers plant pathway analysis, gene function annotation, species identification, crop genomics, and comparative plant biology. Use when asked about plant genes, Arabidopsis, crop improvement, plant pathways, plant metabolism, photosynthesis, plant development, or plant species identification.
---

# Plant Genomics & Biology

Pipeline for investigating plant genes, metabolic pathways, species taxonomy, and comparative plant biology using ToolUniverse tools.

## Reasoning Strategy

Plant genomes are large (wheat is ~17 Gb, vs. 3 Gb for human) and often polyploid — wheat is hexaploid (AABBDD), meaning there are three homeologous copies of most genes. When comparing plant genes to Arabidopsis, always account for whole-genome duplications: a single Arabidopsis gene may have 2–4 paralogs in a crop species, all potentially with diverged functions. Gene families are massively expanded in plants relative to animals (e.g., receptor-like kinases, cytochrome P450s, transcription factors) — a BLAST hit does not mean functional equivalence. Arabidopsis thaliana is the primary model, but its small genome and rapid life cycle mean some features (wood formation, nitrogen fixation symbiosis, C4 photosynthesis) are absent and must be studied in other species.

**LOOK UP DON'T GUESS**: Do not assume gene function by sequence similarity alone in polyploid species; look up functional validation evidence via UniProt (reviewed entries) or PlantReactome. Do not assume KEGG organism codes — use the table or query `kegg_search_pathway` with the species name to confirm availability.

**Key principles**:
1. **Plant-specific pathways** — photosynthesis, secondary metabolism, hormone signaling are unique to plants
2. **PlantReactome as foundation** — curated plant pathway database with cross-species coverage (Oryza, Arabidopsis, Zea mays, etc.)
3. **Ensembl Plants for genomics** — use Ensembl with plant species names for gene lookup and annotation
4. **KEGG for metabolism** — KEGG has plant-specific organism codes (ath=Arabidopsis, osa=rice, zma=maize)
5. **Evidence grading** — T1: functional validation (mutant phenotype), T2: expression/localization data, T3: ortholog-based prediction, T4: computational annotation only

---

## When to Use

- "What pathway is [plant gene] involved in?"
- "Find genes in the flavonoid biosynthesis pathway"
- "Compare [gene] across Arabidopsis and rice"
- "What species is [plant name]?"
- "Plant hormone signaling pathways"
- "Photosynthesis gene annotation"

**Not this skill**: For general pathway analysis (human/mouse), use `tooluniverse-systems-biology`. For phylogenetics, use `tooluniverse-phylogenetics`.

---

## Core Tools

| Tool | Use For |
|------|---------|
| `PlantReactome_search_pathways` | Search plant-specific pathways by keyword |
| `PlantReactome_get_pathway` | Get pathway details (genes, reactions, species) |
| `PlantReactome_list_species` | List all species covered by PlantReactome |
| `POWO_search_plants` | Search Plants of the World Online (taxonomy, distribution) |
| `ensembl_lookup_gene` | Gene lookup — use with plant species (e.g., `species="arabidopsis_thaliana"`) |
| `kegg_search_pathway` | Search KEGG pathways (use plant organism codes: ath, osa, zma) |
| `KEGG_get_pathway_genes` | Get genes in a plant pathway (e.g., `pathway_id="ath00941"` for flavonoid in Arabidopsis) |
| `UniProt_search` | Search plant protein sequences (add `taxonomy_id:3702` for Arabidopsis) |
| `UniProt_get_function_by_accession` | Get protein function annotation |
| `PubMed_search_articles` | Plant biology literature |
| `EnsemblCompara_get_orthologues` | Cross-species plant gene comparison |

---

## Workflow

```
Phase 0: Species & Gene Identification
  Species name → POWO taxonomy; Gene symbol → Ensembl/UniProt IDs
    |
Phase 1: Gene Function & Annotation
  UniProt function, Ensembl annotation, InterPro domains
    |
Phase 2: Pathway Analysis
  PlantReactome → plant-specific pathways; KEGG → metabolism
    |
Phase 3: Cross-Species Comparison
  Ensembl Compara → orthologs in other plant species
    |
Phase 4: Literature & Report
  PubMed → published studies; synthesis
```

### Phase 1: Gene Function

```python
# Look up an Arabidopsis gene
ensembl_lookup_gene(gene_symbol="CHS", species="arabidopsis_thaliana")
# Get protein function
UniProt_search(query="CHS AND taxonomy_id:3702 AND reviewed:true")
```

### Phase 2: Plant Pathway Analysis

**Key plant-specific KEGG pathways**:

| Pathway | KEGG ID (Arabidopsis) | Biological Significance |
|---------|----------------------|------------------------|
| Photosynthesis | ath00195 | Light reactions, electron transport |
| Carbon fixation (Calvin cycle) | ath00710 | CO2 → sugar |
| Flavonoid biosynthesis | ath00941 | UV protection, pigmentation, defense |
| Carotenoid biosynthesis | ath00906 | Photoprotection, vitamin A precursors |
| Auxin signaling | ath04075 | Growth, tropisms |
| Brassinosteroid signaling | ath04712 | Cell elongation, stress response |
| Circadian rhythm (plant) | ath04712 | Photoperiod, flowering time |
| Terpenoid backbone | ath00900 | Secondary metabolite precursors |
| Starch/sucrose metabolism | ath00500 | Carbon partitioning |
| Nitrogen metabolism | ath00910 | Nitrogen assimilation |

```python
# Search PlantReactome for flavonoid pathway
PlantReactome_search_pathways(query="flavonoid")
# Get genes in Arabidopsis flavonoid biosynthesis
KEGG_get_pathway_genes(pathway_id="ath00941")
```

### Phase 3: Species Comparison

**KEGG organism codes for major crops**:

| Species | Code | Common Name |
|---------|------|-------------|
| Arabidopsis thaliana | ath | Thale cress (model plant) |
| Oryza sativa | osa | Rice |
| Zea mays | zma | Maize/corn |
| Triticum aestivum | tae | Wheat |
| Glycine max | gmx | Soybean |
| Solanum lycopersicum | sly | Tomato |
| Nicotiana tabacum | nta | Tobacco |
| Medicago truncatula | mtr | Barrel medic (legume model) |

### Phase 4: Interpretation Framework

**Evidence grading**: T1 = mutant phenotype confirms function; T2 = expression/localization data; T3 = ortholog has validated function in model species; T4 = computational annotation only (domain/GO term). Prioritize T1/T2 evidence; treat T3/T4 as hypotheses requiring further validation.

### Synthesis Questions

1. **Is the gene plant-specific or conserved?** (Plant-specific genes often in secondary metabolism; conserved genes in primary metabolism)
2. **Which tissues/developmental stages express it?** (Root vs shoot vs flower vs seed)
3. **Is there a crop improvement application?** (Yield, stress tolerance, nutritional quality)
4. **What regulatory mechanisms control it?** (Hormone-responsive, light-regulated, circadian)
5. **Are there natural variants with known phenotypes?** (Accession diversity in Arabidopsis 1001 Genomes)

---

## Limitations

- **No TAIR tool** — The Arabidopsis Information Resource has no public REST API. Use Ensembl Plants and UniProt as alternatives for Arabidopsis gene data.
- **PlantReactome coverage** — Focused on Oryza sativa (rice) with cross-references to Arabidopsis. Not all plant species equally covered.
- **No crop breeding tools** — This skill covers gene/pathway analysis, not marker-assisted selection or breeding simulation.
- **POWO is taxonomy-focused** — Plants of the World Online provides species identification and distribution, not genomics data.
