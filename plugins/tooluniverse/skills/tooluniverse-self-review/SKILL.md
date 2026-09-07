---

name: tooluniverse-self-review
description: "Review existing work against the user's actual goal and surface evidence-backed strengths, gaps, risks, and next fixes. Use when asked to eval, evaluate, review, assess, or check current/this/my/our work; decide whether a task is complete; build a definition-of-done checklist or rubric; or perform grading, LLM-as-judge, Qworld, or RET evaluation. Treat plain eval/review requests as qualitative: resolve \"current work\" from the conversation, artifacts, files, or diff, and never assign numeric scores unless the user explicitly requests scores, grades, points, ratings, weighted criteria, Qworld, or RET. Do not use for implementing automated eval suites, tests, graders, or benchmarks.\n"
---

# Self-Review: Understand the Target, Then Review

Review the actual work the user means against the goal it was meant to satisfy. Default
to a concise qualitative assessment. Scoring and the full Qworld Recursive Expansion
Tree (RET) are opt-in.

## Non-Negotiable Rules

1. **Do not confuse the evaluation request with the evaluated task.** In requests such as
   "eval current work", that sentence is an instruction to review. The task being judged
   is the preceding user goal; the work is the current result, implementation, draft,
   plan, or progress.
2. **Do not equate `eval` with scoring.** `Eval`, `evaluate`, `review`, `assess`, and
   `check` mean qualitative review unless the user explicitly asks for a score, grade,
   rating, points, weighted rubric, Qworld, RET, or a numeric scale.
3. **Do not invent work to review.** Inspect the conversation and available artifacts. If
   evidence is unavailable, say what could not be verified.
4. **Do not expose process by default.** Keep scenario expansion, perspective generation,
   and rubric construction internal unless the user asked for those artifacts.
5. **Review against the user's goal, not a generic quality template.** Derive the relevant
   checks from the request, stated constraints, acceptance criteria, and risks.

## Resolve the Review Target

Separate three objects before reviewing:

- **Evaluation instruction**: what the user is asking now (for example, "review this").
- **Original goal**: the request, problem, or acceptance criteria the work should satisfy.
- **Work product**: the answer, code, files, diff, plan, analysis, or current progress to
  examine.

Resolve the work product in this order:

1. An explicitly named file, answer, commit, diff, section, or artifact.
2. Pasted or attached content in the current message.
3. The current repository implementation or working-tree diff when the conversation is
   about code changes.
4. The most recent assistant-produced deliverable relevant to the preceding user goal.
5. The current plan or partial progress when the task is still underway.

Interpret deictic phrases such as "current work", "this work", "what we have", "刚才的
工作", and "当前工作" using that order. In a multi-turn conversation, the last user
message is usually the evaluation instruction, **not** the original goal.

Proceed without asking when the goal and work can be recovered confidently. Ask one
short clarifying question only when there is no reviewable work or when multiple plausible
targets would produce materially different reviews.

## Choose One Mode

| Mode | Trigger | Default output |
|---|---|---|
| **Qualitative review** (default) | "eval/review/check current work", "is this done?", "what is missing?" | Evidence-backed findings, strengths, gaps, fixes, and a completion verdict; no numbers |
| **Checklist** | Explicit request for definition of done, success criteria, or completeness checklist without work to review | Task-specific checklist; no points |
| **Rubric** | Explicit request for evaluation criteria or a rubric, but no scoring request | Binary or observable criteria grouped as must/should/could; no points |
| **Scored evaluation** | Explicit request for score, grade, rating, points, weighted criteria, LLM-as-judge scoring, Qworld, RET, or a numeric scale | Evidence-backed scored review using the requested scale or RET |

The phrase "evaluate this" alone selects **qualitative review**, even when a work product
is present. The presence of work never turns scoring on by itself.

Requests to **create or run evals**, implement a grader, write evaluation tests, or build a
benchmark are engineering tasks, not self-review requests. Do not route those requests to
this workflow merely because they contain the word `eval`.

## Qualitative Review Workflow (Default)

1. **Recover the goal.** Summarize the original goal and important constraints in one or
   two sentences. Prefer explicit acceptance criteria over inferred preferences.
2. **Inspect the work.** Use the actual conversation output, files, diff, test results, or
   supplied artifact. For code, inspect relevant implementation and verification evidence;
   do not judge from a summary alone when the files are available.
3. **Derive focused checks internally.** Identify only the task-specific dimensions needed
   to judge correctness, completeness, user intent, risks, and verification. Do not print a
   large rubric unless asked.
4. **Report findings by impact.** Lead with concrete problems or unmet requirements. For
   each finding, cite the evidence and explain the consequence.
5. **Acknowledge what works.** Note meaningful strengths briefly; do not pad the response
   with generic praise.
6. **Give prioritized fixes.** Recommend the smallest concrete actions that close the most
   important gaps.
7. **State a plain-language verdict.** Use `complete`, `mostly complete`, `partially
   complete`, `not complete`, or `unable to verify`, with a short reason. Do not convert
   the verdict into a number.

### Default Review Shape

Adapt the headings to the task and omit empty sections:

1. **Overall assessment** — target, goal, and verdict.
2. **Findings** — ordered by impact, with evidence.
3. **What is working** — concise, specific strengths.
4. **Recommended next actions** — prioritized fixes.

For code review, prioritize actionable defects and regressions over summaries. Cite file
paths and tight line ranges when possible. If no problems are found, say so directly and
name any residual verification gaps.

## Checklist and Unscored Rubric Modes

- Derive criteria from the task rather than a fixed dimension list.
- Keep each item observable and specific enough to check.
- Use `must`, `should`, and `could` for importance when prioritization helps.
- Do not attach numbers, weights, percentages, earned totals, or pass rates.
- If work is also supplied, mark items `met`, `partially met`, `not met`, or
  `not verifiable`, with brief evidence. These labels are not scores.
- Do not generate scenarios or perspectives unless the user explicitly asks to see the
  derivation.

## Scored Evaluation Mode (Explicit Opt-In Only)

Use this mode only when the request contains an unambiguous scoring signal listed above.

- If the user supplies a scale or grading scheme, follow it.
- If the user asks for Qworld, RET, a weighted rubric, or LLM-as-judge scoring without a
  custom scheme, read and follow
  [references/ret-scored-evaluation.md](references/ret-scored-evaluation.md).
- Keep every verdict evidence-based. Do not award credit for absent evidence or penalize
  criteria outside the original goal.
- Explain what the score means and still provide the highest-impact gaps and fixes. A
  number alone is not a useful review.

## Examples of Correct Routing

| User request | Correct interpretation |
|---|---|
| "Eval current work." | Review the current result against the preceding goal; qualitative, no score |
| "Evaluate whether we finished the original request." | Inspect current artifacts and give a completion verdict; no score |
| "What is missing from this implementation?" | Findings-first implementation review; no score |
| "Make a definition-of-done checklist for this feature." | Checklist mode; no score |
| "Create an evaluation rubric for these answers." | Unscored rubric unless weights or grading are requested |
| "Score this answer from 1 to 10." | Scored mode on the requested scale |
| "Apply Qworld/RET to grade these responses." | Full scored RET mode |
| "Create an eval suite for this agent." | Out of scope for this skill; treat as an eval-engineering task |

## Evidence and Honesty

- Distinguish observed evidence from inference.
- Do not claim tests passed unless their output is available.
- Do not infer completion from a clean diff, a confident summary, or the existence of
  files alone.
- If the user requests evaluation while work is still running, review the available
  progress and label unfinished parts rather than pretending the final result exists.
- Keep the response proportional to the work. A small change should not produce a giant
  framework dump.
