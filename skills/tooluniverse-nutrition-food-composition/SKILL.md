---
name: tooluniverse-nutrition-food-composition
description: "Look up nutrient composition, ingredients, allergens, additives, and processing-level classification for foods and branded products via USDA FoodData Central (authoritative US nutrient values, generic + branded foods) and Open Food Facts (crowdsourced global product database — barcode lookup, allergens, additives, Nutri-Score, NOVA processing classification). Use when someone asks 'how much [nutrient] is in [food]', 'what are the ingredients/allergens in [branded product]', 'look up this barcode', 'find products containing/free of [additive/allergen]', or needs dietary/nutrient data for a clinical or research calculation."
disable-model-invocation: true
---

# Nutrition & Food Composition Lookup

Looks up what's actually in a food or branded product — nutrient values, ingredients, allergens, additives, processing classification — from two complementary sources. Does not itself perform toxicological or epidemiological analysis; feed the retrieved data into `tooluniverse-toxicology` (food additive/allergen safety questions) or `tooluniverse-epidemiological-analysis` (dietary-exposure questions) for that.

**LOOK UP, DON'T GUESS**: Never state a nutrient value, ingredient list, allergen, or Nutri-Score from memory — both sources are live and current; query them.

## When to Use This Skill

- "How much [protein/sodium/vitamin C/...] is in [food]?" -> FoodDataCentral
- "What's the full nutrient profile of [generic or USDA reference food]?" -> FoodDataCentral
- "What are the ingredients/allergens in [branded product]?" -> OpenFoodFacts
- "Look up this barcode" -> `OpenFoodFacts_get_product`
- "Find products with/without [additive, allergen, Nutri-Score grade, label]" -> `OpenFoodFacts_filter_products_by_tags`

**NOT for**: assessing whether an additive/ingredient is toxicologically safe (-> `tooluniverse-toxicology`, e.g. CTD/AOPWiki/EPA CompTox for the additive's own chemical hazard data — this skill only tells you a product *contains* it); population-level dietary-exposure or disease-association analysis (-> `tooluniverse-epidemiological-analysis`); clinical nutrition guidelines or diet-disease management recommendations (out of scope for both tools here — they're data lookups, not guideline sources).

## 1. USDA FoodData Central — Authoritative US Nutrient Values

The USDA's official nutrient database: Foundation Foods (analytically measured reference values), SR Legacy (the historical USDA standard reference), Survey/FNDDS (foods as reported in national dietary surveys), and Branded (commercial products, including label-declared values).

| Tool | Use for | Key params |
|---|---|---|
| `FoodDataCentral_search_foods` | Keyword search across all data types, or one filtered type | `query`, `page_size` (max 200), `page_number`, `data_type` ("Foundation" \| "Branded" \| "SR Legacy" \| "Survey (FNDDS)") |
| `FoodDataCentral_get_food` | Full nutrient profile (70+ nutrients) for a known `fdcId` | `fdc_id` |

