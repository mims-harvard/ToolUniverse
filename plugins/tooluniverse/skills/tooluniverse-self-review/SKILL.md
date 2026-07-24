---

name: tooluniverse-self-review
description: "Generate the success criteria for a task or question, then review work against them. Given a task, goal, or open-ended question, decompose it into scenarios, evaluation perspectives, and fine-grained weighted YES/NO criteria using the Recursive Expansion Tree (RET) method; if work is supplied, score it criterion-by-criterion and surface what is missing or could be better. Use when asked to self-review or check your own work, judge whether a task is done well or completely, build a definition-of-done or completeness checklist, create an evaluation rubric or grading criteria, score or grade answers to a question, set up an LLM-as-judge rubric, or when the user mentions self-review, completeness check, success criteria, evaluation criteria, scoring rubric, Qworld, or the RET algorithm.\n"
---

# Self-Review: Task Success Criteria + Work Review

Derive the criteria that define a good result for a specific task, then review work
against them. Each task defines its own "evaluation world" -- a set of scenarios,
perspectives, and criteria that capture what matters for judging results for that
specific task. Built on the Qworld Recursive Expansion Tree (RET).

## When to Use

- An agent (or person) is about to do, is doing, or has finished a task and wants to know
  what a good result must cover, or what is missing or weak.
- You need a definition-of-done or completeness checklist for a task or goal.
- You need an evaluation rubric / grading criteria for answers to an open-ended question.
- You want to score or grade responses: LLM-as-judge, exam answers, candidate responses.

## Inputs

- **task** (required): the task, goal, or question to evaluate. If it is a multi-turn
  conversation, treat the whole exchange as context and the last user message as the
  primary intent. If it includes an image or retrieved web context, factor that in.
- **work** (optional): a planned approach or a completed result to review. If no work is
  supplied, run in **checklist mode** -- produce the criteria only, no scoring.

## Core Principles

1. **Task-specific**: Every scenario, perspective, and criterion must be derived from the
   task's content, intent, and context. Never reuse a fixed set of dimensions across tasks.
2. **Binary and verifiable**: Each final criterion must be answerable YES or NO by a reviewer.
3. **Non-redundant**: At every level, check for overlap before adding new items.
4. **Balanced**: Include both positive criteria (what a good result must do) and negative
   criteria (what constitutes harmful or misleading content). Positive total points must
   outweigh negative.
5. **Coverage-driven**: At each level, repeatedly ask "what's missing?" to ensure the
   evaluation space implied by the task is fully explored.

## Algorithm Overview

The RET builds a 3-level tree from the task:

```
Task / goal / question
  -> Level 1: Scenarios (contextual framings that change what "good" means)
       -> Level 2: Perspectives (evaluation dimensions per scenario)
            -> Level 3: Criteria (concrete, binary rubric items with scores)
```

At each level, two operators apply:
- **Hierarchical decomposition**: break a node into finer-grained children at the next level.
- **Horizontal expansion**: ask "what else is missing?" and add sibling nodes for coverage.

After the tree is built, **Phase B** reviews supplied work against the leaf criteria.

---

## Step-by-Step Workflow

Copy this checklist and track progress as you work:

```
Task Progress:
- [ ] Step 1: Scenario grounding
- [ ] Step 2: Scenario expansion (3 rounds)
- [ ] Step 3: Perspective generation
- [ ] Step 4: Perspective expansion (4 rounds)
- [ ] Step 5: Perspective review and consolidation
- [ ] Step 6: Criteria generation
- [ ] Step 7: Criteria expansion (3 rounds)
- [ ] Step 8: Criteria review and consolidation
- [ ] Step 9: Polarity check
- [ ] Step 10: Score calibration
- [ ] Phase B: Review work against criteria (or emit checklist if no work supplied)
```

---

### Step 1: Scenario Grounding

**Goal**: Identify the distinct real-world contexts in which this task could arise, where
each context would materially change what constitutes a good result.

**Method**:
- Read the task carefully. Infer its domain, intent, audience, stakes, and implicit
  constraints.
- Ask: "In what different situations could someone pursue this task, and how would the
  situation change what a good result looks like?"
- Produce a minimal, non-redundant set of scenarios. Merge any that would lead to the same
  evaluation criteria.

**Output format** for each scenario:
- `scenario_name`: short descriptive label
- `scenario_description`: 3-5 sentences explaining what is unique about this context and
  why it changes what "good" means

---

### Step 2: Scenario Expansion (3 rounds)

**Goal**: Ensure comprehensive coverage of the evaluation space at the scenario level.

**Method** (repeat 3 times):
1. Review all existing scenarios.
2. Ask: "What contexts or framings are missing that would require different evaluation criteria?"
3. Identify gaps along context axes (audience, setting, stakes, constraints, domain variation, etc.).
4. Generate ONLY new scenarios that differ materially from all existing ones. Do not repeat
   or rephrase existing scenarios.

