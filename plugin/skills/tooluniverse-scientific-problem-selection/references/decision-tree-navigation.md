# Decision-Tree Navigation: Troubleshooting a Stuck Project

Use this module when the user has an active project that stalled, produced an unexpected result, or needs a strategic choice made between options that already exist (rather than a brand-new idea being pitched).

## Step 1 — Map the decision point

Before proposing a fix, get precise about where in the project the user actually is:

- What was the plan at the point things stopped working?
- Is this an *execution-level* problem (something specific failed — an assay, a model, an API, a recruitment target) or a *strategic-level* problem (the whole approach now looks wrong given what was learned)?
- Has the user been oscillating between "just fix this one thing" and "maybe I need to rethink the whole project"? Naming that oscillation explicitly often unblocks the conversation — most stuck projects are stuck at exactly one level, and time gets wasted flipping between the two instead of resolving one before checking the other.

Resolve the execution-level question first if one exists; only escalate to a strategic re-evaluation if the execution-level fix doesn't restore the original plan.

## Step 2 — Fix, pivot, or abandon

For a strategic-level stall, evaluate three options explicitly rather than defaulting to "push through":

- **Fix**: the original plan is still sound; one component needs to change. Ask what's the smallest change that would let the rest of the plan proceed unmodified.
- **Pivot**: the original question is still worth answering, but the method needs to change, or the failure revealed a more interesting adjacent question. Ask whether the pivot target has already been de-risked (does the user have any preliminary evidence for it) or whether it's a second unproven idea being substituted for the first.
- **Abandon**: the failure has genuinely invalidated the premise, and no adjacent version is worth the remaining budget. This is a legitimate outcome — flag it plainly if the evidence points there rather than steering the user toward a forced pivot.

If the "fix" or "pivot" under consideration rests on an assumption about how the field normally handles this problem, run a precedent check (see `precedent-checking.md`) before recommending it — a stated “that's how everyone does X” is exactly the kind of claim that needs a real search, not a nod.

## Step 3 — Reframe the failure

A crisis in an active project usually contains two separable questions: what specifically broke, and does that change the underlying hypothesis? Keep them separate — most failures are answerable at the "what broke" level without touching the hypothesis at all.

When a genuine setback has occurred, look for a response that does two things simultaneously: resolves the immediate problem, and improves some other aspect of the project (a cleaner control, a more general method, a broader dataset) rather than just a patch that restores the status quo. Ask the user directly: "if you have to redo this anyway, is there a version of the redo that also fixes [some other known weakness]?"

## Step 4 — Problem inversion

When stuck on "how do I get X to work," it can help to invert the question:

- Instead of "how do I make the measurement more sensitive," ask "what would make the *effect* larger instead" (change the system, condition, or comparator rather than the assay).
- Instead of "how do I recruit more patients," ask "is there a way to need fewer" (paired design, richer per-subject readout, different endpoint).
- Instead of "how do I prove this mechanism directly," ask "what indirect consequence of this mechanism would be easier to observe."

Always produce at least one workaround alongside any direct fix, even if the direct fix looks achievable — a workaround protects the timeline if the fix takes longer than expected.

## Closing Deliverable

Summarize: the diagnosis (execution vs. strategic, and which specific thing broke), the recommended path (fix / pivot / abandon) with the reasoning, at least one workaround, and a concrete next action the user can take immediately.

## Strategic Question Variant

For a pure strategic question (not tied to an active stall), skip the failure-diagnosis steps and go straight to comparing the options on the same axes: likelihood of a clear result vs. impact if it works, and how many independent things must go right for each option (see the "counting miracles" heuristic in `idea-evaluation.md`). State a direct recommendation with the one or two facts that drove it, rather than an exhaustive pros/cons table for every option.
