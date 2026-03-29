---
name: tooluniverse-chemical-sourcing
description: Find commercial sources for chemical compounds using ZINC, Enamine, eMolecules, and Mcule. Covers compound identification, vendor search, pricing, analog discovery, and order preparation. Use when buying compounds, checking commercial availability, comparing vendors, or finding purchasable analogs.
---

# Chemical Compound Sourcing & Procurement

Pipeline for identifying, sourcing, and purchasing chemical compounds from commercial vendors. Resolves compound identity through PubChem/ChEMBL, searches multiple vendor databases (ZINC, Enamine, eMolecules, Mcule), compares pricing and availability, and identifies purchasable analogs when exact compounds are unavailable.

**Guiding principles**:
1. **Identity first** -- confirm the compound's structure (SMILES, InChI) before searching vendors; names can be ambiguous
2. **Multi-vendor comparison** -- always check multiple sources; pricing and stock vary significantly
3. **Analog fallback** -- if the exact compound is unavailable, search for close analogs
4. **Purity and quantity awareness** -- note catalog purity grades and minimum order quantities
5. **Structure over name** -- vendor searches by SMILES/InChI are more reliable than name searches
6. **English-first queries** -- use English compound names in tool calls

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Typical triggers:
- "Where can I buy [compound]?"
- "Find commercial sources for [SMILES]"
- "Compare prices for [compound] across vendors"
- "Is [compound] commercially available?"
- "Find purchasable analogs of [compound]"
- "I need [quantity] of [compound] -- who sells it?"
- "Search ZINC/Enamine for [compound]"

**Not this skill**: For ADMET/toxicity assessment, use `tooluniverse-admet-prediction`. For drug-target interaction analysis, use `tooluniverse-drug-target-validation`.

---

## Core Databases

| Database | Scope | Best For |
|----------|-------|----------|
| **ZINC** | 230M+ purchasable compounds; aggregates vendors | Broadest coverage; substructure/similarity search; free |
| **Enamine** | ~4M in-stock, 30B+ REAL (make-on-demand) | Large in-stock library; fast delivery; building blocks |
| **eMolecules** | Multi-vendor aggregator; 8M+ compounds | Cross-vendor comparison; pricing transparency |
| **Mcule** | 40M+ compounds; one-stop purchasing | Integrated ordering; quote generation |
| **PubChem** | 110M+ compounds; identity resolution | Authoritative compound identification; CID lookup |
| **ChEMBL** | 2.4M+ bioactive molecules | Bioactivity context for sourced compounds |

---

## Workflow Overview

```
Phase 0: Compound Identity Resolution
  Name/SMILES/CAS -> PubChem CID -> canonical SMILES
    |
Phase 1: Vendor Search
  Query ZINC, Enamine, eMolecules, Mcule
    |
Phase 2: Price & Availability Comparison
  Catalog numbers, pricing, stock status, purity
    |
Phase 3: Analog Search (if needed)
  Similarity search for purchasable alternatives
    |
Phase 4: Bioactivity Context (optional)
  ChEMBL activity data for sourced compounds
    |
Phase 5: Order Summary
  Consolidated vendor comparison table
```

---

## Phase Details

### Phase 0: Compound Identity Resolution

**Objective**: Establish unambiguous compound identity before vendor searches.

**Tools**:
- `PubChem_get_CID_by_compound_name` -- resolve name to CID
  - Input: `name` (compound name)
  - Output: `{IdentifierList: {CID: [...]}}`
- `PubChem_get_compound_properties_by_CID` -- get SMILES, MW, formula
  - Input: `cid` (PubChem CID), `properties` (comma-separated list)
  - Output: `{CID, MolecularWeight, ConnectivitySMILES, IUPACName}`
- `ChEMBL_get_molecule` -- get ChEMBL compound details
  - Input: `molecule_chembl_id` (ChEMBL ID) or search by name
  - Output: SMILES, molecular properties, synonyms

**Workflow**:
1. If user provides a name: resolve to PubChem CID, then get SMILES
2. If user provides SMILES: use directly (optionally verify via PubChem)
3. If user provides CAS number: search PubChem by name (CAS numbers work as search terms)
4. Record: canonical SMILES, molecular weight, molecular formula, IUPAC name

