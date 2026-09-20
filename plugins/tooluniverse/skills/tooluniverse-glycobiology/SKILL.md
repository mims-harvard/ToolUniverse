---

name: tooluniverse-glycobiology
description: "Glycobiology and glycomics research using GlyGen — glycan structure lookup by GlyTouCan accession, glycan search by mass/monosaccharide-count/type, glycoprotein glycosylation profiles by UniProt accession, glycosylation-site-level detail (position, flanking sequence, attached glycan, co-located SNVs). Use when someone asks about \"what glycans are attached to protein X\", \"N-linked vs O-linked glycosylation sites\", \"glycan mass/composition search\", \"GlyTouCan accession lookup\", \"glycosylation site at position N\", or \"which proteins have reported glycosylation in human/mouse\". NOT for protein sequence/structure retrieval alone (use tooluniverse-sequence-retrieval or tooluniverse-protein-structure-retrieval), NOT for general small-molecule chemistry (use tooluniverse-chemical-compound-retrieval), NOT for post-translational modifications other than glycosylation (use tooluniverse-protein-modification-analysis)."
---

# Glycobiology and Glycomics (GlyGen)

Glycan structure and protein-glycosylation research using GlyGen's 5 ToolUniverse
tools: `GlyGen_get_glycan`, `GlyGen_search_glycans`, `GlyGen_get_glycoprotein`,
`GlyGen_search_glycoproteins`, `GlyGen_get_site`.

**LOOK UP, DON'T GUESS**: Glycan composition, mass, and site-level glycosylation
data are highly specific and not reliably recalled from memory — always resolve
through these tools rather than asserting a glycan's structure or a protein's
glycosylation status from general knowledge.

---

## When to Use This Skill

Apply when users ask about:
- A specific glycan's structure, mass, monosaccharide composition, or species
  distribution (given a GlyTouCan accession, e.g. `G17689DH`)
- Finding glycans that match a mass range, monosaccharide-count range, or
  glycan type (N-linked / O-linked)
- A protein's overall glycosylation profile (site count, site positions,
  attached glycans, associated diseases/pathways) given a UniProt accession
- Finding glycosylated proteins in an organism, by gene name, or by
  glycosylation-evidence level
- Detailed information about one specific glycosylation site: exact position,
  flanking amino-acid sequence, the glycan attached there, and any SNVs
  co-located at that position

**NOT for** (route elsewhere):
- Resolving a gene/protein name to its UniProt accession in the first place ->
  `tooluniverse-sequence-retrieval` or `tooluniverse-protein-structure-retrieval`
  (GlyGen tools require a UniProt accession as input, not a gene symbol, except
  `GlyGen_search_glycoproteins`'s `gene_name` filter)
- 3D protein structure -> `tooluniverse-protein-structure-retrieval`
- Non-glycan post-translational modifications (phosphorylation as a topic in
  its own right, ubiquitination, etc.) -> `tooluniverse-protein-modification-analysis`
- General small-molecule/chemical compound lookup -> `tooluniverse-chemical-compound-retrieval`

---

## Tool Chains for Common Questions

**"What glycans are attached to protein X?"**
1. If you only have a gene symbol, resolve it to a UniProt accession first
   (`tooluniverse-sequence-retrieval` / `tooluniverse-protein-structure-retrieval`,
   or pass the gene name straight into `GlyGen_search_glycoproteins`'s
   `gene_name` filter if you just need to confirm the protein is glycosylated
   at all).
2. `GlyGen_get_glycoprotein(uniprot_ac=...)` — returns `glycosylation_count`
   and a `glycosylation_sites` list, each entry giving `position`, `residue`,
   `type` (N-linked/O-linked), and the `glytoucan_ac` of the attached glycan.
3. For full structural detail on any glycan found in step 2, call
   `GlyGen_get_glycan(glytoucan_ac=...)`.
4. For full detail on one specific site (flanking sequence, co-located SNVs),
   build a `site_id` as `<uniprot_ac>.<start_pos>.<end_pos>` (the canonical
   isoform accession from step 2's response usually needs a `-1` suffix, e.g.
   `P14210-1.294.294` — confirm the exact accession format from the
   glycoprotein response rather than assuming) and call `GlyGen_get_site`.

**"Find glycans matching a mass or composition range"**
1. `GlyGen_search_glycans(mass_min=..., mass_max=..., monosaccharide_min=...,
   monosaccharide_max=..., glycan_type=...)` — all filters are optional and
   combine as AND; omit filters you don't need. Returns a ranked list with
   `hit_score`.
2. `GlyGen_get_glycan(glytoucan_ac=...)` on any hit for full structural detail
   (composition breakdown, IUPAC/WURCS notation, species).

**"Which proteins are glycosylated in organism X / by gene name?"**
1. `GlyGen_search_glycoproteins(organism_id=..., gene_name=...,
   glycosylation_type=..., glycosylation_evidence="reported")` — `organism_id`
   is an NCBI taxonomy ID (9606 = human, 10090 = mouse, 10029 = Chinese
   hamster). Returns proteins ranked by `hit_score` with a `glycosylation_count`
   per protein.
2. Drill into any hit with `GlyGen_get_glycoprotein` for the full site list.

---

## Response Shape Notes (observed from live calls, not assumed from schema)

- Every tool wraps its payload as `{"status": "success", "data": {...or [...]},
  "metadata": {"source": "GlyGen", "query": ..., "endpoint": ...}}` on success,
  or `{"error": "..."}` on failure — check `status`/`error` before reading `data`.
- `GlyGen_get_glycan`'s `data` includes a monosaccharide-composition array
  (each entry has `name`, `residue`, `count`, and a PubChem `cid`/`url`) and a
  `byonic` composition string (e.g. `HexNAc(4)Hex(5)dHex(1)NeuAc(2) %
  2368.84091476`) in addition to the fields in the JSON schema.
- `GlyGen_get_glycoprotein`'s `data` includes `sequence_length`, `function`,
  `snv_count`, and `publication_count` alongside the documented fields. Each
  entry in `glycosylation_sites` has `position`, `residue`, `type`,
  `glytoucan_ac`, and `site_category` (e.g. `"reported_with_glycan"`) — this is
  the richest per-site summary and is often enough without a follow-up
  `GlyGen_get_site` call unless you need flanking sequence or SNV detail.
- `GlyGen_search_glycoproteins`'s `metadata` includes `total_results` (may
  exceed the returned page) and `list_id` — use `total_results` to know
  whether to page further with `offset`.
- `GlyGen_get_site`'s `data` includes a `species` array with `common_name` /
  `reference_species`, an `all_sites_count` (other sites reported on the same
  protein), and a `categories` array (e.g. `["glycosylation_flag",
  "snv_flag"]`) indicating what kinds of annotations exist at that position.

See `references/glygen_tool_reference.md` for the full parameter table and
captured example responses for all 5 tools.

## Output

State the GlyTouCan/UniProt accessions used, the resolved values (mass,
site positions, etc.), and cite GlyGen as the source. Do not report a
glycan composition or site position that wasn't actually returned by a tool
call.