Optional `FDC_API_KEY` (free, register at https://fdc.nal.usda.gov/api-guide.html) — **without one, calls fall back to a shared, rate-limited `DEMO_KEY`**, which is what this skill's live verification used successfully; register a personal key for any workload beyond occasional lookups.

Verified live: `FoodDataCentral_search_foods {"query": "raw banana", "page_size": 3, "data_type": "Foundation"}` returned real Foundation-food records (e.g. fdcId `1105073`, "Bananas, overripe, raw") with full `topNutrients` arrays and `totalHits: 164` across 55 pages. `FoodDataCentral_get_food {"fdc_id": 2344723}` returned a complete real nutrient profile — **but for "Starfruit, raw" (Survey/FNDDS), not "Bananas, raw" as the tool's own JSON description example claims**. That description's example `fdcId` is stale/wrong — always use an `fdcId` you actually got back from `search_foods` in the same session, never one quoted in a tool description or from memory.

## 2. Open Food Facts — Crowdsourced Global Product Database

3M+ products worldwide, contributed by users and scanned from packaging — broader branded/international coverage than FoodDataCentral's Branded category, but not centrally curated: expect gaps or inconsistencies in any individual product record (missing nutrient fields, unverified ingredient lists) more often than in USDA's data. No API key required for any of the 3 tools.

| Tool | Use for | Key params |
|---|---|---|
| `OpenFoodFacts_search_products` | Free-text search by product/brand name | `search_terms` (required), `page_size` (max 100, default 50), `page` |
| `OpenFoodFacts_get_product` | Full record for a known barcode (EAN-13/UPC) | `barcode` (required) |
| `OpenFoodFacts_filter_products_by_tags` | Faceted search by controlled-vocabulary tags — answers queries free-text search can't | `additives_tags`, `allergens_tags`, `categories_tags_en`, `brands_tags`, `nutrition_grades_tags`, `labels_tags`, `countries_tags`, `fields`, `page_size`, `page` (all optional; combine with AND) |

Verified live:
- `OpenFoodFacts_search_products {"search_terms": "nutella", "page_size": 2}` -> real results (`count: 1038`), including full `ingredients_text` and `nutriments` for the top match.
- `OpenFoodFacts_get_product {"barcode": "3017620422003"}` -> the real Nutella 400g record: `additives_original_tags` (`en:e322`, `en:e322i` — lecithins), full `_keywords`, ingredient text in French.
- `OpenFoodFacts_filter_products_by_tags {"allergens_tags": "en:peanuts", "page_size": 2}` -> real peanut-allergen products (`count: 38821`) with `additives_tags`, `allergens_tags`, `categories_tags_en`, `labels_tags` per record — this is the right tool for "find products containing/excluding X," which `search_products`' free-text search cannot do reliably.
- One transient failure observed: `search_products` returned an HTML "Page temporarily unavailable" error on a first attempt, then succeeded identically on immediate retry — treat a single such failure as a transient upstream hiccup and retry once before reporting the tool as broken.

## When to Use Which

| Need | Use |
|---|---|
| Rigorous nutrient values for a generic/reference food (clinical dietary calculation, research) | FoodDataCentral (`Foundation` or `SR Legacy`) |
| A specific branded product's nutrient label as declared by the manufacturer | Either — FoodDataCentral's `Branded` type or OpenFoodFacts, cross-check if precision matters |
| Ingredients, allergens, additives, Nutri-Score, or NOVA processing level for a branded product | OpenFoodFacts (FoodDataCentral's `ingredients` field is a plain string only, no structured allergen/additive tags) |
| Scanning/looking up a physical product by barcode | OpenFoodFacts (`get_product`) — FoodDataCentral has no barcode lookup |
| "Which products contain/avoid additive X or allergen Y" | OpenFoodFacts `filter_products_by_tags` — no equivalent in FoodDataCentral |
| Global/international branded products (non-US) | OpenFoodFacts — FoodDataCentral's Branded coverage skews US market |

## Common Pitfalls

- **Don't trust example `fdcId`s from tool descriptions or memory** — the `FoodDataCentral_get_food` tool's own description cites an example ID that returns a different food than claimed (verified above). Always source the ID from a `search_foods` call in the same session.
- **OpenFoodFacts data is crowdsourced, not centrally curated** — a missing or odd-looking field (absent Nutri-Score, sparse nutrients) may just reflect incomplete community contribution for that specific product, not a tool malfunction. Don't assume the record is exhaustive.
- **`filter_products_by_tags`'s tag fields use a controlled vocabulary** (`en:peanuts`, `en:e322`, not free text) — get exact tag values from a product's own tag fields (e.g. `allergens_tags` in a prior `get_product`/`search_products` result) rather than guessing the tag string.
- Retry once on a transient OpenFoodFacts HTML error page before concluding the API is down.

## References

- USDA FoodData Central: https://fdc.nal.usda.gov
- Open Food Facts: https://world.openfoodfacts.org
