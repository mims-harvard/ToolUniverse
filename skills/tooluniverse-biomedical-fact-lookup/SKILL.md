---
name: tooluniverse-biomedical-fact-lookup
description: "Answer biomedical FACTUAL / recall / multiple-choice questions by querying ToolUniverse database tools instead of answering from memory. Triggers on any 'which gene/drug/variant/disease/pathway/miRNA/TF...' lookup, any question phrased 'according to <database>' (DisGeNet, OMIM, MSigDB, miRDB, GTRD, MGI, Ensembl, ClinVar, ChEMBL, OpenTargets, Reactome, GtoPdb, UniProt...), and multiple-choice biology/medicine knowledge questions where one option must be verified against an authoritative source. NOT for analyzing user-supplied data files (CSV/VCF/h5ad → use the data-analysis router) and NOT for open-ended literature synthesis. Use whenever a single correct answer exists in a public biomedical database and could be looked up rather than guessed."
when_to_use: "A factual biomedical question has a single database-checkable answer — especially MCQ of the form 'which of the following X is associated-with / contained-in / a-target-of / located-at Y according to <database>'. Reach for this before answering from memory."
---

# Biomedical Fact Lookup (tool-grounded answering)

Factual biomedical questions — "which gene is in set X", "which gene is associated with disease Y according to DisGeNet", "which gene has a TF binding site per GTRD" — have an authoritative answer in a public database. Guessing from memory is unreliable (≈chance on niche annotations); the matching ToolUniverse tool returns the ground truth.

## RULE ZERO: Look it up, never guess

If a question names a database, a gene set, or any annotation that lives in a database, you MUST query the tool before answering. Answering a "according to <database>" question from memory is a failure mode — these annotations (predicted miRNA targets, ChIP-seq binding, curated gene sets, disease associations) are exactly what models hallucinate. A tool-verified answer beats any recalled fact.

## Multiple-choice procedure

Most of these questions are MCQ with an "Insufficient information to answer the question." distractor. Do this:

1. **Parse** the question for: the **named database/collection**, the **anchor entity** (the gene set, disease, miRNA, TF, locus…), and the **candidate options**.
2. **Resolve** the anchor to the right tool + identifier (see Routing table).
3. **Query** the tool once to get the authoritative member list / association set.
4. **Check each option** against that result. Exactly one option should be supported.
5. **Answer** with that option's letter. Only choose "Insufficient information" if the tool genuinely returns nothing for a valid query (not because you skipped the query).

## Routing table — question pattern → tool

| Question mentions… | Tool(s) (verified) | How |
|---|---|---|
| a named **gene set** / **oncogenic signature** (MSigDB C6, e.g. `ATM_DN.V1_DN`) | `MSigDB_get_gene_set_members` | list members, check which option is in it |
| **miRNA target** "according to miRDB" (e.g. MIR186-3p) | `MSigDB_get_gene_set_members` (collection C3:MIR:MIRDB) | set name = `MIR<number>_<3P\|5P>`, e.g. `MIR186_3P` |
| **TF binding site / target** "according to GTRD" (e.g. PGM3) | `MSigDB_check_gene_in_set` (collection C3:TFT:GTRD) | set name = `<TF>_TARGET_GENES`, e.g. `PGM3_TARGET_GENES`; pass `gene` per option |
| **pathway / hallmark** membership | `MSigDB_get_hallmark_geneset`, `MSigDB_get_geneset` | `HALLMARK_<NAME>` or exact set name |
| **gene ↔ disease** association (DisGeNet, OpenTargets, OMIM) | `umls_search_concepts` → `DisGeNET_get_disease_genes`/`DisGeNET_get_gda`; `OpenTargets_*`, `MyDisease_get_disease`, `OMIM_search`; **text-mined fallback:** `PubTator3_LiteratureSearch` / `PubTator3_GetEntityRelations` (`e1=@GENE_<sym>`), `EPMC_get_text_mined_annotations` | DisGeNET needs a **UMLS CUI** (resolve via `umls_search_concepts` → `C0152200`, then `disease=C0152200`) + `DISGENET_API_KEY`. See the "in X but not Y" recipe below |
| **mouse phenotype** gene set (MP / MGI, e.g. "increased melanoma incidence") | `MSigDB_check_gene_in_set` (mouse M5, set `MP_<PHENOTYPE>`) — fall back to `MGI_search_genes` → `MGI_get_phenotypes` | **one call per option** against the `MP_*` set (e.g. `MP_INCREASED_MELANOMA_INCIDENCE`); the member is the answer. Only if the set name doesn't resolve, use the MGI per-gene route below |
| **gene genomic location** (Ensembl band, e.g. chr7q34) | `Ensembl_*` / `NCBIDatasets_get_gene_by_symbol` | resolve each option, compare cytoband/coordinates |
| **variant / sequence** pathogenicity ("which variant/sequence is pathogenic *or* benign per ClinVar") | (only when genuinely unsure) `annotate_variant_multi_source`, `VEP_predict_pathogenicity`, `UniProt_get_disease_variants_by_accession` | **Be efficient — do NOT query every option (that causes timeouts).** Identify the protein once, find each option's single substitution, and reason about the specific residue changes directly; the base model is usually reliable on well-characterized ClinVar variants. Make at most ONE targeted tool call to resolve a truly uncertain variant. **Watch the question's polarity** (benign vs pathogenic): for "most likely benign", a common/reference-matching variant is the answer; for "most likely pathogenic", a rare damaging one is. |
| **drug / compound** target, MoA, approval | `ChEMBL_*`, `OpenFDA_*`, `GtoPdb_*`, `PubChem_*` | resolve drug, query the relation |
| **which drug for this patient** (clinical vignette naming a modifier) | `FDA_*_by_drug_name` — pick the section by modifier | see "Drug choice for a described patient" below |
| **protein** function / domain / sequence | `UniProt_*` | resolve accession, read annotation |
| **protein localization / expression** "according to the Human Protein Atlas" | `HPA_get_subcellular_location`, `HPA_get_rna_expression_by_source`, `HPA_get_comprehensive_gene_details_by_ensembl_id` | pass the gene symbol — an **antibody ID such as `HPA073143` also works** and resolves to its target gene. **Report main *and* additional locations** — see below |