**Important**: PubChem `ConnectivitySMILES` (not `CanonicalSMILES`) is the correct property name. Always confirm the SMILES matches the intended compound before proceeding.

### Phase 1: Vendor Search

**Objective**: Search all available vendor databases for the target compound.

**Tools**:
- `ZINC_search_compounds` -- search ZINC by name or SMILES
  - Input: `query` (name or SMILES), optional `catalog`, `limit`
  - Output: ZINC IDs, vendor info, purchasability status
- `ZINC_get_compound` -- get detailed compound info from ZINC
  - Input: `zinc_id` (ZINC identifier)
  - Output: vendors, catalogs, pricing, SMILES
- `Enamine_search_catalog` -- search Enamine catalog
  - Input: `query` (name or SMILES), optional `catalog_type`, `limit`
  - Output: catalog numbers, availability, pricing
- `Enamine_get_compound` -- get Enamine compound details
  - Input: `compound_id` (Enamine catalog number)
  - Output: structure, pricing, stock status, delivery time
- `eMolecules_search` -- search across multiple vendors
  - Input: `query` (name or SMILES), optional `limit`
  - Output: vendor list, catalog numbers, pricing
- `eMolecules_get_compound` -- get eMolecules compound details
  - Input: `compound_id` (eMolecules ID)
  - Output: vendors, pricing tiers, purity
- `Mcule_get_compound` -- search Mcule database
  - Input: `query` (name or SMILES), optional `limit`
  - Output: Mcule IDs, availability, pricing
- `Mcule_get_compound` -- get Mcule compound details
  - Input: `compound_id` (Mcule ID)
  - Output: pricing, delivery, purity, catalog number

**Workflow**:
1. Search all four vendor databases in parallel using SMILES (preferred) or name
2. For each hit, retrieve detailed compound info (pricing, stock, purity)
3. Deduplicate results by matching SMILES across vendors
4. Flag any structural mismatches (vendor compound differs from target)

**Tip**: SMILES-based searches are more precise than name searches. If name search returns too many results, switch to SMILES.

### Phase 2: Price & Availability Comparison

**Objective**: Create a comparison table across vendors.

Compile from Phase 1 results:

| Field | Description |
|-------|-------------|
| Vendor | Company name |
| Catalog # | Vendor-specific identifier |
| Quantity | Available pack sizes |
| Price | Per unit or per mg |
| Purity | Stated purity grade (>95%, >98%, etc.) |
| Stock | In-stock vs make-on-demand |
| Delivery | Estimated delivery time |

Rank vendors by: (1) in-stock availability, (2) price per mg, (3) purity grade, (4) delivery time.

### Phase 3: Analog Search

**Objective**: When the exact compound is unavailable, find purchasable structural analogs.

Triggered when:
- No vendors carry the target compound
- The compound is prohibitively expensive
- The user explicitly requests analogs

