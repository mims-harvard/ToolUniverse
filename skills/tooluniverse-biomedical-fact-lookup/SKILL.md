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
| **mouse phenotype** gene set (MGI / MP:xxxxx, e.g. "increased carcinoma incidence") | `MGI_search_genes` → `MGI_get_phenotypes` | for **each** candidate gene: search → take the `MGI:` id → `MGI_get_phenotypes`; the matching gene is the one whose `phenotype_statement` list contains the phenotype the question names (see interpretation note) |
| **gene genomic location** (Ensembl band, e.g. chr7q34) | `Ensembl_*` / `NCBIDatasets_get_gene_by_symbol` | resolve each option, compare cytoband/coordinates |
| **variant / sequence** pathogenicity ("which variant/sequence is pathogenic *or* benign per ClinVar") | (only when genuinely unsure) `annotate_variant_multi_source`, `VEP_predict_pathogenicity`, `UniProt_get_disease_variants_by_accession` | **Be efficient — do NOT query every option (that causes timeouts).** Identify the protein once, find each option's single substitution, and reason about the specific residue changes directly; the base model is usually reliable on well-characterized ClinVar variants. Make at most ONE targeted tool call to resolve a truly uncertain variant. **Watch the question's polarity** (benign vs pathogenic): for "most likely benign", a common/reference-matching variant is the answer; for "most likely pathogenic", a rare damaging one is. |
| **drug / compound** target, MoA, approval | `ChEMBL_*`, `OpenFDA_*`, `GtoPdb_*`, `PubChem_*` | resolve drug, query the relation |
| **protein** function / domain / sequence | `UniProt_*` | resolve accession, read annotation |

When unsure which tool wraps a database, search the catalog by the *relation* (e.g. "gene disease association", "gene set members"), not the brand name — ToolUniverse usually already has it.

## MSigDB set-name conventions (the most common LAB-Bench pattern)

ToolUniverse's `MSigDB_*` tools cover several collections that LAB-Bench questions are built from. Get the set name right:

- **C6 oncogenic signatures** — use the exact set name quoted in the question (e.g. `ATM_DN.V1_DN`, `KRAS.600_UP.V1_UP`).
- **C3:MIR:MIRDB** (miRDB v6.0 predicted miRNA targets) — `MIR<number>_<3P|5P>` (e.g. `MIR186_3P`, `MIR675_3P`). This *is* miRDB; do not say "no access to miRDB".
- **C3:TFT:GTRD** (GTRD TF target genes) — `<TF>_TARGET_GENES` (e.g. `PGM3_TARGET_GENES`). This *is* GTRD.
- **Hallmark** — `HALLMARK_<NAME>`.

`MSigDB_get_gene_set_members` (operation `get_gene_set`) returns `{genes:[...]}`; `MSigDB_check_gene_in_set` (operation `check_gene_in_set`, param `gene`) returns `{is_member: bool}`.

## Gene–disease "in database X but NOT database Y" recipe

These questions (e.g. "which gene is associated with disease D according to DisGeNet but **not** OMIM?") need a *differential* lookup, not a single query:

1. Resolve D to a UMLS CUI (`umls_search_concepts`).
2. **OMIM side:** `OMIM_search`/`OMIM_get_gene_map` for D → the set of OMIM-causal genes.
3. **DisGeNet side:** `DisGeNET_get_disease_genes(disease=CUI)` (curated). Note the academic key is **curated-only**; DisGeNet *also* includes a text-mined tier the key can't see.
4. **Text-mined fallback** (covers DisGeNet's text-mined tier when curated is empty): `PubTator3_LiteratureSearch("<GENE> <disease>")` or `PubTator3_GetEntityRelations(e1="@GENE_<sym>", type="associate")` — a gene with literature co-occurrence to D but **absent from OMIM-for-D** is the "in DisGeNet but not OMIM" answer.
5. **Elimination:** rule out options that ARE OMIM-causal for D; among the rest, pick the one with a DisGeNet/text-mined association. If exactly one option is non-OMIM and has any association signal, that is the answer.
6. Only answer "Insufficient information" if no option has any association in any source. If the gold gene appears in neither curated DisGeNet, OMIM, nor PubTator literature, it may rely on a DisGeNet-internal text-mined signal the academic tier can't reach — say so honestly rather than guessing.

## Mouse-phenotype matching (MGI)

`MGI_get_phenotypes` returns a list of `phenotype_statement` strings per gene. To answer "which gene is annotated to phenotype P" (e.g. an MP term like *increased carcinoma incidence*), query each candidate gene and pick the one whose statements include a phrase matching P (the statements are human-readable, e.g. "increased incidence of carcinoma", "tumor"). Match on the phenotype concept, not an exact MP id string. If several match, prefer the most specific statement.

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