When unsure which tool wraps a database, search the catalog by the *relation* (e.g. "gene disease association", "gene set members"), not the brand name — ToolUniverse usually already has it.

### Human Protein Atlas — report both location fields

`HPA_get_subcellular_location` splits its answer in two, and the split is not
significance ranking:

```
main_locations       : ['Nucleoplasm']
additional_locations : ['Primary cilium', ..., 'Cytosol']
```

A question asking "what localization does this antibody show" wants the
locations HPA reports, which is **both lists** — answering from `main_locations`
alone drops real localizations and is a common way to be half-right (e.g.
answering "Nucleoplasm" where HPA reports "Nucleoplasm, Cytosol"). Use
`location_summary`, which already joins them, or read both fields.

Two further cautions:

- **Locations aggregate over cell lines.** HPA pools immunofluorescence across
  every line an antibody was tested in. If the question names one line (HEK293,
  U-2 OS), treat the list as the candidate set and say which line you are
  reporting for, rather than implying the aggregate is line-specific.
- **Per-cell-type RNA values are only published for enriched cell types.** HPA's
  machine-readable fields give specificity plus nTPM/nCPM for the cell types a
  gene is enriched in; a value for an arbitrary cell type is not exposed. If a
  question asks for one that is absent, say so instead of substituting the
  nearest available number — those differ by an order of magnitude.

## MSigDB set-name conventions (the most common LAB-Bench pattern)

ToolUniverse's `MSigDB_*` tools cover several collections that LAB-Bench questions are built from. Get the set name right:

- **C6 oncogenic signatures** — use the exact set name quoted in the question (e.g. `ATM_DN.V1_DN`, `KRAS.600_UP.V1_UP`).
- **C3:MIR:MIRDB** (miRDB v6.0 predicted miRNA targets) — `MIR<number>_<3P|5P>` (e.g. `MIR186_3P`, `MIR675_3P`). This *is* miRDB; do not say "no access to miRDB".
- **C3:TFT:GTRD** (GTRD TF target genes) — `<TF>_TARGET_GENES` (e.g. `PGM3_TARGET_GENES`). This *is* GTRD.
- **Hallmark** — `HALLMARK_<NAME>`.
- **Mouse M5 (MGI mammalian phenotype)** — `MP_<PHENOTYPE_IN_CAPS>` (e.g. "increased melanoma incidence" → `MP_INCREASED_MELANOMA_INCIDENCE`). These are **mouse** sets: the tools try human then mouse automatically, or pass `species: "mouse"` to skip the human miss. Prefer this over querying each gene's full MGI phenotype list.

