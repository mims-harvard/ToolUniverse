---
name: self-review
description: Review current or supplied work against the user's actual goal, report evidence-backed strengths, gaps, risks, and fixes, and give a plain-language completion verdict. Qualitative by default; only score or grade when explicitly requested.
argument-hint: "[work or review request; omit to review the current work]"
---

Apply the `tooluniverse-self-review` skill to this request: $ARGUMENTS

## Interpret the request

- Treat `$ARGUMENTS` as the **evaluation instruction and optional target**, not
  automatically as the task being evaluated.
- If `$ARGUMENTS` is empty or refers to "current work", "this", or "what we have", recover
  the original goal and current work from the conversation and available artifacts.
- If an artifact, answer, file, diff, or section is supplied explicitly, review that target
  against its stated or preceding goal.
- Plain `eval`, `evaluate`, `review`, `assess`, or `check` requests are qualitative. Do not
  generate points, grades, weighted criteria, or numeric totals unless `$ARGUMENTS`
  explicitly asks for them.
- If the request is to create an eval suite, test, grader, or benchmark, treat it as an
  engineering task rather than running self-review.

## Produce

By default, give a concise evidence-backed assessment with findings ordered by impact,
meaningful strengths, prioritized fixes, and a plain-language completion verdict. Do not
print RET scenarios, perspectives, criteria tables, or scoring machinery unless explicitly
requested.
