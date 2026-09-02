# Qworld RET Scored Evaluation

Use this reference only after the user explicitly requests scoring, grading, weighted
criteria, LLM-as-judge scoring, Qworld, or the Recursive Expansion Tree (RET).

## Inputs

- **Original goal**: the task, question, constraints, and acceptance criteria.
- **Work product**: the actual answer, implementation, artifact, or result to grade.
- **Scale**: the user's requested scheme, or the default weighted scheme below.

Never treat the evaluation instruction itself as the original goal. If the user says
"score current work", recover the goal and work from the preceding conversation and
available artifacts first.

## Recursive Expansion Tree

Build the rubric from the task:

```text
Original goal
  -> scenarios that materially change what good means
       -> task-specific evaluation perspectives
            -> concrete, binary criteria
```

Keep this derivation internal unless the user asks to see it.

### 1. Scenario grounding and expansion

Identify a minimal non-redundant set of real contexts in which the task could arise and
where the context changes what constitutes a good result. Expand three times by asking
what materially different audience, setting, stakes, constraints, or domain variation is
missing. Do not add paraphrases of existing scenarios.

### 2. Perspective generation and expansion

For each scenario, derive evaluation dimensions from the task itself. Do not use a fixed
dimension list. Expand four times by asking which distinct evaluation angle would yield
new criteria. Consolidate overlap and assign perspective IDs (`p0`, `p1`, ...).

### 3. Criteria generation and expansion

For each retained perspective, write self-contained criteria that are:

- answerable `YES` or `NO`;
- specific to the task and scenario;
- observable in the work product;
- non-redundant; and
- phrased as one concrete required or forbidden behavior.

Expand three times by asking what additional observable behavior would materially change
the verdict. Then merge overlap and assign criterion IDs (`c0`, `c1`, ...).

Include negative criteria only for harmful, misleading, or materially quality-reducing
behavior—not minor style preferences. Phrase negative criteria as the bad behavior itself;
the negative point value supplies the polarity.

## Default Weighted Scheme

Use this scheme only when the user did not provide another one:

- Positive `1–10`: `10` critical safety/core requirement; `8–9` important completeness;
  `5–7` meaningful quality; `1–4` minor enhancement.
- Negative `-1–-10`: `-10` dangerous; `-8–-9` major error; `-5–-7` material quality
  problem; `-1–-4` minor problem.

For each criterion provide `criterion_id`, `criterion`, `points`, and a concise reason for
the weight. Check that:

1. desirable criteria have positive signs and harmful behaviors have negative signs;
2. more important criteria have larger absolute weights;
3. positive and negative criteria do not duplicate the same requirement; and
4. total positive points exceed total negative magnitude.

## Apply the Rubric

For every criterion:

1. Mark `YES` or `NO`.
2. Cite the specific evidence or location supporting the verdict.
3. Sum points only for criteria marked `YES`; positive items add and negative items
   subtract.

Report:

- earned positive points and maximum positive points;
- negative penalties triggered;
- net total and the scale interpretation;
- the most important unmet positive criteria and triggered negative criteria; and
- one concrete fix for each high-impact gap.

If there is no work product, do not fabricate a score. Return a weighted rubric and state
that no work was graded.

## Output Discipline

- Show scenarios and perspectives only if the user asks for the full derivation.
- Keep reasoning proportional; do not dump expansion logs.
- Prefer evidence and actionable gaps over score theater.
- If evidence is unavailable, mark the criterion `NO` or `not verifiable` according to the
  user's grading policy and disclose the limitation.

## Citation

This method is based on Qworld:

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
