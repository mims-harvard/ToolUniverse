---

name: tooluniverse-inorganic-physical-chemistry
description: "Inorganic chemistry, physical chemistry, and materials science — crystal structures, coordination chemistry, lattice parameters, thermodynamic properties, electronic structure. Use for unit cell volume calculations, coordination geometry, materials property estimation, and inorganic-mechanism reasoning. Complementary to tooluniverse-organic-chemistry."
---

# Inorganic & Physical Chemistry

## Reasoning Strategy

### 1. Crystal Structure Questions
**When given crystal structure data**, always COMPUTE don't guess:
1. **Calculate unit cell volume** for the crystal system:
   - Cubic: V = a^3
   - Tetragonal: V = a^2 * c
   - Orthorhombic: V = a * b * c
   - Monoclinic: V = a * b * c * sin(beta)
   - Triclinic: V = a*b*c * sqrt(1 - cos^2(alpha) - cos^2(beta) - cos^2(gamma) + 2*cos(alpha)*cos(beta)*cos(gamma))
   - Hexagonal: V = a^2 * c * sqrt(3)/2

2. **Verify density**: d = (Z * M) / (V * Na * 1e-24) where V in Å³, M in g/mol, Na = 6.022e23
3. **Preferred**: Use `CrystalStructure_validate` tool (via MCP/SDK). **Fallback**: `python3 skills/tooluniverse-organic-chemistry/scripts/crystal_validator.py --a X --b Y --c Z --alpha A --beta B --gamma G --Z N --MW M --density D`
4. **For batch comparison** (find the wrong dataset): Save datasets as JSON array and use `--datasets path/to/datasets.json`
5. **When you need REAL experimental crystal data** (not user-supplied numbers to validate), use the Crystallography Open Database (COD) tools — see below. `CrystalStructure_validate` checks internal consistency of numbers you already have; COD looks up actual deposited structures.

#### Looking up real crystal structures (COD)

`COD_search_structures` and `COD_get_structure` query the Crystallography Open Database (500,000+ experimentally determined structures — inorganic, organic, mineral, and metal-organic). Use when a compound/mineral name, chemical formula, elements, or space group is named and you need real unit-cell parameters, space group, and publication details rather than computing from given numbers.

```
COD_search_structures({"el1":"Cu","el2":"O","nel":"2","sgNumber":"225","results":5})   # binary Cu-O compounds, FCC space group
COD_search_structures({"mineral":"calcite","results":5})
COD_search_structures({"text":"aspirin","results":5})   # free-text also matches organic/pharmaceutical crystals, not just inorganic
COD_get_structure({"id":"1011240"})   # full detail (a,b,c,alpha,beta,gamma,vol,Z,sg,sgNumber,doi,...) for one COD entry
```

Verified live: `COD_search_structures({"el1":"Si","el2":"O","nel":"2","results":10})` returns real SiO2 polymorph entries (e.g. COD ID `1000007`, a=9.7397, b=8.9174, c=5.2503 Å); `COD_get_structure({"id":"1515581"})` returns real aspirin crystal data (P 1 21/c 1, sgNumber 14, cell volume 825.44 Å³, temperature 123 K). Workflow: search first (by formula/elements/mineral/text) to find candidate COD IDs, then `COD_get_structure` on a specific ID for the full record including DOI/journal/authors. `query`/`text` and `spacegroup`/`sg` and `max_results`/`results` are alias pairs — use either name.

**Gotcha**: some search combinations legitimately return zero results (verified live) — an empty `data: []` with `count: 0` means no matching structures in COD, not a broken query; try relaxing filters (drop `sgNumber`, widen `nel`) before concluding the compound isn't in COD.

### 2. Bonding & Covalency Questions
**Key reasoning patterns**:
- **Covalency** = orbital mixing between metal and ligand. Greater overlap = more covalent.
- **Lanthanide/actinide**: 4f orbitals of Ce(IV) typically show ENHANCED covalent mixing vs Ce(III) — more contracted 4f in higher oxidation states increases overlap with ligand orbitals
- **But**: Enhanced covalency does NOT always mean stronger bonds — it depends on the specific orbital interactions
- **d-block vs f-block**: d-orbitals have more radial extension → stronger covalent bonds than f-orbitals
- **Nephelauxetic effect**: Reduced electron-electron repulsion in complexes → indicates covalency. Larger effect = more covalent.

