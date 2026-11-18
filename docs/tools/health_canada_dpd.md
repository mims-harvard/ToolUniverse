# Health Canada Drug Product Database

The [Drug Product Database (DPD)](https://www.canada.ca/en/health-canada/services/drugs-health-products/drug-products/drug-product-database.html) lists every drug product that Health Canada has authorized for sale: human, veterinary, biologic, radiopharmaceutical and disinfectant products, marketed and cancelled. The three tools use the public API at `https://health-products.canada.ca/api/drug/`. No key is needed. They add the Canadian market next to the US sources (openFDA, DailyMed, Orange Book).

| Tool | Use it to |
|---|---|
| `HealthCanadaDPD_search_products` | Find products by brand name (substring) or Drug Identification Number (DIN). `marketed_only=true` keeps products that are marketed now. |
| `HealthCanadaDPD_search_by_ingredient` | Find products that contain an active ingredient, with the strength of each. |
| `HealthCanadaDPD_get_product` | Read one product by `drug_code` or DIN: ingredients, status and dates, dosage forms, routes, schedules, ATC code. |

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(categories=["health_canada_dpd"])
product = tu.tools.HealthCanadaDPD_get_product(din="02253275")
# GLEEVEC, imatinib 100 MG, Marketed since 2005-04-05, Tablet, Oral,
# PRESCRIPTION, ATC L01EA01
```

Common ingredients have many cancelled products: acetaminophen is in 1354 products, and the 25 with the lowest drug codes are all cancelled (2026-11-18). Use `marketed_only=true` on `HealthCanadaDPD_search_by_ingredient` to keep marketed products. That option reads the list of all marketed products once (about 13,400 rows) and keeps it for an hour. Without it, the tool makes one product lookup per row, so `limit` is at most 25 (100 with `marketed_only`). Page with `offset` and `metadata.next_offset`.

The API answers an unknown `drug_code` with HTTP 200 and a record of nulls. `HealthCanadaDPD_get_product` reports that as "not found". Sub-resources such as dosage form answer 404 when a product has no entry; the tool returns an empty list for them.
