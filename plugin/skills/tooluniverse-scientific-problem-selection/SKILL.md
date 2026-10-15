---
name: tooluniverse-scientific-problem-selection
description: Conversational framework for choosing what scientific problem to work on, pitching a new project idea, troubleshooting a stuck project, or making a strategic research decision. Use when users say "I have an idea for a project", "I'm stuck on my research", "what should I work on", "help me evaluate this project's risk", "is this idea worth pursuing", "help me decide between two research directions", "I need strategic advice about my research", or ask to pitch/refine/de-risk a hypothesis before running any experiments or analyses. Grounds the conversation in real literature-precedent and funding-landscape lookups rather than pure opinion.
disable-model-invocation: true
---

# Scientific Problem Selection

A structured conversation for the decision that happens *before* any experiment, dataset pull, or analysis: which problem is actually worth the next few months (or years) of work. Problem choice dominates outcome more than execution quality — a well-executed answer to a low-value question is still a low-value result.

**LOOK UP, DON'T GUESS**: Every claim about novelty, precedent, or fundability in this skill must be checked against real tools, not asserted from memory. See `references/precedent-checking.md` for the exact tool names and when to call each one.

---

## When to Use This Skill

Apply when users:
- Pitch a new project idea and want it stress-tested before committing time to it
- Say they are stuck, blocked, or a project stopped working and they need to decide what to do next
- Ask a strategic question about which of several directions to pursue
- Want a risk assessment, feasibility gut-check, or "is this a good use of the next N months" opinion
- Are preparing to write a grant or thesis proposal and need the underlying idea sharpened first
- Ask to define success metrics, decide what to hold fixed vs. leave flexible in a study design, or plan a decision tree for an ongoing project

**NOT for** (route elsewhere):
- Clinical trial feasibility scoring on a specific indication/drug → `tooluniverse-clinical-trial-design`
- Pure literature synthesis with no strategy decision attached → `tooluniverse-literature-deep-research`
- NIH portfolio, funding trend, or PI/institution analysis → `tooluniverse-nih-funding-landscape`
- Drug target or disease biology deep dives → `tooluniverse-target-research`, `tooluniverse-disease-research`

This skill produces a decision framework and a short written artifact. It does not run wet-lab or computational experiments itself — it decides whether they're worth running.

---

## Three Entry Points

Start every conversation by finding out which of these three the user actually needs — do not assume:

1. **Pitch an idea** — a new project, not yet started. Goal: sharpen it and find its cheapest de-risking step.
2. **Troubleshoot a problem** — an active project that stopped working or hit a wall. Goal: decide fix vs. pivot vs. abandon.
3. **Strategic question** — comparing options, choosing a direction, deciding what to work on next. Goal: a ranked recommendation with the reasoning shown.

Ask a one- or two-sentence version of the idea/problem/question first. Reflect it back in your own words (one short paragraph, showing you understood the core of it) before asking for more detail. Then ask for the specifics relevant to that entry point (see `references/idea-evaluation.md` for entry point 1, `references/decision-tree-navigation.md` for entry points 2 and 3).

---

## Core Principles

### 1. Problem choice beats execution quality
Spend real time here — proportionally more than most people naturally do. A team spends days picking a problem and years solving it; that ratio is backwards for how much the choice matters. Push back gently if the user wants to skip straight to methods before the problem itself is well-defined.

### 2. Risk is a resource, not a hazard
An idea with zero risk is usually incremental — someone else would have already done it, or the result won't move anything forward. The goal isn't risk-free; it's *understood, bounded, and worth taking*. Count how many independent things have to go right ("miracles") for the idea to work — one or two is fundable risk, three or more is usually a sign to descope.

### 3. Define success before starting
An idea without an explicit success metric drifts. Before commiting resources, get the user to state: what result, if obtained, would make this worth having done — and what result would mean it's time to stop.

### 4. Fix one thing, float the rest
Overconstrained plans (every parameter locked) break the first time reality disagrees. Underconstrained plans (nothing committed) never converge. Help the user pick the single most load-bearing constraint to fix and explicitly leave everything else adjustable.

