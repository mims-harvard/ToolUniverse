Responses recorded from https://health-products.canada.ca/api/drug/ on
2026-11-18 (`lang=en&type=json`). File names give the resource and the query:
`<resource>_<drug_code>.json` is `<resource>/?id=<drug_code>`.
`activeingredient_imatinib.json` keeps the first 6 of the rows.
`drugproduct_unknown_id_58989.json` shows that an unknown drug code returns
HTTP 200 with drug_code 0 and null fields. Sub-resources such as `form`
answer HTTP 404 with an empty body when a product has no entry.