### 3. Noble Gas Chemistry
- **Xe compounds**: XeF2 (linear), XeF4 (square planar), XeF6 (distorted octahedral)
- **XeF4 synthesis**: Requires Xe + F2 at elevated temperature (400°C) and pressure. Can also form at lower temperatures with specific methods (UV photolysis, electric discharge)
- **Key**: Temperature thresholds matter for synthesis efficiency. LOOK UP DON'T GUESS — search literature for specific synthesis conditions.

### 4. Symmetry & Point Groups
1. Identify the molecular shape
2. Find symmetry elements: C_n axes, mirror planes (σ_h, σ_v, σ_d), inversion center (i), improper rotation (S_n)
3. Use `python3 skills/tooluniverse-organic-chemistry/scripts/chemistry_facts.py point_groups` for point group lookup
4. **Optical activity**: Requires absence of improper rotation axes (S_n, including σ = S_1 and i = S_2). Chiral point groups: C_1, C_n, D_n, T, O, I
5. **Crystal classes with optical activity**: Piezoelectric non-centrosymmetric classes that lack mirror planes and inversion

### 5. Thermodynamics & Kinetics
**COMPUTE DON'T ESTIMATE** — write Python code for:
- Gibbs free energy: ΔG = ΔH - TΔS
- Equilibrium constant: K = exp(-ΔG/RT)
- Arrhenius equation: k = A * exp(-Ea/RT)
- Nernst equation: E = E° - (RT/nF) * ln(Q)
- Clausius-Clapeyron: ln(P2/P1) = -ΔH_vap/R * (1/T2 - 1/T1)

### 6. Solubility & Equilibrium Calculations

**Preferred**: Use `EquilibriumSolver_calculate` tool (via MCP/SDK) with `type`, `ksp`, `stoich`, and other parameters. Fallback: run `equilibrium_solver.py` directly.

```bash
# Simple Ksp: MaXb(s) <-> aM + bX
python3 skills/tooluniverse-inorganic-physical-chemistry/scripts/equilibrium_solver.py \
  --type ksp_simple --ksp 5.3e-27 --stoich 1:3

# Ksp + complex formation (e.g., Al(OH)3 in water with Al(OH)4- complex)
python3 skills/tooluniverse-inorganic-physical-chemistry/scripts/equilibrium_solver.py \
  --type ksp_kf --ksp 5.3e-27 --kf 1.1e33 --stoich 1:3

# Common ion effect (e.g., AgCl in 0.1M NaCl)
python3 skills/tooluniverse-inorganic-physical-chemistry/scripts/equilibrium_solver.py \
  --type common_ion --ksp 1.77e-10 --stoich 1:1 --common-ion 0.1
```

**Key points**:
- `ksp_kf` mode solves the full charge-balance system numerically (Newton's method) — accounts for free cation, complex anion, and OH-/H+ simultaneously
- For `MX_b + X- <-> MX_(b+1)-`, K_overall = Ksp * Kf
- `common_ion` mode uses bisection to solve the exact Ksp expression with extra ion concentration
- Always specify `--stoich a:b` matching the salt formula (e.g., 1:3 for Al(OH)3, 1:2 for CaF2, 1:1 for AgCl)

### 7. Spectroscopy Interpretation
- **UV-Vis**: d-d transitions (weak, Laporte forbidden), LMCT/MLCT (strong), π→π* (organic)
- **IR**: Functional group region (4000-1500 cm⁻¹), fingerprint (1500-400 cm⁻¹)
- **NMR**: Chemical shift indicates electronic environment. For counting peaks, identify symmetry-equivalent protons.
- **For peak counting**: Draw the structure, identify all symmetry operations, group equivalent H atoms. Use `python3 skills/tooluniverse-organic-chemistry/scripts/chemistry_facts.py` for reference data.

## Available Tools

| Tool | Use For |
|------|---------|
| `PubChem_get_CID_by_compound_name` | Get compound CID from name |
| `PubChem_get_compound_properties_by_CID` | Detailed compound data by CID |
| `ChEMBL_search_molecules` | Bioactive compounds |
| `PubMed_search_articles` | Literature on synthesis conditions, properties |
| `CrystalStructure_validate` tool (or `crystal_validator.py` fallback) | Verify crystal structure data consistency |
| `EquilibriumSolver_calculate` tool (or `equilibrium_solver.py` fallback) | Ksp, complex formation, common-ion solubility |
| `COD_search_structures` / `COD_get_structure` | Look up real deposited crystal structures (unit cell, space group, DOI) from the Crystallography Open Database |

## LOOK UP DON'T GUESS

- Noble gas compound synthesis conditions vary by method — search literature before answering
- Crystal structure parameters must be computed, not estimated
- Bonding descriptions (covalent vs ionic) require specific orbital considerations — don't generalize from one system to another
