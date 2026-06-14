---

name: tooluniverse-natural-product-dereplication
description: "Dereplicate a putative natural product and assign its chemical taxonomy. Use to answer \"is [compound] a known natural product\", \"what microbe/organism produces [compound]\", \"what chemical class is [compound]\", \"dereplicate this metabolite (by formula/exact mass/InChIKey/SMILES)\", or \"classify this molecule into ChemOnt\". Searches NPAtlas for known microbial natural products (producing organism + literature reference), assigns the ChemOnt kingdom→superclass→class→subclass hierarchy via ClassyFire, resolves systematic IUPAC names to structure via OPSIN, and cross-references identity in PubChem. NOT for general drug/compound identity or ADMET (use tooluniverse-chemical-compound-retrieval / tooluniverse-small-molecule-discovery) and NOT for metabolomics pathway/enrichment analysis (use tooluniverse-metabolomics skills)."
---

# Natural Product Dereplication & Chemotaxonomy

Decide whether a putative natural product is **already known**, identify the **microbe that produces it**, attach the **literature reference**, and assign its **ChemOnt chemical class**. This is the dereplication question every NP chemist and metabolomics analyst asks of a new feature: *"have we seen this before, and what makes it?"*

**LOOK UP DON'T GUESS**: Never assume an NPAID, producing organism, exact mass, or chemical class. Every identity, provenance, and taxonomy claim must come from a live tool call.

**Scope (microbial NPs only)**: NPAtlas covers natural products from **bacteria and fungi**. It does NOT cover plant, animal, or marine-invertebrate metabolites unless a microbial producer was reported. A "no NPAtlas hit" therefore means *not a known microbial NP* — it does not prove the molecule is novel in an absolute sense.

---

## Backing Tools (all keyless; verify before quoting)

| Tool | Input | Returns |
|------|-------|---------|
| `NPAtlas_search_compounds` | `name` / `inchikey` / `formula` / `smiles`, `limit` | list of {npaid, name, molecular_formula, molecular_weight, exact_mass, inchikey, smiles}. (origin_organism is `null` here — fetch the full record for provenance) |
| `NPAtlas_get_compound` | `npaid` (e.g. `NPA014588`) | full record incl. `origin_organism` (producing microbe + taxonomic lineage) and `origin_reference` (title/doi/journal/year) |
| `ClassyFire_classify_by_inchikey` | `inchikey` (full 27-char) | ChemOnt kingdom→superclass→class→subclass→direct_parent, molecular_framework, substituents. `classified:false` if not in cache |
| `OPSIN_name_to_structure` | `name` (systematic IUPAC) | smiles / inchi / inchikey. `parsed:false` for trade/trivial names |
| `PubChem_get_CID_by_compound_name` | `name` | `{IdentifierList:{CID:[...]}}` |
| `PubChem_get_compound_properties_by_CID` | `cid`, `properties` (e.g. `["MolecularFormula","MolecularWeight","InChIKey","IUPACName"]`) | property table — use to obtain an InChIKey for arbitrary compounds |

---

## Workflow

```
Phase 0: Classify input — name / formula / exact mass / InChIKey / SMILES?
Phase 1: Obtain an InChIKey (the universal key for ClassyFire & precise NPAtlas match)
Phase 2: Dereplicate against NPAtlas (known microbial NP? which organism? which paper?)
Phase 3: Assign ChemOnt chemical class via ClassyFire
Phase 4: Cross-reference identity in PubChem
Phase 5: Report — known/novel call + provenance + class hierarchy + interpretation note
```

### Phase 0 — Classify the input

- **Full InChIKey** (27 chars, `XXXXXXXXXXXXXX-XXXXXXXXXX-X`) → skip to Phase 2; it is already the universal key.
- **Molecular formula / exact mass** → go straight to NPAtlas formula search (Phase 2); these are the rawest dereplication inputs (typical of an untargeted MS feature).
- **SMILES** → usable directly in `NPAtlas_search_compounds(smiles=...)`; also feed to PubChem for an InChIKey.
- **Systematic IUPAC name** (e.g. `2-acetyloxybenzoic acid`) → Phase 1 via OPSIN.
- **Trivial / trade / common name** (e.g. `staurosporine`, `penicillin`) → Phase 1 via PubChem (OPSIN will return `parsed:false` for these).

### Phase 1 — Obtain an InChIKey

