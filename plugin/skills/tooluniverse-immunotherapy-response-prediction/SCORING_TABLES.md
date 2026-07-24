# Scoring Tables: Immunotherapy Response Prediction

## Cancer-Specific ICI Context

| Cancer Type | EFO ID | Baseline ICI ORR | Key Biomarkers | FDA-Approved ICIs |
|-------------|--------|-------------------|----------------|-------------------|
| Melanoma | EFO_0000756 | 30-45% | TMB, PD-L1 | pembro, nivo, ipi, nivo+ipi, nivo+rela |
| NSCLC | EFO_0003060 | 15-50% (PD-L1 dependent) | PD-L1, TMB, STK11 | pembro, nivo, atezo, durva, cemiplimab |
| Bladder/UC | EFO_0000292 | 15-25% | PD-L1, TMB | pembro, nivo, atezo, avelumab, durva |
| RCC | EFO_0000681 | 25-40% | PD-L1 | nivo, pembro, nivo+ipi, nivo+cabo, pembro+axitinib |
| HNSCC | EFO_0000181 | 15-20% | PD-L1 CPS | pembro, nivo |
| MSI-H (any) | N/A | 30-50% | MSI, dMMR | pembro (tissue-agnostic) |
| TMB-H (any) | N/A | 20-30% | TMB >=10 | pembro (tissue-agnostic) |
| CRC (MSI-H) | EFO_0000365 | 30-50% | MSI, dMMR | pembro, nivo, nivo+ipi |
| CRC (MSS) | EFO_0000365 | <5% | Generally poor | Generally not recommended |
| HCC | EFO_0000182 | 15-20% | PD-L1 | atezo+bev, durva+treme, nivo+ipi |
| TNBC | EFO_0005537 | 10-20% | PD-L1 CPS | pembro+chemo |
| Gastric/GEJ | EFO_0000178 | 10-20% | PD-L1 CPS, MSI | pembro, nivo |

## TMB Classification & Scoring

| TMB Range | Classification | ICI Score Component |
|-----------|---------------|---------------------|
| >= 20 mut/Mb | TMB-High | 30 points |
| 10-19.9 mut/Mb | TMB-Intermediate | 20 points |
| 5-9.9 mut/Mb | TMB-Low | 10 points |
| < 5 mut/Mb | TMB-Very-Low | 5 points |

### Cancer-Specific TMB Thresholds

| Cancer Type | Typical TMB Range | High-TMB Threshold | Notes |
|-------------|-------------------|-------------------|-------|
| Melanoma | 5-50+ | >20 | High baseline TMB; UV-induced |
| NSCLC | 2-30 | >10 | Smoking-related; FDA cutoff 10 |
| Bladder | 5-25 | >10 | Moderate baseline |
| CRC (MSI-H) | 20-100+ | >10 | Very high in MSI-H |
| CRC (MSS) | 2-10 | >10 | Generally low |
| RCC | 1-8 | >10 | Low TMB but ICI-responsive |
| HNSCC | 2-15 | >10 | Moderate |

## MSI Status Scoring

| MSI Status | Classification | Score Component |
|-----------|----------------|----------------|
| MSI-H / dMMR | MSI-High | 25 points |
| MSS / pMMR | Microsatellite Stable | 5 points |
| Unknown | Not tested | 10 points (neutral) |

## PD-L1 Scoring

| PD-L1 Level | Classification | Score Component |
|-------------|----------------|----------------|
| >= 50% (TPS) | PD-L1 High | 20 points |
| 1-49% (TPS) | PD-L1 Positive | 12 points |
| < 1% (TPS) | PD-L1 Negative | 5 points |
| Unknown | Not tested | 10 points (neutral) |

### Cancer-Specific PD-L1 Thresholds

| Cancer | Scoring Method | Key Thresholds | ICI Monotherapy Recommended? |
|--------|---------------|----------------|------------------------------|
| NSCLC | TPS | >=50%: first-line mono; >=1%: after chemo | Yes at >=50%, combo at >=1% |
| Melanoma | Not routinely required | N/A | Yes regardless of PD-L1 |
| Bladder | CPS or IC | CPS>=10 preferred | Yes with PD-L1 positive |
| HNSCC | CPS | CPS>=1: pembro; CPS>=20: mono preferred | CPS>=20 for monotherapy |
| Gastric | CPS | CPS>=1 | Pembro+chemo |
| TNBC | CPS | CPS>=10 | Pembro+chemo |

## Neoantigen Score Component

| Estimated Neoantigen Load | Classification | Score |
|---------------------------|---------------|-------|
| >50 neoantigens | High | 15 points |
| 20-50 neoantigens | Moderate | 10 points |
| <20 neoantigens | Low | 5 points |

## ICI-Resistance Mutations (Penalties)

