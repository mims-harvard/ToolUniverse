"""Regression tests for self-review intent routing and scoring behavior."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "skills" / "tooluniverse-self-review" / "SKILL.md"
RET_REFERENCE = (
    REPO_ROOT
    / "skills"
    / "tooluniverse-self-review"
    / "references"
    / "ret-scored-evaluation.md"
)
COMMAND = REPO_ROOT / "plugin" / "commands" / "self-review.md"
ROUTER = REPO_ROOT / "skills" / "tooluniverse" / "SKILL.md"


def _squash(text: str) -> str:
    """Normalize Markdown wrapping so assertions test meaning, not line width."""
    return " ".join(text.split())


def test_plain_eval_defaults_to_qualitative_review():
    text = _squash(SKILL.read_text(encoding="utf-8"))

    assert "Do not equate `eval` with scoring" in text
    assert "The presence of work never turns scoring on by itself" in text
    assert '"Eval current work."' in text
    assert "qualitative, no score" in text


def test_current_work_is_not_the_evaluation_instruction():
    text = _squash(SKILL.read_text(encoding="utf-8"))

    assert "Do not confuse the evaluation request with the evaluated task" in text
    assert "the last user message is usually the evaluation instruction" in text
    assert "The most recent assistant-produced deliverable" in text


def test_scoring_is_explicit_opt_in_and_progressively_disclosed():
    skill_text = _squash(SKILL.read_text(encoding="utf-8"))
    reference_text = _squash(RET_REFERENCE.read_text(encoding="utf-8"))

    assert "Scored Evaluation Mode (Explicit Opt-In Only)" in skill_text
    assert "references/ret-scored-evaluation.md" in skill_text
    assert "Use this reference only after the user explicitly requests" in reference_text
    assert "Scenario grounding and expansion" in reference_text


def test_claude_command_preserves_default_review_semantics():
    text = _squash(COMMAND.read_text(encoding="utf-8"))

    assert "not automatically as the task being evaluated" in text
    assert "Plain `eval`, `evaluate`, `review`, `assess`, or `check`" in text
    assert "Do not" in text and "numeric totals unless" in text
    assert "Build the success criteria for this task" not in text


def test_eval_engineering_is_not_hijacked():
    text = _squash(SKILL.read_text(encoding="utf-8"))
    router_text = _squash(ROUTER.read_text(encoding="utf-8"))

    assert "create or run evals" in text
    assert "engineering tasks, not self-review requests" in text
    assert "Evaluation Intent Rule" in router_text
    assert "do not route requests to create or run an eval suite" in router_text
