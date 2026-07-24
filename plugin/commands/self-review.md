---
name: self-review
description: Generate the success criteria for a task or question, then review work against them. Decomposes the task into scenarios → evaluation perspectives → weighted YES/NO criteria (the Qworld Recursive Expansion Tree method) and, if you supply the work, scores it criterion-by-criterion and lists what is missing or could be better. Use to self-review or check your own work, judge whether a task is done well or completely, build a definition-of-done / completeness checklist, or create an evaluation rubric / grading criteria for answers to a question.
argument-hint: "[task, goal, or question to evaluate — optionally followed by the work to review]"
---

Build the success criteria for this task and review work against them: $ARGUMENTS

Apply the full method by loading the `tooluniverse-self-review` skill, then run it on the input above.

## Input parsing

- Treat all of `$ARGUMENTS` as the **task / goal / question** to evaluate, unless it clearly also contains a **result to review** (a pasted answer, a draft, a "here is what I did" section). If a result is present, evaluate it against the generated criteria. If no result is present, run in **checklist mode** — produce the criteria only, no scoring. Do not invent a result to score.

## What to produce

Follow the `tooluniverse-self-review` skill exactly. In brief:

1. Build the rubric with the Recursive Expansion Tree: scenarios → perspectives → concrete, binary (YES/NO) criteria. Complete every expansion round (3 for scenarios, 4 for perspectives, 3 for criteria), deduplicate, then run the polarity check and score calibration.
2. Present a criteria table: `criterion_id`, `criterion`, `points`, `reasoning`. Keep criteria task-specific, binary, balanced (total positive points outweigh negative), and non-redundant.
3. If work was supplied (review mode): give each criterion a YES/NO with a one-line evidence cite, report earned / max-positive / net score, and a ranked gap list (most important unmet criteria first) with a concrete fix for each. If no work was supplied (checklist mode): present the criteria as a definition-of-done checklist and state that no work was reviewed.
