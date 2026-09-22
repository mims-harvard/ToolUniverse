---

name: tooluniverse-clinical-trial-protocol
description: "Generate a full clinical trial protocol document (ICH E6(R2)/FDA-style) for a drug or medical device, including background, objectives/endpoints, study design, population/eligibility, intervention details, assessment schedule, statistical analysis plan with sample-size justification, safety monitoring, and regulatory/ethical sections. Use when users say \"generate a clinical trial protocol\", \"draft a protocol for [drug/device]\", \"write up the study design as a protocol document\", \"create an FDA submission protocol\", \"help me write section X of a trial protocol\", or \"calculate the sample size for this trial\". Produces a stakeholder-ready Markdown deliverable, not a feasibility score."
---

# Clinical Trial Protocol Generation

Turns a trial concept into an actual protocol DOCUMENT, grounded in real precedent-trial and regulatory-database lookups plus a genuine statistical sample-size calculation.

**This skill is a downstream step, not a replacement for `tooluniverse-clinical-trial-design`.** That skill answers "is this trial feasible, and what should endpoint/population/comparator/effect-size/duration/regulatory-pathway be?" (a 0-100 feasibility score with evidence grading). This skill takes those six answers — freshly run or already available from a prior `tooluniverse-clinical-trial-design` report — and drafts the actual protocol sections around them. **Do not re-derive feasibility scoring, endpoint selection reasoning, or regulatory-pathway strategy here — call `tooluniverse-clinical-trial-design` for that and consume its output.**

## When to Use This Skill

- "Write me a clinical trial protocol for [drug/device]"
- "Generate an FDA submission protocol for our Phase 2 study"
- "Draft the statistical analysis plan / sample size section"
- "I have the feasibility assessment — now turn it into a protocol document"
- "What sample size do I need for a [proportion/continuous/survival] endpoint?"

## NOT for (use other skills instead)

- Feasibility scoring, endpoint/population/comparator selection strategy -> `tooluniverse-clinical-trial-design` (run this FIRST if not already done)
- Patient-to-trial matching for an individual patient -> `tooluniverse-clinical-trial-matching`
- Drug mechanism / preclinical investigation -> `tooluniverse-drug-research` or `tooluniverse-drug-mechanism-research`
- Jurisdiction-aware approval/exclusivity lookups outside the protocol context -> `tooluniverse-drug-regulatory`

---

## Workflow

### Step 1 — Confirm feasibility inputs exist

Ask the user (or check the conversation) whether a `tooluniverse-clinical-trial-design` feasibility report already exists for this indication/intervention.

- **If yes**: reuse its 6-dimension findings directly (endpoint, population, comparator, effect size, duration, regulatory pathway, plus the evidence grades A-D).
- **If no**: run `tooluniverse-clinical-trial-design` first. Do not guess these six answers yourself — that skill's precedent-based reasoning exists precisely so this step doesn't fabricate them.

### Step 2 — Identify intervention type

Ask (if not already clear): **is the intervention a drug/biologic or a medical device?** The regulatory pathway, applicable FDA databases, and several protocol sections differ:

| | Drug/Biologic | Device |
|---|---|---|
| Pathway | IND -> NDA (505(b)(1)/(2)) or BLA | 510(k), De Novo, or PMA |
| Key FDA tools | `FDA_OrangeBook_search_drug`, `FDA_OrangeBook_get_approval_history`, `OpenFDA_search_drug_approvals`, `OpenFDA_get_approval_history`, `FDAGSRS_search_substances` | `OpenFDADevice_get_classification`, `OpenFDADevice_search_510k`, `OpenFDADevice_search_pma`, `OpenFDADevice_search_recalls`, `OpenFDADevice_search_adverse_events` |

See `references/regulatory_pathway_notes.md` for the full decision guide.

### Step 3 — Draft each protocol section with grounded evidence

Work through the 9 sections in `references/protocol_sections_guide.md`. For every factual claim (precedent endpoint use, comparator standard of care, prior trial enrollment/duration, safety signals, regulatory precedent), call the cited real ToolUniverse tool — do not state a regulatory fact from memory. Core tools used throughout:

