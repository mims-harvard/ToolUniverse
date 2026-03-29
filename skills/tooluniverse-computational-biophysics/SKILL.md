---
name: tooluniverse-computational-biophysics
description: Solve quantitative problems in biophysics, pharmacokinetics, epidemiology, toxicology, population genetics, and statistical mechanics. Provides reasoning strategies and Python templates for calculations alongside ToolUniverse data lookups. Use when users ask about drug dosing, half-life decay, radioactive tracers, R0, herd immunity, diffusion, Hardy-Weinberg, binding equilibria, or any computation-heavy biology/chemistry question.
---

# Computational Biophysics & Quantitative Biology Skill

## 1. Recognize the Physical Process

The single most important step: identify what physical process the problem describes. In quantitative biology, almost every problem maps to one of these:

- **Drug enters body → distributes → is eliminated**: pharmacokinetics. Key quantities: dose, bioavailability, volume of distribution, clearance, half-life. The body is a compartment model.
- **Radioactive tracer decays over time**: nuclear medicine. Same math as drug elimination (exponential decay) but the rate constant is a physical property of the isotope, not a patient variable.
- **Pathogen spreads through population**: epidemiology. R₀ determines whether an epidemic grows or dies. Herd immunity threshold = 1 - 1/R₀. Every epidemic model starts here.
- **Ligand binds receptor**: binding equilibrium. At low [ligand], binding is linear. At saturation, all sites occupied. Kd = concentration at half-maximal binding. This same curve describes enzyme kinetics, drug-receptor occupancy, and surface adsorption.
- **Contaminant enters environment**: dilution + persistence. Two questions: what is the concentration after mixing (conservation of mass), and how long does it persist (exponential decay with environmental half-life)?
- **Two populations differ genetically**: population genetics. Fst measures differentiation. HWE tests if mating is random. Gene flow opposes drift.
- **Neurons communicate in a network**: computational neuroscience. Integrate-and-fire models, synaptic dynamics, balanced excitation/inhibition. Mean firing rate depends on input current relative to threshold.

Once you name the process, the mathematical structure follows. Solve algebraically first, substitute numbers second, and always check that units cancel correctly and the magnitude is physically reasonable.

## 2. Reasoning Patterns by Problem Type

These are not formulas. They are ways of thinking about what is happening physically.

### Conservation / Dilution Problems
Something is being spread into a larger volume, or two streams are mixing. The total amount of substance is conserved. Think: **amount_before = amount_after**, where amount = concentration x volume. This covers serial dilutions, mixing streams, stock solution preparation, and environmental discharge into rivers.

### Exponential Decay / Growth Problems
Something is disappearing (or growing) at a rate proportional to how much is currently there. The signature: "half-life" or "doubling time" appears in the problem. This single pattern covers drug clearance, radioactive decay, environmental persistence, bacterial growth, and epidemic doubling. The only things that change between applications are the rate constant and what is decaying.

### Saturation / Binding Problems
Something binds to a limited number of sites. At low concentrations, binding is proportional to concentration. At high concentrations, sites fill up and adding more has diminishing effect. This covers receptor-ligand binding, enzyme kinetics, surface adsorption, and oxygen-hemoglobin curves. The shape is always hyperbolic: response = max_response x [thing] / ([thing] + half_max_constant).

### Threshold / Crossover Problems
"At what point does X equal Y?" or "When does the concentration drop below the therapeutic level?" Set two expressions equal and solve. Examples: time to reach a target drug level, when an environmental concentration exceeds a safety limit, herd immunity threshold (where effective R drops to 1).

### Ratio / Rate Problems
Output = input x time, or output = concentration x flow rate. Clearance, flux, dosing rate, and drip rate calculations are all just dimensional analysis: arrange the given quantities so the units work out.

### Population Comparison Problems
Two groups are being compared. You need a measure of difference (Fst, odds ratio, relative risk) and a measure of whether the difference is real (p-value, confidence interval). Think: what is the effect size, and is it distinguishable from noise?

## 3. When to Compute vs. Estimate vs. Look Up

**Compute carefully** when:
- The answer affects a patient (drug dosing, diagnostic interpretation)
- The problem gives you exact numbers and asks for an exact answer
- You need to fit a curve to data (use scipy)

**Estimate and state uncertainty** when:
- The answer needs an order of magnitude (environmental risk, population-level)
- Input values are themselves uncertain (R0 estimates, BCF from log Kow regressions)
- Say: "This is approximately X, with the main uncertainty coming from Y"

