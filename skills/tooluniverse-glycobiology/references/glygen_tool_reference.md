# GlyGen Tool Reference

All 5 tools verified live against the real GlyGen API. Every field name below
was observed in an actual response, not assumed from the JSON schema alone.

## `GlyGen_get_glycan`

**Purpose**: Full structural detail for one glycan by GlyTouCan accession.

**Parameters**: `glytoucan_ac` (required, string) — e.g. `"G17689DH"`.

**Example call**: `GlyGen_get_glycan(glytoucan_ac="G17689DH")`

**Real (trimmed) response**:
```json
{
  "status": "success",
  "data": {
    "glytoucan_ac": "G17689DH",
    "mass": 2368.84,
    "number_monosaccharides": 12,
    "glycan_type": "N-linked",
    "iupac": "...",
    "wurcs": "...",
    "species": ["Homo sapiens", "..."],
    "composition": [
      {"name": "N-Acetylhexosamine", "residue": "hexnac", "count": 4, "cid": "...", "url": "https://pubchem.ncbi.nlm.nih.gov/compound/..."},
      {"name": "N-Acetyl-Neuraminic Acid", "residue": "neuac", "count": 2, "cid": "439197", "url": "https://pubchem.ncbi.nlm.nih.gov/compound/439197"}
    ],
    "byonic": "HexNAc(4)Hex(5)dHex(1)NeuAc(2) % 2368.84091476",
    "glycoprotein_count": 1783,
    "publication_count": "..."
  },
  "metadata": {"source": "GlyGen", "query": "G17689DH", "endpoint": "glycan/detail"}
}
```
Note: `composition` and `byonic` are real fields returned by the live API that
are NOT listed in the tool's JSON `return_schema` — the schema is a lower
bound on what you get back, not an exhaustive contract.

## `GlyGen_search_glycans`

**Purpose**: Find glycans by mass range / monosaccharide-count range / type.

**Parameters** (all optional, combine as AND): `mass_min`, `mass_max`
(Daltons), `monosaccharide_min`, `monosaccharide_max` (integer counts),
`glycan_type` (`"N-linked"` / `"O-linked"`), `limit` (default 20, max 50),
`offset` (1-indexed, default 1).

**Example call**: `GlyGen_search_glycans(mass_min=1000, mass_max=2000, monosaccharide_min=5, monosaccharide_max=10, limit=5)`

**Real (trimmed) response**:
```json
{
  "status": "success",
  "data": [
    {"glytoucan_ac": "G62765YT", "mass": 1720.59, "number_proteins": 1783, "number_enzymes": "...", "number_species": "...", "hit_score": "..."}
  ]
}
```

## `GlyGen_get_glycoprotein`

**Purpose**: Full glycosylation profile for a protein by UniProt accession.

**Parameters**: `uniprot_ac` (required, string) — e.g. `"P14210"`.

**Example call**: `GlyGen_get_glycoprotein(uniprot_ac="P14210")`

**Real (trimmed) response** — actual top-level `data` keys observed:
`protein_name`, `gene_names`, `species`, `mass`, `sequence_length`,
`glycosylation_count`, `glycosylation_sites`, `function`, `disease_count`,
`snv_count`, `pathway_count`, `publication_count`.

```json
{
  "status": "success",
  "data": {
    "protein_name": "Hepatocyte growth factor",
    "gene_names": ["HGF", "DFNB39", "F-TCF", "HGFB"],
    "species": "Homo sapiens",
    "sequence_length": "...",
    "glycosylation_count": "...",
    "glycosylation_sites": [
      {"position": 294, "residue": "Asn", "type": "N-linked", "glytoucan_ac": "G01543ZX", "site_category": "reported_with_glycan"}
    ],
    "function": "...",
    "disease_count": "...",
    "snv_count": "...",
    "pathway_count": "...",
    "publication_count": "..."
  }
}
```
`sequence_length`, `function`, and `snv_count` are real fields not listed in
the JSON `return_schema`. `glycosylation_sites[].site_category` (e.g.
`"reported_with_glycan"`) is often enough detail on its own — only call
`GlyGen_get_site` if you need flanking sequence or SNV detail at that position.

## `GlyGen_search_glycoproteins`

**Purpose**: Find glycosylated proteins by organism / gene / evidence / type.

**Parameters** (all optional): `organism_id` (NCBI taxonomy ID, e.g. 9606 =
human, 10090 = mouse, 10029 = Chinese hamster), `glycosylation_evidence`
(`"reported"`), `glycosylation_type` (`"N-linked"` / `"O-linked"`),
`protein_name`, `gene_name`, `limit` (default 20, max 50), `offset`
(1-indexed, default 1).

**Example call**: `GlyGen_search_glycoproteins(gene_name="EGFR", glycosylation_type="N-linked", limit=3)`

**Real (trimmed) response** — 7 total results for this query (more than the
page of 3 requested):
```json
{
  "status": "success",
  "data": [
    {"uniprot_canonical_ac": "P00533-1", "protein_name": "Epidermal growth factor receptor", "gene_name": "EGFR", "organism": "...", "glycosylation_count": "...", "hit_score": "..."}
  ],
  "metadata": {
    "total_results": 7,
    "list_id": "597a052b7e75c569044e0c1368326979",
    "query": {"glycosylation_type": "N-linked", "gene_name": "EGFR"},
    "offset": 1,
    "limit": 3
  }
}
```
Use `metadata.total_results` to decide whether to page further with `offset`.

## `GlyGen_get_site`

**Purpose**: Detail on one specific glycosylation site.

**Parameters**: `site_id` (required, string), format
`<UniProtAC-isoform>.<start_pos>.<end_pos>` — e.g. `"P14210-1.294.294"`. Note
the isoform suffix (`-1`) is part of the accession GlyGen expects; confirm it
from a prior `GlyGen_get_glycoprotein` response rather than assuming `-1`
always applies.

**Example call**: `GlyGen_get_site(site_id="P14210-1.294.294")`

**Real (trimmed) response** — top-level `data` keys observed include the
schema's documented fields plus a `species` array (each entry with
`common_name`, `glygen_name`, `reference_species`, and a UniProt `url`), an
`all_sites_count` (other annotated sites on the same protein), and a
`categories` array:
```json
{
  "status": "success",
  "data": {
    "site_id": "P14210-1.294.294",
    "uniprot_ac": "P14210-1",
    "start_pos": 294,
    "end_pos": 294,
    "site_seq": "...",
    "upstream_seq": "...",
    "downstream_seq": "...",
    "glycosylation": ["..."],
    "snv": ["..."],
    "species": [{"common_name": "Human", "glygen_name": "Human", "reference_species": "Homo sapiens [9606]", "url": "https://www.uniprot.org/uniprotkb/P14210"}],
    "all_sites_count": 3,
    "categories": ["glycosylation_flag", "snv_flag"]
  },
  "metadata": {"source": "GlyGen", "query": "P14210-1.294.294", "endpoint": "site/detail"}
}
```

## Live test results (all 5 tools, canned `test_examples`, run via `tu test`)

| Tool | Result |
|---|---|
| `GlyGen_get_glycan` | 2/2 passed |
| `GlyGen_search_glycans` | 2/2 passed |
| `GlyGen_get_glycoprotein` | 2/2 passed |
| `GlyGen_search_glycoproteins` | 2/2 passed |
| `GlyGen_get_site` | 2/2 passed |

10/10 total, all against the live GlyGen API, no failures.