After each round, append new scenarios to the list.

---

### Step 3: Perspective Generation

**Goal**: For each scenario, derive the evaluation dimensions that matter for judging a
result in that context.

**Method**:
- For EACH scenario, produce 4-7 non-overlapping evaluation perspectives.
- Each perspective must be grounded in the scenario and the task. Derive perspectives
  entirely from the task's content and context -- do not apply a pre-set list of dimensions.
- Aim for maximally diverse themes, including unconventional angles that are specific to
  this task.
- Each perspective should be high-level enough to spawn multiple criteria, yet narrow
  enough to avoid overlap with other perspectives.

**Output format** for each perspective:
- `perspective_name`: 2-5 word descriptive label
- `perspective_description`: 3-5 sentences explaining what this perspective evaluates and
  listing 3-5 specific sub-aspects it covers

---

### Step 4: Perspective Expansion (4 rounds)

**Goal**: Fill coverage gaps in the perspective set.

**Method** (repeat 4 times):
1. Review all perspectives across all scenarios.
2. Map coverage across quality dimensions implied by the task.
3. Ask: "What evaluation angles are missing that would yield materially different criteria?"
4. Generate ONLY new perspectives that provide distinct evaluation value. Do not repeat
   existing ones.

After each round, append new perspectives to the collection.

---

### Step 5: Perspective Review and Consolidation

**Goal**: Produce a clean, non-redundant set of perspectives ready for criteria generation.

**Method**:
- If two perspectives target the same evaluation angle but under different scenarios,
  combine scenario-specific details into each description but keep them as separate
  perspectives.
- Remove perspectives that are off-topic, redundant with others, or too vague to guide
  concrete criteria generation.
- Each kept perspective must contribute unique evaluation value for this task.
- Assign each kept perspective a unique ID (p0, p1, p2, ...).

---

### Step 6: Criteria Generation

**Goal**: For each reviewed perspective, generate concrete, binary evaluation criteria.

**Method**:
- For EACH perspective, generate criteria that a reviewer can check YES or NO against a
  result.
- Cover all sub-aspects listed in the perspective description.

**Criteria rules**:
1. **Binary**: Each criterion must be answerable YES/NO.
2. **Scenario-specific**: Explicitly reference features of the task and scenario. Make
   criteria as detailed and specific as possible.
3. **Self-contained**: Each criterion is a standalone statement in the form
   [Verb + Specific Requirement]. Start with one clear action verb, then state the exact
   required or forbidden content with qualifiers.
4. **Balanced**: Include positive criteria (required content/behavior) and negative
   criteria (harmful, misleading, or critically wrong content). Only add negative criteria
   when the issue represents harmful, dangerous, or significantly quality-reducing behavior
   -- not minor stylistic concerns.
5. **Diverse**: Cover all sub-aspects of the perspective.

**Negative criteria phrasing**: Describe the bad behavior directly. Instead of "Avoids
doing X", write "Does X" (where X is the harmful behavior). The criterion text states the
behavior; its negative score indicates that meeting it is bad.

**Scoring standard**:
- Positive: 1-10 (10 = critical safety/core requirement; 8-9 = important completeness;
  5-7 = quality enhancer; 1-4 = minor nice-to-have)
- Negative: -1 to -10 (-10 = dangerous/harmful; -8 to -9 = major omission or error;
  -5 to -7 = quality issue; -1 to -4 = minor issue)

**Output format** for each criterion:
- `criterion`: the criterion text
- `points`: integer score (positive or negative)
- `reasoning`: 2-3 sentences explaining why this criterion matters for this task and why
  it received this weight

---

### Step 7: Criteria Expansion (3 rounds)

**Goal**: Fill coverage gaps in the criteria set.

**Method** (repeat 3 times):
1. Review all existing criteria.
2. Ask: "What concrete content or behavior, if present or absent in a result, would change
   whether it passes or fails -- and is not yet covered?"
3. Generate ONLY new criteria that are non-overlapping with existing ones.
4. Follow the same rules and scoring standard as Step 6.

After each round, append new criteria to the collection.

---

### Step 8: Criteria Review and Consolidation

**Goal**: Produce a concise, non-redundant final rubric.

**Method**:
- **Deduplicate and merge**: Combine criteria that assess the same aspect. Keep the most
  precise wording and include all distinct details from merged criteria.
- **Positive/negative overlap**: If a positive and negative criterion cover the same
  aspect, keep only the positive.
- **Neutralize fixed facts**: Replace hard-coded numbers, dates, versions, limits, or
  placeholders with a requirement that the result states the current/official/latest value
  or standard.
