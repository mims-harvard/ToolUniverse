"""
mc_analyzer.py — Systematic multiple-choice question analyzer.

Usage (analysis mode):
    python mc_analyzer.py \\
        --question "Which of the following best describes..." \\
        --choices "A:option1,B:option2,C:option3,D:option4" \\
        --reasoning "My analysis..."

Usage (verify mode):
    python mc_analyzer.py --verify \\
        --answer "B" \\
        --question "Which of the following..." \\
        --choices "A:option1,B:option2,C:option3,D:option4"

The analyzer forces systematic evaluation of every choice before committing to an answer.
"""

import argparse
import re
import sys
import textwrap


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_choices(choices_str: str) -> dict[str, str]:
    """
    Parse a comma-separated "LETTER:text" string into an ordered dict.

    Accepts formats:
        A:first option,B:second option,C:third option
        A: first option, B: second option
    Colons inside option text are preserved (split only on the first colon
    after the single-character letter key).
    """
    result: dict[str, str] = {}
    # Split on commas that are immediately followed by a letter and a colon.
    parts = re.split(r",\s*(?=[A-Za-z]:)", choices_str)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        colon_idx = part.index(":")
        letter = part[:colon_idx].strip().upper()
        text = part[colon_idx + 1:].strip()
        result[letter] = text
    return result


def wrap(text: str, width: int = 78, indent: str = "    ") -> str:
    return textwrap.fill(text, width=width, initial_indent=indent,
                         subsequent_indent=indent)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_header(title: str) -> None:
    bar = "=" * 72
    print(f"\n{bar}")
    print(f"  {title}")
    print(bar)