```python
# Systematic IUPAC name → structure (OPSIN). parsed:false ⇒ fall through to PubChem.
op = tu.tools.OPSIN_name_to_structure(name="2-acetyloxybenzoic acid")
inchikey = op["data"]["inchikey"]  # only if op["data"]["parsed"]

# Trivial/common name → PubChem CID → properties (incl. InChIKey)
cid = tu.tools.PubChem_get_CID_by_compound_name(name="staurosporine")["data"]["IdentifierList"]["CID"][0]
props = tu.tools.PubChem_get_compound_properties_by_CID(
    cid=cid, properties=["MolecularFormula","MolecularWeight","InChIKey","IUPACName"])
inchikey = props["data"]["PropertyTable"]["Properties"][0]["InChIKey"]
```

The InChIKey is what makes dereplication exact: an InChIKey match is a structure match; a name match is not (synonyms, analogs, and salts share names).

### Phase 2 — Dereplicate against NPAtlas

Search by the most specific key available. Prefer **InChIKey** (exact structure), then **formula** (catches isomers — useful for an MS feature with only a formula), then **name** (loosest — returns analogs).

```python
# Exact, structure-level
hits = tu.tools.NPAtlas_search_compounds(inchikey="HKSZLNNOFSGOKW-FYTWVXJKSA-N", limit=5)
# MS-feature style (formula or exact mass) — expect multiple isomeric hits
hits = tu.tools.NPAtlas_search_compounds(formula="C28H26N4O3", limit=10)
```

For each candidate NPAID, fetch the **full record** to get the producing organism and reference (search results carry `origin_organism: null`):

```python
rec = tu.tools.NPAtlas_get_compound(npaid="NPA014588")["data"]
organism   = rec["origin_organism"]["name"]            # e.g. "Streptomyces"
lineage    = rec["origin_organism"]["ancestors"]       # domain→...→family
reference  = rec["origin_reference"]                    # title, doi, journal, year
```

### Phase 3 — Assign ChemOnt chemical class

```python
cf = tu.tools.ClassyFire_classify_by_inchikey(inchikey=inchikey)["data"]
# cf["kingdom"], cf["superclass"], cf["class"], cf["subclass"], cf["direct_parent"]
# cf["molecular_framework"], cf["substituents"]
```

If `classified:false`, the InChIKey is not in the ClassyFire cache — report the class as *unavailable* (do not invent one). A correct InChIKey is required; a wrong stereo/protonation layer will miss the cache.

### Phase 4 — Cross-reference identity in PubChem

Confirm the same molecule exists in PubChem (CID, IUPAC name, formula, MW) so the identity is anchored to a second independent database. Disagreement in molecular formula between NPAtlas and PubChem is a red flag that the name/structure resolution went astray.

### Phase 5 — Report

Deliver:
1. **Dereplication call** — *Known microbial NP* (with NPAID) **or** *No NPAtlas match (possibly novel / non-microbial)*.
2. **Provenance** — producing organism + taxonomic lineage + literature reference (title, DOI, year).
3. **Chemical class** — ChemOnt kingdom → superclass → class → subclass → direct_parent (+ molecular framework).
4. **Identity cross-refs** — PubChem CID/IUPAC, InChIKey, formula, exact mass.
5. **Interpretation note** (see below).

---

## Interpretation Guidance (dereplication logic)

