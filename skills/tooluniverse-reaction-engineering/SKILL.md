---
name: tooluniverse-reaction-engineering
description: Chemical reaction engineering for reactor sizing and design — rate laws (zero/first/second order), CSTR/PFR/batch reactor sizing, conversion, residence time, space time, and Arrhenius activation energy. Use for chemical process calculations involving ideal reactors and elementary kinetics. Complements tooluniverse-organic-chemistry (molecular-scale reaction prediction) by handling reactor-scale design.
disable-model-invocation: true
---

# Chemical Reaction Engineering

## Overview

This skill guides chemical reaction engineering calculations for ideal reactors (CSTR, PFR, batch). It covers rate law determination, reactor sizing for a target conversion, residence time / space time calculations, and temperature dependence via the Arrhenius equation. It is intended for process-scale reactor design, not molecular-scale reaction mechanism or product prediction (use tooluniverse-organic-chemistry for that).

## When to Use This Skill

**Triggers** (examples of what a user might ask):

- "Size a CSTR for 90% conversion of a first-order reaction."
- "What residence time does a PFR need for second-order kinetics?"
- "Calculate the rate constant at 350°C given activation energy and a reference rate constant."
- "Compare CSTR vs PFR volume for the same conversion."
- "Design a batch reactor for a given reaction time and conversion."

**Use Cases:**

1. Reactor sizing (CSTR, PFR, batch) for a target conversion
2. Rate law parameter estimation from concentration-time data
3. Temperature effect on reaction rate (Arrhenius)
4. Comparing reactor types for the same duty
5. Residence time and space time calculations for flow reactors

## Core Databases and References

| Reference | Coverage | Use |
|-----------|----------|-----|
| RXNChemistry (`RXNChemistry_predict_reaction`) | Forward reaction prediction (ML, IBM RXN) | Predict product SMILES from reactants to identify reacting species |
| PubChem (`PubChem_get_compound_properties_by_CID`, `PubChem_get_CID_by_compound_name`) | Compound properties, identifiers | Resolve reactant/product names to CIDs and properties |
| ChEMBL (`ChEMBL_get_molecule`, `ChEMBL_search_molecules`) | Molecule records, activities | Cross-validate compound identity |
| NIST WebBook (conceptual reference) | Thermochemical data | Heat of reaction, heat capacities (reference only; not queried by this skill) |

## Workflow Overview

```
Input (reaction, kinetics, target conversion or volume)
    → Phase 1: Identify reactants/products and rate law
    → Phase 2: Select reactor type and calculate size / time
    → Phase 3: Temperature correction (Arrhenius) if needed
    → Report: reactor volume, residence time, rate constant, conversion
```

## Phase 1: Identify Reactants/Products and Rate Law

**When:** User provides a reaction and kinetic data or asks for rate-law-based sizing.

**Objective:** Determine reaction order, rate constant, and reacting species.

**Tools Used:**

| Tool | Input | Output | Use |
|------|-------|--------|-----|
| RXNChemistry_predict_reaction | reactant SMILES, reagent SMILES | predicted product SMILES, confidence | Identify product species for the reaction |
| PubChem_get_CID_by_compound_name | compound name | CID, properties | Resolve names to identifiers |
| PubChem_get_compound_properties_by_CID | CID | molecular weight, formula, etc. | Get species properties for mass balances |

**Workflow:**

1. If reaction is given by name/SMILES, use `RXNChemistry_predict_reaction` to confirm product(s).
2. Resolve each species to a PubChem CID for identity confirmation.
3. Determine rate law from user-provided data (zero/first/second order) or state assumptions clearly.
4. Record rate constant `k` at reference temperature `T_ref`.

**Decision Logic:**

| Condition | Action |
|-----------|--------|
| No kinetic data provided | State assumption (e.g., first-order) and flag as assumption |
| Reaction unrecognized | Ask user to clarify reactants/products; cannot proceed |
| Multiple possible products | List candidates; ask user to specify |

## Phase 2: Reactor Sizing

**When:** Rate law and target conversion (or target volume/time) are known.

**Objective:** Calculate reactor volume (CSTR/PFR) or reaction time (batch) for the duty.

**Tools Used:** None required from ToolUniverse registry (hand calculation / Python script). Reference formulas below.

**Key Formulas:**