def print_section(title: str) -> None:
    print(f"\n--- {title} ---")


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyse(question: str, choices: dict[str, str], reasoning: str) -> None:
    """
    Walk through each choice systematically:
      1. Display all choices.
      2. For each choice print guiding questions.
      3. Apply elimination based on the reasoning text.
      4. Report surviving candidates or a single answer.
    """
    print_header("MULTIPLE-CHOICE SYSTEMATIC ANALYZER")

    # ---- Question display ------------------------------------------------
    print_section("QUESTION")
    print(wrap(question, indent="  "))

    # ---- Choices display -------------------------------------------------
    print_section("ALL CHOICES")
    for letter, text in choices.items():
        print(f"  [{letter}] {text}")

    # ---- Per-choice diagnostic questions ---------------------------------
    print_section("PER-CHOICE EVALUATION FRAMEWORK")
    print("  For each choice, consider BOTH angles before deciding.\n")

    for letter, text in choices.items():
        print(f"  [{letter}] {text}")
        print(f"       WHY CORRECT? → Does this align with the core concept?")
        print(f"                       Is it the most specific/complete answer?")
        print(f"       WHY WRONG?   → Does the reasoning contradict this choice?")
        print(f"                       Is it partially true but missing a key element?")
        print()

    # ---- Reasoning display -----------------------------------------------
    print_section("PROVIDED REASONING")
    print(wrap(reasoning, indent="  "))

    # ---- Elimination pass ------------------------------------------------
    print_section("ELIMINATION PASS")
    print("  Scanning reasoning for explicit mentions of each choice ...\n")

    reasoning_lower = reasoning.lower()
    eliminated: list[str] = []
    surviving: list[str] = []

    # Elimination detection strategy
    # -----------------------------------------------------------------------
    # Single-letter matching in free text is noisy ("a", "b", "c" appear as
    # articles and mid-word substrings). We use two complementary patterns:
    #
    # Pattern 1 — anchored reference: the choice letter appears as a
    #   standalone token at the start of a sentence / after punctuation /
    #   inside brackets, AND a negative keyword appears within ±30 chars.
    #   Anchor chars: start-of-string, [.!?\n] + optional space, or [(].
    #
    # Pattern 2 — explicit elimination phrase: unambiguous multi-word phrases
    #   that contain the letter (e.g. "eliminate a", "rule out b").
    #
    # NEG_WORDS are only applied when a valid anchor is found, keeping the
    # window tight (±30 chars) to avoid cross-sentence false positives.

    NEG_WORDS = [
        "not the answer", "is not", "does not", "cannot", "would not",
        "incorrect", "wrong", "eliminate", "rule out", "discard", "exclude",
        "not correct", "not right", "is wrong", "is incorrect",
    ]

    # Explicit multi-word phrases that already include the letter unambiguously.
    EXPLICIT_TEMPLATES = [
        r"eliminate\s+{l}\b",
        r"rule\s+out\s+{l}\b",
        r"discard\s+{l}\b",
        r"exclude\s+{l}\b",
        r"\[{L}\]\s+is\s+(not|incorrect|wrong)",
        r"\({L}\)\s+is\s+(not|incorrect|wrong)",
        r"{L}\s+is\s+incorrect",
        r"{L}\s+is\s+wrong",
        r"{L}\s+is\s+not\s+correct",
        r"{L}\s+is\s+not\s+the\s+answer",
        r"not\s+{L}\b",
        r"not\s+\[?{L}\]?\)",
    ]

    # Anchor pattern: letter appears right after sentence boundary or bracket.
    ANCHOR_RE = r"(?:(?:^|[.!?\n]\s*)(?:\(?\[?)|\[|\()\s*{l}(?:\s|[)\]:.,])"

    for letter in choices:
        ll = letter.lower()
        L = letter.upper()
        is_eliminated = False
        match_reason = ""

        # --- Pattern 1: anchored letter + negative keyword in tight window ---
        anchor_positions = [
            m.start() for m in re.finditer(
                ANCHOR_RE.replace("{l}", re.escape(ll)),
                reasoning_lower, re.MULTILINE,
            )
        ]
        for pos in anchor_positions:
            window_start = max(0, pos - 10)
            window_end = min(len(reasoning_lower), pos + 80)
            window = reasoning_lower[window_start:window_end]
            for neg in NEG_WORDS:
                if neg in window:
                    is_eliminated = True
                    match_reason = f"'{neg}' near anchored [{L}]"
                    break
            if is_eliminated:
                break

        # --- Pattern 2: explicit elimination phrases ---
        if not is_eliminated:
            for tmpl in EXPLICIT_TEMPLATES:
                pattern = tmpl.replace("{l}", re.escape(ll)).replace("{L}", re.escape(L))
                if re.search(pattern, reasoning_lower, re.IGNORECASE):
                    is_eliminated = True
                    match_reason = f"explicit elimination phrase for [{L}]"
                    break

        if is_eliminated:
            eliminated.append(letter)
            print(f"  [{letter}] ELIMINATED  — {match_reason}")
        else:
            surviving.append(letter)
            print(f"  [{letter}] SURVIVING   — no clear elimination signal found")

    # ---- Verdict ---------------------------------------------------------
    print_section("VERDICT")

    if len(surviving) == 0:
        print("  WARNING: All choices appear eliminated — check reasoning for errors.")
        print("  Surviving candidates: (none — logic contradiction detected)")

    elif len(surviving) == 1:
        answer = surviving[0]
        print(f"  ANSWER: [{answer}] — only one choice survives elimination.")
        print(f"  Text: {choices[answer]}")
        print()
        print("  CONFIDENCE CHECK:")
        print(f"    Re-read the question with [{answer}] in mind.")
        print(f"    Does '{choices[answer]}' directly answer what was asked?")
        print(f"    If yes → commit to [{answer}].")

    else:
        print(f"  NEEDS MORE REASONING — {len(surviving)} choices survive:")
        for letter in surviving:
            print(f"    [{letter}] {choices[letter]}")
        print()
        print("  NEXT STEPS:")
        print("  1. Compare surviving choices pairwise — what distinguishes them?")
        print("  2. Re-read the question stem for a specific qualifier")
        print("     (e.g., 'MOST likely', 'FIRST step', 'BEST describes').")
        print("  3. Apply the most restrictive interpretation of the question.")
        print("  4. If still tied, reason from first principles about which is")
        print("     MORE complete, MORE specific, or the DIRECT mechanism.")

    # ---- Pitfall reminders -----------------------------------------------
    print_section("COMMON MC PITFALLS")
    print("  - 'All of the above' traps: true individually but not as a set.")
    print("  - Distractors that are correct in a DIFFERENT context.")
    print("  - Double negatives: 'which is NOT an example of NOT X?' = X.")
    print("  - Qualifiers matter: 'always', 'never', 'most', 'best', 'first'.")
    print("  - The longest or most detailed answer is not automatically right.")
    print()


