# Input Reference: Immunotherapy Response Prediction

## Accepted Input Formats

| Format | Example | How to Parse |
|--------|---------|-------------|
| Cancer + mutations | "Melanoma, BRAF V600E, TP53 R273H" | cancer=melanoma, mutations=[BRAF V600E, TP53 R273H] |
| Cancer + TMB | "NSCLC, TMB 25 mut/Mb" | cancer=NSCLC, tmb=25 |
| Cancer + full profile | "Melanoma, BRAF V600E, TMB 15, PD-L1 50%, MSS" | cancer=melanoma, mutations=[BRAF V600E], tmb=15, pdl1=50, msi=MSS |
| Cancer + MSI status | "Colorectal cancer, MSI-high" | cancer=CRC, msi=MSI-H |
| Resistance query | "NSCLC, TMB 2, STK11 loss, PD-L1 <1%" | cancer=NSCLC, tmb=2, mutations=[STK11 loss], pdl1=0 |
| ICI selection | "Which ICI for NSCLC PD-L1 90%?" | cancer=NSCLC, pdl1=90, query_type=drug_selection |

## Cancer Type Normalization

Common aliases to resolve:
- NSCLC -> non-small cell lung carcinoma
- SCLC -> small cell lung carcinoma
- CRC -> colorectal cancer
- RCC -> renal cell carcinoma
- HNSCC -> head and neck squamous cell carcinoma
- UC / bladder -> urothelial carcinoma
- HCC -> hepatocellular carcinoma
- TNBC -> triple-negative breast cancer
- GEJ -> gastroesophageal junction cancer

## Gene Symbol Normalization

- PD-L1 -> CD274
- PD-1 -> PDCD1
- CTLA-4 -> CTLA4
- HER2 -> ERBB2
- MSH2/MLH1/MSH6/PMS2 -> MMR genes

## Mutation Parsing

Parse each mutation into structured format:
```
"BRAF V600E" -> {gene: "BRAF", variant: "V600E", type: "missense"}
"TP53 R273H" -> {gene: "TP53", variant: "R273H", type: "missense"}
"STK11 loss" -> {gene: "STK11", variant: "loss of function", type: "loss"}
```
