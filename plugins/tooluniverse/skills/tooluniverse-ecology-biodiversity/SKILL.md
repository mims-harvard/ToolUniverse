---

name: tooluniverse-ecology-biodiversity
description: "Ecology, biodiversity, and conservation biology research — species identification (GBIF, NCBI Taxonomy), invasive species impact, ecosystem dynamics, conservation status (IUCN), niche ecology. Use for biodiversity questions, species comparison, invasion biology, conservation prioritization, and ecology-related literature search."
---

# Ecology & Biodiversity Research

## Reasoning Strategy

### 1. Species & Taxonomy Questions
When a question involves identifying or comparing species:
1. **LOOK UP DON'T GUESS** — Use `GBIF_search_species` to get taxonomy, `WoRMS_search_species` for marine organisms
2. If the question asks about invasive species impacts, consider: ecological niche overlap, reproductive rate, predator release, and ecosystem engineering effects
3. Use `PubMed_search_articles` or `EuropePMC_search_articles` to find studies on specific ecological impacts

### 2. Invasive Species Impact Assessment
**Reasoning framework** — when comparing invasive species impacts:
1. **Identify the ecosystem**: What habitat/biome is affected?
2. **Assess impact mechanisms**: Competition? Predation? Disease vector? Habitat modification? Hybridization?
3. **Scale of impact**: Local (single site) vs regional vs continental?
4. **Trophic position**: Invasives at higher trophic levels (predators) often cause more damage than lower (herbivores)
5. **Ecosystem engineering**: Species that modify habitats (beavers, earthworms, honeybees displacing native pollinators) cause outsized impacts
6. **Look up specifics** — don't rely on general knowledge. Search for "[species name] invasive impact [region]" in literature

### 3. Pollinator Ecology
**Reasoning framework** for pollination questions:
1. **Foraging behavior**: Distinguish investigation (approach/assessment) from actual feeding (proboscis insertion)
2. **Interaction types**: Mutualistic (pollination reward), parasitic (nectar robbing), commensal
3. **Observation methods**: Camera traps have resolution/FOV limitations — consider what's identifiable at given resolution
4. **Statistical considerations**: Observer agreement (inter-rater reliability), sampling effort, temporal patterns
5. **Ethogram interpretation**: Each behavior category has specific start/end criteria — follow them precisely

### 4. Population Dynamics
**Reasoning framework** for population ecology questions:
1. **Growth models**: Exponential (unlimited), logistic (K-limited), Allee effects (low-density problems)
2. **Extinction analysis**: Distinguish deterministic extinction (r < 0) from stochastic extinction (small population fluctuations)
3. **Survival analysis**: Time-to-event analysis needs appropriate statistical tests (log-rank, Cox regression, Kaplan-Meier)
4. **Microbial ecology**: For microbial stressor responses, use survival curve analysis with time-kill kinetics. To compare extinction points between populations, you need time-to-extinction data analyzed with survival statistics (not just endpoint comparisons)