# ---------------------------------------------------------------------------
# Verify mode
# ---------------------------------------------------------------------------

def verify(answer: str, question: str, choices: dict[str, str]) -> None:
    """
    Re-read the question and selected answer letter; check for consistency.
    """
    print_header("CONFIDENCE CHECKER — VERIFY MODE")

    answer = answer.strip().upper()

    print_section("QUESTION")
    print(wrap(question, indent="  "))

    print_section("SELECTED ANSWER")
    if answer not in choices:
        print(f"  ERROR: [{answer}] is not among the given choices: "
              f"{', '.join(choices.keys())}")
        sys.exit(1)

    print(f"  [{answer}] {choices[answer]}")

    print_section("CONSISTENCY CHECK")
    print("  Verify each of the following manually:\n")

    checks = [
        f"Does [{answer}] directly answer what the question asks?",
        f"Is '{choices[answer]}' the most COMPLETE answer (not just partially true)?",
        f"Would a different choice be eliminated if [{answer}] is correct?",
        f"Does [{answer}] address the SPECIFIC qualifier in the question "
        f"(most, first, best, always, never)?",
        f"If you substituted [{answer}] back into the question, does the "
        f"sentence make logical sense?",
    ]

    for i, check in enumerate(checks, start=1):
        print(f"  [{i}] {wrap(check, indent='      ').strip()}")
        print()

    print_section("LETTER vs. TEXT ALIGNMENT")
    print(f"  You selected letter [{answer}].")
    print(f"  The text for [{answer}] is: \"{choices[answer]}\"")
    print()
    print("  Confirm: Is this the text your reasoning concluded was correct?")
    print("  If your reasoning said a DIFFERENT letter, you have a mismatch.")
    print("  Common cause: reasoning names B but you wrote C — re-check.")
    print()

    print_section("ALL CHOICES FOR REFERENCE")
    for letter, text in choices.items():
        marker = " ← YOUR CHOICE" if letter == answer else ""
        print(f"  [{letter}] {text}{marker}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Systematic multiple-choice analyzer. Forces evaluation of "
                    "every option before committing to an answer.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Analysis mode
              python mc_analyzer.py \\
                --question "Which drug class inhibits ACE?" \\
                --choices "A:Beta-blockers,B:ACE inhibitors,C:ARBs,D:Statins" \\
                --reasoning "Beta-blockers act on beta receptors, not ACE ..."

              # Verify mode
              python mc_analyzer.py --verify \\
                --answer B \\
                --question "Which drug class inhibits ACE?" \\
                --choices "A:Beta-blockers,B:ACE inhibitors,C:ARBs,D:Statins"
        """),
    )

    parser.add_argument(
        "--verify", action="store_true",
        help="Run in confidence-checker mode instead of full analysis.",
    )
    parser.add_argument(
        "--question", required=True,
        help="The full MC question text (quote the entire string).",
    )
    parser.add_argument(
        "--choices", required=True,
        help='Comma-separated letter:text pairs, e.g. "A:opt1,B:opt2,C:opt3".',
    )
    parser.add_argument(
        "--reasoning",
        help="Your analysis or reasoning string (required in analysis mode).",
    )
    parser.add_argument(
        "--answer",
        help="The answer letter to verify (required in --verify mode).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    choices = parse_choices(args.choices)
    if not choices:
        print("ERROR: Could not parse --choices. "
              "Expected format: \"A:text,B:text,C:text\"")
        sys.exit(1)

    if args.verify:
        if not args.answer:
            parser.error("--verify mode requires --answer LETTER")
        verify(args.answer, args.question, choices)
    else:
        if not args.reasoning:
            parser.error("Analysis mode requires --reasoning TEXT")
        analyse(args.question, choices, args.reasoning)


if __name__ == "__main__":
    main()
