# What this pipeline does not do

Read before promising anyone a design. Most of what follows is the authors' own assessment.

## The honest summary

> "All of these limitations indicate that our models do not meaningfully model the physics of catalysis."

The designs work by producing geometry a structure predictor still believes in, not by modelling catalysis. That is why the filters carry the weight, and why a filter set that is not grounded in your reaction's mechanism will not transfer.

## Activity is still well short of nature

Catalytic activities of de novo designs remain **orders of magnitude lower** than natural enzymes or enzymes optimised by directed evolution. Where the published designs win, be precise about what was won:

| campaign | what was actually achieved |
|---|---|
| Kemp eliminase | kcat/Km 14,600 M⁻¹s⁻¹ — 70× the best previous *novel-scaffold* design, but 10–100× below experimentally optimised designs |
| Serine esterase (4MU-Ac) | 360,000 M⁻¹s⁻¹, exceeding iteratively optimised prior designs — **but the design has natural serine-esterase topology** |
| DEHPase | *less* active than natural DEHPases at room temperature; the win is operating at 90 °C and in 75% acetonitrile, where the natural enzymes are completely inactive |
| Nitrene transferase | 22 turnovers, 99:1 regioselectivity — two orders of magnitude more piperidine turnover than the best natural starting point, which never exceeded 30:70 selectivity |
| Carbene transferase | 96% e.e., in a single round with no experimental feedback |

Turnover numbers in the tens are a real result for new-to-nature chemistry and are not a usable biocatalyst.

## Novelty needs checking, not assuming

"De novo" does not guarantee a novel fold. Using the authors' own definition — TM-score > 0.45 **and** scaffold-aligned triad RMSD < 5 Å to an annotated enzyme of the same class — **16.4%** of the published serine esterases had natural serine-esterase topology, and **six of the top seven by catalytic efficiency** did. The paper reports the best non-natural-topology design separately; do the same. Across all novel-scaffold designs the median maximum TM-score to the PDB was 0.33, and the most active design's maximum sequence identity to anything natural was 29%.

## The motif decides more than the model

The input motif has a strong influence that **the filters do not capture**. Same pipeline, same filters, different catalytic base: Asp/Glu 37% hit rate (32/86) against His 10% (9/87). A model upgrade did not help: a generator with >2× higher in-silico pass rate produced a *similar measured activity distribution* once the same filters were applied.

Corollary: in-silico benchmarks are weak proxies. Benchmark improvements may not transfer to experimental success, and in this work they demonstrably did not.

## Known pipeline defects, as disclosed

- Stock AF3 mishandles leaving atoms, giving ~180° angles at Ser Oγ for covalent tetrahedral intermediates where ~109° is correct. AF3-LA fixes the common case but **still handles examples with multiple heavy leaving atoms incorrectly**.
- AF3 incorrectly dropped glycan O1 for three benchmark motifs.
- The published TI2 filter requires oxyanion-hole H-bonds to the **ester** oxygen rather than the oxyanion, which was not intended. It was kept because round 2 produced active designs with it.
- Rare pairs of designs come back with TM-score ≈ 1, probably coincidental diffusion seed repetition. De-duplicate before counting diversity.
- Indexed tip-atom conditioning sometimes fails to recapitulate a ligating His — hence a dedicated `sampled_his_rmsd` filter.
- Unindexed conditioning is **not guaranteed to reproduce every motif residue**; check `num_missing_motif_residues`.

## Cost

Many samples must be generated per motif to find one that passes filters, which the authors call "practically prohibitive". Budget generation in the hundreds-to-thousands of designs per motif, with 1000 denoising steps each, plus folding in every mechanistic state at 7–10 seeds. The MR and MPD filters multiply this by another 7–10×.

## Scope of what has been validated here

The ToolUniverse `apnovo` provider's own validation status is in `src/tooluniverse/remote/apnovo/README.md` and is the authority on what has and has not been run on this machine. Nothing in this skill should be read as a claim that a stage has been verified.

## Terms of use

The generator weights are **non-commercial only** — universities, non-profit organisations and research institutes, educational, journalism and government bodies. Not available to commercial organisations even for non-commercial work, and Input must not come from or on behalf of a commercial organisation.

Also binding:

- **Output carries terms.** Generated structures and sequences are subject to the AP Novo Output Terms of Use. The pipeline writes a notice into its CIF/FASTA output; if you convert formats and strip it, you must re-attach the notice and a copy of the terms when distributing.
- **Citation is required** for any publication or disclosed finding: Wu, Z. et al., *Designing enzymes for new-to-nature chemistry and non-natural substrates with AlphaProtein Novo*, bioRxiv 2026, doi 10.64898/2026.10.01.756017.
- **Weights must not be redistributed** — not published, not shared outside your organisation, and only used if received directly from Google.
- **Output must not train** another de novo protein/enzyme design, structure generation or sequence design model, including by distillation or synthetic data.
- **Prohibited inputs and uses** include motifs, scaffolds, ligands or substrates derived from or targeting biological toxins, venoms, virulence factors, regulated pathogens, chemical or biological weapons or their precursors, controlled substances, or hazardous metabolic disruptors; and circumventing biosecurity screening, gene-synthesis customer or sequence screening, or safety filters.

The paper itself contains no biosecurity or dual-use discussion — that governance lives entirely in the licence files, which is why they are summarised here and reproduced in the provider README.