**Approach**:
1. Use ZINC or Enamine similarity search (if supported by the tool's search mode)
2. Search by substructure using the compound's core scaffold SMILES
3. Filter analogs by: Tanimoto similarity >= 0.7, commercial availability, reasonable price
4. Present analogs with structural differences highlighted

### Phase 4: Bioactivity Context (Optional)

**Objective**: Provide biological activity data for context when sourcing compounds for research.

**Tools**:
- `ChEMBL_get_molecule` -- get bioactivity summary
  - Input: compound identifier
  - Output: known targets, activity values, assay data

Useful when:
- User is sourcing compounds for a specific biological assay
- Comparing analogs that might have different activity profiles
- Verifying the compound has published bioactivity data

### Phase 5: Decision & Order Summary

**Vendor selection decision matrix** — don't just list vendors, recommend one:

| Scenario | Best Vendor Strategy | Why |
|----------|---------------------|-----|
| **Need it this week** | In-stock vendor with fastest shipping | Make-on-demand takes 2-4 weeks minimum |
| **Budget-constrained** | Cheapest per mg, accept lower purity (>95%) | Academic budgets are tight; >95% is fine for screening |
| **High-throughput screen** | ZINC/Enamine for large libraries; mg quantities | Price per compound matters more than purity |
| **Assay validation** | Highest purity (>98%) from reputable vendor | False positives from impurities waste months |
| **Building blocks for synthesis** | Enamine (largest building block catalog) | Purpose-built for medicinal chemistry |
| **Exact compound unavailable** | Analog search → check bioactivity (ChEMBL) → source best analog | Tanimoto > 0.85 likely retains activity; 0.7-0.85 may have different SAR |

**Red flags when sourcing**:
- Vendor has no published purity data → request CoA before ordering
- Price is 10x lower than other vendors → may be a different salt form or impure
- "In stock" but delivery estimate is 4+ weeks → likely not actually in stock
- SMILES in vendor catalog differs from target SMILES → wrong compound

Generate a final sourcing report:

1. **Compound Identity** -- name, SMILES, MW, CAS (if known), PubChem CID
2. **Vendor Comparison Table** -- all vendors with pricing, stock, purity, delivery time
3. **Recommended Source** -- specific vendor with reasoning (not just cheapest)
4. **Analogs** (if searched) -- alternative compounds with similarity scores and bioactivity comparison
5. **Notes** -- special handling, storage conditions, salt form, stereochemistry considerations

---

## Common Analysis Patterns

| Pattern | Description | Key Phases |
|---------|-------------|------------|
| **Quick Availability Check** | Is this compound purchasable? | 0, 1 |
| **Full Vendor Comparison** | Compare all sources with pricing | 0, 1, 2, 5 |
| **Analog Discovery** | Compound unavailable; find alternatives | 0, 1, 3, 5 |
| **Building Block Sourcing** | Find reagents for synthesis | 0, 1, 2 |
| **Hit-to-Lead Sourcing** | Source screening hits with bioactivity context | 0, 1, 2, 4, 5 |

---

## Edge Cases & Fallbacks

- **Name ambiguity**: Multiple compounds share a name (e.g., "aspirin" vs "acetylsalicylic acid"). Always resolve to SMILES first
- **Stereochemistry**: Vendors may sell racemic mixtures vs specific enantiomers. Check SMILES stereochemistry carefully
- **Salt forms**: The same drug may be sold as different salts (HCl, maleate, etc.). Note the specific form
- **No vendors found**: Compound may be available through custom synthesis. Note this in the report
- **Make-on-demand**: Enamine REAL compounds require synthesis (2-4 weeks). Distinguish from in-stock items

---

## Interpretation Framework

| Evidence Grade | Criteria | Action |
|----------------|----------|--------|
| **A -- High confidence** | In-stock at 2+ vendors, purity >=98%, CoA available | Order directly |
| **B -- Moderate confidence** | Single vendor or make-on-demand, purity >=95% | Request CoA, verify structure |
| **C -- Low confidence** | No stock, purity unstated, or price outlier (>5x median) | Custom synthesis or analog search |

**Interpreting vendor results:**
- A 10x price difference between vendors for the same compound usually indicates different salt forms, purity grades, or packaging sizes rather than genuine cost differences -- always compare on a per-mg, same-purity basis.
- Purity of >=95% is sufficient for primary screening; >=98% is recommended for dose-response and SAR studies; >=99% is needed for reference standards and pharmacokinetic work.
- "In-stock" status in aggregator databases can be stale by weeks -- confirm real-time availability with the vendor before committing to a timeline.

**Synthesis questions to address in the final report:**
1. Do all vendor SMILES resolve to the same canonical structure (including stereochemistry and salt form)?
2. Is the price-per-mg consistent with the compound's synthetic complexity, or does an outlier suggest a catalog error?
3. For analogs: does the structural change fall outside the pharmacophore, preserving expected activity?

---

## Limitations

- **Pricing accuracy**: Database prices may be outdated; actual quotes from vendors are authoritative
- **Regional availability**: Some vendors ship only to specific regions; check shipping policies
- **Quantity limits**: Academic vs commercial pricing may differ; some vendors require institutional accounts
- **Controlled substances**: Some compounds have regulatory restrictions; this skill does not check legal status
- **No direct ordering**: This skill finds sources but does not place orders; users need vendor accounts
