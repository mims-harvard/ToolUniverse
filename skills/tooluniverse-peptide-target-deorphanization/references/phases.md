# Peptide Target Deorphanization — per-phase manual reference

Detailed manual/fallback reference for the `tooluniverse-peptide-target-deorphanization` skill. The two scripts in `../scripts/` automate Phases 1–4 (and the Phase 5 dry-run); **read this file when a script step fails, when you want to drive a phase by hand, or when you extend the pipeline to a new tool.** Every tool call the scripts make is documented here with exact parameter names and gotchas.

## Contents
- [Phase 0 — Tool verification](#phase-0--tool-verification-run-first)
- [Phase 1 — Peptide characterization + motif](#phase-1--peptide-characterization--motif-keyless)
- [Phase 2 — Multi-route candidate generation](#phase-2--multi-route-candidate-generation-run-routes-in-parallel)
- [Phase 3 — Cross-species reconciliation](#phase-3--cross-species-reconciliation-keyless)
- [Phase 4 — Narrowing & ranking](#phase-4--narrowing--ranking)
- [Phase 5 — Structural confirmation (co-folding / ClusPro)](#phase-5--structural-confirmation-via-co-folding-optional-key-gated)
- [Phase 6 — Ranked shortlist report](#phase-6--ranked-shortlist-report-evidence-tiers--wet-lab-recommendation)
- [Fallback Chains](#fallback-chains)
- [NVIDIA NIM / runtime notes](#nvidia-nim--runtime-notes)
- [Worked example A — exendin-4 → GLP1R (control)](#worked-example-a--exendin-4--glp1r-control-recovers-the-class-b-family)
- [Worked example B — anti-insulin-resistance peptide (the real case)](#worked-example-b--anti-insulin-resistance-peptide-that-does-not-bind-glp1r-in-mouse)
- [Worked example C — ω-conotoxin → ion channel (NON-GPCR target class)](#worked-example-c--ω-conotoxin--ion-channel-non-gpcr-demonstrates-generality)

---

## Phase 0 — Tool verification (run first)

Confirm every tool you intend to use is loadable before building the pipeline. Mark any tool that errors here and substitute its fallback.

```bash
# repo root = cwd; SDK uses sys.path.insert(0,"src")
python3 -m tooluniverse.cli run PepCalc_peptide_properties '{"seq":"HGEGTFTSDLSKQMEEEAVRLFIEWLKNGGPSSGAPPPS"}'
```

Verification targets (all expected KEYLESS unless noted):
- Characterization/motif: `PepCalc_peptide_properties`, `ProtParam_calculate`, `ScanProsite_scan_protein`, `PROSITE_get_entry`, `ELM_list_classes`, `ELM_get_interaction_domains`, `ELM_get_instances`, `ESMFold_predict_structure`
- Homology: `BLAST_protein_search`, `EBI_msa_align`, `AMPSphere_sequence_match`
- Receptor family / pharmacology: `GtoPdb_search_targets`, `GtoPdb_search_ligands`, `GtoPdb_get_interactions`, `GPCRdb_get_protein`, `GPCRdb_list_proteins`, `GPCRdb_get_ligands`, `HGNC_fetch_gene_by_symbol`, `HGNC_fetch_gene_family_members`
- Phenotype / cross-species: `OpenTargets_get_disease_id_description_by_name`, `OpenTargets_get_associated_targets_by_disease_efoId`, `EnsemblCompara_get_paralogues`, `EnsemblCompara_get_orthologues`, `Alliance_get_gene_orthologs`
- Target-engagement (soluble candidates, keyless): `ProteomicsDB_get_protein_meltome`
- ID mapping / sequences: `UniProt_search`, `UniProt_get_sequence_by_accession`, `PDBeSIFTS_get_best_structures`
- **Key-gated (note, do not block):** `NvidiaNIM_boltz2`, `NvidiaNIM_esmfold`, `NvidiaNIM_esm2_650m`, `NvidiaNIM_alphafold2_multimer`, `NvidiaNIM_openfold3` — require `NVIDIA_API_KEY`; `ClusPro_submit_peptide_docking` — requires a free academic `CLUSPRO_USERNAME` / `CLUSPRO_API_SECRET`.

If any keyless tool fails to load, record it and use the Fallback Chains below. Do **not** abort the pipeline because a key-gated co-folding tool is unavailable — co-folding is Phase 5 (optional confirmation only).

---

## Phase 1 — Peptide characterization + motif (keyless)

Establish what the peptide *is* before guessing what it binds.

### 1a. Physicochemical properties — run BOTH (cross-check pI/MW)
```bash
python3 -m tooluniverse.cli run PepCalc_peptide_properties '{"seq":"<SEQUENCE>"}'      # param is 'seq' (raw 1-letter)
python3 -m tooluniverse.cli run ProtParam_calculate        '{"sequence":"<SEQUENCE>"}'  # param is 'sequence' (different name!)
```
- **Gotcha:** the two tools use **different parameter names** (`seq` vs `sequence`).
- PepCalc → formula, monoisotopic + average MW, pI, extinction coefficient (source Pep-Calc.com).
- ProtParam → MW, pI, instability index (+ stable/unstable call), aliphatic index, GRAVY, +/- charged counts, full AA composition.
- Use the **pI agreement across both tools** as a sanity check (control: pI ~4.4, MW ~4.19 kDa, instability 12.9 = stable, GRAVY −0.69 = hydrophilic).
- **Non-canonical / cyclic check:** any residue outside the 20 standard L-amino acids means BLAST/PROSITE/ProtParam will mischaracterize the peptide (common for unicellular-organism natural products / non-ribosomal peptides). Look such peptides up by name with `Norine_get_peptide` and treat them as cyclic in co-folding (`cofold_screen.py --cyclic`).

### 1b. Signature / family scan — the decisive family-ID step
```bash
python3 -m tooluniverse.cli run ScanProsite_scan_protein '{"seq":"<SEQUENCE>"}'   # 'seq' accepts a RAW SEQUENCE or a UniProt acc
python3 -m tooluniverse.cli run PROSITE_get_entry        '{"accession":"<PSxxxxx>"}'  # resolve each matchset hit
```
- ScanProsite returns a `matchset` of PROSITE accessions (`PSxxxxx`) with start/stop. Resolve **each** with `PROSITE_get_entry`.
- A PROSITE family/domain hit names a protein family; for receptor-ligand peptides, the matching signature often names the receptor's **natural ligand family** → candidate receptors.
- Control: single hit **PS00260** (res 1–23) → *"Glucagon / GIP / secretin / VIP family signature"* → names the class B1 GPCR ligand family containing GLP1R + paralogs. **This is the family-level deorphanization signal.**

### 1c. SLiM classes + motif→binding-domain map (for peptides whose signature is NOT a named PROSITE family)
```bash
python3 -m tooluniverse.cli run ELM_list_classes            '{"operation":"list_classes","motif_type":"LIG","max_results":50}'
python3 -m tooluniverse.cli run ELM_get_interaction_domains '{"operation":"get_interaction_domains","query":"<motif or domain kw>"}'
python3 -m tooluniverse.cli run ELM_get_interaction_domains '{"operation":"get_interaction_domains","elm_identifier":"LIG_SH3_1"}'
```
- `operation` is **enum-locked and required**. `motif_type`: `LIG` (ligand-binding — most relevant), also `CLV`/`DEG`/`DOC`/`MOD`/`TRG`.
- `ELM_list_classes` gives each SLiM class a **regex** (+ probability, instance counts). Match candidate class regexes against your peptide.
- `ELM_get_interaction_domains` is the **mechanistic core**: it maps each SLiM class → the **Pfam domain it binds** (e.g. `LIG_SH3_1 → PF00018 'SH3 domain'`; 409 total mappings). That Pfam domain points to candidate receptor/partner families.
- **Receptor-side check** (use on a *known candidate receptor*, NOT the orphan peptide):
  ```bash
  python3 -m tooluniverse.cli run ELM_get_instances '{"operation":"get_instances","uniprot_id":"<RECEPTOR_ACC>"}'
  ```
  Lists curated SLiM instances on a known protein (with PDB IDs). **Coverage is sparse for membrane GPCRs** — GLP1R (P43220) returns 0 instances; this is expected, not a failure. Most useful for soluble/adaptor candidate partners.

### 1d. Optional fold (keyless; do NOT block the pipeline on it)
```bash
python3 -m tooluniverse.cli run ESMFold_predict_structure '{"sequence":"<SEQUENCE>"}'   # KEYLESS public ESM Atlas, ~30–60s
```
- Returns `mean_plddt`, per-residue pLDDT, confident fractions, `pdb_text`. Control: mean pLDDT 0.85.
- Key-gated alternative: `NvidiaNIM_esmfold` (`NVIDIA_API_KEY`). Use the keyless one first.

### 1e. Target-class router — classify before you enumerate
A peptide's real target is **not necessarily a GPCR**. Before Route 2C, classify the likely target class from the motif/homology text + sequence features, and let it pick the enumeration strategy and the seedless search nouns. The script does this automatically (`_classify_target_class`); doing it by hand is just reading the signals:

| Signal | Likely target class | Seedless nouns |
|---|---|---|
| PROSITE/BLAST text: glucagon/secretin/opioid/chemokine/neuropeptide… | `gpcr_ligand` | receptor |
| text: natriuretic/guanylin | `guanylyl_cyclase_ligand` | receptor, guanylate cyclase |
| text: interleukin/interferon/growth factor/leptin | `cytokine_or_growth_factor` | receptor |
| text: conotoxin/scorpion/sodium-potassium-calcium channel | `ion_channel_toxin` | channel, receptor |
| text: kunitz/protease inhibitor/serpin | `protease_inhibitor_or_substrate` | protease, peptidase |
| **RGD** motif in sequence, or text: integrin/disintegrin | `integrin_ligand` | integrin |
| text: defensin/cathelicidin/antimicrobial | `antimicrobial` | (membrane-acting; often no single protein target) |
| cysteine-rich short peptide, no named family | `ion_channel_toxin` (disulfide toxin/knottin) | channel, receptor, protease |
| nothing specific | `unknown` | receptor, enzyme, channel, transporter |

The class only **steers** enumeration (which resource, which nouns); phenotype + homology still drive the actual candidates. Record the class + the evidence that triggered it in the report.

---

## Phase 2 — Multi-route candidate generation (run routes in parallel)

Generate candidate **receptor/target** genes by **four independent routes**, then take the union (and note overlaps — overlap = stronger evidence). Routes 2A–2C are sequence/structure plausibility; Route 2D is phenotype plausibility. **The deorphanization candidate set is the intersection of phenotype-plausible and sequence/structure-plausible targets.**

### Route 2A — Homology (sequence → ligand family → receptor family)
```bash
python3 -m tooluniverse.cli run BLAST_protein_search '{"sequence":"<SEQUENCE>","database":"swissprot","expect":10.0,"hitlist_size":10}'
```
- Params: `sequence` (≥10 aa), `database` (`swissprot` curated+fast | `pdb` structures | `nr` comprehensive+slow), `expect`, `hitlist_size`.
- **Always start with `swissprot` + small `hitlist_size` (10).** Curated → hits return informative `hit_def` names (e.g. "Glucagon-like peptide 1") instead of raw accessions, and it's much faster than `nr`.
- **Runtime is the main gotcha.** Remote NCBI submit+poll: measured 62 s and 181 s on the *same* control query (server-load dependent). Treat anything under ~8 min as normal; **do not retry early.** Run this route **first/async** while other routes proceed. Requires Biopython; no key.
- **Reading it:** inspect `data.alignments[*].hit_def` and best `hsps[*].expect`/`identities`. Recurring family names in the hit list ARE the clue. Control: all 10 SwissProt hits were exendin/glucagon/GLP-1/GLP-2/pro-glucagon → glucagon/GLP/secretin ligand family.
- **Confirm family membership** by explicit alignment against hand-picked candidate ligands:
  ```bash
  python3 -m tooluniverse.cli run EBI_msa_align '{"sequences":">unknown\n<SEQ>\n>cand1\n<GLP1_SEQ>\n>cand2\n<GLUCAGON_SEQ>","method":"clustalo","sequence_type":"protein"}'
  ```
  Needs ≥2 sequences. Fast (EMBL-EBI). Returns `aligned_fasta` + `guide_tree_newick`. Read off the conserved receptor-binding motif (control: shared N-terminal `HxxGTFTSD` core).
- **Origin screen** (rule out antimicrobial-peptide origin):
  ```bash
  python3 -m tooluniverse.cli run AMPSphere_sequence_match '{"query":"<SEQUENCE>"}'
  ```
  Exact-membership check. `{"matched":false,"result":null}` = clean no-match (control). A hit suggests AMP origin rather than a hormone/receptor-ligand. `matched:false` is **informative, not a failure**.
- **NOTE:** homology surfaces the **ligand** family; mapping ligand-family → receptor genes is a downstream knowledge/lookup step (do it via Route 2C).

### Route 2B — Motif → binding domain (from Phase 1b/1c)
Carry the PROSITE family / ELM Pfam-domain hits from Phase 1 into Route 2C: a named ligand family or Pfam binding domain becomes the seed for receptor-family enumeration.

### Route 2C — Target-family enumeration + known pharmacology (keyless)
From ONE seed target (from a homolog, a known-drug class, or the motif hit), enumerate the **full candidate panel** (seed + close paralogs) using **independent resources that must agree**. The **general backbone is HGNC gene-family + InterPro** (work for any target class — kinases, channels, proteases, GPCRs alike); **GPCRdb** is an extra cross-check that applies only when the target is a GPCR.

**General family enumeration (any target class) — HGNC + InterPro:**
```bash
python3 -m tooluniverse.cli run HGNC_fetch_gene_by_symbol '{"symbol":"<SEED>"}'              # -> gene_group_id[], uniprot_ids[]
python3 -m tooluniverse.cli run HGNC_fetch_gene_family_members '{"gene_group_id":"<ID>"}'     # STRING id; the whole family
# InterPro: general route that does NOT depend on GPCRdb (e.g. the seed is a kinase/channel/protease)
python3 -m tooluniverse.cli run InterPro_get_entries_for_protein '{"accession":"<SEED_UNIPROT>"}'   # -> entries[]; take FAMILY-type (type=="family") IPR ids
python3 -m tooluniverse.cli run InterPro_get_proteins_by_domain '{"domain_id":"<IPRxxxxxx>","page_size":50,"reviewed_only":true}'  # -> proteins[] (accession + tax_id; MIXED organisms)
# proteins[] carry UniProt accessions, NOT gene symbols, and mix species -> filter tax_id=="9606", then batch-map:
python3 -m tooluniverse.cli run UniProt_search '{"query":"accession:Q00975 OR accession:O00555","limit":60}'   # -> results[].gene_names per accession
```
- **HGNC gene_group works for any family** — its own docs example is non-GPCR (`gene_group_id '366'` = the 56 'Ubiquitin specific peptidases'). This is why the script's family enumeration is **not** GPCR-locked. **Gotcha:** a gene can sit in several HGNC groups, including a **domain supergroup** (e.g. CACNA1B is in both 'Calcium voltage-gated channel alpha1 subunits' (10) and 'EF-hand domain containing' (~200)). The script **skips any group with > ~80 members** so the supergroup does not flood the panel — enumerate the bounded target family, not the domain supergroup.
- **InterPro** is the second general cross-check (live-verified): take the seed's **FAMILY-type** entries (`type=="family"`; skip `domain`/`homologous_superfamily` — those explode), list each family's members via `InterPro_get_proteins_by_domain`, **keep only human (`tax_id=="9606"`)** because InterPro mixes organisms, and **batch-map the accessions → gene symbols** with one `UniProt_search "accession:A OR accession:B …"` query (proteins have no gene field). Bounded (≤60). When the seed is in no curated HGNC group, InterPro **supplies** the panel. Control: `Q00975` (CACNA1B/Cav2.2) → `{CACNA1A…CACNA1S}` calcium-channel family, with each member cross-checked HGNC+InterPro.

**Known pharmacology (GtoPdb — general: GPCRs, ion channels, enzymes, transporters):**
```bash
python3 -m tooluniverse.cli run GtoPdb_search_ligands  '{"query":"exenatide"}'                 # -> ligandId 1135, name 'exendin-4'
python3 -m tooluniverse.cli run GtoPdb_search_targets  '{"query":"glucagon"}'                   # USE A SINGLE KEYWORD
python3 -m tooluniverse.cli run GtoPdb_get_interactions '{"gene_symbol":"GLP1R"}'               # query by TARGET, not ligandId
```
- **Gotchas:** multi-word phrases (`"glucagon-like peptide"`) return count=0 — use a single keyword (`"glucagon"`, `"secretin"`). `GtoPdb_get_interactions` indexed by **target**: `{"ligandId":1135}` returns EMPTY; always pass `gene_symbol`.

**Family slug from GPCRdb (GPCR targets ONLY — skip for channels/proteases/enzymes):**
```bash
python3 -m tooluniverse.cli run GPCRdb_get_protein  '{"protein":"GLP1R"}'                       # bare gene symbol auto-resolves -> family slug, e.g. 002_001_003_003
python3 -m tooluniverse.cli run GPCRdb_list_proteins '{"family":"002_001_003"}'                 # tight subfamily panel
python3 -m tooluniverse.cli run GPCRdb_list_proteins '{"family":"002_001"}'                     # broader class B1 (adds CALCR/CRF/PTH/PAC1/VPAC)
python3 -m tooluniverse.cli run GPCRdb_get_ligands  '{"protein":"GLP1R","max_results":8}'       # annotated ligands w/ activities, SMILES, source
```
- The slug is hierarchical: `002`=class B1/Secretin, `002_001`=class B1 receptors, `002_001_003`=glucagon-receptor subfamily, `..._003`=GLP1R itself. **Trim the slug** one level for the broader class; trim to subfamily for the tight panel.
- **Gotchas:** do NOT pass `"Class B1 (Secretin)"` (not a recognized key → 0); do NOT add `"operation":"list"` (breaks it); calling with NO args returns 1002 entries all with `family=None` (cannot slug-filter that dump). Valid human-readable keys for `protein_class`: `"class b1"`, `"class b"`, `"secretin"` (all → slug `002`).
- Control: `002_001_003` → exactly {GHRHR, GIPR, GLP1R, GLP2R, glucagon receptor, SCTR}.

**Cross-check via gene-family graph (HGNC):**
```bash
python3 -m tooluniverse.cli run HGNC_fetch_gene_by_symbol     '{"symbol":"GLP1R"}'              # -> gene_group_id:[269] 'Glucagon receptor family'
python3 -m tooluniverse.cli run HGNC_fetch_gene_family_members '{"gene_group_id":"269"}'        # -> {GCGR, GHRHR, GIPR, GLP1R, GLP2R, SCTR}
```
- **Gotcha:** `gene_group_id` MUST be a **STRING** (`"269"`); passing int `269` raises ToolValidationError despite the description saying it accepts an integer.
- **The two panels (GPCRdb slug ∩ HGNC group) should agree one-to-one.** Disagreement = re-check the seed.

### Route 2D — Phenotype anchor (OpenTargets; keyless)
Build a phenotype-relevant human target set to intersect with the sequence/structure candidates.
```bash
python3 -m tooluniverse.cli run OpenTargets_get_disease_id_description_by_name '{"diseaseName":"type 2 diabetes mellitus"}'   # -> hits[0].id = MONDO_0005148
python3 -m tooluniverse.cli run OpenTargets_get_associated_targets_by_disease_efoId '{"efoId":"MONDO_0005148"}'              # -> rows[]: target.approvedSymbol, target.id (Ensembl), score
```
- **Pick the DISEASE node, not a downstream symptom.** Control: `"type 2 diabetes mellitus"` → MONDO_0005148 → top-25 associated targets contain **GLP1R (0.767) AND GIPR** (recovers the true target family). By contrast `"insulin resistance"` → HP_0000855, whose target set does **NOT** contain the secretin-family receptors (correct biology — insulin resistance is downstream of incretin signaling). **Lesson: anchor on the disease the peptide's pathway treats, not the symptom.**
- Each row has `target.approvedSymbol`, `target.id` (Ensembl), `score`. **Intersect `approvedSymbol`s with the Route-2A/2C candidate list.** Overlap = phenotype-supported, sequence-plausible target = top candidates.
- For an unknown peptide, run for **each** plausible disease/tissue phenotype implicated by the bioassay readout or source organism's physiology, and take the union.

---

## Phase 3 — Cross-species reconciliation (keyless)

This is where "binds in species A but not B" gets resolved. Pull the candidate receptor's paralog and ortholog sets, then compare the **ligand-binding interface** across the assay species.

> **Automated:** `deorphanize_peptide.py` does the interface comparison for the top ≤3 candidates — it resolves the human + assay-species (+ optional `--source-species`) ortholog sequences via UniProt and aligns them with `EBI_msa_align`, printing per-pair % identity and substitution counts (`x-species GIPR: human_vs_assay 92.1% id (34 subs)`). The manual calls below are the reference for running, extending, or debugging that step, and for the **paralog** disambiguation (which the script leaves to the HGNC family panel).

**Paralogs (disambiguate which family member is the real target):**
```bash
python3 -m tooluniverse.cli run EnsemblCompara_get_paralogues '{"gene":"GLP1R","species":"homo_sapiens"}'
```
- Returns `data[]` of {source_gene, paralogue_gene (ENSG), paralogue_protein (ENSP), paralogy_type, taxonomy_level}. **Output is Ensembl IDs only — map ENSG→symbol downstream** (use `tooluniverse:translate-id` or an HGNC/Ensembl resolver).
- Control: recovered GCGR/GLP2R/SCTR; GIPR was a *deeper* paralog not in the immediate list but recovered by the Route-2D phenotype anchor → **use the UNION of paralog + phenotype evidence.**

**Orthologs (the core of "binds in A not B"):**
```bash
python3 -m tooluniverse.cli run EnsemblCompara_get_orthologues '{"gene":"GLP1R","species":"homo_sapiens"}'
# optionally restrict: add "target_species":"mus_musculus"
```
- Returns {target_species, target_gene, target_protein (ENSP), homology_type, taxonomy_level, method}. Control: 133 orthologs / 122 species; mouse + rat are `ortholog_one2one`.
- **Pull the human vs assay-species `target_protein` (ENSP) and align them at the peptide-binding interface** (feed both sequences to `EBI_msa_align`). Interface substitutions explain species-specific binding — this is the mechanistic answer to "active in human assay, not mouse."

**Confidence cross-check (Alliance):**
```bash
python3 -m tooluniverse.cli run Alliance_get_gene_orthologs '{"gene_id":"HGNC:4324","stringency":"all","limit":50}'
```
- **`gene_id` MUST be a prefixed Alliance ID** (`HGNC:4324` = GLP1R), not a bare symbol — resolve the symbol to HGNC first (`HGNC_fetch_gene_by_symbol`).
- Adds per-ortholog `methods[]` count (confidence), `stringency` tier, `has_disease_annotations`/`has_expression_annotations` flags. Control: mouse Glp1r (MGI:99571) + rat Glp1r (RGD:2703), each via 10 methods. Use `stringency:"stringent"` (default) to trim; `"all"` for distant homologs.

**Gotcha:** `EnsemblCompara_get_gene_tree` returned an empty tree (members=[], tree_id=null) for GLP1R despite status success — **do not rely on gene_tree** for clade grouping; use `get_paralogues` + the phenotype anchor instead.

---

## Phase 4 — Narrowing & ranking

Reduce the union candidate set to a ranked shortlist (**target ≤15** before any co-folding). Score each candidate on:

1. **Sequence/structure plausibility** — appears in BLAST hits / PROSITE family / ELM Pfam-domain map / GPCRdb-HGNC family panel. (Strongest: present in ≥2 of these.)
2. **Phenotype plausibility** — appears in the OpenTargets associated-target set for the relevant disease (Route 2D). Record the `score`.
3. **Known pharmacology cross-check** — does GtoPdb already list peptide ligands for this receptor (`GtoPdb_get_interactions {"gene_symbol":...}`)? Existing peptide ligands of the same family raise prior plausibility.
4. **Cross-species consistency** — is the receptor conserved (clean `ortholog_one2one`) in the assay species, and does the interface match? A receptor that is *absent or interface-diverged* in the assay species explains a negative binding result and **stays on the list** rather than being dropped.
5. **Target-engagement context (soluble candidates only)** — `ProteomicsDB_get_protein_meltome {"gene_symbol":...}` returns the candidate's thermal proteome profiling (TPP) melting curves. Presence in the meltome means it is a soluble protein with a measurable Tm; if the lab can run CETSA/TPP, a peptide-induced **Tm shift directly confirms target engagement** (the strongest experimental cross-check). NOTE: membrane GPCRs are absent from the meltome (returns 0 curves) — this signal applies to soluble candidates (kinases, enzymes), not the class-B GPCR panel.

**Ranking rule:** sort by (sequence/structure plausibility tiers) then (phenotype score), then by **how many independent family resources agree** (HGNC + InterPro + GPCRdb), and **explicitly promote paralogs / phenotype-shared receptors when the hypothesized target tested negative.** The non-binding result against the hypothesized target is itself evidence that re-ranks the panel.

> **Multi-class note (live-verified across GPCR, ion-channel, RTK, cytokine-receptor and protease seeds):** some HGNC groups are loose/broad — a protease seed (MMP9, CTSK) can pull a 35–46-gene panel spanning several protease sub-families, whereas an RTK (EGFR → {EGFR, ERBB2/3/4}) or channel (CACNA1B → the 10 CACNA1x) gives a tight one. For the loose cases the **HGNC∩InterPro intersection is the high-confidence tight core** (e.g. the 11 matrix metallopeptidases within MMP9's 46-gene panel), so a member corroborated by **both** resources outranks an HGNC-only loose-group member. The supergroup cap (skip HGNC groups >80, e.g. 'CD molecules' 394, 'Ig-like domain containing' 101, 'EF-hand' ~200) keeps these panels from exploding while preserving legitimate large families (interleukin receptors ~41).

Keep the shortlist to ≤15 (ideally ≤8) before Phase 5 — co-folding is slow and key-gated.

---

## Phase 5 — STRUCTURAL CONFIRMATION via co-folding (OPTIONAL, key-gated)

> **This phase is the only key-gated step and is OPTIONAL.** Everything above already produces a defensible ranked shortlist. Use co-folding to *confirm/rank* the top candidates structurally — never as a gate on producing a report. Requires `NVIDIA_API_KEY`. **Narrow to ≤15 (ideally ≤8) candidates first** — each co-fold is slow.

For each shortlisted receptor, co-fold the peptide with the receptor's ectodomain/full sequence and rank by **interface confidence (ipTM / interface pLDDT)**:

- `NvidiaNIM_boltz2` — peptide–protein complex prediction (preferred for ranking).
- `NvidiaNIM_alphafold2_multimer` — classic multimer co-fold; rank by interface ipTM.
- `NvidiaNIM_openfold3` — alternative co-fold backend.

Inputs are the **peptide sequence** + each candidate **receptor protein sequence** (pull receptor sequences from `GPCRdb_get_protein` `sequence` field, or the ortholog `target_protein` ENSP for the assay species). **Load the exact schema with ToolSearch before calling** (`select:NvidiaNIM_boltz2`, etc.) — these are deferred/key-gated and will error if called without their schema.

**Interpretation:** the candidate with the **highest interface ipTM / interface pLDDT** at the peptide-binding pocket is the top structurally-supported target. Run the co-fold for **both the human and assay-species ortholog** of the leading candidate to confirm the cross-species binding difference structurally (a drop in interface ipTM for the mouse ortholog mechanistically explains "binds human, not mouse").

If `NVIDIA_API_KEY` is unset, **skip Phase 5 and report the shortlist with its Phase 1–4 evidence**, clearly flagging that structural confirmation was not performed.

### Academic-free alternative (no NVIDIA key): ClusPro peptide docking

If you have a **free academic ClusPro account** (set `CLUSPRO_USERNAME` + `CLUSPRO_API_SECRET`) and the candidate receptor has a solved **PDB structure**, submit a native peptide–protein docking job instead of co-folding:

`ClusPro_submit_peptide_docking {"receptor_pdb_id": "<4-letter PDB>", "peptide_sequence": "<SEQ>", "peptide_motif": "<motif, optional>"}`

- **Which PDB?** `deorphanize_peptide.py` already prints a `ClusPro-ready PDB for <GENE>: <PDBID>` line for each top candidate (resolved keyless via `PDBeSIFTS_get_best_structures` from the candidate's UniProt accession). Use that id directly, or run `PDBeSIFTS_get_best_structures {"uniprot_accession":"<acc>"}` yourself to pick a higher-coverage/resolution entry.

It returns a ClusPro **job id** — docking is asynchronous, so retrieve clustered poses + scores from your ClusPro results page later (hours). Best for **short peptides (≤~30 residues)** against a receptor with a solved structure. Use this as the academic-free structural path when no NVIDIA key is available; the co-folding backends above remain preferred for direct interface-ipTM ranking and for receptors that have only a sequence (no PDB). For a **cyclic/non-ribosomal** peptide, prefer `cofold_screen.py --backend boltz2 --cyclic` (ClusPro peptide mode assumes a linear peptide).

---

## Phase 6 — Ranked shortlist report (evidence tiers + wet-lab recommendation)

Produce a report (no extra files — return it inline) with:

1. **Peptide characterization summary** — length, MW, pI, GRAVY, instability, PROSITE/ELM signature(s), non-canonical/cyclic flag, fold confidence (if run).
2. **Ranked candidate target table**, one row per receptor, columns:
   - Gene symbol + accession (UniProt / Ensembl / HGNC).
   - Evidence tier (see below).
   - Routes that surfaced it (BLAST family / PROSITE / GPCRdb+HGNC family / OpenTargets phenotype / paralog).
   - OpenTargets phenotype score (if any).
   - Known-pharmacology note (GtoPdb peptide ligands present?).
   - Cross-species status (conserved one2one? interface % identity in assay species?).
3. **Cross-species reconciliation note** — for the lead candidate, the human-vs-assay-species (-vs-source-species) interface comparison and what it predicts for the observed "binds A not B."
4. **Recommended wet-lab validation** — e.g. binding/competition assay against the top ≤3 candidates (and their assay-species orthologs), radioligand-displacement using the known family antagonist (GtoPdb-listed), or cAMP/β-arrestin functional assay for class-B GPCR candidates.

**Evidence tiers:**
- **Tier 1 (strong):** surfaced by ≥2 independent sequence/structure routes **AND** present in the phenotype anchor **AND** (if Phase 5 run) top interface ipTM.
- **Tier 2 (moderate):** surfaced by 1 sequence/structure route AND phenotype-supported, OR by ≥2 sequence routes without phenotype support.
- **Tier 3 (weak / hypothesis):** single-route only (e.g. a deep paralog or a phenotype-only hit not corroborated by sequence/structure).

Always state which evidence is **keyless/validated** vs **key-gated (co-fold not run)**, and flag any candidate that is a **negative against the originally hypothesized target** so the reader understands the deorphanization re-ranking.

---

## Fallback Chains

- **Physicochemical:** `PepCalc_peptide_properties` ⇄ `ProtParam_calculate` (run both; if one fails, the other still gives pI/MW). ProtParam additionally gives instability/GRAVY/charge.
- **Signature/family ID:** `ScanProsite_scan_protein` → `PROSITE_get_entry`. If no PROSITE hit, fall to ELM: `ELM_list_classes` (regex match) → `ELM_get_interaction_domains` (→ Pfam binding domain).
- **Homology:** `BLAST_protein_search` (swissprot) → if down/too slow, `EBI_msa_align` against a hand-picked candidate-ligand panel (lightweight family-membership test). `AMPSphere_sequence_match` is only an exact-match AMP screen, not a homology search.
- **Receptor-family enumeration:** `GPCRdb_get_protein`→`GPCRdb_list_proteins` (slug) **and** `HGNC_fetch_gene_by_symbol`→`HGNC_fetch_gene_family_members` (group id, STRING). Use both; intersect. `GtoPdb_search_targets`/`GtoPdb_get_interactions` add known-pharmacology grounding.
- **Phenotype anchor:** `OpenTargets_get_disease_id_description_by_name`→`OpenTargets_get_associated_targets_by_disease_efoId`. DisGeNET (`DisGeNET_get_disease_genes`, `DisGeNET_get_gda`) is **KEY-GATED** (`DISGENET_API_KEY`) — skip unless configured. `CTD_get_gene_diseases` is **structurally unavailable** (RENCI CTD mirror has no gene→disease edges) — do not use for the reverse anchor.
- **Cross-species:** `EnsemblCompara_get_orthologues`/`get_paralogues` **and** `Alliance_get_gene_orthologs` (prefixed gene_id). Do **not** use `EnsemblCompara_get_gene_tree` (returns empty tree for GLP1R).
- **ID mapping (ENSG→symbol):** EnsemblCompara/OpenTargets return Ensembl IDs; resolve with `tooluniverse:translate-id` before intersecting with symbol-based panels.
- **Ortholog sequences (for the interface alignment):** `UniProt_search {"query":"gene:<SYM>","organism":"<common name>"}` → `UniProt_get_sequence_by_accession`. The script does this automatically; the GPCRdb entry-name path is unreliable across species (its suffixes are common names like `_mouse`, not the `mus_musculus` token). **Gotcha:** UniProt_search `organism` takes a **common name** (`"human"`, `"mouse"`), NOT a taxid — `"9606"` errors. When UniProt is transiently down (`RemoteDisconnected`), seedless derivation and the InterPro accession→symbol map yield nothing; the run degrades to HGNC family + phenotype (still functional).
- **Structure (optional):** keyless `ESMFold_predict_structure` for the monomer; key-gated `NvidiaNIM_boltz2` / `NvidiaNIM_alphafold2_multimer` / `NvidiaNIM_openfold3` for the **complex** co-fold confirmation, or academic-free `ClusPro_submit_peptide_docking` (needs a solved PDB; `PDBeSIFTS_get_best_structures` resolves one). If no key at all, report without Phase 5.

---

## NVIDIA NIM / runtime notes

- **Co-folding is key-gated AND slow.** `NvidiaNIM_boltz2`, `NvidiaNIM_alphafold2_multimer`, `NvidiaNIM_openfold3`, `NvidiaNIM_esmfold`, `NvidiaNIM_esm2_650m` all require `NVIDIA_API_KEY`. Configure via `tooluniverse:setup-keys` if you want Phase 5.
- **Co-fold argument shapes** (the script builds these — documented here for manual calls): boltz2 → `{"polymers":[{"molecule_type":"protein","sequence":<pep>},{...receptor}]}` (add `"cyclic":true` to the peptide polymer for a cyclic peptide); alphafold2_multimer → `{"sequences":[<pep>,<receptor>]}`; openfold3 → `{"inputs":[{"input_id":"complex","molecules":[{"type":"protein","sequence":<pep>},{"type":"protein","sequence":<receptor>}]}]}` (ONE input, both chains in `molecules` — two separate inputs would be two monomer predictions, not a co-fold).
- **Narrow to ≤15 candidates (ideally ≤8) before any co-fold.** Each peptide–receptor co-fold is minutes-scale; co-folding a 25-receptor panel is wasteful. Phases 1–4 exist precisely to shrink the panel first.
- **BLAST is keyless but variable-runtime** (62 s–181 s observed on the control; documented up to 30 min on `nr`). Run it **first/async**; never abort before ~8 min.
- **ESMFold (keyless)** ~30–60 s for a ~40-mer; fine to run inline. Use it as cheap monomer evidence, not as a complex predictor.
- Schemas for the NIM/co-fold tools are **deferred** — call `ToolSearch` with `select:NvidiaNIM_boltz2` (etc.) to load the schema before invoking, or they error with InputValidationError.

---

## Worked example A — exendin-4 → GLP1R (control; recovers the class-B family)

**Input:** `HGEGTFTSDLSKQMEEEAVRLFIEWLKNGGPSSGAPPPS` (exendin-4, 39 aa, *Heloderma* venom). Hypothesized/known target: GLP1R.

1. **Characterization (Phase 1):** PepCalc + ProtParam → pI ~4.4 (agree), MW ~4.19 kDa, stable (instability 12.9), GRAVY −0.69. ESMFold mean pLDDT 0.85 (confident 39-mer).
2. **Motif (Phase 1b):** `ScanProsite_scan_protein` → single hit **PS00260** (res 1–23); `PROSITE_get_entry(PS00260)` → *"Glucagon / GIP / secretin / VIP family signature."* **→ class B1 GPCR ligand family.**
3. **Homology (Route 2A):** `BLAST_protein_search` (swissprot) → all 10 hits exendin/glucagon/GLP-1/GLP-2/pro-glucagon (self-hit Exendin-4 E=3.5e-22, 39/39). `EBI_msa_align` vs human GLP-1 + glucagon → shared N-terminal `HxxGTFTSD` core. `AMPSphere_sequence_match` → clean no-match (not an AMP).
4. **Receptor family (Route 2C):** GtoPdb `glucagon`→{GLP-1R, GLP-2R, glucagon R}, `secretin`→SCTR; `exenatide`→ligand 1135 'exendin-4'. GPCRdb GLP1R→slug `002_001_003_003`; `002_001_003`→{GHRHR, GIPR, GLP1R, GLP2R, glucagon R, SCTR}. HGNC GLP1R→group **269** 'Glucagon receptor family'→{GCGR, GHRHR, GIPR, GLP1R, GLP2R, SCTR}. **GPCRdb and HGNC panels agree.**
5. **Phenotype (Route 2D):** `type 2 diabetes mellitus`→MONDO_0005148→associated targets include **GLP1R (0.767) and GIPR**. (`insulin resistance`→HP_0000855 does NOT contain the family — symptom node, correct biology.)
6. **Cross-species (Phase 3):** EnsemblCompara paralogues recover GCGR/GLP2R/SCTR (GIPR via phenotype); orthologues → 133/122 species, mouse+rat `ortholog_one2one`; Alliance confirms mouse/rat Glp1r each via 10 methods.
7. **Result:** intersection of all routes = **GLP1R + GCGR/GIPR/GLP2R/SCTR** (class B1 / secretin family). The true target GLP1R is **Tier 1** (≥2 sequence routes + PROSITE family + phenotype score 0.767). Optional Phase 5 co-fold would rank GLP1R top by interface ipTM. **The correct receptor family is recovered with zero target knowledge and (except optional co-fold) zero API keys.**

---

## Worked example B — anti-insulin-resistance peptide that does NOT bind GLP1R in mouse

**Scenario (the real user case):** A peptide produces an **anti-insulin-resistance / metabolic phenotype**, was *hypothesized* to act via **GLP1R**, but in a **mouse** binding/functional assay it **does not bind GLP1R**. Goal: surface the alternative class-B / metabolic receptors that could be the real target — without guessing.

How this skill drives it (no target assumed from the name):

1. **Characterize + motif (Phase 1):** PepCalc/ProtParam for properties; `ScanProsite_scan_protein` → resolve every `PSxxxxx` with `PROSITE_get_entry`. If it again hits the glucagon/GIP/secretin/VIP signature (PS00260), the peptide is a **class-B1 ligand-family** member — which says "a secretin-family receptor," **not specifically GLP1R**. If no PROSITE family, fall to ELM regex → Pfam binding domain.
2. **Homology (Route 2A):** BLAST swissprot — if the top hits skew toward **GIP / glucagon / GLP-2 / secretin** rather than GLP-1, that *re-weights* the candidate panel toward GIPR/GCGR/GLP2R/SCTR. `EBI_msa_align` against GLP-1 vs GIP vs glucagon shows which family member the peptide's binding motif most resembles.
3. **Receptor family (Route 2C):** seed from whichever family member homology favored; GPCRdb slug + HGNC group **269** enumerate the **full class-B1/glucagon-receptor panel** {GLP1R, GCGR, GIPR, GLP2R, SCTR, GHRHR}. **All of these are now explicit candidates** — the hypothesized GLP1R is just one of them.
4. **Phenotype anchor (Route 2D):** `type 2 diabetes mellitus` → MONDO_0005148 → the associated-target set contains **GLP1R AND GIPR** (and other metabolic targets). Because the phenotype is metabolic, **GIPR is strongly phenotype-supported** even though the peptide failed against GLP1R. Intersect with the family panel → **GIPR (and GCGR) rise as the leading alternative targets.**
5. **Cross-species reconciliation (Phase 3) — the crux of "doesn't bind in mouse":** pull `EnsemblCompara_get_orthologues` for **each surviving candidate** (GLP1R, GIPR, GCGR…) restricted to `mus_musculus`, get the mouse `target_protein` (ENSP), and `EBI_msa_align` human vs mouse at the **ligand-binding interface** (the script automates this and also takes `--source-species` to add the organism where binding WAS observed, for a 3-way comparison). Two possible mechanistic answers, both produced by tools, not guessed:
   - The peptide's real target is a **paralog (e.g. GIPR/GCGR)** that the GLP1R assay never tested — promoted by phenotype + homology re-weighting.
   - OR the target **is** a family member but the **mouse ortholog's interface has diverged** from human at the binding pocket (interface substitutions in the alignment), explaining a human-active / mouse-negative result. Confirm with Alliance ortholog confidence (`methods[]`).
6. **Narrow + (optional) co-fold (Phases 4–5):** rank the panel by sequence/structure + phenotype + pharmacology + cross-species consistency. If `NVIDIA_API_KEY` is set, co-fold the peptide with **GLP1R, GIPR, GCGR (human and mouse)** via `NvidiaNIM_boltz2` and rank by interface ipTM — a high human-GIPR / low mouse-GLP1R interface score would structurally confirm both "real target = GIPR" and "GLP1R interface diverged in mouse."
7. **Report (Phase 6):** ranked shortlist with the **GLP1R negative flagged**, GIPR/GCGR promoted to Tier 1–2 with their phenotype scores and cross-species interface notes, and a wet-lab recommendation: binding/competition + cAMP assays against **GIPR and GCGR (human + mouse orthologs)**, using the GtoPdb-listed family antagonists as controls.

**Takeaway:** the negative GLP1R result is not a dead end — by anchoring on PHENOTYPE × SEQUENCE/STRUCTURE plausibility and reconciling across species, the skill surfaces the **paralog / interface-diverged** alternatives (GIPR, GCGR, …) as the testable real-target hypotheses, every one of them backed by a recorded tool result rather than a name-level guess.

---

## Worked example C — ω-conotoxin → ion channel (NON-GPCR; demonstrates generality)

**Input:** `CKGKGAKCSRLMYDCCTGSCRSGKC` (ω-conotoxin MVIIA / ziconotide, 25 aa, *Conus magus* venom). Phenotype: analgesia / severe chronic pain. **The target is an ion channel, not a GPCR** — this case exists to show the pipeline is not GPCR-only.

1. **Characterize + classify (Phase 1 + 1e):** PepCalc/ProtParam → small, basic, **6 cysteines / 25 aa**. The target-class router sees the cysteine-rich short peptide (and, if BLAST has run, "omega-conotoxin" in the hit names) → **`ion_channel_toxin`**, seedless nouns `channel, receptor, protease`. **Crucially it does NOT default to "receptor"-only enumeration.**
2. **Homology (Route 2A):** `BLAST_protein_search` (swissprot) → hits are conotoxins / channel-blocking toxins; `AMPSphere_sequence_match` → not an AMP.
3. **Target-family enumeration (Route 2C, GENERAL path — no GPCRdb):**
   - Seedless derives keywords (`omega`, `conotoxin`, `calcium`) × nouns (`channel`) → `UniProt_search "calcium channel"` → seeds **CACNA1B** (Cav2.2, the real target) and its relatives.
   - `HGNC_fetch_gene_by_symbol CACNA1B` → gene group **"Calcium voltage-gated channel alpha1 subunits"** → `HGNC_fetch_gene_family_members` → {CACNA1A, CACNA1B, CACNA1C, CACNA1D, CACNA1E, …}. **GPCRdb returns nothing (correct — not a GPCR); InterPro cross-checks the same calcium-channel family.** The "two general resources agree" principle holds with HGNC + InterPro instead of HGNC + GPCRdb.
4. **Phenotype anchor (Route 2D):** `neuropathic pain` / `chronic pain` → OpenTargets associated targets include **CACNA1B** (and CACNA2D1, the gabapentinoid target) → intersect with the channel family → CACNA1B is phenotype-supported.
5. **Cross-species (Phase 3):** ortholog interface alignment of CACNA1B across human/assay species — conotoxin selectivity is famously species- and subtype-specific, so interface divergence is the expected lever for any "binds in A not B".
6. **Narrow + report (Phases 4–6):** ranked shortlist led by **CACNA1B (N-type Cav2.2)**, Tier 1 (channel family + pain phenotype), with electrophysiology (not cAMP) as the class-appropriate validation assay.

**Takeaway:** with the target-class router selecting channel/HGNC/InterPro enumeration instead of GPCRdb, the **same pipeline** recovers a non-GPCR ion-channel target — confirming the skill covers the broad class "peptide → any protein target", not only GPCR ligands.
