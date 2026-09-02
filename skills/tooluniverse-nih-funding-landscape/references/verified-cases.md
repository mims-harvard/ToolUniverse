# Verified OpenNIH Case Patterns

These cases were exercised against the deployed OpenNIH MCP service. Use them as workflow regressions and response-shape examples, not as frozen statistics: rerun the tools for current values.

## Contents

- [Case matrix](#case-matrix)
- [Reusable assertions](#reusable-assertions)
- [Public-value regressions](#public-value-regressions)
- [Live regression](#live-regression)

## Case matrix

| Case | Real inputs | Tool path | Contract behavior verified |
|---|---|---|---|
| Topic growth | `CRISPR`, FY2012–2025 | `source_status` → `search_grants` → `topic_trend` → `ic_topic_cross` | Title trend, full-slice metadata, pagination reconciliation, text fallback |
| Query sensitivity | `CRISPR`, `gene editing`, `CRISPR-Cas9` | Separate `topic_trend` calls | Variant totals overlap and must not be added |
| RCDC classification | `Alzheimer's Disease`, `Alzheimer`, forced `rcdc` and `text` | `ic_topic_cross` | Generic category words create noisy matched-category lists; RCDC and text totals differ |
| Institution comparison | Johns Hopkins vs University of Pennsylvania, FY2020–2025 | `rank_institutions` → profile → mechanism mix → growth | Entity-ID discovery, family-rollup caveat, mixed profile scopes, fraction/percent units |
| PI identity | Michelle Bretl | `search_grants` name variants → `get_pi_profile(78918667)` | `First Last` can miss; surname and `LAST, FIRST` resolve; zero-year window remains a successful identity lookup |
| PI window leakage | Eileen Crimmins, FY2100 | `get_pi_profile(1891769)` | Grants and totals are empty for the window while four collaborators remain; collaborator edges are not year-filtered |
| Misspelled filter | `fiscal_yaer_start=2025` | Raw `search_grants` MCP request | The server ignores the unknown field and widens the slice; ToolUniverse schemas must reject additional properties locally |
| Concentration | FY2000, 2010, 2020, 2025 | Repeated `institution_concentration` | Gini/top-five fractions, HHI scale, single-year comparability, changing institution denominator |
| Exact award | `1F31DC023096-01` | Exact search → fetch | Search row and canonical citation record agree; fetch supplies the public URL |
| Snapshot absence | `1F31DC023096-99` | Exact search → fetch → source status | Valid-shaped nonexistent suffix produces zero search plus actionable fetch error, not proof of nonexistence |
| Mechanism portfolio | NIH and NCI, FY2025 | `activity_code_distribution` | IC alias resolution and project-year mechanism counts; no distinct-award or class-level coverage fields |
| Cross-endpoint topic units | `CRISPR`, FY2020–2025 | Full `search_grants` pagination → RPG filter → `ic_topic_cross(ALL)` | `total_grants` is distinct RPG core awards; `ALL` is one combined scope, not an IC ranking |
| Canonical component collapse | `genomics core`, FY2026 | `search` ↔ `search_grants` | Citation search can show a parent title without the query words even though a component title matched |
| Institution substring collision | `Harvard`, FY2025 | `search_grants` → paginated `rank_institutions` | One raw-name query spans several separate canonical entities |
| Ranking objective | FY2025 | `rank_institutions` with `composite`, `funding_scale`, `avg_award_size` | Different sort objectives return different orders; only `funding_scale` means top-funded |
| Historical IC alias | `NIADDK`, `NIDDK`, `NIAMS`, FY1985–1986 | `search_grants` with each IC filter | Legacy and modern labels are not a safe historical crosswalk |
| Current-year completeness | FY2025–2026 | `source_status` → `funding_trend` | A loaded/refreshed FY2026 shard still returns `partial=true` |
| Mechanism reconciliation | FY2025 | `activity_code_distribution` ↔ `funding_trend` | Same-window all-mechanism class sums reconcile to annual counts and recorded dollars |
| All-null dollar slice | `cancer`, FY1985 | `search_grants` ↔ `topic_trend` ↔ `funding_trend` | Counts exist while all dollars remain null; an empty non-null sum is not $0 |
| Pagination ceiling | `cancer` and institution `University`, all years | `search_grants` | 144,899 and 1,889,182 rows exceed the 100,050-row retrievable window |
| Historical RCDC floor | `Alzheimer`, FY1985–1990 | forced `rcdc` ↔ `auto` | Forced RCDC zero is a coverage-floor result; auto falls back to 137 text-matched RPG awards |
| Partial-year growth | FY2025–2026 | `funding_growth` ↔ `funding_trend` | Growth returns −26.33% without a partial flag, while the endpoint year is partial |
| Empty topic series | nonsense seed, FY2024–2026 | `topic_trend` | A wholly unmatched window returns `data=[]`, not zero-filled years |
| Ambiguous IC fragment | `National Institute`, FY2025 | `search_grants` | Fragment reports `n=26`, 25 list entries, and 17 unique modernized names—not one exact IC |
| Historical ranking divergence | FY1985 and FY1998 | rank ↔ search/profile/growth/concentration | Ranking shows positive dollars while the other dollar surfaces are null |
| Rare-disease public map | `Friedreich ataxia`, FY2015–2025 | Full search pagination → title/mechanism/PI inspection → profile | Funding-only PI order can elevate one intramural core award over investigators with several topic-research awards |
| Headline outlier audit | `maternal mortality`, FY2015–2025 | Full search pagination → activity/IC decomposition → forced text/RCDC | One OT2 coordinating-center award accounts for 83.77% of title-search dollars; R01 leads by distinct awards |
| Acronym collision | `long COVID`, `PASC`, and specific sequelae phrases, FY2020–2025 | Separate search slices → title inspection | `PASC` matches unrelated words/names and produces an inflated total; synonym totals cannot be added |
| Career-mechanism interpretation | NIMH K23/K99/R00, FY2015–2025 | Exact-IC activity distributions | Annual mechanism rows show portfolio presence, not new awards, success odds, or K99-to-R00 cohort conversion |
| Broad technology classification | `gene therapy`, FY2015–2025 | forced text ↔ forced RCDC | RCDC category expansion includes broad adjacent fields and produces a much larger portfolio than literal titles |
| Geography false friend | `institution=Massachusetts` and `Boston`, FY2025 | raw institution search/provenance inspection | Place strings filter organization names, not locations; grant rows expose no geographic fields |
| Modern RCDC vocabulary gap | `health equity`, FY2015–2025 | auto/text ↔ forced RCDC | Forced RCDC zero plus 112 alternate text awards means no exact category match, not no funding |
| Small-business synonym split | `artificial intelligence` and `machine learning`, R41/R42/R43/R44, FY2025 | exact activity searches → core deduplication | Technical synonyms return different company/award sets; rows and core awards differ |
| Historical terminology drift | `HIV`, `AIDS`, and combined terms, FY1985–2005 | separate topic trends | The dominant title term reverses over time; early dollars remain null |
| Award transfer lineage | Marek Napierala / `R01NS121038`, FY2021–2025 | PI disambiguation → full-number rows → fetch | Five annual full project numbers, two institutions, and one core award; core ID is not fetchable |
| PI surname collision | `Napierala`, FY2010–2025 | broad PI search → exact-name/profile disambiguation | One surname spans four profile IDs and must not be merged |
| Multi-component double count | `1U54AG099000-01`, FY2026 | exact search → component reconciliation → fetch | Parent and six components each sum to $1,499,966; row-sum metadata is exactly twice unique parent dollars |
| PI profile component inflation | Eileen Crimmins profile `1891769`, FY2026 | profile → duplicate full-number audit → exact award search | Three U54 component rows repeat the official parent amount, inflating profile count and dollars |
| Shared-award network | Crimmins and Ailshire FY2026 profiles | PI profile collaborators → shared grant inspection | Collaborator edges mean co-association on an award, not direct collaboration or coauthorship |
| Historical profile fragmentation | Fauci and Baltimore, FY1985–1998 | broad PI search → profile-ID collection | One normalized name/institution can span multiple historical source IDs; profiles must not be summed |
| Exact publication attribution | `R01NS121038` | PubMed Grant Number → PMID details → iCite | Two exact grant-number-linked papers are X1 attribution; iCite metrics do not establish causal impact |
| Trial candidate separation | `R01NS121038` and `Friedreich ataxia` | exact trial search → topic search → study detail | Exact grant search is zero; 111 topical trials remain X3 candidates and require NCT detail retrieval |

## Reusable assertions

### Topic aggregation

- The first `search_grants` page's `meta.total_funding` describes the full slice, not the page.
- A complete page walk must reconcile row count, reported-row count, recorded dollars, and non-null distinct core awards.
- Representative records should include early, largest, and recent rows so an aggregate is not interpreted from one era.
- A slice above 100,050 rows cannot be completely walked because `offset=100000` succeeds and `offset=100001` is rejected. Partition by non-overlapping fiscal years and, if necessary, IC/activity; never derive a full-slice custom table from the reachable prefix.
- When `reported_grant_count=0`, require `total_funding=null`. Count rows and distinct awards normally, but represent funding as not reported rather than using Python's empty sum of zero.

The all-years `cancer` query returned 144,899 rows, while the raw institution substring `University` returned 1,889,182. Both exceed the paging ceiling. In contrast, `cancer` FY1985 was retrievable in principle and returned 1,434 rows, 1,163 distinct awards, zero reported amounts, and null total funding.

### RCDC behavior

`ic_topic_cross(query="Alzheimer's Disease", match_strategy="auto")` selected RCDC but returned a noisy category list containing many labels with “Disease.” Using `query="Alzheimer"` produced the precise Alzheimer/ADRD category family. The aggregate happened to remain the same in the verified run, but the category list itself must still be audited; do not assume that will hold for another topic.

Forced RCDC and title-text searches for `Alzheimer` returned materially different totals. This is expected because they are different evidence surfaces, not a reason to prefer the larger number.

For FY1985–1990, forced RCDC returned zero awards, null funding, an empty category list, and `alternate_surface_grants=137`. Its `no_match_note` explicitly said the service RCDC surface begins in FY2008. Auto correctly selected text and returned 137 distinct RPG awards, still with null dollars. The forced zero is coverage, not absence.

### IC-by-topic behavior

For CRISPR in FY2020–2025, complete pagination returned 938 all-mechanism project-year rows, 386 distinct core awards, and $413,532,496 in recorded nominal funding. Restricting those rows to `comparable=true` produced 575 RPG-research project-year rows, 226 distinct core awards, and $237,874,188. Those last two values exactly matched `ic_topic_cross(ic="ALL").total_grants` and `total_funding`.

This establishes two separate contracts: `total_grants` means distinct core awards, and `ALL` is a combined IC scope. The per-IC ranking had to be derived from the 575 fully paginated RPG rows; it was not present in the cross-tool response. Rerun before quoting the values because the public snapshot can change.

### Institution profile behavior

The institution profile response deliberately combines:

- all-mechanism `mechanism_mix`;
- RPG-research `funding_trend`;
- RPG-research `top_pis`.

For FY2020–2025, Johns Hopkins' mechanism mix returned `share=0.528174` for RPG research, which means 52.82%. University of Pennsylvania's `cagr_pct=3.9084` means 3.91% per year. These values verify the two different percentage conventions.

In the FY2025 collision probe, `search_grants(institution="Harvard")` returned 702 raw-name rows and its first page already contained `HARVARD MEDICAL SCHOOL`, `HARVARD UNIVERSITY`, and `HARVARD UNIVERSITY D/B/A HARVARD SCHOOL OF PUBLIC HEALTH`. The funding-scale ranking resolved these as separate entity IDs (ranks 62, 116, and 120 in that run), with additional unrelated names such as Harvard Pilgrim also matching the broader label. Never label the raw substring total as one institution's portfolio.

The FY2025 top five also changed order between `sort_by="composite"` and `sort_by="funding_scale"`; Johns Hopkins ranked second by composite score but fourth by funding. `avg_award_size` produced a very different small-recipient list. Report the selected objective in every ranking title.

### PI behavior

`pi_name="Michelle Bretl"` returned zero in the verified run, while `Bretl`, `BRETL`, `Bretl, Michelle`, and `BRETL, MICHELLE` resolved profile `78918667`. A first-name-only search returned thousands of rows and is unsuitable for identity resolution.

For a FY2024-only profile request, the resolved identity remained populated but `meta.total_grants=0`, the grant list was empty, and profile funding/year fields were null. Report the requested window from `meta`, not the profile headline.

The FY2026 Eileen Crimmins profile (`1891769`) reported four grant rows and
$4,680,010. Three rows shared `1U54AG099000-01` and each carried the same
$1,499,966 official parent amount; the fourth P30 row was $180,112. Therefore
the profile total equals its row sum but is not unique-award funding. Its four
returned collaborators were shared-award participants, not verified direct
collaborators. The endpoint returned no `publications` field; missing cannot be
reported as zero.

Historical identity probes also found five source profile IDs for the same
displayed Fauci name/institution and two for David Baltimore. Profile
provenance acknowledges normalized-name/institution source drift. Inspect
overlapping grants and keep fragments separate rather than adding their totals.

### Multi-component award behavior

Exact FY2026 search for `1U54AG099000-01` returned seven rows, one full project
number, and one core award. The $1,499,966 parent amount equaled the sum of six
component allocations, while `meta.total_funding=$2,999,932`. This proves that
successful row-count and row-dollar reconciliation does not establish a
deduplicated award total. `fetch` returned the parent amount and
`metadata.matching_rows=7`; its canonical amount and the component allocation
table must be reported separately. With `limit=1`, no duplicate was visible on
the page, but `meta.total=7` and `meta.unique_project_nums=1` still exposed the
full-slice repetition; warning logic must use metadata as well as page rows.

### Funding-to-output behavior

PubMed Grant Number search for `R01NS121038` returned PMID `37691621` (2023
primary research) and PMID `41514384` (2026 review). The exact identifier makes
each an X1 attributed output, not causal impact. iCite reported seven citations
and RCR 1.1272 for the older paper; APT and citation metrics remain model and
bibliometric context, not probabilities of translation or product success.

ClinicalTrials.gov returned zero studies for the exact grant number but 111 for
the disease term *Friedreich ataxia*. Those 111 are X3 topical candidates. The
search summaries omitted fields that were populated in detail; retrieving
`NCT04102501` established its Phase 3 design, completed status, enrollment of
65, RT001/placebo interventions, and Biojiva sponsorship. Cite trial facts only
from the detail record and do not attribute the study to the award.

### Concentration behavior

The verified snapshots showed `top5_share` near `0.11`, meaning about 11%, while Gini was above `0.83`. This is not contradictory: a long tail of small recipients can generate high inequality without the top five owning most funding. Report both metrics and the number of institutions.

FY1985 and FY1998 concentration returned null Gini/HHI/top-five share, an empty top five, `total_institutions=0`, and null funding because no recorded-dollar denominator survived on that surface. This is “metric unavailable,” not zero concentration. FY2000 produced populated metrics again.

### Canonical search behavior

For the FY2026 query `genomics core`, `search_grants` showed matching component titles such as `Core C: Computational Biology and 3D Genomics` and `Genomics and Modeling Core`. Citation-shaped `search` returned the same project IDs with canonical parent titles such as `Epigenetics of Aging and Age-Associated Diseases` and `Exploiting virus and host diversity to define mechanisms of cross-species infections`; the visible citation text did not contain both query words. Use the former to validate the match and the latter only as the canonical citation surface.

### IC history and latest-year behavior

In FY1985–1986, `ic="NIADDK"` resolved as an empty name fragment, `ic="NIDDK"` resolved as an alias over three raw-label entries rendered with the same modern name, and `ic="NIAMS"` resolved separately. The response provenance also warns that thousands of NIADDK-era rows render under a modern NIDDK label even though the historical institute later split across NIDDK and NIAMS. An external historical crosswalk is required for lineage claims.

The source snapshot checked on 2026-08-10 contained FY2026 project and sidecar shards, but `funding_trend` explicitly marked FY2026 `partial=true`. Availability, weekly refresh, and sidecar coverage do not make a current fiscal year final. For the completed FY2025 all-mechanism slice, summing every mechanism class returned exactly the same 76,224 project-year rows and $42,806,594,530 as `funding_trend`, providing a useful cross-endpoint regression.

The phrase `ic="National Institute"` resolved as `ic_scope.kind="fragment"` with `n=26`, but `matched_ic_names` contained 25 entries and only 17 unique modernized display names. This is a response-contract mismatch as well as an ambiguous filter. It must not be described as an exact IC or all NIH, and no single “number of ICs” should be inferred without qualification.

`funding_growth` over FY2025–2026 returned RPG totals of $21.06B and $15.51B with `cagr_pct=-26.3348`, but did not attach a partial flag. The same-window `funding_trend` marked FY2026 partial, so the apparent decline is not a completed-year growth conclusion.

### Historical ranking divergence

In the checked deployment, FY1985 `rank_institutions(sort_by="funding_scale")` reported Johns Hopkins at $60,061,510 with 403/403 rows reported. Yet the exact institution's FY1985 `search_grants`, profile, mechanism mix, and funding growth all returned null dollars; system `funding_trend` reported zero dollar-bearing rows, and concentration was unavailable. FY1998 showed the same pattern. FY1999 ranking returned null dollars, and FY2000 ranking/concentration again used populated main-surface amounts.

The most plausible explanation is a rank-specific historical enrichment or stale/materialized surface, but that is an inference because the response provenance does not disclose a separate basis. Treat FY1985–1998 ranking dollars and composite scores as quarantined until the service exposes their source or the values reconcile at runtime. Count-based award/breadth fields may be reported separately with the divergence noted.

### Empty topic behavior

A deliberately unmatched topic over FY2024–2026 returned `data=[]`. `topic_trend` does not create rows containing zero for requested years. A derived chart may fill an omitted year with zero matching rows only after confirming the project corpus covers that year; it must not imply that the endpoint returned an observed zero-dollar row.

### Public-value regressions

The fully reconciled Friedreich ataxia FY2015–2025 slice contained 97
project-year/component rows, 33 distinct awards, 94 reported-dollar rows, and
$49,287,379. A funding-only PI ranking placed an NCATS contact first because of
one intramural core award; investigators with multiple topic-research awards
became visible only after inspecting mechanisms, distinct awards, titles, and
recency. This is a research-network case, not a clinical-referral case.

The maternal mortality title slice contained 56 rows, 18 distinct awards, and
$156,022,863. One Westat OT2 coordinating-center award contributed
$130,698,674 (83.77%), while R01 represented eight of the 18 distinct awards.
Within the RPG endpoint, forced text returned 11 awards and $19,336,256; forced
RCDC returned 623 awards and $701,545,600. The public answer must show both the
outlier and the definition difference.

For Long COVID FY2020–2025, the literal title query returned 221 rows, 96
distinct awards, and $126,812,115. The acronym `PASC` returned 66 rows, 30
awards, and $854,676,643 while matching unrelated strings including *PASCALL*
and a surname. `post-acute sequelae` also matched Ebola; the SARS-CoV-2-specific
phrase was more precise. These query totals overlap and must not be summed.

For gene therapy FY2015–2025, forced RPG title text returned 524 awards and
$759,208,899, while forced RCDC returned 2,575 awards and $3,054,172,837. The
RCDC match expanded into categories such as Genetics, Immunotherapy, Macular
Degeneration, Neurodegenerative, and Regenerative Medicine. A larger official
classification surface is not automatically a better answer to the narrower
public question.

NIMH mechanism tests showed K23 rows of 149 in FY2015, 192 in FY2024, and 172
in FY2025; K99 rows changed from 29 to 22 between FY2015 and FY2025, while R00
changed from 36 to 49. These are annual project-year populations. They do not
track individual K99 recipients into R00 awards and cannot yield a conversion
rate or application success probability.

The FY2025 raw institution substrings `Massachusetts` and `Boston` returned
large, internally valid portfolios, but neither was geographic. Grant-query
rows had no city/state fields and the provenance described a raw
organization-name substring. `source_status` listed underlying location
columns, but they were not queryable or returned. Use a separate
institution-location crosswalk or withhold the local total.

For *health equity* FY2015–2025, auto/text returned 112 RPG awards and
$147,266,168. Forced RCDC returned zero, null funding, no categories, and
`alternate_surface_grants=112`; its note identified a controlled-vocabulary
gap. The related *health disparities* phrase produced 348 text awards versus
10,438 RCDC awards across 21 matched categories, proving that a nearby official
term is not a neutral substitute.

The FY2025 R41/R42/R43/R44 small-business probe returned five distinct awards
and $2,754,529 for *artificial intelligence*, versus 14 rows, 13 distinct
awards, and $9,272,436 for *machine learning*. The sets were disjoint in the
checked snapshot. All four codes and material synonyms are required, and the
R43/R44 or R41/R42 ratios are not phase-conversion estimates.

Historical title terminology changed sharply: FY1985 returned nine `HIV` rows
and 142 `AIDS` rows, whereas FY2005 returned 2,834 and 816. The early amount
fields were all null. A forty-year analysis must deduplicate multiple terms and
cannot calculate early nominal or real growth from missing dollars.

The surname `Napierala` returned 48 FY2010–2025 rows across four PI profile IDs.
After selecting Marek Napierala, 21 rows resolved to four core awards.
`R01NS121038` contributed five annual full project numbers and moved from UAB
to UT Southwestern through a type-7 transfer while remaining one core award.
Full project numbers fetched successfully; the core alone returned an
actionable full-number-required error.

A FY2100 window for PI profile `1891769` returned zero grants and null funding
but still returned four collaborator rows. The window applies to grants and
profile totals, not collaborator edges. A raw `search_grants` request with the
misspelled `fiscal_yaer_start` parameter also succeeded and returned an
all-years slice, confirming that client-side rejection of unknown parameters is
required to prevent silent scope widening.

See [public-value-cases.md](public-value-cases.md) for audience routing, complete
case narratives, and the public-facing answer contract.

## Live regression

Run the opt-in regression script from the repository root when changing this skill or the OpenNIH tool contract:

```bash
PYTHONPATH=src python skills/tooluniverse-nih-funding-landscape/scripts/verify_live_cases.py
PYTHONPATH=src python skills/tooluniverse-nih-funding-landscape/scripts/verify_live_contract.py
PYTHONPATH=src python skills/tooluniverse-nih-funding-landscape/scripts/verify_output_links.py
```

The script uses real public data and network calls. A failure can indicate a service change, snapshot change, transient transport issue, or a skill assumption that needs revision; inspect the response before updating expected behavior.