**Look up via ToolUniverse** when:
- You need a physical constant: half-life, molecular weight, Kd, log Kow, allele frequency
- The user names a specific drug, compound, gene, or variant
- You want to validate your calculation against a known case

| Data needed | Tool to use |
|-------------|-------------|
| Molecular weight, log Kow, SMILES | `PubChem_get_CID_by_compound_name`, `PubChem_get_compound_properties_by_CID` |
| Drug PK properties, mechanism | `ChEMBL_get_molecule` |
| Binding affinity (Kd, Ki, IC50) | `BindingDB_search_by_target` |
| Allele frequencies | `gnomad_get_variant`, `MyVariant_query_variants` |
| Literature values (R0, BCF, etc.) | `EuropePMC_search_articles` |

**Just compute** when:
- The problem gives you all the numbers
- No specific real-world compound/gene is named

## 4. Python Computation Templates

**CRITICAL: When a problem gives you numbers and asks for a numerical answer, WRITE AND RUN Python code using the Bash tool.** Do not try to compute in your head — write a script, execute it, and report the result. Mental arithmetic on multi-step problems introduces errors. The templates below are starting points — adapt them to the specific problem, then EXECUTE.

**Answer Format Rules**: Match the precision and format the question expects. If data uses 2 decimal places, round to 2. For large numbers (>10^6), use scientific notation; if the question says "in units of 10^28", give just the coefficient. For small numbers, match the question's format (e.g., "1.776 × 10^-3" not "1.8e-3"). Give ONLY the number — no units or descriptions unless explicitly asked.

```
# Pattern for every computation problem:
# 1. Extract ALL given values from the problem — write them down with units
# 2. Identify EXACTLY what quantity the question asks for
# 3. Write a Python script connecting givens to the unknown
# 4. Run it with: python3 -c "..."
# 5. VERIFY: substitute your answer back into the original problem — does it make sense?
#    e.g., if computing a drip rate, check: rate × time = total volume?
#    e.g., if computing vaccine coverage, check: coverage × efficacy × population > herd immunity?
```

### Template 1: Exponential Decay / Growth

Covers: drug clearance, radioactive decay, environmental persistence, bacterial growth, epidemic doubling.

```python
import numpy as np

def exponential_process(initial, half_life, time):
    """Amount remaining after exponential decay. For growth, use negative half_life."""
    return initial * (0.5 ** (time / half_life))

def time_to_reach(initial, target, half_life):
    """Time for exponential process to reach a target value."""
    return half_life * np.log2(initial / target)

# Examples — same math, different domains:
# Drug: 500 mg dose, t½ = 6 h, after 24 h → 31.25 mg
# Radioactive: 20 mCi Tc-99m, t½ = 6 h, after 12 h → 5 mCi
# Environmental: 100 ppm pesticide, t½ = 30 days, after 90 days → 12.5 ppm
```

### Template 2: Conservation / Dilution / Mixing

Covers: C1V1=C2V2, stream mixing, serial dilutions. Core logic: `C1*V1 = C2*V2` (pass 3 knowns, solve for 4th). For mixing n streams: `final_conc = sum(Ci*Qi) / sum(Qi)`.

### Template 3: Threshold / Equilibrium Solver

Covers: when drug drops below therapeutic level, herd immunity threshold. Use `scipy.optimize.brentq(lambda x: func(x) - target, lo, hi)` to find the crossover point.

### Template 4: Saturation / Binding Curve

Covers: receptor binding, enzyme kinetics, adsorption, dose-response. Shape: `response = Rmax * C / (C + Kd)`. Fit with `scipy.optimize.curve_fit` using `p0=[median(C), max(response)]`.

### Template 5: Statistical Comparison

Covers: HWE chi-square, contingency tables, group comparisons. Use `scipy.stats.chisquare(observed, expected)` for goodness-of-fit, `stats.ttest_ind/ttest_rel` for group comparisons.

### Template 6: Rate / Dimensional Analysis

Covers: IV drip rate, clearance, flux, dosing rate. Core: `rate = amount / time`, `mass_rate = concentration * flow_rate`. Arrange units to cancel correctly.

### Template 7: Compartmental Models & R0

Covers: SIR/SEIR, R0 derivation. `R0 = beta * N / gamma` (basic SIR). General: `R0 = transmission_rate * infectious_duration * susceptible_contacts`. Derive by tracing one infected individual through all compartments.

## 5. Multiple-Choice Strategy

Multiple-choice questions in biophysics, pharmacology, and clinical medicine are frequently answered incorrectly not because of missing knowledge but because of process errors: skipping an option, confusing a letter with the text, or committing to the first plausible-sounding choice. Use the systematic approach below every time.