`MSigDB_get_gene_set_members` (operation `get_gene_set`) returns `{genes:[...]}`; `MSigDB_check_gene_in_set` (operation `check_gene_in_set`, param `gene`) returns `{is_member: bool}`. Both report which `species` collection matched.

**Fetch the set once, not once per option.** A multiple-choice question asks about one set and 3-5 candidates, so `MSigDB_get_gene_set_members` answers all of them in a single call — compare the options against the returned list yourself. Reserve `MSigDB_check_gene_in_set` for a single-gene question, or when the set is too large to return comfortably.

## Gene–disease "in database X but NOT database Y" recipe

These questions (e.g. "which gene is associated with disease D according to DisGeNet but **not** OMIM?") need a *differential* lookup, not a single query:

1. Resolve D to a UMLS CUI (`umls_search_concepts`).
2. **OMIM side:** `OMIM_search`/`OMIM_get_gene_map` for D → the set of OMIM-causal genes.
3. **DisGeNet side:** `DisGeNET_get_disease_genes(disease=CUI)` (curated). Note the academic key is **curated-only**; DisGeNet *also* includes a text-mined tier the key can't see.
4. **Text-mined fallback** (covers DisGeNet's text-mined tier when curated is empty): `PubTator3_LiteratureSearch("<GENE> <disease>")` or `PubTator3_GetEntityRelations(e1="@GENE_<sym>", type="associate")` — a gene with literature co-occurrence to D but **absent from OMIM-for-D** is the "in DisGeNet but not OMIM" answer.
5. **Elimination:** rule out options that ARE OMIM-causal for D; among the rest, pick the one with a DisGeNet/text-mined association. If exactly one option is non-OMIM and has any association signal, that is the answer.
6. Only answer "Insufficient information" if no option has any association in any source. If the gold gene appears in neither curated DisGeNet, OMIM, nor PubTator literature, it may rely on a DisGeNet-internal text-mined signal the academic tier can't reach — say so honestly rather than guessing.

## Drug choice for a described patient (clinical vignette)

"Which of the following is most appropriate for this patient?" with a vignette
naming a **modifier** — hepatic or renal impairment, a Child-Pugh class, a
concomitant strong CYP3A4 inhibitor, pregnancy, an allergy or contraindication —
and several candidate drugs. These read like clinical-judgement questions, but
the modifier is doing all the work and the deciding fact is printed in each
candidate's FDA label. Answering from recall is the failure mode here: the
options are usually all plausible drugs for the condition, and only the label
separates them.

**1. Resolve every option brand → generic first.**
`FDA_get_active_ingredient_info_by_drug_name` on each option. Do this before any
reasoning, for two reasons: label lookups are keyed on the ingredient, and **two
options are sometimes the same drug** under a brand and a generic name. When
that happens neither can be the intended answer — they cannot be
distinguished — so it eliminates both and often decides the question outright.
Note the duplicate explicitly; it is also worth reporting as a benchmark defect.

**2. Look up only the section the modifier turns on.** One targeted call per
candidate beats pulling whole labels:

| The vignette says… | Read this section |
|---|---|
| hepatic impairment, Child-Pugh A/B/C, cirrhosis | `FDA_get_pharmacokinetics_by_drug_name` (hepatic-impairment subsection), then `FDA_get_dosage_and_storage_information_by_drug_name` for the adjustment. A Child-Pugh grading may sit in either of those or in contraindications, and some labels describe hepatic impairment without using the term at all — absence from one section is not absence from the label |
| renal impairment, CrCl/eGFR, dialysis | same pair — PK first, then dosage |
| "on a strong CYP3A4 inhibitor/inducer", any named co-medication | `FDA_get_drug_interactions_by_drug_name`; `FDA_get_clinical_pharmacology_by_drug_name` when the label states the metabolic pathway rather than the pairing |
| pregnancy, breastfeeding, "planning to conceive" | `FDA_get_pregnancy_or_breastfeeding_info_by_drug_name` (`FDA_get_teratogenic_effects_by_drug_name` when the question is about fetal harm specifically) |
| an allergy, a comorbidity that rules a drug out | `FDA_get_contraindications_by_drug_name`, then `FDA_get_boxed_warning_info_by_drug_name` |
| elderly / pediatric patient | `FDA_get_geriatric_use_info_by_drug_name` / `FDA_get_pediatric_use_info_by_drug_name` |
| the drug simply may not treat the condition | `FDA_get_indications_by_drug_name` |

The naming is regular — `FDA_get_<section>_by_drug_name` — so a section not listed
here can be found by searching the catalog for the section name rather than
guessing a tool name.

**3. Decide by elimination, and say what eliminated each option.** The intended
answer is normally the one candidate the modifier does *not* exclude:
contraindicated in hepatic impairment, requires an unavailable dose reduction,
interacts with the stated co-medication, or is not indicated for the condition.
Quote the label phrase that rules each option out — a vignette answer without a
cited label sentence is a guess wearing a citation.

**Do not over-query.** Resolve the ingredients (one call per option), then read
one section per remaining candidate. If the label is silent on the modifier for
every option, say so and answer on indication — do not keep pulling sections
hoping for a discriminator.

## Mouse-phenotype matching (MGI) — fallback only

Try the `MP_<PHENOTYPE>` MSigDB set first (above): it answers in one call per option and is the same MGI annotation. Use this per-gene route only when the set name does not resolve.

`MGI_get_phenotypes` returns a list of `phenotype_statement` strings per gene, **paginated** — a gene's matching statement is often on a later page, so a single page is not evidence of absence. To answer "which gene is annotated to phenotype P", query each candidate gene and pick the one whose statements include a phrase matching P (the statements are human-readable, e.g. "increased incidence of carcinoma", "tumor"). Match on the phenotype concept, not an exact MP id string. If several match, prefer the most specific statement.

## Computational procedures (when the answer is COMPUTED, not looked up)

Any question with a **single deterministic numeric/combinatorial answer** must be obtained by **RUNNING code**, never by estimating or doing it in your head. This covers sequence questions (ORF counts, restriction fragments/sizes, GC content, translation) **and** any other exactly-computable question — e.g. **genetics segregation / Mendelian or polyploid gamete ratios, combinatorial probabilities, stoichiometry, dosage/PK arithmetic, counting problems**. Mental arithmetic on these is the #1 avoidable error: the model reliably mis-counts or mis-multiplies. If a question reduces to "enumerate the cases / multiply the probabilities / count the objects", **write a short Python snippet, execute it, and report exactly what it returns** — even when the topic looks like a biology "reasoning" question, if the answer is a definite number, compute it rather than reason it out. Match the question's wording for conventions (which strand; linear vs circular; which cross/segregation model) and **state the convention you used** so the answer is auditable.

**Final-answer discipline (avoid "computed right, answered wrong").** After the code returns the value, map it back to the option letters **carefully and explicitly**: quote the computed value, then find the option that matches it exactly (for a set of fragment sizes, match the whole multiset; for a count, match the integer). A surprising number of misses are cases where the computation was correct but the wrong letter was selected — do not let this happen; re-read each option against the computed result before emitting `[ANSWER]`.

**Procedure: "how many ORFs encode proteins greater than N amino acids?"**

Read the phrasing literally. "How many ORFs … **in the DNA sequence** `<X>`" asks about the **single strand you were given** — count that strand only (3 frames), NOT both strands. Do **not** "helpfully" add the reverse complement on the reasoning that DNA is double-stranded: the question hands you one sequence string and asks what is *in it*, so the reverse strand is out of scope unless the question **explicitly** says "both strands" / "double-stranded" / "either strand" / "reverse complement". Adding the reverse strand by default is the single most common way these items are missed — resist it. Count **every distinct start (ATG) that reaches an in-frame stop**; overlapping/nested ORFs each count (two ATGs in the same frame before one stop = two ORFs). Length rule is **strict**: protein length in aa = (stop_index − start_index); keep those with `aa_len > N` for "greater than N". Report the number your code returns for the given strand — if you also computed a both-strands figure, do not let it override the single-strand answer the question asked for.

```python
from Bio.Seq import Seq

def count_orfs(dna, min_aa, both_strands=False):
    """Count ORFs (ATG..in-frame-stop) encoding a protein STRICTLY longer than min_aa.
    Counts every qualifying ATG, including nested/overlapping ORFs. Forward strand
    by default; set both_strands=True only if the question asks for both strands."""
    dna = "".join(dna.split()).upper()
    strands = [Seq(dna)]
    if both_strands:
        strands.append(Seq(dna).reverse_complement())
    n = 0
    for s in strands:
        for off in range(3):                       # three reading frames per strand
            trimmed = s[off: len(s) - (len(s) - off) % 3]
            prot = str(trimmed.translate())        # '*' marks stop codons
            i = 0
            while i < len(prot):
                if prot[i] == "M":                 # ATG
                    stop = prot.find("*", i)
                    if stop != -1 and (stop - i) > min_aa:
                        n += 1                      # count this ATG; do NOT jump past stop
                i += 1
    return n
# e.g. count_orfs(seq, 12) -> integer; report exactly that number.
```

**Procedure: restriction digest fragment count/sizes**

```python
# Count fragments after digesting with named enzyme(s).
# LINEAR DNA is the default (a plain sequence string): fragments = cuts + 1.
# Only use circular=True if the question says plasmid/circular.
from Bio.Seq import Seq
from Bio.Restriction import RestrictionBatch

def digest(dna, enzymes, circular=False):
    dna = "".join(dna.split()).upper()
    rb = RestrictionBatch(enzymes)            # e.g. ["EcoRI","BamHI"] or ["AluBI","MalI"]
    cut_positions = sorted(p for sites in rb.search(Seq(dna), linear=not circular).values() for p in sites)
    if not cut_positions:
        return 1, []                          # uncut: one fragment (linear or circular)
    n_frag = len(cut_positions) if circular else len(cut_positions) + 1
    return n_frag, cut_positions
```

If `RestrictionBatch` raises on an enzyme name (isoschizomer / rare supplier name), resolve it via the DNA-digest tool (which has a Biopython fallback) or map it to its recognition site, then re-run — do not fall back to guessing.

**Procedure: genetics segregation / gamete & progeny ratios (enumerate, don't recall)**

Genetics questions that hinge on a ratio — gamete frequencies, offspring genotype proportions, polyploid segregation — are exactly computable by **enumerating equally-likely allele combinations**. Do not recall a memorized ratio; derive it. For a parent carrying a multiset of alleles at a locus, gametes under random chromosome segregation are all equally-likely ways to draw the gamete's allele count from the parent's alleles; count genotype classes with `Counter` + `combinations`.

```python
from itertools import combinations
from collections import Counter

def gamete_ratio(alleles, gamete_size):
    """Genotype distribution of gametes under random segregation.
    e.g. tetraploid AAaa -> gametes carry 2 alleles: gamete_ratio(['A','A','a','a'], 2)."""
    classes = Counter("".join(sorted(c)) for c in combinations(alleles, gamete_size))
    return dict(classes)   # e.g. {'AA':1, 'Aa':4, 'aa':1}

def progeny_fraction(parent_alleles, gamete_size, target_gamete, selfing=True):
    """Fraction of progeny that are homozygous target (e.g. 'aa' gamete x 'aa' gamete -> aaaa)."""
    g = gamete_ratio(parent_alleles, gamete_size); tot = sum(g.values())
    p = g.get(target_gamete, 0) / tot
    return p * p if selfing else p   # selfing/self-cross: square the gamete frequency
# tetraploid AAaa: gamete_ratio(['A','A','a','a'],2) = {'AA':1,'Aa':4,'aa':1};
# recessive 'aa' gamete freq = 1/6, so aaaa progeny under selfing = (1/6)^2 = 1/36.
```

Interpret the enumerated ratio against the options (e.g. the scenario giving a 1:4:1 AA:Aa:aa gamete ratio maximizes the `aa` gamete and hence `aaaa` progeny). Report the computed fraction/ratio and pick the option matching it.

Interpretation: report the **exact value the code returns** (ORF count; fragment count/sizes as the whole multiset; longest-ORF length in nt or aa; gamete ratio / progeny fraction — exactly as the question asks). Always say which convention you applied (forward vs both strands; linear vs circular; segregation model) so the choice is auditable. If two readings are plausible, compute both and pick the one that matches the question's literal phrasing. **Then match the computed value back to the options explicitly before answering** (see final-answer discipline above).

## Interpretation

- A tool result listing the anchor's members/associations is authoritative — pick the option present in it.
- If a tool errors on a *name* (e.g. set not found), re-derive the name from the convention above before concluding "insufficient".
- "Insufficient information" is correct only when the authoritative tool returns an empty result for a well-formed query — not when a query was never attempted.

## Limitations (honest)

- **Key-gated sources**: `DisGeNET_*` and OMIM tools need `DISGENET_API_KEY` / OMIM key. Without a key, fall back to `OpenTargets_*` / `MyDisease_*` (keyless) and state the source used. If no keyless source can answer and the question is database-specific, this is a genuine "Insufficient information" case — say so.
- **Release mismatch**: a tool's snapshot of a database may differ slightly from the exact release a question cites; report the source and version when it matters.
- This skill grounds *factual* lookups. For computing over user data files, use the data-analysis router skills instead.
