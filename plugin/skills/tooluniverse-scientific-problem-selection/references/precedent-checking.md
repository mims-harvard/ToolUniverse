# Precedent and Fundability Checking

Never assert novelty, existing consensus, or fundability from memory or intuition. Run a real search first. This is the concrete point where this skill differs from a purely conversational framework: ToolUniverse can check the claim instead of just discussing it.

All tool names below were verified against existing ToolUniverse skill files (`tooluniverse-clinical-trial-design/SKILL.md`, `tooluniverse-literature-deep-research/SKILL.md`, `tooluniverse-nih-funding-landscape/SKILL.md`) — do not substitute an unverified tool name.

## When to check literature precedent

Trigger a literature check whenever the user's idea, risk assessment, or troubleshooting plan rests on a claim like:
- "No one has looked at this before" / "this is novel"
- "Everyone in the field does X" / "the standard approach is Y"
- "This mechanism is well established" / "this is a known risk factor"

**Tools to use:**
- `PubMed_search_articles` — first pass for biomedical literature precedent on the exact phrasing of the idea.
- `EuropePMC_search_articles` — broader biomedical/preprint coverage; useful as a second pass if PubMed returns few or zero hits.
- `advanced_literature_search_agent` — for a more exhaustive, multi-database sweep when the novelty claim is a load-bearing part of the pitch (e.g., a grant-worthiness judgment hinges on it).
- For the full literature workflow with evidence grading and theme extraction, delegate to the `tooluniverse-literature-deep-research` skill rather than reimplementing it here.

**Interpreting results:**
- A zero-hit search on the exact phrase is *not* proof of novelty — try at least one synonym or an adjacent term before concluding the idea is unstudied. Field terminology drifts, and a "novel" idea is often just phrased differently from prior work.
- A handful of hits in adjacent contexts is not the same as "this exact question has been answered" — check whether the retrieved work actually addresses the user's specific claim or just a related one.
- Report what was actually found, including partial precedent, rather than a binary novel/not-novel verdict.

## When to check the funding landscape

Trigger a funding-landscape check whenever the user is evaluating grant-fundability, asking whether a topic is currently well- or under-funded, or wants to know who else is active in the space before pitching it.

**Tools to use** (via the `tooluniverse-nih-funding-landscape` skill's `OpenNIH_*` tools):
- `OpenNIH_search_grants` — find funded projects on the topic; check whether the specific angle is already well-covered or represents a gap.
- `OpenNIH_topic_trend` — see whether funding for the topic area is growing, flat, or shrinking, which affects how a pitch should be framed.
- `OpenNIH_rank_institutions` / `OpenNIH_get_pi_profile` — identify who else is active in the space, useful for competitive-landscape context or finding potential collaborators/reviewers.

**Interpreting results:** follow the caveats in `tooluniverse-nih-funding-landscape`'s own SKILL.md exactly (null dollars are "not reported" not zero, `topic_trend` is title-keyword evidence not semantic classification, don't infer application success rates from awarded-grant records). Do not re-derive funding conclusions independently of that skill's documented interpretation rules — invoke it or read its reference files rather than guessing at OpenNIH semantics.

## What to do with a precedent hit

If a check surfaces work that closely overlaps the user's idea, don't treat this as a verdict to abandon — bring it back to the user as new information: what's already been done, what's the same, what's actually different about their angle, and whether the difference is enough to still be worth pursuing. Precedent should sharpen the pitch (differentiate it from what's known), not just kill it.