### The Mandatory MC Process

1. **Read the stem twice.** Identify the exact action being asked: "MOST likely", "FIRST step", "BEST describes", "EXCEPT". These qualifiers change the answer.
2. **Force evaluation of every choice.** For each option ask:
   - *Why would this be correct?* — does it align with the core concept?
   - *Why would this be wrong?* — does the reasoning contradict it, or is it only partially true?
3. **Eliminate with explicit justification.** Mark a choice eliminated only when you can state a factual reason (not just a feeling).
4. **Count survivors.** One survivor → that is your answer. Two or more → go back to the stem and look for the qualifier that distinguishes them.
5. **Verify letter-to-text alignment.** Before writing your answer, confirm the letter you intend to write corresponds to the option text you reasoned about. This catches the common error of reasoning "B is correct" but writing "C".
6. **Quantitative MC**: Calculate the exact answer FIRST using Python, THEN match to the closest option. Do not let the listed choices bias your computation — compute independently.
7. **MC traps**: "All/None of the above" is correct only ~25% of the time. Absolute language ("always", "never", "only") is usually wrong. The longest/most detailed option is correct more often. When two options are opposites, one is usually correct.

**CRITICAL FOR BATCH PROCESSING**: When answering multiple MC questions in sequence, do NOT rush. Apply the FULL elimination process to EVERY question. Common batch error: answering based on first impression without elimination. For each MC question, you MUST:
- Write out at least 2 eliminated options with reasons BEFORE selecting your answer
- If you cannot eliminate any options, that's a sign you need to LOOK UP information

### `mc_analyzer.py` — Automated MC Scaffold

Located in `skills/tooluniverse-computational-biophysics/scripts/mc_analyzer.py`.

```
# Analysis mode: systematic elimination
python mc_analyzer.py --question "..." --choices "A:opt1,B:opt2,C:opt3,D:opt4" --reasoning "..."

# Verify mode: confirm letter-text alignment
python mc_analyzer.py --verify --answer "B" --question "..." --choices "A:opt1,B:opt2,C:opt3,D:opt4"
```

Analysis mode scans reasoning for elimination signals, reports survivor count. Verify mode checks letter-text alignment. Use for any scored MC question.

---

## 6. Bundled Scripts

These ready-to-run scripts live in `skills/tooluniverse-computational-biophysics/scripts/`.
Use them via the Bash tool instead of computing by hand — they include verification steps and handle edge cases.

### `epidemiology.py` — Epidemiology calculations (5 types via `--type`)

**Preferred**: Use ToolUniverse tools (via MCP/SDK) instead of the script:
- `Epidemiology_r0_herd` tool -- R0 and herd immunity threshold
- `Epidemiology_vaccine_coverage` tool -- Vaccine coverage from field data
- `Epidemiology_nnt` tool -- Number needed to treat
- `Epidemiology_diagnostic` tool -- Diagnostic test performance (2x2 table)
- `Epidemiology_bayesian` tool -- Bayesian pre/post-test probability

**Fallback**: Pure stdlib script. Types: `r0_herd`, `vaccine_coverage`, `nnt`, `diagnostic`, `bayesian`.

```
python epidemiology.py --type r0_herd --R0 3.5 --VE 0.90
python epidemiology.py --type nnt --control_rate 0.30 --treatment_rate 0.20
python epidemiology.py --type diagnostic --tp 90 --fp 10 --tn 880 --fn 20
python epidemiology.py --type bayesian --prevalence 0.01 --sensitivity 0.95 --specificity 0.90
```

Key formulas: `r0_herd`: Hc=1-1/R0, Vc=Hc/VE. `vaccine_coverage`: derives VE from PCV/PPV field data. `nnt`: ARR=control-treatment, NNT=1/ARR. `diagnostic`: full 2x2 table. `bayesian`: pre-test odds → LR → post-test probability.

### `herd_immunity.py` — Legacy vaccination threshold

```
python herd_immunity.py --R0 4.2 --VE 0.94
```
Formula: `Vc = (1 - 1/R0) / VE`. Prefer `epidemiology.py --type r0_herd` for new work.

### `radioactive_decay.py` — Activity remaining / time to target / parent-daughter

Three modes: forward (`--A0 --half_life --time`), reverse (`--A0 --half_life --target`), parent-daughter (`--parent_daughter` with Bateman equation).

```
python radioactive_decay.py --A0 8 --half_life 67.3 --time 72          # forward
python radioactive_decay.py --A0 8 --half_life 67.3 --target 5         # reverse
python radioactive_decay.py --parent_daughter --half_life_parent 306.05 --half_life_daughter 40.27 --A1 1.4 --A2 2.1 --delta_t 336 --counted daughter
```

