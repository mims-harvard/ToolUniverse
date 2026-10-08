# Method, Data Provenance, and Limitations

## Data provenance

All data comes from the public `neurosynth/neurosynth-data` GitHub repository
(https://github.com/neurosynth/neurosynth-data), maintained by the Neurosynth
project (Yarkoni et al., 2011, *Nature Methods*). `download_data.py` fetches,
for a given `--version` (default `7`):

| File | Contents | v7 shape (verified) |
|---|---|---|
| `..._coordinates.tsv.gz` | One row per reported activation peak: `id` (study), `table_id`, `table_num`, `peak_id`, `x`, `y`, `z` (MNI space) | one row per peak, many peaks per study |
| `..._metadata.tsv.gz` | One row per study: `id`, `doi`, `space`, `title`, `authors`, `year`, `journal` | 14,371 studies |
| `..._vocabulary.txt` | One cognitive/neuroscience term per line, no header | 3,228 terms |
| `..._features.npz` | Sparse (scipy CSC) study×term tfidf weight matrix | (14371, 3228) |

**Positional alignment, not ID-based.** The feature matrix's row `i`
corresponds to `metadata.tsv` row `i` — there is no shared key column tying
them together. `_neurosynth_data.py` verifies `matrix.shape[0] == len(meta)`
and `matrix.shape[1] == len(vocab)` on every load and warns loudly (not
silently) if a future data version breaks this assumption. This alignment
was confirmed empirically, not assumed: the top tfidf-weighted studies for
the term `"memory"` were manually checked and are genuinely memory-research
papers.

Terms are derived automatically from study abstracts (tfidf-weighted, not
human-curated), so the vocabulary includes both genuine cognitive constructs
(`"working memory"`, `"language comprehension"`) and some noisier
abstract-derived tokens. Treat a single term hit with caution; a coordinate
result with many converging, semantically related top terms (as in the
Broca's-area validation below) is much stronger evidence than any one term
alone.

## Statistical method (`decode_coordinate.py`)

This is a simplified version of Neurosynth's own "reverse inference" test —
not a reimplementation of activation-likelihood estimation (ALE) or
multilevel kernel density analysis (MKDA), which model spatial uncertainty
around each peak with a smoothing kernel. This script instead uses a hard
`--radius` cutoff and binary term presence/absence per study:

1. **Near-coordinate set**: every study with ≥1 reported peak within
   `--radius` mm (Euclidean, in MNI space) of the query point.
2. **Term presence**: a study counts as "term-positive" if its tfidf weight
   for that term is `> 0` (not weighted by magnitude).
3. **Two-proportion z-test**: compares the term-positive rate in the
   near-coordinate set against the rest of the corpus, using pooled-variance
   standard error.
4. **Multiple-testing correction**: with ~3,228 terms tested per query,
   Benjamini-Hochberg FDR correction is applied and reported as
   `fdr_q_value` alongside the raw `p_value`. **Always prefer the q-value**
   when stating how confident a result is.

### Validation

Query: Broca's area, MNI `(-50, 20, 10)`, `--radius 8`, `--top 15`.
`n_studies_near_coordinate = 914`, `n_studies_rest_of_corpus = 13457`.
Top terms returned (all `fdr_q_value ≈ 0`): `language`, `inferior frontal`
(Broca's area's actual anatomical name), `semantic`, `sentence`,
`comprehension`, `sentences`, `inferior`, `word`, `frontal gyrus`, `frontal`,
`meaning`, `linguistic`, `sentence comprehension`, `words`, `verb`.

This matches established neuroanatomy (Broca's area / left inferior frontal
gyrus is textbook-canonical for language production and syntactic
processing) and is used as the regression sanity check for this skill —
re-run it after any change to `decode_coordinate.py` and confirm `language`
and `inferior frontal` still lead the list.

## Known limitations

- **Binary presence, not weighted magnitude.** A study with a tfidf weight
  of 0.01 for a term counts identically to one with 0.9. A weighted test
  (e.g., comparing mean weight, or a proper meta-regression) would be more
  sensitive but is out of scope for this lightweight decoder.
- **No spatial smoothing.** A hard `--radius` cutoff means a peak at
  `radius + 0.1mm` is excluded entirely while one at `radius - 0.1mm` counts
  fully — unlike ALE's smooth Gaussian kernel. Try a couple of radius values
  (e.g., 6mm and 10mm) if a result looks borderline.
- **Vocabulary is abstract-derived, not curated.** Expect some tokens that
  aren't clean cognitive constructs (author names, methods jargon).
- **English-language, published-literature bias.** The corpus reflects what
  gets published and indexed, not the true prevalence of any cognitive
  process — absence of a term near a coordinate means "not commonly reported
  in this literature," not "this region is uninvolved."
- **Version 7 is what's fetched by default.** If a newer version is
  published upstream, pass `--version` explicitly; `download_data.py`'s file
  naming pattern assumes the same `data-neurosynth_version-{v}_...` scheme
  Neurosynth has used historically — verify against the repo's file listing
  if a fetch 404s.
- **For anything publication-grade**: use NiMARE
  (https://nimare.readthedocs.io), which implements real ALE/MKDA with
  proper cluster-level family-wise-error correction against this same
  underlying coordinate data.
