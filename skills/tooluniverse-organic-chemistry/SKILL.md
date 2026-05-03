---
name: tooluniverse-organic-chemistry
description: Teaches reasoning strategies for organic chemistry problems — reaction product prediction, spectroscopy interpretation, stereochemistry, and quantitative calculations. Use when users ask about reaction products, spectra, mechanisms, stereochemistry, or molecular formulas.
---

# Organic Chemistry Reasoning Guide

This skill teaches **how to think through** organic chemistry problems, not what to memorize.

---

## 1. Predicting Reaction Products — A Reasoning Process

Do NOT pattern-match to a named reaction. Instead, reason from first principles:

### Step 1 — Find the most reactive sites

Look at each molecule and ask: where is the electron density?
- **Electron-rich sites** (nucleophiles): lone pairs on N, O, S; pi bonds (C=C, aromatics); carbanions; enolates
- **Electron-poor sites** (electrophiles): carbons bonded to electronegative atoms (C=O, C-X); carbocations; atoms with empty orbitals

The reaction will happen where the strongest nucleophile meets the strongest electrophile.

### Step 2 — What kind of bond-making/breaking is this?

Three fundamental categories:
- **Ionic (polar)**: electrons move in pairs. One species donates electrons, the other accepts. Most common in solution chemistry.
- **Radical**: electrons move one at a time. Look for: heat + peroxides, UV light (hv), NBS, or radical initiators.
- **Pericyclic**: electrons move in a concerted cyclic transition state. Look for: heat or light with no other reagents, dienes + dienophiles, sigmatropic rearrangements.

### Step 3 — Where do the electrons flow?

Draw the arrow from nucleophile to electrophile. Ask:
- Which atom has the best orbital overlap?
- Is backside attack required (SN2) or can the nucleophile approach from either face (SN1)?
- For additions to C=C: which carbon gets the electrophile? (Markovnikov = more substituted carbocation intermediate; anti-Markovnikov = radical or hydroboration)
- For additions to C=O: the nucleophile attacks carbon (Burgi-Dunitz angle ~107 degrees).
- For E2 eliminations: **base size determines regiochemistry**. Bulky bases (KOtBu, LDA, DBU) favor the Hofmann product (less substituted alkene) because they abstract the less sterically hindered proton. Small bases (NaOEt, KOH, NaOMe) favor the Zaitsev product (more substituted, more stable alkene). Always check base size before predicting regiochemistry.
- For ion tracking in multi-step syntheses: write out the complete ionic equation at each step. Track every cation and anion through each transformation — identify what dissolves, what precipitates, what complexes form, and what remains in solution. Verify at each step: are all ions accounted for? Does the mass balance? Use solubility rules (Ksp) and complex stability constants (Kf) to predict which species persist.

### Step 4 — What is the driving force?

Every reaction needs a thermodynamic reason to proceed:
- **Leaving group departure**: good leaving groups (I > Br > Cl > F; tosylate, triflate) stabilize themselves after leaving
- **Ring strain relief**: epoxide opening, cyclopropane opening
- **Aromaticity gain**: tautomerization to aromatic form, elimination to form conjugation
- **Strong bond formation**: C-O, C-F, H-O bonds are strong; reactions that form them are favored
- **Gas evolution**: loss of CO2, N2, or H2O drives equilibrium forward

### Step 5 — Sanity-check your product

