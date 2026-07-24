---

name: tooluniverse-primer-design
description: "PCR / qPCR primer and oligo design — design forward/reverse primers for a target region (SantaLucia nearest-neighbor thermodynamics), compute melting temperature (Tm) and annealing temperature (Ta), check GC content, and screen an oligo for hairpins and primer-dimers. Use when you need primers for a sequence, want to QC an existing primer pair, or need the Tm of an oligo. Covers the primer-design rules (Tm matching, GC clamp, 3'-end, length) and the tools' constraint quirks."
---

# PCR / qPCR Primer & Oligo Design

Design primers for a target DNA region, get their Tm/Ta, and QC them for the secondary-structure problems that make a PCR fail.

## When to use this

- Design a forward/reverse primer pair to amplify a region of a sequence.
- Compute the Tm / annealing temperature of a primer.
- QC an existing primer pair (GC clamp, 3'-end, hairpins, self/cross dimers, Tm match).

## Step 1 — Design a primer pair

```bash
tu run DNA_primer_design '{"operation":"primer_design",
  "sequence":"ATGGCG...AACGTG",        # full template; must be >= target_end + flanking primer room
  "target_start":40, "target_end":125,
  "tm_target":60, "product_size_min":80, "product_size_max":140}'
```

Returns `forward_primer` / `reverse_primer` (sequence, tm, gc_content, length, position) and `product_size`. (`target_end` is clamped to the sequence length, so a too-short template silently shrinks the target — see the constraint quirk below.)

> **Constraint quirk — read this or it will error.** `target_start..target_end` is the region the **amplicon must cover**, and the design only succeeds when that span fits inside the product-size window AND good-Tm primers can be placed flanking it. So you need roughly: `product_size_min ≤ (target span) ≤ product ≤ product_size_max`, with enough flanking sequence on both sides. Common errors and the fix:
> - *"Target region (N bp) is smaller than product_size_min"* → your target is narrower than `product_size_min`; lower `product_size_min` or widen the target.
> - *"product does not cover the target / does not span"* → the target is too wide for `product_size_max`, or runs too close to a sequence end; widen `product_size_max` or give more flanking sequence.

## Step 2 — Get Tm / annealing temperature for specific primers

```bash
tu run NEB_Tm_calculate '{"primer_sequence":"CTACCTGAAGAACCTGAG",
  "primer_sequence_2":"CTTGATGTCCTCCAGCAT",
  "polymerase":"Q5", "primer_concentration":500, "monovalent_salt_mm":50}'
```

NEB returns Tm for each primer and a recommended **annealing temperature (Ta)** for the chosen polymerase. `IDT_analyze_oligo` (sequence, salt/Mg/dNTP/oligo concentrations) adds GC%, molecular weight, and **hairpin / self-dimer** screening. `DNA_calculate_gc_content` is a quick GC check.

> **Tm depends on method + conditions.** SantaLucia NN (the design tool), NEB, and IDT use different parameter sets, and Tm shifts with monovalent salt, Mg²⁺, and primer/dNTP concentration. Pick **one** calculator + condition set and use it for the whole experiment; don't compare a SantaLucia Tm to an IDT Tm. Always state the conditions.

## Step 3 — Primer design rules (what "good" looks like)

| Property | Target | Why |
|---|---|---|
| **Length** | 18–24 nt | long enough for specificity, short enough for efficient annealing |
| **Tm** | 58–62 °C | works with standard cycling; keep the **pair within ~2–3 °C** of each other |
| **ΔTm (forward vs reverse)** | < 3 °C (≤5 absolute max) | mismatched Tm → one primer anneals poorly |
| **GC content** | 40–60 % | balanced stability |
| **GC clamp** | 1–2 G/C in the last 3 nt of the 3′ end | stabilizes 3′ priming; >3 G/C risks mispriming |
| **3′ end** | avoid 3′ complementarity within a pair and within a primer | prevents primer-dimers |
| **Runs / repeats** | avoid ≥4 identical bases in a row and di-nucleotide repeats | reduce slippage / mispriming |
| **Annealing temp (Ta)** | ~ Tm − 3 to −5 °C (use the polymerase's calculator) | specificity vs yield |
| **Amplicon (qPCR)** | 70–150 bp | efficient amplification |

`scripts/primer_qc.py` checks a primer pair against these rules (GC clamp, 3′ self/cross-complementarity, runs, GC%, length, Wallace/NN Tm, Tm match) and flags problems — use it to QC primers from any source.

## Step 4 — Specificity (the tools do NOT do this)

Tm and structure are necessary but **not sufficient**. A primer can be thermodynamically perfect and still amplify the wrong locus. These tools do **not** check genome specificity — always BLAST each primer (or use Primer-BLAST) against the target genome and confirm a single intended product before ordering. State this in any recommendation.

## Step 5 — Common gotchas

- **Forgetting specificity** (Step 4) — the #1 cause of a "well-designed" primer failing.
- **Mismatched pair Tm** — design tries to match, but a hand-picked pair often isn't; check ΔTm.
- **3′ primer-dimers** — 3′ complementarity between forward and reverse is the classic dimer; `IDT_analyze_oligo` / the QC script flag it.
- **Tm method/condition mixing** (Step 2).
- **Secondary structure in the template** (GC-rich/hairpin regions) can block priming even with good primers — consider additives or moving the target.

## Honest limitations

- Thermodynamic Tm/structure prediction ≠ empirical performance; validate by gradient PCR.
- No genome-specificity check (Step 4) and no SNP-masking — handle those separately.

## Related skills
- `tooluniverse-sequence-analysis` — upstream sequence handling (FASTQ, alignment, coverage).
- `tooluniverse-enzyme-kinetics` / `tooluniverse-dose-response` — other quantitative assay analyses.
