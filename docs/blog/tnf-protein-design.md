---
orphan: true
title: "Using ToolUniverse to test an apparent improvement in TNF binder design"
date: 2026-10-18
---

# Using ToolUniverse to test an apparent improvement in TNF binder design

**A follow-up to our EGFR exploration, focused on how an agent investigates conflicting predictions before promoting a variant.**

One substitution gave us a useful question in the TNF-α competition: had we improved the design, or changed the assumptions behind its score? A favorable pH comparison could become unfavorable when we changed the unbound reference. Re-preparing an unchanged predicted structure could also reverse the comparison.

Our [first post on EGFR](https://aiscientist.tools/posts/egfr-protein-design) covered organizing an agent’s investigation with ToolUniverse’s skills and tools, including deploying GPU models on DGX Spark as remote tools. We reused that infrastructure here. The harder task was deciding which computation would explain a disagreement—and what result would justify changing our candidate selection.

The [TNF-α challenge](https://proteinbase.com/competitions/anthropic-adaptyv-2026/challenges/tnf-alpha) also reversed the pH objective. We needed human-target binding at pH 7.4 with no detectable binding at pH 6.0, alongside mouse cross-reactivity. That meant pursuing **neutral-pH binding with acidic release**. Binding and pH selectivity remained experimentally unverified throughout the exploration described here.

## Build a matched comparison before spending more compute

Our de novo route used RFdiffusion3 for backbone generation and ProteinMPNN for sequence design. The deeper investigation compared one parent with **M48L**, a methionine-to-leucine substitution at position 48. We wanted to test a local packing change while preserving the proposed binding environment.

The first task was to establish what had already been computed. The agent reconciled exact sequences, constructs, model settings, seeds, input content and completed outputs. Six parent requests already matched the required protocol, so we reused them. We launched only the six missing M48L requests: Protenix, Boltz and RoseTTAFold3 against human and mouse targets.

This is where the existing ToolUniverse workflow paid off. The campaign skill guided the comparison and reuse checks; GPU remote tools supplied predictions on DGX Spark. The agent could carry earlier results and exclusions into the new analysis without treating every new job label as a new scientific request.

The M48L batch returned **14 structures; 12 qualified** for downstream comparison. Two lacked a supported terminal carbonyl and were excluded under the existing structural requirements. We compared the qualified set with 12 previously qualified parent structures.

Both sequences had a compatible joint human glycan-root placement in **6/6 sampled contexts**. The hypothetical mouse-root screen had a compatible placement in **5/6 contexts** for each. Removing the binder did not rescue the failing mouse context: the receptor-only check also failed. That result could not identify M48L as the cause of the clash. These counts describe the sampled root hypotheses, not all native glycoforms.

These checks established which structural hypotheses we could analyze. They did not distinguish the two sequences as experimentally better binders. The next useful question was whether the proposed pH behavior survived a more careful comparison.

## Separate a model disagreement from a reference disagreement

A pH calculation depends on both the complex and the unbound components. Looking only at a histidine in the interface would miss changes elsewhere in the binder, receptor or termini. We audited **174 ionizable protein groups**, including the actual termini, in the selected modeled systems.

We then evaluated two free-state conventions separately:

- **Independent free structures:** separately modeled free binder and apo receptor references.
- **Same-coordinate components:** binder and receptor extracted from the complex, then evaluated separately without changing their coordinates.

Both conventions use titrating pKas. The second holds coordinates fixed during extraction; it does not freeze protonation.

For each sequence, PROPKA supplied an independent-site protonation-linked energy term for pH 6.0 relative to 7.4, at 298.15 K. We compared **M48L minus parent** for that term. A positive difference means a larger modeled acidic-release contribution for M48L. It does not determine absolute affinity or guarantee preservation of neutral-pH binding.

The family labels identify the source of the complex coordinates; PROPKA was common to these full-system comparisons. The original Protenix comparison was negative with independent free references: **−0.219 to −0.100 kcal/mol**. Boltz gave **−0.142 to −0.023 kcal/mol** under the independent convention, but **+0.035 kcal/mol** with same-coordinate components. Selecting only that positive Boltz result would have hidden a reference-dependent sign change.

The ranges came from five own free-binder samples combined with two same-family apo-receptor references. Those ten combinations share inputs. They probe reference sensitivity; they are not ten independent experiments.

Additional neural pKa analyses and selected-histidine learned-energy diagnostics did not supply a common ranking. Their coverage differed: partial-site calculations could omit contributions included in the full protein inventory, and learned energies had their own units and assumptions. The agent compared shared sites where appropriate and kept the complete-system and restricted diagnostics separate. Related weight sets remained one model family. Averaging them would have concealed the question we needed to resolve.

That question became more specific: **was the apparent mutation effect stable to the way we prepared the structures?**

## Re-prepare the unchanged structures before interpreting the mutation

Some M48L predictions appeared to lose a histidine–receptor contact present in the parent. A sequence-based explanation was plausible, but hydrogen placement and local minimization could also change the interaction.

We tested that alternative with a bounded pilot of **15 prepared contexts**:

- Three unchanged parent starting poses, one from each structural family.
- Three unchanged M48L starting poses under the same preparation protocol.
- Nine M48L sidechain starts: three Leu48 starting orientations (first sidechain torsion −60°, +60° and 180°) across the same three families.

We kept the hydrogenation and restrained physical preparation protocol matched, including its force field and restraints, and retained the existing qualification criteria. **All 15 contexts passed the physical requirements and retained a compatible human glycan-root placement.** This let us compare their downstream scores without silently changing the gates.

Re-preparing an unchanged M48L predicted pose restored the histidine–receptor contact whose absence had prompted concern. The missing contact was sensitive to preparation. Its earlier absence could not establish that the mutation had destroyed that interaction.

The pH comparison also changed. With independently modeled free references, the originally negative Protenix range (**−0.219 to −0.100 kcal/mol**) became positive (**+0.190 to +0.308 kcal/mol**) after matched re-preparation. Yet its same-coordinate difference stayed negative, moving from **−0.356** to **−0.134 kcal/mol**.

![M48L-minus-parent pH linkage comparisons before and after re-preparing the unchanged predicted starting poses, separated by model family and free-state convention.](assets/tnf-design/reference_sensitivity.svg)

*Each row uses the same bound sample before and after preparation. Lines span ten correlated combinations of five free-binder samples and two apo-receptor references; points show one same-coordinate comparison. RoseTTAFold3 uses sample 0 in both preparations. Values are complete modeled 174-group protein-only PROPKA linkage comparisons at 298.15 K, pH 6.0 relative to 7.4. These are sensitivity ranges, not confidence intervals. [All 33 paired comparisons](assets/tnf-design/paired_deltas.csv) and [plotted ranges](assets/tnf-design/reference_sensitivity.csv) are available as aggregate source data.*

The other families made the picture clearer. After re-preparation, Boltz still favored opposite signs across the two reference conventions: **−0.177 to −0.058 kcal/mol** with independent free structures, versus **+0.022 kcal/mol** with same-coordinate components. The RoseTTAFold3 sample-0 independent comparison spanned zero, **−0.030 to +0.088 kcal/mol**, while its same-coordinate comparison was **+0.128 kcal/mol**.

Re-preparation had therefore changed more than a contact annotation. It changed the assessment of the mutation, and the new assessment still depended on the reference. None of the nine M48L sidechain starts gave a uniformly favorable change across the evaluated methods and references. Some starts also relaxed toward similar minima, so counting them as separate thermodynamic states would have exaggerated the evidence.

We kept M48L as an exploratory alternative. The pilot did not support promoting it on the strength of a favorable local score.

## Check whether the controls support the decision

The remaining question was how much authority to give the scores themselves. Two additional public known-binder predictions passed physical preparation but recovered **zero native interface contacts** under the existing evaluation. A physically acceptable structure had not demonstrated successful recovery of a known binding pose. We retained those failures and treated blind pose recovery as uncalibrated for this decision.

The pH controls required a different check. The acid-wash experiments in [the anti-TNF patent’s Examples 3 and 8](https://patents.google.com/patent/US20250388665A1/en) measured retained binding following a prolonged dissociation step. Retention, dissociation behavior, EC50 and equilibrium KD are different observables. Such experiments can inform a pH mechanism, but they did not provide paired equilibrium measurements that directly calibrated our complete linkage calculation.

An independent free-fold check supplied another tempting result. M48L passed the existing reference-core Cα RMSD gate at **1.13 Å**, while its parent was **2.18 Å**, above the original **2 Å** threshold. That was a passing mutant and a failing parent. It did not provide a qualified pair with which to validate the mutation comparison. We reused the existing outputs, preserved the failed parent result and kept the threshold unchanged.

Each control narrowed a different claim: physical preparation did not calibrate binding-pose recovery; an acid-wash endpoint did not calibrate equilibrium affinity; a mutant-only fold pass did not establish paired free-state validation. Together, they directed the next useful work toward control recovery and reference robustness before further score-driven sequence expansion.

## What changed in the agent’s next task

The investigation progressed through concrete questions. A glycan failure prompted a receptor-only check. A pH sign change prompted separate free-reference calculations. An apparent contact loss prompted re-preparation of unchanged sequences. A passing mutant fold prompted inspection of the matched parent. Each result changed what the agent should do next.

ToolUniverse helped connect those questions to executable work through its skills, scientific tools and GPU remote tools. The value was in keeping the comparison explicit: which sequence changed, which coordinates changed, which reference was used, which groups were covered, and which controls had actually passed. That record made it possible to identify a favorable number whose interpretation depended on an untested assumption.

We retained the reviewed submission of **seven designs**, each 99 amino acids long and belonging to one backbone lineage. M48L’s exploratory results did not justify replacing that package. All seven passed the portal’s novelty checks, and we verified the saved sequences and order against the reviewed file. The [submission collection](https://proteinbase.com/collections/anthropic-adaptyv-protein-design-competition-submission-1-X8MAX9zP0b) records those candidates; experimental selection and binding measurements were still pending when this account was written.

For deployment and installation, see the [EGFR post’s ToolUniverse and DGX Spark walkthrough](https://aiscientist.tools/posts/egfr-protein-design) and the [official setup guide](https://aiscientist.tools/setup.md). The reusable [Protein Design Campaign skill](https://github.com/mims-harvard/ToolUniverse/tree/main/skills/tooluniverse-protein-design-campaign) supports this style of comparison. Once ToolUniverse is configured, a focused next task for an agent is:

```text
Compare this proposed variant with its parent using ToolUniverse. Reuse verified
completed requests first. Separate model, free-reference and preparation effects;
re-prepare both unchanged starting poses before attributing a difference to the
mutation. Check that controls support the intended decision, preserve conflicting
results, and identify the next computation that could resolve the disagreement.
```
