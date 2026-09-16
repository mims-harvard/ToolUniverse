# Public-Value OpenNIH Cases

Use these cases when the audience is not already an NIH data specialist. The
product promise is not “search 40 years of grants.” It is “answer a public
decision question while showing the definition, evidence, uncertainty, and a
safe next action.”

Statistics below were verified against the deployed OpenNIH MCP snapshot on
2026-08-10–11. They are regression anchors, not permanent facts; rerun the same
queries before publishing current numbers.

## Contents

- [Audience-to-decision map](#audience-to-decision-map)
- [Case 1 — Rare-disease family](#case-1--rare-disease-family-map-the-friedreich-ataxia-research-network)
- [Case 2 — Maternal-health reporter](#case-2--maternal-health-reporter-explain-a-156m-headline)
- [Case 3 — Long-COVID fact-check](#case-3--long-covid-fact-check-reject-acronym-inflation)
- [Case 4 — Early-career researcher](#case-4--early-career-researcher-read-nimh-mechanism-activity-safely)
- [Case 5 — Technology strategist](#case-5--technology-strategist-audit-an-over-broad-gene-therapy-market-map)
- [Case 6 — Taxpayer](#case-6--taxpayer-audit-one-award-without-learning-nih-syntax)
- [Case 7 — Institution and policy audience](#case-7--institution-and-policy-audience-compare-portfolios-not-labels)
- [Case 8 — Local reporter](#case-8--local-reporter-refuse-fake-geography)
- [Case 9 — Health-equity advocate](#case-9--health-equity-advocate-diagnose-a-vocabulary-zero)
- [Case 10 — Biomedical entrepreneur](#case-10--biomedical-entrepreneur-build-an-ai-small-business-landscape)
- [Case 11 — Historical reporter](#case-11--historical-reporter-detect-hivaids-language-drift)
- [Case 12 — Taxpayer award lineage](#case-12--taxpayer-award-lineage-follow-one-core-across-institutions)
- [Case 13 — Expert discovery](#case-13--expert-discovery-disambiguate-a-shared-surname)
- [Case 14 — Multi-component award audit](#case-14--multi-component-award-audit-stop-a-2x-dollar-error)
- [Case 15 — Collaboration map](#case-15--collaboration-map-separate-shared-awards-from-direct-collaboration)
- [Case 16 — Funding-to-output chain](#case-16--funding-to-output-chain-link-papers-without-inventing-clinical-impact)
- [Public-facing answer contract](#public-facing-answer-contract)

## Audience-to-decision map

| Audience | Real decision | Useful OpenNIH answer | Required guardrail |
|---|---|---|---|
| Patient or family | Where is research on this condition active? | Topic-specific awards, recent institutions and investigators, representative project titles | This is a research map, not a doctor ranking, referral, treatment recommendation, or proof of clinical expertise |
| Patient advocate | Is a neglected topic gaining attention, and who could inform an advocacy agenda? | Reconciled trend, distinct awards, ICs, mechanisms, and concrete projects | Test synonyms; separate title text from RCDC; do not equate dollars with patient benefit |
| Journalist or fact-checker | Is a headline number real and what drives it? | Definition-sensitive totals, largest awards, outlier decomposition, public award links | Audit acronyms, canonical parents, multi-component awards, partial years, and null-dollar coverage |
| Researcher or trainee | Which labs and mechanisms are active in a field? | Topic-specific award history, recent activity, titles, and investigator/institution candidates | Funding is not scientific quality; a PI profile is not a complete publication record or evidence of mentorship capacity |
| Grant applicant | What funded precedents and mechanism patterns exist? | Comparable titles, ICs, activity codes, distinct award counts, and portfolio shifts | Awarded projects contain no rejected-application denominator, reviewer preferences, or individual success probability |
| Institution leader | How does our portfolio compare with peers? | Resolved-entity RPG trends, all-mechanism mix, growth, breadth, and concentration | Use identical windows/scopes; raw institution substrings and family rollups are not interchangeable |
| Policy or taxpayer audience | Where did public money go and how concentrated was it? | Nominal recorded dollars, award/project-year units, institution concentration, and audit-ready grant URLs | Do not convert missing dollars to zero, treat current years as final, or infer impact from spending alone |
| Translational team | Which funded projects merit literature, trial, or patent follow-up? | Exact awards and stable identifiers that seed downstream ToolUniverse searches | A grant-output association or later trial is not causal impact; grade every cross-source link |
| Local reporter or community | How much funded work is located here and who benefited? | Resolved institutions joined to a separately verified location source | A place word in an organization name is not geography; recipient, research site, participants, and beneficiaries differ |
| Biomedical entrepreneur | Which related small businesses and phase-labeled awards are active? | R41/R42/R43/R44 project records across collision-checked topic variants | Phase-code ratios are not conversion; awards do not prove commercialization, approval, survival, or market size |

## Case 1 — Rare-disease family: map the Friedreich ataxia research network

**Public question:** “Who is actually working on Friedreich ataxia, and where
is the research happening?”

**Verified path:** fully paginate
`search_grants(query="Friedreich ataxia", FY2015–2025)`, reconcile metadata,
inspect titles/mechanisms, and compare topic-specific investigator histories.

**Observed surface:** 97 project-year/component rows, 33 distinct core awards,
94 rows with reported dollars, and $49,287,379 in recorded nominal funding.
The title-keyword trend rose from four rows and $1,331,597 in FY2015 to a peak
of 12 rows and $7,218,058 in FY2022; FY2025 returned eight rows and $3,626,987.
The RPG-text slice contained 24 distinct awards and $30,670,070. Its leading
institutions included Children's Hospital of Philadelphia (five distinct RPG
awards), Weill Cornell (three), and the University of Alabama at Birmingham
(four).

**Why it is useful:** a family or advocacy group gets a concrete, inspectable
map of research projects and organizations rather than a generic web search.
For research collaboration, Marek Napierala's 16 topic rows covered three
research awards through FY2025, while Ronald Crystal's rows covered two
AAV-therapy awards. Elizabeth Ottinger had the largest topic-linked dollar
total in the returned PI field, but it came from one NCATS intramural core
award. That contrast proves why “most dollars” is not a safe expert ranking.

**Boundary:** call these people topic-linked research contacts, not the best
clinicians. Inspect mechanisms, distinct awards, titles, and recency before
ranking; do not infer patient-care expertise. In the tested window, PI profiles
returned no publications or collaborators, so those sections were explicitly
incomplete.

## Case 2 — Maternal-health reporter: explain a $156M headline

**Public question:** “Did NIH put roughly $156 million into maternal mortality
research, and what does that number actually represent?”

**Verified path:** fully paginate title search, decompose by activity/mechanism
and IC, then compare forced text and RCDC in `ic_topic_cross`.

**Observed surface:** the all-mechanism title search for FY2015–2025 returned 56
rows, 18 distinct awards, and $156,022,863, with all 56 row amounts reported.
One core award—Westat's `OT2HL158287`, the NHLBI Maternal Morbidity and
Mortality administrative coordinating center—accounted for seven rows and
$130,698,674, or 83.77% of the title-search dollars. By distinct awards, R01
was more common: eight of 18 awards, versus one OT2 award.

Within the comparable RPG slice, forced title text returned 11 distinct awards
and $19,336,256. Forced RCDC used the categories *Infant Mortality*, *Maternal
Health*, and *Maternal Morbidity and Mortality* and returned 623 distinct awards
and $701,545,600. Both are valid surfaces with different definitions.

**Why it is useful:** the tool can turn a sensational total into an honest
explanation: one coordinating-center award dominates the dollar figure, the
common award mechanism is different from the dollar-dominant mechanism, and
the official classification is much broader than literal titles.

**Boundary:** do not say OT2 is the usual path for applicants, that R01 has a
higher success rate, or that either total measures maternal-health outcomes.

## Case 3 — Long-COVID fact-check: reject acronym inflation

**Public question:** “How much did NIH fund for Long COVID?”

**Verified path:** run separate title queries for `long COVID`, `PASC`,
`post-acute sequelae`, and `post-acute sequelae SARS-CoV-2`; inspect records and
never add the query totals without identifier deduplication.

**Observed surface for FY2020–2025:** `long COVID` returned 221 rows, 96
distinct awards, and $126,812,115. `PASC` returned only 66 rows and 30 awards
but $854,676,643 because it included false-positive strings such as *PASCALL*
and a person's surname. `post-acute sequelae` also included non-COVID sequelae,
including Ebola. The more specific `post-acute sequelae SARS-CoV-2` returned 25
rows and 11 awards.

**Why it is useful:** this is a public fact-checker that exposes why a plausible
acronym can produce a wildly inflated number. It also identifies multi-component
RECOVER-style awards whose row funding needs structural inspection.

**Boundary:** do not publish an acronym-only total or sum synonym totals.
Report each query's definition and deduplicate stable award identifiers before
constructing a union.

## Case 4 — Early-career researcher: read NIMH mechanism activity safely

**Public question:** “Is NIMH using K23, K99, and R00 mechanisms, and what does
the recent landscape look like?”

**Verified path:** use exact `ic="NIMH"` plus `activity_code` grant searches by
year, preserve project-year units, and compare each mechanism separately. Use
`activity_code_distribution` only for the broader mechanism-class context.

**Observed surface:** K23 project-year rows rose from 149 ($24,272,040) in
FY2015 to 192 ($33,346,007) in FY2024 and 172 ($31,890,121) in FY2025. K99
returned 29 rows in FY2015 and 22 in FY2025; R00 returned 36 and 49,
respectively. The FY2025 NIMH portfolio contained 410 career project-year rows
and $73,741,611, alongside 2,075 research rows and $1,269,161,598.

**Why it is useful:** a trainee can see that these mechanisms are present,
their relative annual footprint, and relevant funded precedents before reading
NOFOs and official eligibility rules.

**Boundary:** annual rows are not new-award counts. K99 and R00 are separate
annual populations, not a tracked cohort, so their ratio is not a conversion
rate. OpenNIH cannot estimate application odds.

## Case 5 — Technology strategist: audit an over-broad “gene therapy” market map

**Public question:** “Which NIH-funded institutions lead gene therapy?”

**Verified path:** inspect the query-to-RCDC category expansion and compare
forced text with forced RCDC before ranking institutions.

**Observed surface for FY2015–2025:** forced RPG title text returned 524
distinct awards and $759,208,899. Forced RCDC returned 2,575 awards and
$3,054,172,837 because the matched category list expanded beyond *Gene
Therapy* and *Gene Therapy Clinical Trials* to broad areas including
*Genetics*, *Immunotherapy*, *Macular Degeneration*, *Neurodegenerative*, and
*Regenerative Medicine*.

**Why it is useful:** the service can prevent a business, policy, or partnership
team from mistaking the largest available number for the most relevant one.

**Boundary:** audit and, when needed, narrow the category family. Do not title
the broad RCDC ranking “gene-therapy leaders” unless every included category is
accepted and disclosed.

## Case 6 — Taxpayer: audit one award without learning NIH syntax

**Public question:** “What is NIH award `1F31DC023096-01`, and where is the
official public record?”

**Verified path:** exact `search_grants(project_num=...)` followed by `fetch`.
The search row supplies the project-year evidence; the fetch record supplies a
canonical citation and public URL.

**Why it is useful:** any member of the public can move from an opaque grant
number to an audit-ready title, PI, organization, year, amount basis, and public
source. A nonexistent suffix such as `-99` returns a useful not-found result
rather than being silently conflated with the real `-01` record.

**Boundary:** “not found in this snapshot/query” is not proof that an award
never existed. Check source status and preserve the requested full project
number.

## Case 7 — Institution and policy audience: compare portfolios, not labels

**Public question:** “Which institutions receive the most NIH research funding,
and is funding becoming more concentrated?”

**Verified path:** use `rank_institutions(sort_by="funding_scale")` to resolve
entity IDs; compare identical single-year concentration snapshots; use profiles
only with their section-specific scopes.

**Observed behavior:** the FY2025 composite and funding-scale top-five orders
differed, so the default composite cannot be called “top funded.” A raw
`institution="Harvard"` search spanned Harvard Medical School, Harvard
University, the public-health school, Harvard Pilgrim, and other names. In
concentration results, a Gini above 0.83 coexisted with a top-five share near
11%, reflecting a large long tail rather than top-five dominance.

**Why it is useful:** leaders and policy reporters can reproduce a fair peer
comparison and understand concentration through several measures instead of a
single league table.

**Boundary:** report the ranking objective, entity definition, RPG scope,
institution count, Gini, HHI, and top-five share. Historical FY1985–1998 ranking
dollars remain quarantined because they diverge from other OpenNIH dollar
surfaces.

## Case 8 — Local reporter: refuse fake geography

**Public question:** “How much NIH money came to Massachusetts or Boston in
FY2025?”

**Verified path:** inspect `search_grants(institution=...)` results and
provenance before treating a place word as a location.

**Observed behavior:** `institution="Massachusetts"` returned 2,046 rows, 1,694
distinct awards, and $1,069,595,692; `institution="Boston"` returned 1,324
rows, 1,119 awards, and $665,538,526. Neither is a geographic total. The filter
is a raw organization-name substring: it finds names such as Massachusetts
General Hospital or Tufts University Boston, but omits Massachusetts recipients
whose names contain neither word. Grant-query rows do not expose city, state,
ZIP, congressional district, or beneficiary geography. `source_status` lists
underlying `org_city` and `org_state` columns, but those fields are not returned
or queryable through `search_grants`; a source-column inventory is not a
geographic analysis surface.

**Why it is useful:** an honest refusal prevents a locally compelling but
methodologically false headline. OpenNIH can supply the award portfolio after
institutions are resolved; a cited institution-location crosswalk must supply
the geography.

**Boundary:** distinguish recipient address, research site, and people served.
Report external-join coverage and unmatched institutions before publishing a
state, city, rural, or district total.

## Case 9 — Health-equity advocate: diagnose a vocabulary zero

**Public question:** “Does a zero RCDC result mean NIH funded no health-equity
research?”

**Verified path:** compare auto, forced text, and forced RCDC in the same RPG
FY2015–2025 window; inspect categories, alternate-surface count, and note.

**Observed surface:** auto selected text and returned 112 distinct RPG awards
and $147,266,168. Forced RCDC returned zero awards and null funding because
*health equity* names no exact official RCDC category; its response explicitly
reported `alternate_surface_grants=112`. For the related but broader phrase
*health disparities*, forced text returned 348 awards and $648,530,412, while
RCDC expanded across 21 categories and returned 10,438 awards and
$10,330,574,370.

**Why it is useful:** the skill can tell an advocate whether zero means no
matching projects, a historical coverage floor, or a controlled-vocabulary
gap—and can show how a nearby official category changes the policy question.

**Boundary:** do not choose *health disparities* merely to obtain a larger
number. Disclose its broad category family, and do not infer who benefited or
whether inequities improved from titles and funding alone.

## Case 10 — Biomedical entrepreneur: build an AI small-business landscape

**Public question:** “Which NIH-funded small businesses are developing AI or
machine-learning health technology?”

**Verified path:** query the same FY2025 title terms separately under R41, R42,
R43, and R44; inspect companies/titles and deduplicate core awards.

**Observed surface:** *artificial intelligence* returned five project-year rows
and five distinct awards—one R41, no R42, two R43, and two R44—with $2,754,529
reported. *Machine learning* returned 14 rows but 13 distinct awards—no
R41/R42, five R43, and nine R44 rows representing eight R44 cores—with
$9,272,436. The checked award sets did not overlap, yielding an 18-core union;
that disjointness must be recalculated after every snapshot refresh.

**Why it is useful:** an entrepreneur or partnership team gets named funded
precedents, companies, mechanisms, and exact award links, while query
sensitivity reveals opportunities hidden by fashionable terminology.

**Boundary:** R43/R44 or R41/R42 ratios are not phase-conversion rates. Awards
do not prove present company survival, commercial success, product efficacy,
regulatory progress, or market size; verify those separately.

## Case 11 — Historical reporter: detect HIV/AIDS language drift

**Public question:** “How did NIH HIV/AIDS research activity change from the
start of the epidemic?”

**Verified path:** run `HIV`, `AIDS`, and combined-title variants separately,
inspect early and later years, and preserve null historical dollars.

**Observed surface:** in FY1985, title trend returned nine `HIV` rows but 142
`AIDS` rows; by FY2005, it returned 2,834 `HIV` rows and 816 `AIDS` rows. The
apparent inversion is partly terminology drift, not a literal measure of how
research activity changed. FY1985–1998 award amounts are unreported on the
main trend surface, so the early dollar series is null rather than zero.

**Why it is useful:** a forty-year story becomes more credible when the tool
detects changing language instead of presenting one keyword as a stable
historical classification.

**Boundary:** build a deduplicated multi-term series, state that it remains
title based, and use an explicit price index only after comparable dollar
coverage exists. Do not turn null early dollars into a growth rate.

## Case 12 — Taxpayer award lineage: follow one core across institutions

**Public question:** “Was `R01NS121038` one award or several, and why did its
institution change?”

**Verified path:** resolve Marek Napierala, retain all full project numbers,
group by core, and fetch a full project record.

**Observed surface:** core `R01NS121038` appeared in five annual rows from
FY2021–2025 and $1,957,950 in recorded annual amounts. It began as
`1R01NS121038-01` at the University of Alabama at Birmingham, appeared as the
type-7 transfer `7R01NS121038-02` in FY2022, and continued through
`5R01NS121038-05` at UT Southwestern. These are five full project numbers but
one distinct core award. `fetch("R01NS121038")` correctly failed because fetch
requires a full project number; either full endpoint record returned a public
URL.

**Why it is useful:** a taxpayer, institution, or journalist can follow a
project across time without double-counting an institutional transfer as a new
award.

**Boundary:** preserve each legitimate annual amount and inspect supplements or
multiple transfer-year rows. Core-level deduplication is for award counts, not
permission to discard row-level funding.

## Case 13 — Expert discovery: disambiguate a shared surname

**Public question:** “Show me Napierala's NIH work.”

**Verified path:** use the surname for candidate discovery, then compare every
profile ID, full name, institution, title, and year before selecting one person.

**Observed surface:** `pi_name="Napierala"` over FY2010–2025 returned 48 rows
and 13 distinct awards spanning four profile IDs: Dobrawa Napierala, Jill
Sergeskette Napierala, Marek Napierala, and Sue Napierala. Marek's exact form
returned 21 rows, four distinct awards, and $6,501,628.

**Why it is useful:** the broad search is valuable as candidate discovery, but
the skill prevents an expert profile from silently combining unrelated people.

**Boundary:** surname, topic, or institution similarity is not identity. If
multiple candidates remain plausible after corroboration, present them and ask
the reader to choose rather than merging their portfolios.

## Case 14 — Multi-component award audit: stop a 2× dollar error

**Public question:** “How much did NIH award to the Geroscience of Sex
Differences SCORE center in FY2026?”

**Verified path:** exact `search_grants(project_num="1U54AG099000-01")`, group
the seven returned rows by title and amount, then call `fetch` and inspect
`metadata.matching_rows`.

**Observed surface:** the search returned one full project number and one core
award across seven rows. The canonical parent was $1,499,966. Six component
allocations—$332,803, $372,018, $209,998, $160,867, $60,382, and $363,898—also
summed to $1,499,966. Consequently, `meta.total_funding` was $2,999,932: a
correct row sum but exactly twice the unique parent obligation. `fetch`
returned the $1,499,966 canonical parent and reported seven matching rows. Even
with `limit=1`, the full-slice metadata retained `total=7` and
`unique_project_nums=1`, so a one-row page was not falsely treated as safe.

**Why it is useful:** a taxpayer, reporter, or institution can inspect both the
center-level obligation and its internal component allocation without a
headline that double-counts the same money.

**Boundary:** do not add the parent to its components. If a repeated-project
structure does not reconcile as cleanly as this case, report the rows and
withhold a unique-award dollar total.

## Case 15 — Collaboration map: separate shared awards from direct collaboration

**Public question:** “Who works with Eileen Crimmins on NIH-funded projects,
and how much funding does her profile represent?”

**Verified path:** resolve profile `1891769`, inspect every grant row and
collaborator edge, then reconcile repeated project numbers through the exact U54
search and fetch.

**Observed surface:** the FY2026 profile returned four grant rows and
`total_funding=$4,680,010`. Three rows were the same U54 full project number,
each carrying the official parent amount of $1,499,966, plus one P30 row of
$180,112. The profile total therefore repeated the U54 parent three times; it
was not a unique-award total. Four named collaborators were returned through
the shared U54 award. A related profile for Jennifer Ailshire returned 12 such
shared-award contacts.

**Why it is useful:** the profile can seed a research-network map while the
duplicate check prevents a large funding overstatement.

**Boundary:** these edges mean co-association on an award, not verified
coauthorship, mentorship, equal responsibility, or a direct working
relationship. Profile counts and totals are row-level when project numbers
repeat.

## Case 16 — Funding-to-output chain: link papers without inventing clinical impact

**Public question:** “What came out of Friedreich-ataxia award `R01NS121038`,
and did it lead to a clinical trial?”

**Verified path:** query PubMed's Grant Number field for `R01NS121038`, retain
the exact PMIDs, add iCite context, search ClinicalTrials.gov first by exact
grant number and then by disease topic, and retrieve full study details for any
cited NCT candidate.

**Observed surface:** PubMed returned two exact grant-number-linked records:
PMID `37691621`, a 2023 primary-research paper on cardiac mitochondrial stress,
and PMID `41514384`, a 2026 review of human pluripotent-stem-cell models. iCite
reported seven citations and RCR 1.1272 for the first record; the second was too
new for a meaningful citation signal. The exact grant-number trial search
returned zero studies. A broad *Friedreich ataxia* search returned 111 topical
studies, but these are X3 candidates, not outputs attributable to the award.
Study `NCT04102501`, for example, required detail retrieval to reveal its Phase
3 design, 65-person enrollment, RT001/placebo interventions, completed status,
and Biojiva sponsorship because the search summary omitted several fields.

**Why it is useful:** patients, advocates, and funders get a reproducible bridge
from public funding to concrete papers, plus an honest answer that no exact
grant-to-trial link was found.

**Boundary:** an exact grant acknowledgment is X1 attribution, not proof that
the grant caused a paper or outcome. APT is a model-derived indicator, not a
probability of clinical or commercial success. Patent coverage was unavailable
without the required USPTO credential and must be named as a gap rather than
silently omitted.

## Public-facing answer contract

Every public answer should fit this structure:

1. **The answer in one sentence** — include the window, evidence surface, unit,
   and nominal-dollar basis.
2. **What drives it** — show the two or three records, mechanisms, institutions,
   or outliers that explain the aggregate.
3. **Why definitions matter** — name the query variants and text/RCDC choice;
   show materially different totals instead of hiding them.
4. **What this does not prove** — one audience-specific sentence covering care,
   success odds, scientific quality, outcomes, or causality as applicable.
5. **What to do next** — provide public grant links or stable identifiers and a
   concrete next investigation, such as publications, trials, patents, official
   NOFOs, or institution/PI disambiguation.

Prefer memorable comparisons over giant tables, but preserve enough provenance
for a reader to reproduce every number. A useful answer changes the reader's
next action; a dashboard dump does not.
