# Idea Evaluation: Sharpening a New Project

Use this module when the user is pitching something not yet started. Goal: leave the conversation with a sharper idea, a bounded risk list, an explicit success metric, and one deliberately-fixed parameter.

## Step 1 — Intuition pumps: sharpen before judging

Before evaluating an idea, make sure it is stated precisely enough to evaluate. Common traps to watch for and gently push back on:

- **The idea is really a method looking for a question.** ("I want to apply technique X" is not a project until paired with a specific question X would answer that nothing else can.)
- **The idea is stated at the wrong altitude.** Too abstract ("understand cancer resistance") can't be evaluated for risk or feasibility; too narrow ("run this one assay") skips the "why does it matter" question. Aim for a level where you can state a single falsifiable claim.
- **The exciting part and the actual plan don't match.** Ask what result, specifically, would make this a big deal — then check whether the proposed method could actually produce that result, not just data adjacent to it.
- **Borrowed excitement.** An idea that's exciting because a paper/talk was exciting, without a clear line to what *this* project would add, usually needs another pass before it's ready to resource.

Reflect the idea back to the user in one paragraph after this pass, in the sharpened form, and confirm you have it right before moving to risk.

## Step 2 — Risk assessment: count the miracles

For each major risk, ask: is this a *known* uncertainty (an experiment will resolve it either way) or a *hoped-for* one (the plan only works if it comes out a specific way)? Hoped-for uncertainties are the ones that matter.

Count how many independent hoped-for outcomes the idea depends on simultaneously:

- **0-1 required "miracle"**: well-bounded risk, worth pursuing largely as scoped.
- **2 required "miracles"**: fundable but should have an explicit go/no-go checkpoint after the first one resolves, before committing to the second.
- **3+ required "miracles"**: usually a sign to descope to the single riskiest assumption and test that alone first, rather than building the whole chain before finding out an early link fails.

For each identified risk, note: what would falsify it fastest and cheapest, and what happens to the rest of the project if it does.

Before finalizing the risk list, run a precedent check (see `precedent-checking.md`) — do not assume a risk is novel or unaddressed without checking whether someone has already resolved it in the literature.

## Step 3 — Define the optimization function (success metric)

Get the user to state, in one sentence: what specific result, if obtained, means this was worth doing. This is different from "what am I measuring" — it's the threshold that separates success from a negative/null/inconclusive result worth reporting as such.

Ask two follow-ups if the first answer is vague:
- What would make you say "this didn't work, and here's why," rather than "this is still ambiguous, let's run it again"?
- Would a strong reviewer or PI agree that hitting this threshold is actually the interesting outcome, or is there a more interesting question hiding one level up?

## Step 4 — Parameter strategy: what to fix, what to float

Ask the user to list the 3-5 major design choices in the plan (e.g., model system, cohort, comparator, readout, timeline). For each, classify as:

- **Fixed** — committed now, changing it later would mean restarting.
- **Floating** — deliberately left open, to be decided based on early results.

The common failure mode is fixing everything (brittle — one surprise forces a full restart) or fixing nothing (no forward progress, because every early result reopens the whole plan). Help the user pick exactly one parameter that is the most load-bearing — the one whose value most determines whether the rest of the plan makes sense — and commit to it explicitly, while flagging the rest as intentionally flexible.

## Closing Deliverable

Produce a short (1-2 page) markdown summary with four sections: Sharpened Idea, Risk List (with the cheapest de-risking step per risk), Success Metric, and Fixed Parameter (with the floating ones listed underneath). Do not expand this into a full grant-style proposal unless asked.