### 5. Community Ecology & Food Webs
1. **Trophic cascades**: Removing top predators → mesopredator release → prey decline
2. **Keystone species**: Disproportionate impact relative to abundance
3. **Island biogeography**: Species-area relationship, distance-colonization tradeoff
4. **Competitive exclusion**: Two species cannot stably coexist on single limiting resource (Gause's principle)

### 6. Evolutionary Ecology
1. **Aposematism**: Warning coloration signals toxicity/unpalatability
2. **Mimicry**: Batesian (harmless mimics dangerous) vs Mullerian (dangerous mimics dangerous)
3. **Life history tradeoffs**: r-selected (many offspring, low investment) vs K-selected (few offspring, high investment)
4. **Birth-death models**: For phylogenetic questions, identifiability issues arise with time-varying rates. Strategies to resolve: constrain rate variation, add fossil data, use molecular data calibration, or restrict to specific functional forms

## Available Tools

| Tool | Use For |
|------|---------|
| `IUCN_get_conservation_status` | **Red List conservation status** (CR/EN/VU/NT/LC) by scientific name — the authoritative extinction-risk source (needs a free IUCN_API_KEY) |
| `GBIF_search_species` | Species taxonomy, occurrence data, distribution |
| `GBIF_search_occurrences` | Where has a species been observed? |
| `GBIF_get_taxon_parents` | Walk UP the GBIF Backbone tree — ranked ancestor lineage (kingdom→genus) for a taxonKey |
| `GBIF_get_taxon_children` | Walk DOWN the tree — direct child taxa (e.g. species in a genus) for a taxonKey |
| `GBIF_get_taxon_synonyms` | Alternative / historical scientific names for an accepted taxonKey |
| `GBIF_get_vernacular_names` | Common names (with language code) for a taxonKey; optional `language` filter |
| `GBIF_parse_name` | Parse messy/authored name strings into canonical name + genus/epithet/author/year |
| `iDigBio_search_records` | Search 130M+ digitized museum/herbarium specimen records (Darwin Core) by `genus`/`scientificname`/locality — use to complement GBIF with physical-specimen provenance |
| `iDigBio_get_record` | Full Darwin Core detail for one specimen by `uuid` (from `iDigBio_search_records`) |
| `WoRMS_search_species` | Marine species taxonomy |
| `BOLDSystems_search_by_taxon` / `_search_by_bin` / `_get_record` | DNA barcode-based species identification (COI barcoding); BIN clusters group specimens by barcode similarity, useful for cryptic-species questions GBIF's name-based search can't resolve |
| `ensembl_get_taxonomy` | Taxonomic classification |
| `NCBIDatasets_get_taxonomy` | NCBI taxonomy lookup |
| `PubMed_search_articles` | Literature on ecology topics |
| `EuropePMC_search_articles` | European literature including ecology |

## Navigating the GBIF taxonomic tree

Resolve a name to a GBIF `usageKey` once, then navigate the Backbone tree:

```python
key = tu.run_tool("GBIF_match_name", {"name": "Panthera leo"})["data"]["usageKey"]  # 5219404
tu.run_tool("GBIF_get_taxon_parents", {"taxon_key": key})        # Animalia→...→Felidae→Panthera
tu.run_tool("GBIF_get_taxon_synonyms", {"taxon_key": key})       # Felis leo Linnaeus, 1758, ...
tu.run_tool("GBIF_get_vernacular_names", {"taxon_key": key, "language": "eng"})  # Lion, African Lion
# Walk down from a genus key (Panthera = 2435194) to its species:
tu.run_tool("GBIF_get_taxon_children", {"taxon_key": 2435194, "limit": 8})
# Normalize an authored name string without a key:
tu.run_tool("GBIF_parse_name", {"name": "Quercus robur L."})     # canonicalName 'Quercus robur'
```

All five tools hit the public GBIF API with no key. Get the starting `taxon_key`
from `GBIF_match_name` or `GBIF_search_species`.

## Additional Taxonomy & Biodiversity Sources

GBIF/WoRMS/BOLDSystems/iDigBio (above) are the primary sources. These eight
add authority-specific, phylogenetic, and observational coverage GBIF alone
doesn't provide — use them when GBIF is ambiguous, when you need a
phylogenetic tree rather than a flat classification, or when you need
citizen-science occurrence density rather than museum-specimen records.

| Tool | Use For |
|------|---------|
| `EOL_search_species` / `EOL_get_page` / `EOL_get_hierarchy_entry` / `EOL_get_collection` | Encyclopedia of Life — aggregated species pages (images, text, multiple classification systems per page), curated topical collections |
| `ITIS_search_by_scientific_name` / `_search_by_common_name` / `ITIS_get_hierarchy` / `ITIS_get_full_record` | ITIS (Integrated Taxonomic Information System) — the authoritative North American taxonomy standard; returns a `tsn` (Taxonomic Serial Number) |
| `CoL_search_species` / `CoL_get_taxon` / `CoL_get_children` | Catalogue of Life — the broadest single global species checklist (consolidates 190+ source databases); good first stop when GBIF's backbone doesn't have a clean match |
| `OpenTree_match_names` / `OpenTree_get_taxon` / `OpenTree_get_mrca` / `OpenTree_get_induced_subtree` | Open Tree of Life — a synthetic **phylogenetic** tree (not just a rank hierarchy) across all of life; use when the question is about evolutionary relationships/branch order, not just classification |
| `iNaturalist_search_taxa` / `_get_taxon` / `_search_observations` / `_get_species_counts` | iNaturalist — citizen-science observation records with photos/location/date; use for occurrence density and recent sightings, not authoritative taxonomy |
| `OBIS_search_taxa` / `OBIS_search_occurrences` | OBIS (Ocean Biodiversity Information System) — marine-species occurrence records with coordinates/time, resolved to AphiaID (WoRMS' identifier); the marine analog of GBIF occurrence search |
| `eBird_get_taxonomy` / `eBird_get_taxon_groups` | eBird (Cornell Lab) — bird-specific taxonomy and species groupings; use for bird questions instead of generic taxonomy sources, which are shallower on avian subspecies/hybrid codes |
| `MarineRegions_search_by_name` / `MarineRegions_get_record` | Marine Regions Gazetteer (VLIZ) — geographic/political marine boundaries (seas, EEZs, bays) by `MRGID`; pairs with OBIS for "which occurrences fall inside this named sea" questions |

**Choosing among the identity/taxonomy sources** (EOL, ITIS, CoL, GBIF all
answer "what is this species"):
- **ITIS** if you need the North American regulatory-standard identifier (`tsn`).
- **CoL** for the broadest global checklist coverage when GBIF's backbone misses a match.
- **EOL** when you want an aggregated page (images, multiple hierarchies, curated collections) rather than a bare taxonomic record.
- **Open Tree of Life** only when the question is genuinely phylogenetic (MRCA, branch order, a Newick subtree) — none of the others return evolutionary relationships.
- Cross-check IDs are NOT interchangeable: the same species has a different key in each system (GBIF `usageKey`, ITIS `tsn`, CoL `taxon_id`, EOL `page_id`, Open Tree `ott_id`, iNaturalist `taxon_id`, OBIS `AphiaID`) — always resolve within one system, don't mix an ID from one database into another's lookup call.

**Example: cross-checking a species across four identity systems** (verified live, real IDs):
```python
tu.run_tool("EOL_search_species", {"query": "Panthera leo"})            # page_id 1270491
tu.run_tool("ITIS_search_by_scientific_name", {"scientific_name": "Panthera leo"})  # tsn 183803
tu.run_tool("CoL_search_species", {"q": "Panthera leo"})                # 293 CoL-database matches
tu.run_tool("OpenTree_match_names", {"names": "Panthera leo,Panthera tigris"})
# -> ott_id 563151 (leo), 42314 (tigris); note `names` is a comma-separated
# STRING, not a JSON array, even though it takes multiple names
```

**Example: phylogenetic MRCA and subtree** (verified live):
```python
tu.run_tool("OpenTree_get_mrca", {"ott_ids": "417950,770315"})
# -> mrca_name "Homininae", mrca_ott_id 312031, num_tips 19
tu.run_tool("OpenTree_get_induced_subtree", {"ott_ids": "417950,770315,312031"})
# -> real Newick tree with supporting_studies citations (pg_2741@tree6645, ...)
```

**Example: marine species + region** (verified live):
```python
tu.run_tool("OBIS_search_taxa", {"scientificname": "Rhincodon typus"})   # whale shark occurrence-resolved AphiaID
tu.run_tool("MarineRegions_search_by_name", {"name": "Mediterranean Sea"})  # MRGID 25180
```

**Example: citizen-science occurrence density** (verified live):
```python
tu.run_tool("iNaturalist_search_taxa", {"query": "Panthera leo"})
# -> genus-level hit "Panthera" (59,036 observations) if the exact binomial
# isn't the top match — check the returned `rank` before assuming species-level
```

## LOOK UP DON'T GUESS

Ecology questions often have counter-intuitive answers. For example:
- Honeybees (Apis mellifera) are invasive in the Americas and displace native pollinators — this surprises people who think of bees as "good"
- The most damaging invasive species are often not the most obvious ones
- Microbial extinction points require survival analysis, not simple t-tests

**Always search the literature** before answering ecology questions. Use `PubMed_search_articles` with specific terms like "[species] invasive impact [region]" or "[organism] [ecological process]".

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.