### 5. Crises are data, not verdicts
When a project stalls, the instinct is to treat it as a referendum on the whole idea. Usually it's one specific, nameable failure. Separate "what broke" from "was the idea wrong," and look for the version of the fix that also upgrades the project rather than just patching it.

### 6. Ground claims in evidence, not confidence
Any statement about "no one has done this," "this would be fundable," or "this is the standard approach" must be checked with a real search — see the precedent-checking workflow below. Confident-sounding claims about novelty are wrong often enough that skipping the check is a real risk to the user's time.

---

## Workflow by Entry Point

### Pitching an idea
1. Get the one-to-two-sentence pitch, reflect it back.
2. Ask for: what exactly they want to do, how they'd currently do it, why it matters if it works, and what they think the biggest risks are.
3. Run a precedent check (see below) before evaluating novelty or risk — do not rely on the user's or your own assumption that something is unstudied.
4. Walk through `references/idea-evaluation.md`: sharpen the idea, assess risk (how many miracles), define the success metric, and decide what to fix vs. keep flexible.
5. Close with a short written summary: the sharpened idea, the risk list with mitigation ideas, the success metric, and the one fixed parameter — 1-2 pages, not a full proposal. Use `references/communication-and-synthesis.md` for the layout, and to run the full framework in order if the user wants a complete workup.

### Troubleshooting a stuck project
1. Get the one-to-two-sentence problem statement, reflect it back, and ask a clarifying question or two if the failure mode is unclear.
2. Ask for: the project's overall goal (if not already established), exactly what went wrong, and any fix ideas already in mind.
3. Run a precedent check if the "fix" under consideration assumes something about the field (e.g., "everyone uses method X for this") — verify rather than assume.
4. Walk through `references/decision-tree-navigation.md`: map the decision point, decide fix vs. pivot vs. abandon, and always produce at least one workaround alongside any actual fix.
5. Close with: the diagnosis, the recommended path (fix/pivot/abandon) with reasoning, and a concrete next action.

### Strategic question
1. Get the one-to-two-sentence question, reflect it back.
2. Ask whether this is about a current project or a future one, and get a bit more detail on the options being weighed.
3. Pull whichever of `references/idea-evaluation.md` (future-facing) or `references/decision-tree-navigation.md` (current-project) modules actually apply — don't run the full framework end-to-end for a narrow question.
4. If the question hinges on fundability or competitive landscape, run the funding-landscape check from `references/precedent-checking.md`.
5. Close with a direct recommendation and the one or two facts that drove it — not an exhaustive survey of every option.

---

## Precedent and Fundability Grounding

Before telling a user an idea is novel, well-trodden, or fundable, verify it. See `references/precedent-checking.md` for exactly which real ToolUniverse tools to call at each stage (literature precedent via PubMed/literature-deep-research tools, NIH funding landscape via the `tooluniverse-nih-funding-landscape` skill's OpenNIH tools) and how to interpret a zero-hit search (absence of evidence in a keyword search is not proof the idea is novel — it may just be a terminology mismatch; try at least one synonym before concluding novelty).

---

## Output

Keep outputs short and decision-oriented: a 1-2 page markdown summary per completed workflow step, not a full research proposal unless the user explicitly asks for a complete package spanning all steps. State assumptions and open risks explicitly rather than smoothing over them.

## Reference Files

| File | Content |
|------|---------|
| `references/idea-evaluation.md` | Sharpening a new idea: intuition pumps, risk-as-miracle-count, success metrics, fixed-vs-flexible parameters |
| `references/decision-tree-navigation.md` | Troubleshooting a stuck project: decision-tree mapping, fix/pivot/abandon, adversity reframing, problem inversion |
| `references/precedent-checking.md` | Which real ToolUniverse tools to call for literature-precedent and funding-landscape grounding, and how to interpret the results |
| `references/communication-and-synthesis.md` | Running the whole framework in order, the one-page decision summary, and how to tell it to an advisor, committee, collaborators or funders |

## Attribution

The problem-choice-over-execution-quality framing draws on the general body of public scientific-methodology writing on research strategy, including Fischbach & Walsh, "Problem choice and decision trees in science and engineering," *Cell* 187 (2024). This skill is an original synthesis for ToolUniverse, not a reproduction of any single source.