Before reporting an answer:
- Are all valences correct? (C=4, N=3, O=2, H=1, halogens=1)
- Does the molecular formula balance? Count every atom on both sides.
- Is the product thermodynamically reasonable? (Don't propose anti-aromatic products or strained small rings without justification)
- Does degrees of unsaturation make sense? (DoU = (2C + 2 + N - H - X) / 2; a benzene ring = 4 DoU)

### Named Reaction Decision Tree

Identify the reaction type from reagents/conditions, then apply its product topology:

| Reagent/Condition Pattern | Reaction Type | Product Logic |
|---|---|---|
| RMgBr (or RLi) + ArX + Pd or Ni catalyst | **Kumada coupling** | R replaces X on Ar; excess RMgBr replaces ALL X |
| Ph3P=CHR + aldehyde/ketone | **Wittig** | C=C replaces C=O; **unstabilized ylide → Z-alkene; stabilized (ester/CN) → E-alkene** |
| Sulfoxide + strong electrophile (Tf2O, Ac2O) | **Pummerer rearrangement** | S-oxidation state drops; alpha-carbon gets new bond to nucleophile/leaving group |
| Allyl vinyl ether heated (or 1,5-dien-3-ol + base) | **[3,3]-sigmatropic** (oxy-Cope/Claisen) | Redraw 6-membered chair TS; new sigma bond at 1,6 positions; old 3,4 bond breaks |
| Diene + dienophile, heat | **Diels-Alder** | [4+2] cycloaddition; endo rule for stereochemistry; cis dienophile substituents stay cis |
| ArX + excess organometallic (no catalyst) | **Nucleophilic aromatic substitution** or **benzyne** | Each X replaced by nucleophile; count equivalents to determine degree of substitution |

### Retrosynthetic Analysis

Work backward from product to starting materials by identifying how key bonds were formed:

1. **Robinson Annulation** (product is a 2-cyclohexenone fused or substituted system):
   - Disconnect the C-C bond alpha to the enone carbonyl → two fragments: a 1,3-dicarbonyl compound + methyl vinyl ketone (or equivalent Michael acceptor)
   - The 1,3-dicarbonyl (e.g., ethyl 2-methyl-6-oxocyclohexanecarboxylate) is the starting material
   - Mechanism: Michael addition then intramolecular aldol condensation

2. **Intramolecular Aldol** (fused ring from KOH/base on an open-chain substrate):
   - Product is a fused bicyclic enone → starting material is a 1,5-diketone (or 1,n-diketone)
   - Carbon counting rule: product ring size = carbons between the two carbonyls + 1
   - Example: hexahydronaphthalen-2-one from KOH → start with 2-(3-oxopentyl)cyclohexanone, not a butyl chain

3. **General disconnection heuristic** — identify the new bond, then choose the right reaction:
   - New C-C bonds: aldol, Claisen, Michael, Wittig, Grignard, Diels-Alder
   - New C-O bonds: epoxidation, hydration, oxidation
   - New C-N bonds: reductive amination, Gabriel synthesis, amide coupling

### Product Prediction Strategy (Stepwise)

1. **Reactive sites**: Mark every nucleophilic and electrophilic center in all reactants
2. **Reaction type**: Match reagent/condition pattern to the decision tree above
3. **Bond changes**: Explicitly list which bonds break and which form (write them out)
4. **Regiochemistry**: Markovnikov (cation stability) vs anti-Markovnikov (radical/BH3); for ArX, each leaving group is an independent reactive site
5. **Stereochemistry**: Wittig E/Z from ylide type; SN2 inversion; [3,3] suprafacial-suprafacial (chair TS); Pummerer retains sulfur connectivity
6. **Name the product**: Convert the final structure to IUPAC; for biaryl systems count the phenyl groups systematically (e.g., three linked phenyls = terphenyl, not triphenylbenzene)

### Structure Determination from Reactions

- When a hydrocarbon reacts with Br2 under "normal conditions" (no UV, no catalyst): this is ionic ADDITION (to a strained ring or C=C), not radical substitution
- If the product has exactly 1 Br per carbon that reacted: suspect ring-opening of a strained cyclopropane or addition across C=C
- Strained 3-membered rings with Br2 undergo ionic ring-opening, not radical substitution
- When a metal dissolves in a solution of its own higher-valent salt, the product is the intermediate oxidation state (comproportionation), not a metal displacement

### Combustion Analysis Strategy

- Preferred: use `MolecularFormula_analyze` tool (via MCP/SDK) with `sample_g`, `CO2_g`, `H2O_g`, and `molar_mass` parameters. Fallback: run `molecular_formula.py` directly.
- Preferred: use `DegreesOfUnsaturation_calculate` tool with `formula` parameter. Fallback: run `degrees_of_unsaturation.py --formula <result>`.
- Match DoU + any functional group test results (Br2 decolorization, KMnO4, etc.) to narrow the structure

---

## 2. Spectroscopy Interpretation — A Problem-Solving Strategy

Do NOT look up tables of chemical shifts. Instead, follow this systematic approach:

### Start with molecular formula

If given, calculate degrees of unsaturation first. This immediately tells you:
- DoU = 0: no rings or double bonds (saturated, open chain)
- DoU = 1: one ring OR one double bond
- DoU = 4: almost certainly a benzene ring (3 double bonds + 1 ring)
- DoU = 2: could be a triple bond, or two double bonds, or a ring + double bond

This single number eliminates huge categories of structures before you look at any spectrum.

### IR: Look for the obvious peaks first

Do not try to assign every peak. Instead, ask three questions:
1. **Is there a broad absorption around 2500-3500?** If yes: O-H (very broad) or N-H (sharper, sometimes two peaks for primary amine).
2. **Is there a strong sharp peak around 1650-1750?** If yes: C=O. Its exact position tells you the type (ester ~1735, ketone ~1715, acid ~1710, amide ~1680).
3. **Is there a peak around 2100-2300?** If yes: triple bond (C-triple-C or C-triple-N) or cumulated double bond.

If you can answer these three questions, you have identified the major functional groups. Everything else is confirmatory.

### 1H NMR: Three pieces of information per signal

Every signal tells you three things — use all of them:
1. **Chemical shift (where)**: How deshielded is this proton? Near electronegative atoms = downfield (higher ppm). Aromatic protons are 6.5-8.5 ppm; alkyl are 0.8-1.7 ppm; adjacent to C=O are 2.0-2.7 ppm.
2. **Multiplicity (splitting pattern)**: How many neighboring protons does this one have? n neighbors = n+1 peaks. A triplet means 2 adjacent H; a quartet means 3 adjacent H. This tells you about connectivity.
3. **Integration (area)**: How many protons does this signal represent? Ratios matter more than absolute values. A 3:2:1 integration ratio on a C3 compound strongly suggests CH3, CH2, CH.

### 13C NMR: Count the symmetry

- Count the number of distinct carbon signals. Compare to the molecular formula.
- Fewer signals than carbons = the molecule has symmetry (equivalent carbons).
- Carbonyl carbons appear above 160 ppm. Aromatic/alkene carbons: 100-160 ppm. sp3 carbons: 0-90 ppm.

### The combination strategy

No single spectrum gives the answer. Combine them:
1. Molecular formula gives DoU (structural constraints)
2. IR identifies functional group classes (C=O? O-H? N-H?)
3. 13C tells you how many unique carbon environments exist
4. 1H tells you connectivity (through splitting) and hydrogen count (through integration)
5. Propose a structure that is consistent with ALL data
6. Verify: does your proposed structure predict every observed signal?

---

## 3. Stereochemistry — How to Think in 3D

### Finding stereocenters

A stereocenter is a carbon with four DIFFERENT substituents. To find them:
- Look at each sp3 carbon in the molecule
- Check: are all four groups attached to it different? (Trace each path outward — if two paths become identical at any point, those groups are the same)
- Ring carbons count too — the two "ring paths" going in opposite directions around the ring are different substituents if they differ at any point

### Assigning R/S

1. Rank the four substituents by CIP priority (higher atomic number = higher priority)
2. For ties: move to the next atom along the chain and compare again
3. Orient the molecule so the lowest-priority group (#4) points AWAY from you
4. Read priorities 1-2-3: clockwise = R, counterclockwise = S
5. Shortcut: if #4 is already pointing away in a drawing, just read the arrangement directly. If #4 points toward you, read the arrangement and FLIP the answer.

### Predicting stereochemical outcomes of reactions

Ask: what is the mechanism?
- **SN2**: inversion at the stereocenter (backside attack). Always.
- **SN1**: racemization (planar carbocation intermediate attacked from both faces). Expect ~50:50 or slight preference.
- **E2**: requires anti-periplanar geometry (H and leaving group 180 degrees apart). This constrains which alkene geometry forms.
- **Addition to alkenes**: syn addition (hydroboration, catalytic hydrogenation) vs anti addition (bromine, epoxidation then opening)
- **Addition to carbonyls with alpha-stereocenter**: Felkin-Anh model — nucleophile attacks anti to the largest substituent on the alpha carbon

### Relationship between stereoisomers

- **Enantiomers**: non-superimposable mirror images. Same physical properties except optical rotation.
- **Diastereomers**: stereoisomers that are NOT mirror images. Different physical properties — can be separated.
- **Meso compounds**: have stereocenters but an internal mirror plane makes them achiral overall.

---

## 4. Bundled Scripts

These ready-to-run scripts live in `skills/tooluniverse-organic-chemistry/scripts/`.
Use them via the Bash tool instead of computing by hand — they validate inputs and print verification lines.

### `chemistry_facts.py` — Chemical and physical facts reference

A lookup tool for facts that are easy to mis-remember. **Query this script instead of guessing.**
Three categories: `allotropes`, `point_group`, `common_reagents`. Run with no extra args to list all entries in a category.

```
python chemistry_facts.py --type allotropes --element P
python chemistry_facts.py --type point_group --molecule "benzene"
python chemistry_facts.py --type common_reagents --reagent "LiAlH4"
python chemistry_facts.py --type allotropes          # list all elements
```

**Coverage:** Allotropes for P, C, S, O. Point groups for 15 molecules (water C2v through H2 D∞h). 24 reagents (LiAlH4 through DMDO) with full name, function, selectivity, stereochemistry, and KEY DISTINCTION notes.

**When to use:** Any question about allotropes, molecular symmetry/point groups, or reagent selectivity. Always query before reporting reagent facts.

### `crystal_validator.py` — Crystal structure density validator

Preferred: use `CrystalStructure_validate` tool (via MCP/SDK) with unit cell parameters (`a`, `b`, `c`, `alpha`, `beta`, `gamma`, `Z`, `MW`, `density`). Fallback: run `crystal_validator.py` directly.

Validates crystal structure data by computing theoretical density from unit cell parameters and
comparing against a reported value. Flags inconsistencies that indicate errors in published datasets.

Supports all seven crystal systems (cubic, tetragonal, orthorhombic, hexagonal, trigonal, monoclinic, triclinic).

```
python crystal_validator.py --a 5.43 --b 5.43 --c 5.43 --Z 8 --MW 28.085 --density 2.329
python crystal_validator.py --datasets datasets.json   # batch mode: JSON array of datasets
```

Angles default to 90deg. Output: crystal system, volume, calculated density, %error, verdict (OK/WARNING/MISMATCH).
Batch mode compares multiple datasets to find the outlier. Density formula: d = (Z * MW) / (V * Na).

**When to use:** Crystal structure verification, density consistency checks, finding erroneous datasets.

### `stereochem_tracker.py` — Stereochemistry through reaction sequences

Tracks R/S configuration at a stereocenter through a series of reactions, predicting the
stereochemical outcome at each step.

```
python stereochem_tracker.py --start R --reactions "SN2, oxidation, SN1"
```

**Supported reactions:** SN2 (inversion), SN1 (racemization), E2/E1 (elimination), reduction/oxidation/hydrogenation/hydroboration/epoxidation (retention), mitsunobu (inversion), double_inversion (retention), racemization/epimerization/enolization (racemization).

**When to use:** Multi-step synthesis chirality tracking, verifying net retention/inversion.

### `smiles_verifier.py` — SMILES molecular property verifier (no RDKit)

Preferred: use `SMILES_verify` tool (via MCP/SDK) with `smiles` and optional constraint parameters (`mw`, `heavy_atoms`, `valence_electrons`, `total_atoms`, `formal_charge`). Fallback: run `smiles_verifier.py` directly.

Parses a SMILES string without external dependencies and computes molecular weight, heavy atom
count, valence electron count, total atom count, and formal charge. Then optionally checks these
against user-supplied constraints. **Use this every time you design or propose a SMILES answer.**

```
python smiles_verifier.py --smiles "CC(C)(C(=N)N)N=NC(C)(C)C(=N)N" --mw 198.15 --heavy_atoms 14 --valence_electrons 80
```

**Constraint flags:** `--mw` (tolerance 0.5), `--heavy_atoms`, `--valence_electrons`, `--total_atoms`, `--formal_charge`

**When to use:** Always verify SMILES answers before reporting. Catches MW, atom count, and electron count errors.

### `degrees_of_unsaturation.py` — Degrees of unsaturation (DoU) calculator

Preferred: use `DegreesOfUnsaturation_calculate` tool (via MCP/SDK) with `formula` or individual atom count parameters. Fallback: run `degrees_of_unsaturation.py` directly.

Computes DoU = (2C + 2 + N − H − X) / 2 from a formula string or individual atom counts.
Handles all halogens (F, Cl, Br, I) and notes that O and S do not affect DoU.
Prints the full arithmetic, a structural interpretation, and a round-trip verification.

```
python degrees_of_unsaturation.py --formula C6H6
python degrees_of_unsaturation.py --C 10 --H 14 --O 2 --N 1
```

Output: atom counts, step-by-step formula, result, structural interpretation, non-integer DoU warning.

### `molecular_formula.py` — Combustion analysis and formula analysis

Preferred: use `MolecularFormula_analyze` tool (via MCP/SDK) with combustion or formula parameters. Fallback: run `molecular_formula.py` directly.

Two modes in one script.

**Mode 1: combustion analysis** — `--sample_g`, `--CO2_g`, `--H2O_g`, optional `--molar_mass`
**Mode 2: formula analysis** — `--formula C6H6` (MW, DoU, elemental composition)

```
python molecular_formula.py --sample_g 0.2 --CO2_g 0.4874 --H2O_g 0.1998 --molar_mass 78
python molecular_formula.py --formula C6H6
```

---

## 5. Computational Procedures

**ALWAYS EXECUTE as Python scripts** using the Bash tool — do not compute mentally. Prefer the bundled scripts (`molecular_formula.py`, `degrees_of_unsaturation.py`) over writing code from scratch.

**Key formulas** (write and run Python when bundled scripts don't cover the case):
- **Combustion analysis**: moles_C = CO2_g / 44.01; moles_H = H2O_g / 18.015 * 2; moles_O by mass difference. Ratio → GCD → empirical formula. Factor = MM / empirical_MM.
- **DoU**: (2C + 2 + N - H - X) / 2. O and S do not affect the count.
- **Limiting reagent**: equiv = mass / (MW * stoich_coeff) for each reagent; minimum equiv is limiting; yield = min_equiv * product_stoich * product_MW.

---

## 6. When to Reason vs When to Look Things Up

### REASON through these (do not look up):
- Reaction products and mechanisms
- Spectroscopy interpretation (combine the data you have)
- Stereochemical outcomes
- Degrees of unsaturation
- Whether a reaction is thermodynamically favorable

### COMPUTE with bundled scripts for these:
- Crystal structure density verification: Preferred: `CrystalStructure_validate` tool. Fallback: `crystal_validator.py` (never compute unit cell volumes by hand)
- Stereochemistry tracking through multi-step synthesis: `stereochem_tracker.py` (tracks R/S through SN2, SN1, etc.)
- Degrees of unsaturation: Preferred: `DegreesOfUnsaturation_calculate` tool. Fallback: `degrees_of_unsaturation.py`
- Combustion analysis and formula analysis: Preferred: `MolecularFormula_analyze` tool. Fallback: `molecular_formula.py`
- SMILES verification (MW, heavy atoms, valence electrons): Preferred: `SMILES_verify` tool. Fallback: `smiles_verifier.py` (always verify SMILES answers)

### LOOK UP with tools for these:
- Allotropes of an element (count, names, properties): `chemistry_facts.py --type allotropes --element X`
- Molecular point group and symmetry elements: `chemistry_facts.py --type point_group --molecule "name"`
- Reagent function, selectivity, or key distinction: `chemistry_facts.py --type common_reagents --reagent "name"`
- Specific physical constants (boiling points, pKa values, solubility): `PubChem_get_CID_by_compound_name` then `PubChem_get_compound_properties_by_CID`
- Whether a compound exists and its canonical SMILES/InChI: `PubChem_get_CID_by_compound_name` or `PubChem_get_compound_properties_by_CID`
- Drug-likeness, bioactivity data, assay results: `ChEMBL_get_molecule` or `ChEMBL_search_molecules`
- Metabolite pathways and biological context: `HMDB_get_metabolite`

### Crystal structure verification strategy:
Extract unit cell params, Z, MW, density for each dataset. Run `crystal_validator.py --datasets datasets.json` in batch. Largest %error = the error. Common errors: wrong Z, swapped params, angle transcription errors.

### Molecular Design from Constraints (SMILES design):
1. Start from constraints (MW, heavy atoms, VE) to estimate formula
2. Build SMILES, then **always verify**: `python smiles_verifier.py --smiles "..." --mw X --heavy_atoms Y --valence_electrons Z`
3. If any constraint FAILs, revise and re-run until all pass

### The verify-after-reasoning pattern:
1. Reason through the problem, arrive at a proposed answer
2. Verify known compounds with PubChem; verify numerical answers with Python computation
3. **For numerical answers**: ALWAYS compute with scripts before answering
