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

`HealthCanadaDPD_search_by_ingredient` makes one product lookup per returned row, so `limit` is at most 25. `metadata.total_products` gives the full count.

The API answers an unknown `drug_code` with HTTP 200 and a record of nulls. `HealthCanadaDPD_get_product` reports that as "not found". Sub-resources such as dosage form answer 404 when a product has no entry; the tool returns an empty list for them.