| Reactor | Design Equation | Variables |
|---------|----------------|-----------|
| CSTR | `V = F_A0 * X / (-r_A)` | V = volume, F_A0 = molar feed rate, X = conversion, -r_A = rate of disappearance |
| PFR | `V = F_A0 * ∫(0→X) dX / (-r_A)` | integral form; for first-order: `V = (F_A0 / k) * ln(1 / (1 - X))` |
| Batch | `t = ∫(0→X) dX / (-r_A)` | t = reaction time; for first-order: `t = (1 / k) * ln(1 / (1 - X))` |
| Space time (CSTR/PFR) | `τ = V / v_0` | v_0 = volumetric feed rate |
| Residence time (PFR) | `θ = V / v_0` | same as space time for constant density |

**Workflow:**

1. Write the rate law: `-r_A = k * C_A^n` (n = reaction order).
2. Substitute concentration in terms of conversion (for liquid-phase constant density: `C_A = C_A0 * (1 - X)`).
3. Solve the design equation for V (flow) or t (batch).
4. Calculate space time / residence time.
5. Compare CSTR vs PFR volume if both are candidates.

**Decision Logic:**

| Condition | Action |
|-----------|--------|
| Gas-phase with volume change | Use expansion factor ε; cannot assume constant density |
| Non-elementary / unknown order | Flag; user must provide rate law form |
| Target volume given instead of conversion | Solve for achievable conversion X |

## Phase 3: Temperature Correction (Arrhenius)

**When:** Rate constant is known at one temperature and rate at another temperature is needed.

**Objective:** Adjust `k` for temperature using the Arrhenius equation.

**Formula:**

```
k2 = k1 * exp[ (Ea/R) * (1/T1 - 1/T2) ]
```

where Ea = activation energy, R = gas constant (8.314 J/mol·K), T in Kelvin.

**Workflow:**

1. Confirm Ea and k1 at T1 are provided (or state typical range if assumed).
2. Convert all temperatures to Kelvin.
3. Calculate k2 at T2.
4. Re-run Phase 2 reactor sizing with k2 if temperature changes the duty.

## Output Structure

Every reaction-engineering report must include:

1. **Reaction Statement** — balanced reaction, phases, species
2. **Kinetics** — rate law, order, rate constant (with temperature), activation energy if used
3. **Reactor Selection** — CSTR / PFR / batch chosen and rationale
4. **Design Calculations** — conversion, volume/time, residence/space time, with formulas shown
5. **Assumptions** — constant density, ideal reactor, isothermal, etc. (must be explicit)
6. **Temperature Correction** — Arrhenius adjustment if applied (or state not applied)
7. **Comparison** — CSTR vs PFR volume if both evaluated
8. **Limitations** — ideal reactor only; non-ideal, catalytic, or multiphase systems need specialized tools

## Tool Parameter Reference

| Tool | Critical Parameter | Correct Name | Common Mistake |
|------|-------------------|--------------|----------------|
| RXNChemistry_predict_reaction | reactants | `reactants` (SMILES string) | passing names instead of SMILES |
| PubChem_get_CID_by_compound_name | compound name | `name` | passing CID instead of name |
| PubChem_get_compound_properties_by_CID | CID | `cid` | passing name instead of CID |

## Fallback Strategies

| Primary | Fallback | Default |
|---------|----------|---------|
| RXNChemistry product prediction | Manual product specification by user | Cannot proceed; ask user |
| PubChem name→CID | ChEMBL molecule search | Report identity unresolved |
| Kinetic data from user | State first-order assumption; flag clearly | Calculation marked as assumption-based |

## Limitations & Known Issues

- Ideal reactors only (CSTR, PFR, batch). Non-ideal reactors (recycle, bypass, dead zones) not covered.
- Constant density assumed unless user provides expansion factor.
- Isothermal operation assumed; adiabatic/non-isothermal energy balance not included.
- Catalytic reactions (surface kinetics, deactivation) not covered.
- RXNChemistry requires `RXN4CHEMISTRY_API_KEY`; without it, product prediction is unavailable.
- This skill provides design guidance and formulas; it does not execute the calculation automatically unless paired with a script.

## Summary

**Capabilities:**

- Rate law determination (zero/first/second order)
- CSTR / PFR / batch reactor sizing for target conversion
- Conversion, residence time, space time calculations
- Arrhenius temperature correction
- CSTR vs PFR volume comparison

**Outputs:** Structured reaction-engineering report (8 required sections above).

**Best for:** Undergraduate-level chemical reaction engineering design calculations and quick reactor sizing checks. Not for detailed equipment design, non-ideal reactors, or safety-critical processes without engineer review.
