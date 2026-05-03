---
name: tooluniverse-ecology-biodiversity
description: Ecology, biodiversity, and conservation biology research — species identification, invasive species assessment, pollinator ecology, population dynamics, food webs, trophic interactions, community ecology, island biogeography. Use for ANY ecology question including species distributions, invasive impacts, pollination biology, predator-prey dynamics, or conservation assessment.
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
| `GBIF_search_species` | Species taxonomy, occurrence data, distribution |
| `GBIF_search_occurrences` | Where has a species been observed? |
| `WoRMS_search_species` | Marine species taxonomy |
| `ensembl_get_taxonomy` | Taxonomic classification |
| `NCBIDatasets_get_taxonomy` | NCBI taxonomy lookup |
| `PubMed_search_articles` | Literature on ecology topics |
| `EuropePMC_search_articles` | European literature including ecology |

## LOOK UP DON'T GUESS

Ecology questions often have counter-intuitive answers. For example:
- Honeybees (Apis mellifera) are invasive in the Americas and displace native pollinators — this surprises people who think of bees as "good"
- The most damaging invasive species are often not the most obvious ones
- Microbial extinction points require survival analysis, not simple t-tests

**Always search the literature** before answering ecology questions. Use `PubMed_search_articles` with specific terms like "[species] invasive impact [region]" or "[organism] [ecological process]".

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.
