# Variant Notation Conversion (NCBI Variation Services)

Source: `src/tooluniverse/data/ncbi_variation_tools.json` (8 tools, all live-tested
against the real NCBI Variation Services API — 8/8 tools, 14/14 baked-in
`test_examples` passed).

## Why this matters

The same variant looks different depending on which database or tool you're
talking to:

- **VCF** (`CHROM POS REF ALT`, e.g. `chr19 44908684 T C`) — what alignment/
  variant-calling pipelines produce.
- **SPDI** (`SeqID:Position:Deleted:Inserted`, e.g.
  `NC_000019.10:44908683:T:C`) — NCBI's canonical internal representation;
  0-based position, deletion-then-insertion.
- **HGVS** (`NC_000019.10:g.44908684T>C`) — the human-readable form used in
  ClinVar, clinical reports, and most literature.
- **rsID** (`rs429358`) — dbSNP's population identifier; not every variant
  has one (novel/rare variants often don't).

Converting between these is a real, recurring need before annotation lookups
elsewhere in this skill (ClinVar via `MyVariant_query_variants`, VEP
consequence prediction, etc. all expect specific notations).

## Tool reference

### `NCBIVariation_vcf_to_spdi`

- **Parameters**: `chrom` (RefSeq accession, e.g. `NC_000007.14` for chr7
  GRCh38 — NOT a bare chromosome number), `pos` (1-based VCF position,
  string), `ref`, `alt`.
- **Returns**: `spdis[]`, each with `seq_id`, `position` (0-based SPDI
  position — note this is `pos - 1` relative to the VCF input),
  `deleted_sequence`, `inserted_sequence`.
- **Real example** (BRAF V600E-region variant):
  ```
  tu run NCBIVariation_vcf_to_spdi '{"chrom":"NC_000007.14","pos":"140753336","ref":"A","alt":"T"}'
  → {"status":"success","data":{"spdis":[{"seq_id":"NC_000007.14","position":140753335,"deleted_sequence":"A","inserted_sequence":"T",...}]}}
  ```

### `NCBIVariation_spdi_to_hgvs`

- **Parameters**: `spdi` (string).
- **Returns**: `{"hgvs": "<string>"}` — a single HGVS expression.
- **Real example**:
  ```
  tu run NCBIVariation_spdi_to_hgvs '{"spdi":"NC_000019.10:44908683:T:C"}'
  → {"status":"success","data":{"hgvs":"NC_000019.10:g.44908684T>C"}}
  ```
  Note the coordinate shift: SPDI's 0-based `44908683` becomes HGVS's 1-based
  `44908684` — this is expected, not an off-by-one bug; never hand-adjust
  coordinates yourself, let the tool do the conversion.

### `NCBIVariation_hgvs_to_spdi`

- **Parameters**: `hgvs` (genomic `g.`, coding `c.`, or RNA `r.`).
- **Returns**: `spdis[]` — can be more than one entry when the HGVS maps to
  multiple assemblies/transcripts (e.g. a coding `c.` HGVS maps to both the
  transcript-level and genomic-level SPDI).
- Also validates HGVS syntax as a side effect — a malformed HGVS string
  returns an error rather than a spurious SPDI.

### `NCBIVariation_spdi_canonical`

- **Parameters**: `spdi`.
- **Returns**: one canonical (right-shifted, normalized) SPDI — same shape
  as one entry of `spdis[]` above but always singular.
- Use for **deduplication**: two SPDI strings that look different (e.g. an
  indel represented with the inserted/deleted sequence shifted left vs.
  right) can canonicalize to the same variant.

### `NCBIVariation_spdi_equivalents`

- **Parameters**: `spdi`.
- **Returns**: `equivalents[]` — the same variant mapped across GRCh37,
  GRCh38, RefSeqGene, and transcript coordinate systems. Use for **liftover**
  (GRCh37→GRCh38) or to get a transcript-level HGVS-c from a genomic SPDI.

### `NCBIVariation_rsid_lookup`

- **Parameters**: `rsid` (e.g. `rs429358`).
- **Returns** (real response captured for rs429358 — APOE ε4 allele):
  `refsnp_id`, `create_date`, `last_update_date`, `citations[]` (PubMed IDs,
  often hundreds for well-studied variants like this one), `mane_select_ids`
  (e.g. `["NM_000041.4"]`), `variant_type` (`"snv"`), `grch38_placements[]`
  (each with `seq_id`, `position` — 1-based, `spdi_position` — 0-based,
  `deleted_sequence`, `inserted_sequence`; **multiple placements per rsID is
  normal** — one per possible ALT allele), `genes[]` (`gene`, `name`,
  `gene_id`), `clinical_significance[]` (each with `accession` (RCV
  number), `review_status`, `disease_names[]`, `significance[]` — e.g.
  `"pathogenic-established-risk-allele"` for Alzheimer disease 2). This is
  often enough on its own without a follow-up ClinVar-specific call.
- One call gives coordinates + gene + ClinVar summary + citation count in
  one round trip — prefer this over separate lookups when starting from an
  rsID.

### `NCBIVariation_alfa_frequencies_by_rsid`

- **Parameters**: `rsid`.
- **Returns** (real response for rs429358): `refsnp_id`, `build_id`,
  `positions[]` → `studies[]` → `populations[]`, each population entry with
  `biosample_id`, `population` (e.g. `"Total"`, `"European"`, `"African"`,
  `"African American"`, `"East Asian"`, `"South Asian"`, `"Latin American 1"`,
  `"Latin American 2"`, `"Other"`), `total_alleles`, `allele_counts` (per
  allele letter), `allele_frequencies` (per allele letter, as a fraction).
- **This is per-ancestry, not a single global MAF** — for rs429358 the C
  allele frequency ranges from ~2.3% (South Asian) to ~7.5% (Other) to ~5.3%
  (African/African American) to ~3.1% (European/Asian) in the captured
  response. Reporting one "the frequency is X%" number without naming the
  population is misleading for a variant with this much ancestry variation.
- **Do not conflate with gnomAD**: `gnomad_get_variant` / `MyVariant_query_variants`
  report gnomAD's own population buckets and numbers, which are a different
  aggregation than NCBI's ALFA study — state the source when citing a
  frequency.

### `NCBIVariation_spdi_to_rsids`

- **Parameters**: `spdi`.
- **Returns**: `{"spdi": "<echoed input>", "rsids": [<int>, ...], "count": <int>}`.
- **Real example** (reverse-lookup confirms the same round trip):
  ```
  tu run NCBIVariation_spdi_to_rsids '{"spdi":"NC_000019.10:44908683:T:C"}'
  → {"status":"success","data":{"spdi":"NC_000019.10:44908683:T:C","rsids":[429358],"count":1}}
  ```
  Note `rsids` are returned as bare integers (`429358`), not the `rs`-prefixed
  string — prepend `rs` yourself when displaying to a user.

## Worked example: VCF coordinate → HGVS → per-ancestry frequency (rs429358, APOE)

Real chained calls, real responses (abbreviated where noted):

```
1) tu run NCBIVariation_rsid_lookup '{"rsid":"rs429358"}'
   → grch38_placements include NC_000019.10, spdi_position 44908683, T>C
   → genes: [{"gene":"APOE","name":"apolipoprotein E","gene_id":348}]
   → clinical_significance includes "pathogenic-established-risk-allele" for
     Alzheimer disease 2 (RCV000019448.48)

2) tu run NCBIVariation_spdi_to_hgvs '{"spdi":"NC_000019.10:44908683:T:C"}'
   → {"hgvs":"NC_000019.10:g.44908684T>C"}

3) tu run NCBIVariation_alfa_frequencies_by_rsid '{"rsid":"rs429358"}'
   → Total: C=3.54% (n=349,596 alleles)
   → European: C=3.12%  |  African: C=5.26%  |  African American: C=5.29%
   → East Asian: C=2.69%  |  South Asian: C=2.25%  |  Other: C=7.53%
```

This demonstrates the full pipeline from an rsID to a genomic coordinate, to
HGVS notation for a clinical report, to a population-stratified frequency
table — all from real API responses, no field assumed from the JSON schema
alone.
