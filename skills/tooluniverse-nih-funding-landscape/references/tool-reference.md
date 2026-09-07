# OpenNIH Tool Reference

## Contents

- [Tool selection](#tool-selection)
- [Identifier flow](#identifier-flow)
- [Count units](#count-units)
- [Response-field interpretation](#response-field-interpretation)
- [Funding scopes](#funding-scopes)
- [Pagination and reconciliation](#pagination-and-reconciliation)
- [Multi-component funding protocol](#multi-component-funding-protocol)
- [Topic-query protocol](#topic-query-protocol)
- [PI-disambiguation protocol](#pi-disambiguation-protocol)
- [Funding-to-output protocol](#funding-to-output-protocol)
- [Institution-comparison protocol](#institution-comparison-protocol)
- [Concentration protocol](#concentration-protocol)
- [IC and mechanism protocol](#ic-and-mechanism-protocol)
- [Small-business protocol](#small-business-protocol)
- [Geography and award-lineage protocol](#geography-and-award-lineage-protocol)
- [Citation-shaped search](#citation-shaped-search)
- [Freshness, failures, and evidence grades](#freshness-and-coverage)

## Tool selection

| Tool | Use | Required discovery step | Funding scope or unit |
|---|---|---|---|
| `OpenNIH_source_status` | Corpus, sidecar, and freshness checks | None | Coverage metadata |
| `OpenNIH_search_grants` | Filtered grant/project-year discovery | None | Project-year rows; also reports distinct project numbers and awards |
| `OpenNIH_rank_institutions` | Ranked institutions and entity IDs | None | Competitive RPG research; historical-dollar reconciliation required for FY1985–1998 |
| `OpenNIH_get_pi_profile` | One PI's grant rows and shared-award collaborators; current response has no publications field | Resolve `pi_profile_id` from grant search, using name-order fallbacks | Row-level profile totals for selected window; collaborators are not year-filtered; audit duplicate project numbers |
| `OpenNIH_get_institution_profile` | One institution's history, mechanisms, and PIs | Get `entity_id` from institution ranking | Same window, but mechanism mix is all-mechanism and trend/top PIs are RPG-only |
| `OpenNIH_funding_trend` | Annual totals for NIH, IC, activity, or institution | None | All mechanisms; nominal recorded dollars |
| `OpenNIH_topic_trend` | Annual title-keyword topic series | None | Project-year rows and recorded dollars |
| `OpenNIH_activity_code_distribution` | System or IC mechanism classes | None | Counts and recorded totals by class |
| `OpenNIH_institution_concentration` | Gini, HHI, and top-five share | None | Competitive RPG research; null awards excluded |
| `OpenNIH_mechanism_mix` | One institution's portfolio mix | Get `entity_id` from institution ranking | Institution: all mechanisms; no entity: system RPG research |
| `OpenNIH_ic_topic_cross` | One topic within one IC, or one combined all-IC slice | None | RPG research; distinct core awards and recorded dollars; no per-IC table when `ic=ALL` |
| `OpenNIH_funding_growth` | Year-over-year growth and CAGR | Entity ID needed only for one institution; check partial years with `funding_trend` | Null awards excluded; percent values already in percent units; no partial flag |
| `OpenNIH_search` | Deep Research citation-shaped search | None | Canonical project-level hits; limited filters |
| `OpenNIH_fetch` | Citation-shaped canonical project record | Full project number from `OpenNIH_search` or exact `search_grants` | Latest canonical project record |

## Identifier flow

```text
search_grants result.pi_profile_id -> get_pi_profile(profile_id)
rank_institutions result.entity_id -> get_institution_profile / mechanism_mix / funding_growth
search result.id OR search_grants result.project_num -> fetch(id)
search_grants result.project_num -> citation/fetch of one full record
search_grants result.core_project_num -> deduplication/lineage only; not fetchable
```

Do not guess PI profile IDs or institution entity IDs. `search_grants` does not return institution entity IDs.

## Count units

- `meta.total`: matching application/project-year rows. Multi-component awards can contribute multiple rows in one year.
- `meta.unique_project_nums`: distinct full project numbers.
- `meta.distinct_awards`: distinct core project numbers; use this for an award count unless the question explicitly asks for another unit.
- `grant_count` in trends: project-year rows for that fiscal year, not lifetime awards.
- `reported_grant_count`: rows with reported award amounts; it is not necessarily the number of distinct awards.
- `ic_topic_cross.total_grants`: distinct non-null core awards after the endpoint's RPG-research filter. It is not the number of project-year rows despite the field name.

When reproducing `distinct_awards`, use distinct non-null `core_project_num` values. SQL `COUNT(DISTINCT ...)` excludes null; a Python set containing `None` otherwise adds a false extra award.

A full `project_num` preserves application type, activity, IC, serial number,
support year, and supplement suffix. A `core_project_num` intentionally collapses
many of those annual/administrative variants. Use the former for citations and
the latter for distinct-award grouping; never substitute one unit for the other.

## Response-field interpretation

| Field | Unit | Correct rendering | Common error |
|---|---|---|---|
| `meta.total` | Application/project-year rows | “1,416 matching rows” | Calling them 1,416 grants |
| `meta.distinct_awards` | Distinct non-null core project numbers | Preferred award count | Recomputing with `None` as one award |
| `meta.total_funding` | Full matching-slice row sum of reported nominal dollars, or null when none reported | Reconcile custom pagination to it; audit repeated project numbers; preserve all-null as “not reported” | Calling a parent-plus-components row sum unique-award funding, or converting null to $0 |
| `reported_grant_count` | Rows with non-null award amount | Report coverage as reported/total | Treating missing rows as $0 |
| `ic_topic_cross.total_grants` | Distinct RPG core awards | “226 distinct RPG awards” | Calling it 226 project-year rows |
| `mechanism_mix.classes[].share` | Fraction from 0 to 1 | `0.528174` → 52.82% | Printing 0.53% |
| `funding_growth.yoy_growth_pct` | Percent | `-2.6835` → −2.68% | Multiplying by 100 again |
| `funding_growth.cagr_pct` | Percent | `3.9084` → 3.91% per year | Treating it as a fraction |
| `institution_concentration.gini` | Fraction from 0 to 1 | Report with method and institution count | Converting to the HHI scale |
| `institution_concentration.top5_share` | Fraction from 0 to 1 | `0.110852` → 11.09% | Printing 0.11% |
| `institution_concentration.hhi` | 0–10,000 scale | Compare like-for-like years | Applying antitrust thresholds as a policy conclusion |

## Funding scopes

- `funding_trend`: all mechanisms.
- `topic_trend`: matching rows across all mechanisms.
- `rank_institutions` and `institution_concentration`: competitive RPG research.
- `mechanism_mix(entity_id=...)`: the named institution's whole NIH-administered portfolio.
- `mechanism_mix(entity_id omitted)`: system-wide RPG research.
- `get_institution_profile.profile.mechanism_mix`: the resolved entity's whole NIH-administered portfolio.
- `get_institution_profile.profile.funding_trend` and `top_pis`: RPG research only.

Never calculate a share using a numerator and denominator drawn from different scopes.

`get_institution_profile` applies one requested fiscal-year window to all sections, but that does **not** make the sections scope-compatible. Treat it as a multi-scope container. Also distinguish `rank_institutions` campus-family rollups from the single canonical entity used by profiles, growth, mechanism mix, and concentration.

## Pagination and reconciliation

`search_grants` returns at most 50 rows per call and rejects offsets above 100000. Therefore one unpartitioned query can fully expose at most 100,050 rows. For custom aggregation:

1. Save `meta.total`, `meta.total_funding`, and `meta.reported_grant_count` from the first page.
2. If `meta.total > 100050`, stop. Narrow the window/filter or partition by non-overlapping fiscal years (and IC/activity if needed); reconcile every partition independently before combining it.
3. Fetch offsets `0, 50, 100, ...` until the collected row count equals `meta.total`.
4. Assert the collected row count equals `meta.total` and the number of non-null `award_amount` values equals `meta.reported_grant_count`.
5. When reported count is positive, sum non-null amounts and assert equality with `meta.total_funding`. When it is zero, assert `meta.total_funding is null`; do not use Python's empty-sum value `0` as a funding result.
6. Count distinct non-null `core_project_num` values and reconcile to `meta.distinct_awards`.
7. If any check fails, do not publish the custom aggregate; retry once and report the inconsistency if it persists.

## Multi-component funding protocol

One full project number can appear on a parent row and several component rows in
the same fiscal year. The service's row-sum metadata can reconcile perfectly and
still overstate unique-award dollars. In the verified FY2026 U54 case,
`1U54AG099000-01` returned seven rows: a $1,499,966 parent plus six component
allocations summing to the same $1,499,966, so `meta.total_funding` was
$2,999,932.

For every repeated non-null `project_num`:

1. compare `meta.total` with `meta.unique_project_nums`; a larger row count proves repetition somewhere in the full slice even when pagination hides the duplicate;
2. separate the canonical parent row from component titles;
3. compare parent amount, component sum, and `meta.total_funding`;
4. call `fetch` and inspect `metadata.matching_rows`;
5. report the canonical parent amount and component allocations separately when they reconcile;
6. never label the raw row sum as unique-award funding; withhold a unique total if the parent/component structure is ambiguous.

Treat every PI profile's `grant_count`, `active_grants`, and `total_funding` as
row-level fields. Official-detail joins can copy the parent amount to several
component rows and inflate them, while pagination can hide the repeated number.
Preserve the raw fields for audit, but do not use them as distinct-award facts
until reconciled through `search_grants` and `fetch`.

## Topic-query protocol

1. Start with the user's exact term.
2. List material synonyms, legacy names, acronyms, and spelling variants.
3. Run separate `topic_trend` or `search_grants` calls when OR logic is needed; do not add their totals until deduplicating project identifiers within each fiscal year.
4. Inspect titles from each query variant for precision.
5. Treat a short acronym as high collision risk. Inspect whether it appears as a substring of an unrelated word or as a person's name; `PASC` matched *PASCALL* and a surname in the verified Long-COVID case.
6. Use `ic_topic_cross(match_strategy="auto")` and report whether OpenNIH selected RCDC or text matching.
7. If RCDC was selected, inspect `matched_rcdc_categories`. Remove generic suffixes such as “disease,” “disorder,” “syndrome,” or “research” from the probe and rerun when they produce unrelated category labels. Example: `Alzheimer` is a safer RCDC probe than `Alzheimer's Disease`.
8. When policy conclusions depend on classification, run both forced `rcdc` and forced `text`. Present them as separate surfaces; never add or splice their totals.
9. Present a primary definition and a query-sensitivity range when terminology changes the result materially.
10. `ic_topic_cross(ic="ALL")` is one combined all-IC result. To rank ICs, fully paginate `search_grants`, select all rows or `comparable=true` RPG rows explicitly, group `ic`, and reconcile count, distinct awards, reported rows, and dollars. Match the RPG filter when comparing with `ic_topic_cross`.
11. `topic_trend` returns only years with matches. An empty `data` list means no matching rows were returned for the window; it is not a zero-filled annual series. Check source coverage before filling covered, omitted years with zero match counts in a derived chart.

### RCDC decision table

| Runtime result | Interpretation | Action |
|---|---|---|
| `match_strategy="text"` | Title-keyword surface; not official categorization | Inspect titles and test synonyms |
| `match_strategy="rcdc"`, categories precise | Official RCDC-tag surface for the reported window | Report categories and coverage |
| RCDC categories include unrelated generic labels | Query-to-category match is noisy even though RCDC tags are official | Rerun a distinctive seed; show both category lists if material |
| Window coverage below threshold | Auto may fall back to text | Report coverage and avoid an RCDC absence claim |
| Forced RCDC and text totals differ | They measure different concepts | Keep both; do not select whichever supports the narrative |
| Forced RCDC, window ends before FY2008 | Coverage-floor zero; no service-surface rows exist | Read `no_match_note`/`alternate_surface_grants`; retry auto/text or extend the window |
| Forced RCDC, modern covered window, no matched categories | Controlled-vocabulary gap, not topic absence | Read `no_match_note`; compare `alternate_surface_grants`; rerun auto/text |

## PI-disambiguation protocol

1. Try surname or `LAST, FIRST`; the corpus display form commonly uses that order.
2. If `First Last` returns zero, reverse it and retry surname-only. A broad first-name query can return thousands of unrelated rows.
3. Collect all `pi_profile_id` values returned across candidates.
4. Compare display name, institution, project titles, ICs, and fiscal years. Ask the user only if more than one plausible identity remains.
5. Call `get_pi_profile` with the selected ID. The profile headline name and institution follow the PI's latest grant.
6. For a zero-result year window, use `meta.total_grants == 0` and `meta.fiscal_year_start/end`; profile identity may remain populated while profile totals and year fields are null.
7. `official_detail_source_loaded=true` is a server-level capability flag. Check the returned detail fields and `source_status` year coverage before claiming official details or linked publications are complete.
8. For public expert discovery, aggregate only topic-matching rows and compare distinct awards, mechanisms, titles, institutions, and recency. Do not rank by dollars alone: one large coordinating-center or intramural award can dominate. Label the output “research-contact candidates,” not clinicians, mentors, or best experts.
9. The same normalized historical PI name and institution can map to several profile IDs because source identifiers drift. Treat them as candidate fragments, inspect overlapping grants and profile provenance, and never add profile totals merely because the labels match.
10. The current profile contract has no `publications` field. A missing field is unavailable data, not zero publications. Collaborators are shared-award participants, not verified coauthors, mentors, or direct collaborators.

## Funding-to-output protocol

Use a staged link rather than a topic-only narrative:

1. Start with the full and core NIH project numbers from verified OpenNIH rows.
2. Query PubMed's Grant Number field with the exact identifier. Preserve every PMID and article type. Grade an exact grant-number association X1, while stating that acknowledgment/attribution is not proof the grant caused the result.
3. Retrieve publication details from PubMed/PMC/OpenAlex. Use iCite only for clearly labeled bibliometric context. APT is a model-derived indicator, not a literal probability of translation, approval, or commercial success.
4. Search ClinicalTrials.gov for the exact grant number before disease or intervention terms. Exact zero means no exact link was found in that query, not that no related trial exists.
5. Treat disease/topic trial hits as X3 candidates. Search summaries can contain null sponsor, enrollment, phase, and intervention fields even when the study record has them; call the study-detail tool for every NCT ID cited.
6. Search patents or other outputs only when the required source and credentials are available. Name an unavailable source explicitly instead of silently omitting it.

Minimum evidence table columns are award identifier, output identifier, output
type/date, match method, evidence grade, verified detail source, and limitation.

## Institution-comparison protocol

1. Use the same fiscal-year window and the same ranking sort for every institution.
2. Resolve each institution to `entity_id` via `rank_institutions`.
3. Compare profiles, mechanism mix, or growth using the same funding scope.
4. Check entity-resolution notes. Campus-family rollups and canonical entities can differ across endpoints.
5. Avoid per-capita or productivity claims unless staff, faculty, publication, or trial denominators come from a separately documented source.
6. Convert mechanism `share` fractions to percentages, and label the mechanism total as all-mechanism.
7. Treat `cagr_pct` and `yoy_growth_pct` as already-percent values, and label growth as RPG-research.
8. Use `sort_by="funding_scale"` for a top-funded table. The default composite score mixes funding scale, portfolio breadth, new-grant activity, and average award size, so its order answers a different question.
9. Treat `search_grants(institution=...)` as raw-name discovery. Inspect all returned `org_name` values; a substring such as `Harvard` can span several separately ranked entities.
10. For FY1985–1998, do not publish `rank_institutions` funding or composite results until a representative ranking row reconciles with its institution profile/growth and the main funding surface reports dollar coverage. The verified deployment returned positive ranking dollars while all those other endpoints returned null.

## Concentration protocol

1. Use single-year snapshots for temporal comparisons; a multi-year window pools funding and answers a different question.
2. Report Gini, HHI, top-five share, total institutions, RPG-research scope, and entity-resolution method together.
3. Convert top-five share to percent; leave HHI on its 0–10,000 scale.
4. Interpret Gini jointly with top-five share and institution count. A high Gini can coexist with an approximately 11% top-five share because of a long tail of small recipients.
5. Do not infer competition quality, geographic fairness, or policy optimality from concentration metrics alone.
6. If `total_institutions=0` and Gini/HHI/top-five share are null, report the concentration metric as unavailable because no recorded-dollar denominator survived; do not render zeros.

## IC and mechanism protocol

- Prefer an IC abbreviation such as `NCI`; preserve `ic_scope.kind`, `n`, and `matched_ic_names` to show how the alias resolved. A `fragment` scope is an arbitrary inspected subset, potentially with repeated modernized names, not an exact IC match. If `n != len(matched_ic_names)`, report the contract mismatch; also report the unique displayed-name count rather than silently deduplicating or choosing one number.
- Historical IC display labels can be modernized. A modern alias can resolve to several raw labels, and an obsolete abbreviation can resolve to none. Do not perform historical institutional analysis from display names alone; document the returned scope and use an external historical crosswalk when organizational lineage matters.
- `activity_code_distribution` counts project-year rows and returns recorded totals by mechanism class; it does not return distinct awards or per-class reported-row coverage.
- Derive class shares only when the denominator uses the same endpoint, window, IC scope, and reported-dollar basis.
- For a complete single-year all-mechanism slice, the sum of class counts and class funding should reconcile to the same-window `funding_trend` row. If it does not, stop and inspect scope, partial-year state, and service changes.

## Small-business protocol

1. Run identical topic queries for all four activity codes: R41/R42 are STTR
   Phase I/II and R43/R44 are SBIR Phase I/II. A zero in one code is a
   mechanism/query result, not evidence that no small-business work exists.
2. Test an exact public phrase plus material technical synonyms. In the
   verified FY2025 case, *artificial intelligence* and *machine learning*
   returned disjoint title-matched small-business award sets.
3. Combine rows only after deduplicating non-null `core_project_num` values.
   Report project-year rows separately; one core can have multiple rows in one
   code and year.
4. Inspect company, title, IC, full project number, and award amount. The raw
   organization is the award recipient at that time, not evidence of current
   corporate status or ownership.
5. Do not divide R44 by R43 or R42 by R41 to estimate phase conversion. The
   returned annual populations are not linked originating cohorts and can
   contain continuing awards.
6. Route commercialization, patents, trials, regulatory status, company
   survival, and market-size questions to independently verified sources.

## Geography and award-lineage protocol

`search_grants(institution=...)` is a case-insensitive substring over raw
`org_name`. It is not a geographic filter. A state/city string both omits local
institutions whose names lack that word and can include a word without proving
the award site's current location. OpenNIH grant-query rows expose no state,
city, ZIP, congressional district, or beneficiary geography. `source_status`
may list underlying source columns such as `org_city` and `org_state`; a column
inventory does not make those fields queryable or returned by `search_grants`.

For a geographic portfolio:

1. resolve intended organizations to canonical entities;
2. join them to a dated, cited institution-location source;
3. publish matched and unmatched entity counts and any campus rule;
4. distinguish recipient location from research site and beneficiary location;
5. withhold the geographic total if the external join is absent or materially incomplete.

For award history, group by non-null `core_project_num` but retain every full
`project_num`, fiscal year, organization, and amount. Application type 7 can
mark a grantee-institution transfer; supplements and transfers can create more
than one row for one core in a fiscal year. Count the core once when answering
“how many awards,” but do not discard legitimate row-level dollars. Fetch one
of the full project numbers; `fetch(core_project_num)` returns an actionable
error because a core ID is not a citation record.

## Citation-shaped search

`OpenNIH_search` canonicalizes matching records to project-level citations. In a multi-component award, the matching component title can be replaced by the parent project's canonical title. The hit is still useful for citation and `fetch`, but the visible title/text may not show the query terms.

Before treating a citation hit as representative evidence:

1. rerun the concept with `search_grants`;
2. locate the matching full/core project identifier;
3. inspect the actual matching component title;
4. use `search`/`fetch` only for the canonical citation and URL.

## Freshness and coverage

Call `OpenNIH_source_status` at analysis time rather than copying a fixed snapshot date into the report. The main project corpus and official detail/publication sidecars can have different fiscal-year coverage. A grant added to RePORTER after the snapshot cutoff may be absent from OpenNIH; report it as absent from the checked snapshot, not nonexistent.

For the latest fiscal year, inspect `funding_trend.data[].partial`; a current-year project shard, official-detail sidecar, or weekly refresh is evidence of availability, not full-year completeness.

`funding_growth` does not repeat that partial flag. Join its years to `funding_trend`; if the endpoint year is partial, withhold YoY/CAGR interpretation or rerun through the latest completed year. In the verified FY2025–2026 case, the raw RPG CAGR was −26.33% solely across a window whose endpoint was marked partial, so it was not evidence of a completed-year decline.

For an exact absence:

1. Validate the full project-number form.
2. Run `search_grants(project_num=...)`.
3. If zero, run `fetch(id=...)` only as a canonical-record check; preserve its error message.
4. Read `source_status` and say “not found in this snapshot/query.”
5. Do not turn a zero result into “NIH never awarded this project” without a separately verified live authoritative source.

## Failure handling

| Failure | Retry | Then |
|---|---|---|
| Timeout, HTTP 429, or 5xx | Once | Report OpenNIH unavailable and preserve the requested scope |
| Validation error | No blind retry | Correct parameter shape, year order, ID, or bound |
| Unknown or misspelled parameter | No retry | Correct the parameter name; never accept a successful response whose intended filter was silently ignored |
| Zero results | Try documented name/query variants | Report zero with source status and query definition |
| RCDC category noise | Rerun distinctive seed and forced text | Present surfaces separately |
| Pagination reconciliation failure | Retry the full slice once | Do not publish the derived aggregate |
| `meta.total > 100050` | Do not page blindly | Partition into non-overlapping, individually reconciled slices |
| All dollar values null | No retry unless unexpected | Report counts only; keep dollars, shares, growth, and concentration unavailable |
| Historical ranking dollars disagree with profiles/main surface | Retry once and inspect source state | Quarantine the funding/composite ranking; report the endpoint divergence |
| Missing sidecar years | No retry | Use main-corpus fields only and record the gap |

## Cross-source evidence grades

- **F1 direct:** an OpenNIH row or endpoint aggregate with its returned scope.
- **F2 derived:** a calculation whose pages, units, and reconciliation checks are reported.
- **X1 exact link:** a stable grant, PMID, trial, patent, ORCID, or other identifier joins sources.
- **X2 resolved entity:** a normalized PI or institution match with corroborating fields and time overlap.
- **X3 candidate:** name or topical similarity only; never present as attribution.

Preserve the original identifiers and URLs in the report so users can audit every link.