| Gene | Mutation | Cancer Context | Mechanism | Penalty |
|------|----------|---------------|-----------|---------|
| STK11/LKB1 | Loss/inactivation | NSCLC (esp. KRAS+) | Immune exclusion, cold TME | -10 points |
| PTEN | Loss/deletion | Multiple | Reduced T cell infiltration | -5 points |
| JAK1 | Loss of function | Multiple | IFN-g signaling loss | -10 points |
| JAK2 | Loss of function | Multiple | IFN-g signaling loss | -10 points |
| B2M | Loss/mutation | Multiple | MHC-I loss, immune escape | -15 points |
| KEAP1 | Loss/mutation | NSCLC | Oxidative stress, cold TME | -5 points |
| MDM2 | Amplification | Multiple | Hyperprogression risk | -5 points |
| MDM4 | Amplification | Multiple | Hyperprogression risk | -5 points |
| EGFR | Activating mutation | NSCLC | Low TMB, cold TME | -5 points |

## ICI-Sensitivity Mutations (Bonuses)

| Gene | Mutation | Cancer Context | Mechanism | Bonus |
|------|----------|---------------|-----------|-------|
| POLE | Exonuclease domain | Any | Ultramutation, high neoantigens | +10 points |
| POLD1 | Proofreading domain | Any | Ultramutation | +5 points |
| BRCA1/2 | Loss of function | Multiple | Genomic instability | +3 points |
| ARID1A | Loss of function | Multiple | Chromatin remodeling, TME | +3 points |
| PBRM1 | Loss of function | RCC | ICI response in RCC | +5 points (RCC only) |

## Pathway-Level Resistance

| Pathway | Resistance Mechanism | Genes |
|---------|---------------------|-------|
| IFN-g signaling | Loss of IFN-g response | JAK1, JAK2, STAT1, IRF1 |
| Antigen presentation | MHC-I downregulation | B2M, TAP1, TAP2, HLA-A/B/C |
| WNT/b-catenin | T cell exclusion | CTNNB1 activating mutations |
| MAPK pathway | Immune suppression | MEK, ERK hyperactivation |
| PI3K/AKT/mTOR | Immune suppression | PTEN loss, PIK3CA |

## ICI Drug Profiles

| Drug | Target | Type | Key Indications |
|------|--------|------|-----------------|
| Pembrolizumab (Keytruda) | PD-1 | IgG4 mAb | Melanoma, NSCLC, HNSCC, Bladder, MSI-H, TMB-H, many others |
| Nivolumab (Opdivo) | PD-1 | IgG4 mAb | Melanoma, NSCLC, RCC, CRC (MSI-H), HCC, HNSCC |
| Atezolizumab (Tecentriq) | PD-L1 | IgG1 mAb | NSCLC, Bladder, HCC, Melanoma |
| Durvalumab (Imfinzi) | PD-L1 | IgG1 mAb | NSCLC (Stage III), Bladder, HCC, BTC |
| Ipilimumab (Yervoy) | CTLA-4 | IgG1 mAb | Melanoma, RCC (combo), CRC (MSI-H combo) |
| Avelumab (Bavencio) | PD-L1 | IgG1 mAb | Merkel cell, Bladder (maintenance) |
| Cemiplimab (Libtayo) | PD-1 | IgG4 mAb | CSCC, NSCLC, Basal cell |
| Dostarlimab (Jemperli) | PD-1 | IgG4 mAb | dMMR endometrial, dMMR solid tumors |
| Tremelimumab (Imjudo) | CTLA-4 | IgG2 mAb | HCC (combo with durva) |

### Key ICI ChEMBL IDs

| Drug | ChEMBL ID |
|------|-----------|
| Pembrolizumab | CHEMBL3137343 |
| Nivolumab | CHEMBL2108738 |
| Atezolizumab | CHEMBL3707227 |
| Durvalumab | CHEMBL3301587 |
| Ipilimumab | CHEMBL1789844 |
| Avelumab | CHEMBL3833373 |
| Cemiplimab | CHEMBL4297723 |

## ICI Drug Selection Algorithm

```
IF MSI-H:
  -> Pembrolizumab (tissue-agnostic FDA approval)
  -> Nivolumab (CRC-specific)
  -> Consider nivo+ipi combination

IF TMB-H (>=10) and not MSI-H:
  -> Pembrolizumab (tissue-agnostic for TMB-H)

IF Cancer = Melanoma:
  IF PD-L1 >= 1%: pembrolizumab or nivolumab monotherapy
  ELSE: nivolumab + ipilimumab combination
  IF BRAF V600E: consider targeted therapy first if rapid response needed

IF Cancer = NSCLC:
  IF PD-L1 >= 50% and no STK11/EGFR: pembrolizumab monotherapy
  IF PD-L1 1-49%: pembrolizumab + chemotherapy
  IF PD-L1 < 1%: ICI + chemotherapy combination
  IF STK11 loss: ICI less likely effective
  IF EGFR/ALK positive: targeted therapy preferred over ICI

IF Cancer = RCC:
  -> Nivolumab + ipilimumab (IMDC intermediate/poor risk)
  -> Pembrolizumab + axitinib (all risk)

IF Cancer = Bladder:
  -> Pembrolizumab or atezolizumab (2L)
  -> Avelumab maintenance post-platinum
```
