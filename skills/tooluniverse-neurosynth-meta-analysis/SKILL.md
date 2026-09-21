---
name: tooluniverse-neurosynth-meta-analysis
description: Meta-analytic decoding of human fMRI coordinates using the Neurosynth coordinate database (14,371 studies, ~3,228 cognitive/neuroscience terms) — given an MNI brain coordinate, statistically identify which cognitive terms are over-represented in studies reporting activation there ("reverse inference"); given a term, find the studies and coordinates most associated with it ("forward" lookup). Use when someone asks "what does this brain coordinate/region do", "decode this fMRI activation peak", "what terms are associated with [MNI coordinate]", "find studies about [cognitive term] and their activation coordinates", or "reverse-infer cognitive function from a brain location". This is real local analysis on a downloaded, cached coordinate database — not a live API — following ToolUniverse's honesty-contract pattern (real computed statistics, no fabricated term associations).
disable-model-invocation: true
---

# Neurosynth Meta-Analytic Coordinate Decoding

Statistically decode human fMRI brain coordinates against ~14,000 published neuroimaging studies, or look up which studies/coordinates are associated with a cognitive term — using the real, freely-downloadable Neurosynth coordinate database (no API key, no login).

## Honesty contract (read first)

This skill downloads a real coordinate database and runs real statistics on it. It must never fabricate a term association, a study result, or a p-value.

1. **Preflight before anything.** Run `scripts/download_data.py` first. If any file fails to download, STOP and report the failure — do not proceed with partial data or describe hypothetical decoding results.
2. **Never guess a term.** `search_by_term.py` requires an exact (case-sensitive) vocabulary match. If the term isn't found, it returns suggestions (substring matches, or close spellings when there are none, e.g. `hipocampus` → `hippocampus`) — use those, don't invent a plausible-sounding term.
3. **Report the multiple-testing caveat every time.** `decode_coordinate.py` tests ~3,228 terms simultaneously per query. Uncorrected p-values will produce false positives at this scale — always surface the FDR-corrected `fdr_q_value`, not just the raw `p_value`, when characterizing how confident a result is.
4. **This is a simplified reverse-inference test, not a full meta-analysis pipeline.** It does binary term-presence comparison (near-coordinate studies vs. rest of corpus) via a two-proportion z-test — a real, defensible statistical test, but not the same as running NiMARE's full activation-likelihood-estimation (ALE) or multilevel kernel density analysis (MKDA) methods. Say so if precision matters (e.g., the user is drafting something for publication).
5. **Never overwrite the cached data files** — `download_data.py` writes to a dedicated cache directory and is idempotent (skips re-download if already cached, unless `--force`).

## When to Use This Skill

Apply when users:
- Give an MNI coordinate (or a named landmark you can translate to one, e.g. Broca's area ≈ (-50, 20, 10)) and ask what cognitive function it's associated with
- Ask to "decode" an fMRI activation peak from their own study against the published literature
- Want to know which studies report activation for a specific cognitive term, or where those studies' peaks are located
- Ask for a quick meta-analytic sanity check before writing a discussion section ("is this activation consistent with what's typically reported at this location?")

**NOT for** (route elsewhere):
- Single-neuron morphology, raw neuroimaging dataset discovery, computational models, or statistical brain-map hosting → `tooluniverse-neuroscience` (NeuroMorpho/OpenNeuro/ModelDB/NeuroVault sections — genuinely different resource types, see that skill's comparison table)
- A full, publication-grade coordinate-based meta-analysis (ALE/MKDA with proper cluster-level FWE correction) → this skill's method is a real but simplified proxy; point the user to NiMARE for the full pipeline
- Anything requiring raw fMRI voxel data, not just reported peak coordinates — this database only has published peak coordinates and term weights, never raw scans

## Setup

```bash
python3 scripts/download_data.py
```

Downloads ~9MB total (coordinates, study metadata, term vocabulary, term×study weight matrix) from the public `neurosynth/neurosynth-data` GitHub repo — no authentication, no rate limiting observed — and caches it under `~/.cache/tooluniverse/neurosynth/` (override with `TOOLUNIVERSE_CACHE_DIR`). Re-running is a no-op unless `--force` is passed. Takes a few seconds.

## Workflow

### Decode a coordinate ("what does this location do?")

```bash
python3 scripts/decode_coordinate.py <x> <y> <z> --radius 8 --top 15
```

Finds every study with a reported peak within `--radius` mm of the query point, then ranks all ~3,228 terms by how much more often they appear in that near-coordinate study set than in the rest of the corpus (two-proportion z-test). Returns both raw `p_value` and BH-corrected `fdr_q_value` per term — **always cite the q-value when characterizing confidence**. Fails cleanly (not silently) if fewer than `--min-studies` (default 5) studies are found nearby — widen the radius rather than trusting an underpowered result.

**Verified example**: Broca's area, `(-50, 20, 10)`, radius 8mm → top terms were `language`, `inferior frontal`, `semantic`, `sentence`, `comprehension`, `linguistic`, `verb` — all with q≈0, matching well-established neuroanatomy. Use this as a sanity-check case if something looks wrong after a code change.

**More landmarks (radius 8mm; verified 2026-09-20, all q < 1e-5):**

| Region | MNI (x y z) | Top terms (z-score) |
|---|---|---|
| Fusiform face area | 40 -52 -20 | `face` 25.1, `fusiform` 23.5, `faces` 21.3, `ffa` 20.1 |
| Left primary motor cortex (hand) | -38 -24 58 | `motor` 21.2, `finger` 20.4, `primary motor` 19.8, `hand` 18.4 |
| Left hippocampus | -24 -18 -18 | `hippocampus` 24.1, `hippocampal` 18.8, `episodic` 14.5, `memory` 13.5 |
| Left amygdala | -22 -4 -18 | `amygdala` 47.3, `emotional` 23.2, `emotion` 20.5, `faces` 18.1 |
| Primary visual cortex (V1) | 0 -90 0 | `primary visual` 7.9, `visual` 7.7, `v1` 7.3 (fewer studies, 454, so a weaker but still correct signal) |

### Look up a term ("what studies/coordinates are about X?")

```bash
python3 scripts/search_by_term.py "working memory" --top 10 --with-coordinates
```

Returns the top-N studies with the highest tfidf weight for that exact term (title, authors, year, journal, weight), and optionally their reported MNI coordinates. If the term isn't an exact vocabulary match, returns `did_you_mean` suggestions (substring matches, else close spellings) instead of guessing. This is a simple ranking, not a statistical test — don't present a high tfidf weight as equivalent to the coordinate-decoding z-score/q-value above.

## Reference

- `references/method.md` — the statistical method in more detail, data provenance, and known limitations
- Neurosynth: https://neurosynth.org
- Data source: https://github.com/neurosynth/neurosynth-data
- For a full ALE/MKDA meta-analysis pipeline instead of this simplified proxy: NiMARE (https://nimare.readthedocs.io)