- **Balance check**: Ensure total positive points outweigh total negative points. Retain
  all distinct, non-overlapping items.
- Assign each final criterion a unique ID (c0, c1, c2, ...).

---

### Step 9: Polarity Check

**Goal**: Verify that every criterion's score sign correctly reflects whether meeting it is
good or bad.

**Method**:
- For each criterion, determine: does meeting this criterion improve the result (positive)
  or indicate a problem (negative)?
- A criterion that describes desirable behavior should have a positive score.
- A criterion that describes harmful, wrong, or misleading behavior should have a negative
  score.
- Phrasing like "Avoids doing X" describes desirable behavior (positive). Phrasing like
  "Does X" (where X is bad) describes undesirable behavior (negative).
- Adjust the sign of points if misclassified. Do not change the criterion text.

---

### Step 10: Score Calibration

**Goal**: Ensure score magnitudes accurately reflect importance.

**Method**:
- Review each criterion's absolute score against the scoring standard from Step 6.
- A more important or severe issue must always have a higher absolute score than a less
  important one.
- Adjust magnitudes where needed. Do not change the sign (positive/negative direction) or
  the criterion text.
- Verify the scoring standard is applied consistently:
  - Positive: 10 = critical, 8-9 = important, 5-7 = quality, 1-4 = minor
  - Negative: -10 = dangerous, -8 to -9 = major, -5 to -7 = moderate, -1 to -4 = minor

---

### Phase B: Review Work Against Criteria

**Goal**: Apply the finalized criteria to the actual work, or emit a checklist if none was
supplied.

**If no work was supplied (checklist mode)**:
- State explicitly: "No work supplied -- criteria only (definition-of-done checklist)."
- Present the criteria as a checklist the user can run against any future result.
- Stop here; do not invent or assume a result to score.

**If work was supplied (review mode)**:
1. For EACH criterion, judge whether the work meets it: YES or NO, with a one-line cite of
   the specific evidence in the work (quote or location) that justifies the verdict.
2. Compute the score: sum the `points` of every criterion marked YES (positive criteria add,
   negative criteria subtract). Report earned points, maximum positive points, and the
   net total.
3. Produce a ranked **gap list**: the unmet positive criteria and any met negative criteria,
   ordered by absolute `points` (most important first). For each, give a one-line concrete
   fix.
4. Keep the review evidence-based. Do not credit a criterion the work does not actually
   satisfy, and do not penalize for criteria outside the stated task.

---

## Final Output Format

Present results in this order:

1. **Mode line**: "review mode" or "checklist mode (no work supplied)".
2. **Scenarios**: list with IDs, names, descriptions.
3. **Reviewed perspectives**: list with IDs, names, descriptions.
4. **Criteria table**: each row has `criterion_id`, `criterion`, `points`, `reasoning`.
5. **Summary statistics**: number of scenarios, perspectives, raw criteria, final criteria;
   total positive and total negative points.
6. **Review** (review mode only): per-criterion YES/NO + evidence, earned/max/net score,
   and the ranked gap list with fixes.

---

## Handling Special Inputs

**Multi-turn conversations**: If the task is a conversation (user-assistant exchange), treat
the full conversation as context. The last user message is typically the primary intent;
earlier messages provide context that may affect evaluation dimensions.

**Tasks with images**: If the task includes an image, factor image content into scenario
analysis and criteria generation. Reference visual elements where relevant in criteria.

**Tasks with retrieved web context**: If web-retrieved context is provided alongside the
task, use it to inform factual grounding of scenarios and criteria. Do not limit analysis
to only the retrieved content -- also apply general reasoning.

---

## Key Constraints

- **No fixed dimension lists**: Never apply a pre-defined set of evaluation dimensions.
  Every scenario, perspective, and criterion must be freshly derived from the task.
- **Expansion counts matter**: Complete all specified expansion rounds (3 for scenarios,
  4 for perspectives, 3 for criteria). Skipping rounds reduces coverage.
- **Deduplication is mandatory**: After each expansion phase and before finalization, check
  for and remove redundant items.
- **Criteria must be binary**: Every criterion in the final set must be checkable as YES or
  NO. Do not produce criteria that require subjective degree judgments.
- **Evidence-based review**: In review mode, every YES/NO must be backed by specific
  evidence from the supplied work.

---

## Citation

This skill ports the Qworld method. If you use it in your work, please cite:

```bibtex
@misc{gao2026qworldquestionspecificevaluationcriteria,
      title={Qworld: Question-Specific Evaluation Criteria for LLMs},
      author={Shanghua Gao and Yuchang Su and Pengwei Sui and Curtis Ginder and Marinka Zitnik},
      year={2026},
      eprint={2603.23522},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2603.23522},
}
```