- `search_clinical_trials`, `ClinicalTrials_search_studies`, `ClinicalTrials_get_study`, `ClinicalTrials_search_by_intervention`, `get_clinical_trial_eligibility_criteria`, `get_clinical_trial_outcome_measures`, `extract_clinical_trial_adverse_events` — precedent trials, eligibility patterns, outcome measures, safety signals
- Drug pathway: `FDA_OrangeBook_search_drug`, `FDA_OrangeBook_get_approval_history`, `FDA_OrangeBook_get_exclusivity`, `OpenFDA_search_drug_approvals`, `OpenFDA_get_approval_history`, `OpenFDA_get_approved_products`, `FDAGSRS_search_substances`
- Device pathway: `OpenFDADevice_get_classification`, `OpenFDADevice_search_510k`, `OpenFDADevice_search_pma`, `OpenFDADevice_search_recalls`, `OpenFDADevice_search_adverse_events`, `OpenFDADevice_search_udi`
- `FDAPurpleBook_search_products` — for biologics/biosimilars
- `PubMed_search_articles` — literature support for background/rationale and endpoint validation

**LOOK UP, DON'T GUESS**: never state an eligibility criterion, a comparator's approval status, a device's regulatory class, or a precedent effect size from memory — every one of those is a tool call away.

### Step 4 — Calculate sample size

Run `scripts/sample_size_calculator.py` with the effect-size assumptions established in Step 1 (from the feasibility report) or looked up from precedent trials in Step 3. Three modes are supported:

```bash
# Binary endpoint (e.g. response rate, ORR)
python3 scripts/sample_size_calculator.py two-proportion --p1 0.3 --p2 0.5 --alpha 0.05 --power 0.8

# Continuous endpoint (e.g. change in a biomarker or score)
python3 scripts/sample_size_calculator.py two-mean --mean-diff 0.5 --sd 1.0 --alpha 0.05 --power 0.8

# Time-to-event endpoint (e.g. PFS, OS) -- event_rate must come from precedent trials, not a guess
python3 scripts/sample_size_calculator.py survival --hr 0.7 --event-rate 0.6 --alpha 0.05 --power 0.8
```

Verify the implementation itself with `python3 scripts/sample_size_calculator.py --self-test` (checks all three formulas against hand-derived reference values). The calculator never fabricates a sample size — if you don't have a defensible effect-size assumption yet, go back to Step 3 and find one in precedent trials before running it.

### Step 5 — Assemble the final document

Fill `templates/protocol_template.md` with the Step 3 content and the Step 4 statistical justification. Deliver as a single Markdown file, e.g. `[INTERVENTION]_clinical_trial_protocol.md`. Do not show raw tool JSON to the user — write directly into the document sections as you gather evidence (progressive report writing, same pattern as `tooluniverse-clinical-trial-design`).

---

## Reference Files

| File | Content |
|------|---------|
| `references/protocol_sections_guide.md` | What belongs in each of the 9 protocol sections, and which tool to call for evidence in each |
| `references/regulatory_pathway_notes.md` | Drug (IND->NDA/BLA) vs device (510(k)/PMA/De Novo) pathway decision guide with real FDA tool names |
| `templates/protocol_template.md` | Fill-in-the-blank Markdown template for the final document |
| `scripts/sample_size_calculator.py` | Two-proportion, two-mean, and survival (Schoenfeld) sample-size calculator with `--self-test` |

## Integration with Other Skills

- **tooluniverse-clinical-trial-design**: run first for feasibility scoring and the 6-dimension inputs this skill consumes
- **tooluniverse-drug-regulatory**: deeper jurisdiction-aware regulatory status lookups (FDA vs EMA, exclusivity, generics) if the protocol needs more regulatory depth than Step 2/3 cover
- **tooluniverse-clinical-trial-matching**: once the protocol exists, match individual patients against its eligibility criteria