- **InChIKey hit in NPAtlas** = structure-level match ⇒ confidently a known microbial NP. Quote the NPAID, organism, and paper.
- **Formula / exact-mass hit(s) only** = candidate(s) at the molecular-formula level. Multiple isomers can share one formula and exact mass (e.g. `C28H26N4O3`, 466.2005 Da, returns *both* staurosporine and an ardeemin derivative). Treat these as a **ranked candidate list, not an identification** — confirm with InChIKey, MS/MS, or NMR before claiming identity.
- **Name hit only** = weakest evidence. A name search returns analogs and congeners (searching "staurosporine" returns 5'-hydroxystaurosporine, etc.), not necessarily the exact molecule. Always escalate to an InChIKey check.
- **No NPAtlas hit** = not a known *microbial* natural product. Possible meanings: genuinely novel; a plant/animal/marine metabolite outside NPAtlas scope; or a synthetic/derivatized compound. State which interpretations remain open — do **not** declare "novel" unconditionally.
- **ClassyFire `classified:false`** = ChemOnt has no cached classification for that exact InChIKey (often because the InChIKey's stereo/charge layer differs from the cached entry, or the compound is new). Report class as unavailable rather than guessing.
- **OPSIN `parsed:false`** = the name was not systematic IUPAC (trade/trivial name); route to PubChem for an InChIKey instead.

---

## Worked Example — Staurosporine (trivial name in)

Input: `staurosporine` (a trivial name).

1. **OPSIN** `name=staurosporine` → `parsed:false` (not systematic IUPAC) → fall through to PubChem.
2. **PubChem** name→CID = `44259`; properties → `MolecularFormula C28H26N4O3`, `MW 466.5`, `InChIKey HKSZLNNOFSGOKW-FYTWVXJKSA-N`.
3. **NPAtlas** `inchikey=HKSZLNNOFSGOKW-FYTWVXJKSA-N` → **1 exact hit**: `NPA014588 Staurosporine`, exact_mass `466.2005`. → **Known microbial NP**.
4. **NPAtlas** `get_compound NPA014588` → producing organism **Streptomyces** (genus; lineage Bacteria → Actinobacteria → Actinobacteria → Streptomycetales → Streptomycetaceae); reference *"X-Ray crystal structure of staurosporine: a new alkaloid from a Streptomyces…"*, DOI `10.1039/C39780000800`, 1978.
5. **ClassyFire** `inchikey=HKSZLNNOFSGOKW-FYTWVXJKSA-N` → Organic compounds → **Organoheterocyclic compounds** → Indoles and derivatives → Carbazoles → direct parent **Indolocarbazoles**; molecular framework: aromatic heteropolycyclic.

**Call**: Known microbial natural product (NPA014588), an indolocarbazole alkaloid produced by *Streptomyces*, first reported 1978.

**Dereplication-logic footnote**: the formula `C28H26N4O3` (exact mass 466.2005) alone is *not* unique — NPAtlas formula search returns **2** isomers (staurosporine **and** 5-N-acetyl-15b-didehydroardeemin). The InChIKey is what pins the identity to staurosporine specifically. An MS feature with only this formula would need MS/MS or NMR to choose between the isomers.

## Worked Example — Acetylsalicylic acid (systematic name in)

Input IUPAC `2-acetyloxybenzoic acid`.
1. **OPSIN** → `parsed:true`, `InChIKey BSYNRYMUTXBXSQ-UHFFFAOYSA-N`.
2. **NPAtlas** `inchikey=BSYNRYMUTXBXSQ-...` → no microbial NP record ⇒ *not a known microbial natural product* (it is a semisynthetic drug — consistent with NPAtlas scope).
3. **ClassyFire** → Organic compounds → **Benzenoids** → Benzene and substituted derivatives → Benzoic acids and derivatives → direct parent **Acylsalicylic acids**.

**Call**: Classified into ChemOnt (acylsalicylic acid), but no NPAtlas microbial-NP provenance — illustrating a legitimate "no hit" that is *not* a novel NP.

---

## Limitations (be honest in every report)

- **NPAtlas = microbial NPs only** (bacteria + fungi). No plant, animal, or marine-invertebrate metabolites unless a microbial producer was reported. Absence is not proof of novelty.
- **ClassyFire is a cache lookup** by InChIKey. `classified:false` means "not cached for this exact InChIKey", not "unclassifiable". Wrong stereo/charge layers miss the cache.
- **Name search ≠ structure match.** NPAtlas/PubChem name searches return synonyms, analogs, and salts. Always confirm identity at the InChIKey level before declaring a compound "known".
- **Formula/exact-mass hits are candidate lists**, not identifications — isomers share formulas. Confirm with orthogonal evidence (MS/MS, NMR, InChIKey).
- **OPSIN parses systematic IUPAC names only** — trivial/trade names return `parsed:false`; route them through PubChem.
- Search-result records carry `origin_organism: null`; provenance requires the `NPAtlas_get_compound` full record.

## Out of Scope → route elsewhere

- General drug/compound **identity & ADMET**, properties, bioassays → **tooluniverse-chemical-compound-retrieval** / **tooluniverse-small-molecule-discovery**.
- Metabolomics **pathway/enrichment** analysis → **tooluniverse-metabolomics** skills.

## Completeness Checklist

- [ ] Input type classified (name / formula / mass / InChIKey / SMILES).
- [ ] An InChIKey was obtained (OPSIN or PubChem) when starting from a name/SMILES.
- [ ] NPAtlas searched with the most specific key available; full record fetched for any hit (organism + reference).
- [ ] Known/novel call made with the correct caveats (microbial-only scope).
- [ ] ChemOnt class reported from ClassyFire, or marked unavailable if `classified:false`.
- [ ] Identity cross-referenced in PubChem (CID/formula/InChIKey agree).
- [ ] Interpretation note included (InChIKey vs formula vs name match; meaning of no-hit / classified:false).
- [ ] Limitations stated; every NPAID, organism, DOI, and class came from a live tool call.