Formulas: `A(t) = A0 * 0.5^(t/t_half)`. Parent-daughter: Bateman equation. `--counted`: daughter/both/parent.

### `env_risk_assessment.py` — Environmental risk (hazard quotient)

Computes HQ for soil contaminant exposure via food pathway. Food format: `"name:intake_g:bioavailability:PUF:TSCF"`.

```
python env_risk_assessment.py --total_mass_ug 1e9 --area_m2 250000 --depth_m 0.6 \
    --bulk_density 1500 --theta_w 0.35 --foc 0.03 --Koc 28.3 \
    --food "fruit:300:0.5:0.1:5" --body_weight 80 --RfD 0.02
```

Formulas: C_soil → Kd=foc*Koc → C_sw → DI per pathway → HQ = sum(DI)/BW/RfD.

### `fluid_calculations.py` — Clinical fluid and dosing (4 types via `--type`)

Types: `drip_rate`, `bsa_dose`, `maintenance`, `dilution`. Preferred over legacy `iv_drip_rate.py`.

```
python fluid_calculations.py --type drip_rate --volume_ml 50 --time_min 60 --drop_factor 60
python fluid_calculations.py --type bsa_dose --dose_per_m2 25 --bsa 0.8
python fluid_calculations.py --type maintenance --weight_kg 22
python fluid_calculations.py --type dilution --c1 20 --v1 4.7 --v2 50
```

Formulas: drip_rate = (vol/time)*drop_factor. bsa_dose = dose_per_m2*BSA. maintenance = Holliday-Segar. dilution = C1V1=C2V2.

### `enzyme_kinetics.py` — Km/Vmax, Hill, Ki (3 types via `--type`)

Preferred: use `EnzymeKinetics_calculate` tool (via MCP/SDK) with `type` and data parameters. Fallback: run `enzyme_kinetics.py` directly.

Pure stdlib. Types: `km_vmax` (Lineweaver-Burk + nonlinear), `hill` (cooperativity), `ki` (competitive/uncompetitive/noncompetitive).

```
python enzyme_kinetics.py --type km_vmax --substrate "1,2,5,10,20" --velocity "0.5,0.8,1.2,1.5,1.7"
python enzyme_kinetics.py --type ki --substrate "1,2,5,10,20" --velocity_no_inh "0.5,0.8,1.2,1.5,1.7" --velocity_inh "0.3,0.5,0.8,1.0,1.1" --inhibitor_conc 5 --inhibition_type competitive
```

### `burn_fluids.py` — Burn resuscitation + maintenance

Adult: Parkland (`4*kg*%TBSA`). Pediatric (<30kg): Galveston (`5000*BSA*%TBSA + 2000*BSA`).

```
python burn_fluids.py --weight_kg 80 --tbsa_pct 40
python burn_fluids.py --weight_kg 25 --age_years 7 --tbsa_pct 45 --bsa_m2 0.95
```

Output: hourly rates (first 8h / next 16h), total volume, urine output target. 8h clock starts from burn time.

---

## 7. Combinatorics & Counting Problems

For genetics combinatorics (F2 haplotypes, genotype counts, specimen tallies) or any counting/permutation/combination problem: **ALWAYS write and execute Python code**. Never attempt to enumerate or count mentally — even simple-looking problems (e.g., "how many unique chromosomes from 5 SNPs") have subtleties that cause errors without code. Use `itertools.product`, `itertools.combinations`, or direct formulas, then verify the count.

## 8. Common Pitfalls to Flag

- **Unit mismatch**: mg vs g, mL vs L, hours vs seconds. Always write units next to every number and verify cancellation before computing.
- **Mono- vs multi-exponential**: Drug clearance is often biexponential (distribution + elimination phases). Simple half-life decay assumes one compartment. State this assumption.
- **R0 vs Re**: R0 = fully susceptible population. Re = R0 x fraction_susceptible. Most real-world questions want Re.
- **Single-site estimates are noisy**: One SNP's Fst, one patient's response, one measurement's Kd. Always note when genome-wide averages, population means, or replicate experiments would be more reliable.
- **Regression estimates are order-of-magnitude**: BCF from log Kow, toxicity from QSAR. Flag the uncertainty explicitly.
- **SI units in simulations**: Neuron models, diffusion, thermodynamics — always convert to SI (seconds, meters, joules, volts) before computing. Mixed ms/mV causes silent factor-of-1000 errors.
