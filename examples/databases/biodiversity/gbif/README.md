### GBIF Examples (Biodiversity → Databases)

About GBIF
- GBIF (Global Biodiversity Information Facility) is an open platform for global biodiversity data, providing species checklists, occurrence records, sampling events, and datasets used in ecology, biogeography, and conservation research.

Run:
```bash
python examples/databases/biodiversity/gbif/use_gbif.py
```

What it does:
- GBIF_search_species: calls `/species/search` with a small page
- GBIF_search_occurrences: calls `/occurrence/search` with basic filters

Notes:
- Network required; respect GBIF rate limits.
- Adjust `limit/offset` for pagination.

