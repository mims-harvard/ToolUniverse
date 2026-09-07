---
name: tooluniverse-molecular-cloning
description: Molecular cloning, in both directions. DESIGN — Gibson Assembly (overlap design for seamless multi-fragment joining) and Golden Gate Assembly (Type IIS / BsaI / BbsI / Esp3I / BsmBI / SapI design with unique 4-bp fusion overhangs). ANALYSIS — work out what an existing reaction produces: given input plasmid sequences and an enzyme, digest them, join the fragments by their overhangs, and identify features of the product (expressed ORF, gRNA spacer and its target gene). Use when you need to plan how to join DNA fragments into a construct, design assembly overlaps/overhangs, decide between cloning methods, or determine the product of a stated Gibson/Golden Gate reaction. Covers the domestication (internal-site removal), overhang-uniqueness, and overlap-Tm rules. For PCR primers to generate the fragments, see tooluniverse-primer-design.
disable-model-invocation: true
---

# Molecular Cloning Assembly Design (Gibson & Golden Gate)

Plan how to join DNA fragments into a construct: design the **overlaps** (Gibson) or **Type IIS overhangs** (Golden Gate) and avoid the failures that come from internal sites and non-unique junctions.

## Step 0 — Pick the method

| Use **Gibson Assembly** when | Use **Golden Gate** when |
|---|---|
| A few fragments, **scarless/seamless** junctions anywhere you choose | Many parts, **standardized reusable** parts (MoClo/modular), one-pot |
| You can add ~20–40 bp homology by PCR | You can remove internal BsaI/BbsI sites (domestication) |
| One-off constructs | Combinatorial libraries / repeated assemblies |

Both are sequence-independent (no scar at the junction for Gibson; a 4-bp fusion scar for Golden Gate). For 2–4 unique fragments, Gibson is usually simplest; for libraries or a parts toolkit, Golden Gate.

## Step 1 — Gibson Assembly

```bash
tu run DNA_gibson_design '{"operation":"gibson_design",
  "fragments":["ATGGCG...GAGGAC","GAGGAC...GGCAAG","GGGCAAG...ATCCT"],
  "overlap_length":20}'
```

For each fragment it returns `left_overlap`, `right_overlap`, and `with_overlaps` (the fragment extended with the homology arms you'd add to your PCR primers — hand these to `tooluniverse-primer-design`).

**Gibson design rules**
- **Overlap length 15–40 bp** (20–25 typical); longer for GC-poor junctions.
- **Overlap Tm ≈ 48–65 °C** and balanced between junctions.
- **Fragment order matters** — list fragments in assembly order; the last fragment's 3′ overlaps the first only if you're making a circle (vector).
- **Avoid repeats/secondary structure** at the junctions (hairpins, direct repeats) → misassembly.
- **Unique junctions** — if two junctions share homology, fragments can swap; redesign so each overlap is unique.

## Step 2 — Golden Gate Assembly

```bash
tu run DNA_golden_gate_design '{"operation":"golden_gate_design",
  "parts":["ATGGCG...AAGAAC","CTGAGC...CTGATC","GAGGAG...GTGGTG"],
  "enzyme":"BsaI"}'
```

Returns `parts_with_overhangs`: each part's unique 4-bp `left_overhang`/`right_overhang` and the `full_sequence` flanked by the Type IIS recognition sites (e.g. BsaI `GGTCTC(N1)` … cutting outside its site to leave the 4-bp fusion overhang).

**Golden Gate design rules**
- **Domestication is mandatory.** The chosen enzyme's site (BsaI `GGTCTC`, BbsI `GAAGAC`) must NOT occur **inside** any part, or it will be cut internally. Remove internal sites by silent mutation before assembly — check every part.
- **Overhangs must be unique and non-palindromic.** Each 4-bp fusion site must differ from the others and not equal its own reverse complement, or junctions misligate. The tool assigns unique non-palindromic overhangs; keep them.
- **Avoid high-GC or all-AT overhangs**; published high-fidelity overhang sets (e.g. Potapov 2018) ligate most cleanly.
- **Order is encoded by the overhangs**, not by listing order — the 4-bp junctions define assembly.

## Step 3 — QC before ordering

`scripts/cloning_qc.py` screens parts for the problems above: internal BsaI/BbsI sites (Golden Gate), overhang uniqueness/palindromes, and Gibson overlap GC/length — and flags PASS/WARN.

## Step 4 — Gotchas (state these)

- **Internal Type IIS sites** (Golden Gate) — the #1 failure; domesticate every part.
- **Non-unique Gibson overlaps** or shared homology → fragment swapping / misassembly.
- **Repeats and strong secondary structure** at junctions reduce efficiency in both methods.
- **Overlap Tm imbalance** (Gibson) → some junctions form, others don't.
- **Generating the fragments** still needs primers with the overlaps/overhangs appended — design and QC those in `tooluniverse-primer-design` (and BLAST for specificity).

## Working backwards — what does an existing assembly produce?

The reverse question ("I combined these plasmids in a Golden Gate reaction with
Esp3I — what does the product express / what does the gRNA target?") is answered by
one call. Do **not** hand-write a digestion/ligation simulator.

```bash
tu run DNA_golden_gate_assemble '{"fragments":["<plasmid1>","<plasmid2>","<plasmid3>"],
    "enzyme":"Esp3I","labels":["pLAB-CTU","pLAB-gTU2E","pLAB-CH3"]}'
```

It digests each input, drops the fragments that keep a recognition site (those are
re-cut in the reaction and cannot persist), chains the rest by matching 4-bp
overhangs, and returns `product_sequence`, `product_length` and the `assembly_order`
with the overhang at every junction. Inputs are treated as circular plasmids unless
you pass `circular: false`.

Then **annotate the product**. Locate features in `product_sequence` (promoter, ORF,
gRNA spacer). For a gRNA cassette the spacer is the ~20 nt immediately 5′ of the
scaffold (`GTTTTAGAGCTAGAAATAGCAAG`); identify its target by matching that spacer
against the genome (`BLAST_*`, or an Ensembl/NCBI/SGD sequence lookup) and check for
an adjacent PAM. Match the **species implied by the construct** — yeast tRNA/Pol III
parts mean search the yeast genome, not human.

If the assembly reports that the fragments do not chain, digest the inputs
individually with `DNA_virtual_digest` (`circular: true`) to see what each released:
a Golden Gate donor carries its two Type IIS sites **inverted** around the insert, so
a correct digest gives **2 fragments** per plasmid. Getting 1 means the enzyme name or
`circular` is wrong — not that the plasmid lacks sites.

Enzyme names: `Esp3I` and `BsmBI` are the same enzyme (`CGTCTC`); `BsaI`
(`GGTCTC`), `BbsI` (`GAAGAC`) and `SapI` (`GCTCTTC`) all resolve too.

## Honest limitations

- Digestion and overhang-driven ligation are simulated faithfully (`DNA_virtual_digest`
  and `DNA_golden_gate_assemble` cut both strands at each enzyme's real offset, including
  Type IIS enzymes that cut outside their site). What is *not* modelled is reaction
  efficiency — overhang ligation bias, partial digestion, incorrect-but-possible
  junctions — so a returned product is the intended assembly, not a yield prediction.
  Validate by sequencing the assembled construct.
- No vector-backbone or ORF-frame checking — confirm reading frame and backbone compatibility yourself.

## Related skills
- `tooluniverse-primer-design` — design the PCR primers (with homology arms / Type IIS tails) to make the fragments.
- `tooluniverse-sequence-analysis` — handle the input sequences.
