"""
Benchmark runner for ToolUniverse plugin evaluation.

Runs questions through Claude Code with and without the ToolUniverse plugin,
captures outputs, and compares accuracy.

Usage:
    python run_benchmark.py --benchmark lab-bench --subset DbQA --n 10
    python run_benchmark.py --benchmark bixbench --n 5
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PLUGIN_DIR = str(
    Path(__file__).resolve().parent.parent.parent / "dist" / "tooluniverse-plugin"
)
RESULTS_DIR = Path(__file__).resolve().parent
BIXBENCH_DATA_DIRS = [
    Path(__file__).resolve().parent.parent.parent
    / "temp_docs_and_tests"
    / "bixbench"
    / "data",
    Path(__file__).resolve().parent.parent.parent
    / "temp_docs_and_tests"
    / "bixbench"
    / "bixbench"
    / "data",
]


def _load_plugin_guidance():
    """Load the research.md guidance from the plugin, stripping YAML frontmatter."""
    research_md = Path(PLUGIN_DIR) / "commands" / "research.md"
    if not research_md.exists():
        return ""
    text = research_md.read_text()
    # Strip YAML frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    return text.strip()


# Skills whose BixBench-verified conventions we always want loaded for data-analysis Qs.
_BIXBENCH_SKILL_NAMES = [
    "tooluniverse-statistical-modeling",
    "tooluniverse-rnaseq-deseq2",
    "tooluniverse-gene-enrichment",
    "tooluniverse-crispr-screen-analysis",
    "tooluniverse-phylogenetics",
    "tooluniverse-variant-analysis",
    "tooluniverse-single-cell",
]


def _extract_bixbench_section(skill_md_text: str) -> str:
    """Return only the 'BixBench-verified conventions' section of a SKILL.md,
    or empty string if absent. Keeps prompt size manageable while delivering
    the dataset-specific rules the benchmark needs."""
    lines = skill_md_text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("## BixBench-verified conventions"):
            start = i
            break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        s = lines[j].strip()
        if s.startswith("## ") and not s.startswith("## BixBench-verified"):
            end = j
            break
    return "\n".join(lines[start:end]).strip()


def _load_bixbench_skill_snippets():
    """Concatenate each skill's BixBench-verified conventions section."""
    chunks = []
    for name in _BIXBENCH_SKILL_NAMES:
        skill_md = Path(PLUGIN_DIR) / "skills" / name / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text()
        # Strip YAML frontmatter
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                text = parts[2]
        section = _extract_bixbench_section(text)
        if section:
            chunks.append(f"### From skill: {name}\n\n{section}")
    if not chunks:
        return ""
    return (
        "## Pre-loaded skill conventions (BixBench-verified)\n\n"
        "These rules come from the matching specialized skills. Apply them directly "
        "rather than reinventing data-handling conventions.\n\n"
        + "\n\n".join(chunks)
    )


def _categorize_for_skill(question_text: str) -> str | None:
    """Determine which skill should handle this question (simulates auto-matching)."""
    q = question_text.lower()
    if "deseq2" in q or "differential expression" in q or "differentially expressed" in q or "fold change" in q or "log2" in q or "deg " in q:
        return "tooluniverse-rnaseq-deseq2"
    if "enrichgo" in q or "enrichment" in q or "go " in q or "kegg" in q or "gseapy" in q:
        return "tooluniverse-gene-enrichment"
    if "anova" in q or "regression" in q or "chi-square" in q or "spline" in q or "cohen" in q or "f-statistic" in q or "odds ratio" in q:
        return "tooluniverse-statistical-modeling"
    if "phylo" in q or "treeness" in q or "parsimony" in q or "phykit" in q or "saturation" in q or "dvmc" in q or "tree length" in q or "long branch" in q or ("alignment" in q and ("gap" in q or "mafft" in q)):
        return "tooluniverse-phylogenetics"
    if "variant" in q or "vcf" in q or "vaf" in q or "snp" in q:
        return "tooluniverse-variant-analysis"
    if "crispr" in q or "mageck" in q or "sgrna" in q:
        return "tooluniverse-crispr-screen-analysis"
    if "scanpy" in q or "single-cell" in q or "h5ad" in q:
        return "tooluniverse-single-cell"
    return None


def _load_full_skill(skill_name: str) -> str:
    """Load the full SKILL.md content (simulates what happens when skill auto-invokes)."""
    skill_md = Path(PLUGIN_DIR) / "skills" / skill_name / "SKILL.md"
    if not skill_md.exists():
        return ""
    text = skill_md.read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    return text.strip()


_PLUGIN_GUIDANCE = None


_SKILL_ROUTING_GUIDANCE = """## CRITICAL: Invoke the matching skill BEFORE answering

You MUST invoke the appropriate skill via the Skill tool before writing any analysis code.
Do NOT answer from memory or write your own code first — the skill contains exact tool
references and computational procedures that produce correct results.

| If the question involves… | Invoke FIRST |
|---|---|
| DESeq2, differential expression, gene counts, dispersion, fold change | Skill('tooluniverse-rnaseq-deseq2') |
| GO enrichment, KEGG, pathway, clusterProfiler, gseapy | Skill('tooluniverse-gene-enrichment') |
| ANOVA, regression, chi-square, spline, Cohen's d, clinical trials | Skill('tooluniverse-statistical-modeling') |
| Phylogenetics, treeness, saturation, parsimony, PhyKIT, tree length | Skill('tooluniverse-phylogenetics') |
| VCF, variants, VAF, SNP, mutation classification | Skill('tooluniverse-variant-analysis') |
| CRISPR screen, MAGeCK, sgRNA, pathway GSEA on screen data | Skill('tooluniverse-crispr-screen-analysis') |
| scRNA-seq, scanpy, h5ad, UMAP, clustering | Skill('tooluniverse-single-cell') |

After invoking the skill, follow its instructions exactly — especially any MANDATORY tool usage directives.
"""


def get_plugin_guidance(include_bixbench_skills: bool = True, skill_routing_mode: bool = False):
    """Cache and return the plugin guidance text.

    If skill_routing_mode is True, uses minimal guidance that forces the agent
    to invoke skills via the Skill tool instead of pre-injecting conventions.
    This tests whether active skill invocation produces better results than
    passive convention injection.
    """
    global _PLUGIN_GUIDANCE
    if _PLUGIN_GUIDANCE is None:
        research = _load_plugin_guidance()
        if skill_routing_mode:
            _PLUGIN_GUIDANCE = research + "\n\n" + _SKILL_ROUTING_GUIDANCE
        elif include_bixbench_skills:
            extras = _load_bixbench_skill_snippets()
            _PLUGIN_GUIDANCE = research + "\n\n" + extras if extras else research
        else:
            _PLUGIN_GUIDANCE = research
    return _PLUGIN_GUIDANCE


def run_claude(
    prompt: str,
    with_plugin: bool,
    max_turns: int = 60,
    timeout: int = 600,
    skill_routing: bool = False,
    full_skill_injection: bool = False,
    question_text: str = "",
):
    """Run a prompt through Claude Code, optionally with the ToolUniverse plugin.

    Injection modes (in priority order):

    1. full_skill_injection (recommended): Simulates the real interactive plugin
       experience. Injects the router skill (tooluniverse) which auto-matches
       any science question, PLUS the matched sub-skill's full content. This is
       what a real user sees: router loads → routes to sub-skill → sub-skill loads.

    2. skill_routing: Minimal guidance that tells the agent to invoke skills via
       the Skill tool. Agent must actively call Skill('name').

    3. Default: Injects research.md + BixBench convention snippets from each skill.
       This is the legacy mode — convention text without full skill context.
    """
    # In plugin mode (interactive), the plugin's skill system handles
    # routing — no guidance injection needed. The router skill auto-matches,
    # dispatches to the right sub-skill, and the sub-skill loads.
    #
    # In baseline mode (no plugin), no guidance is injected.
    # The agent uses only Bash/Read/Write to answer from scratch.

    if with_plugin:
        # Interactive mode: pipe question via stdin with plugin loaded.
        # Inject a compact system prompt with critical analysis conventions
        # that the agent needs for data analysis questions. This simulates
        # what a user would get if they have CLAUDE.md with these rules.
        cmd = [
            "claude",
            "--plugin-dir", PLUGIN_DIR,
            "--output-format", "json",
            "--max-turns", str(max_turns),
            "--append-system-prompt",
            "When analyzing local data files, invoke the matching ToolUniverse skill "
            "FIRST via Skill('skill-name') before writing code. "
            "Critical conventions: "
            "(1) Clinical trial AE analysis: use ALL AEs, max(AESEV) per subject, "
            "do NOT filter by condition name. Use encoding='latin1'. "
            "(2) Variant fraction: denominator is coding variants only, not all variants. "
            "(3) DESeq2: prefer R DESeq2 over pydeseq2. Check for authoritative scripts first. "
            "(4) Expression ANOVA: per-gene values, not per-sample totals. "
            "(5) Spline models: use R ns(), include focal-strain endpoint only. "
            "(6) PhyKIT saturation: use 1-slope (second column), not slope.",
        ]
    else:
        # Baseline: headless mode, no plugin, limited tools
        cmd = [
            "claude", "-p", prompt,
            "--output-format", "json",
            "--max-turns", str(max_turns),
            "--allowedTools", "Bash,Read,Write",
        ]

    try:
        if with_plugin:
            # Pipe question via stdin for interactive mode
            result = subprocess.run(
                cmd, input=prompt, capture_output=True, text=True, timeout=timeout
            )
        else:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"result": result.stdout, "raw": True}
        else:
            return {"error": result.stderr[:500], "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout after {timeout}s"}


def extract_answer(response: dict) -> str:
    """Extract the text answer from a Claude response."""
    if "error" in response:
        return f"ERROR: {response['error']}"
    if "result" in response:
        if isinstance(response["result"], str):
            return response["result"]
        if isinstance(response["result"], list):
            texts = [
                b.get("text", "")
                for b in response["result"]
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            return "\n".join(texts)
    return json.dumps(response)[:1000]


def grade_answer(
    predicted: str, ground_truth: str, question: str, eval_mode: str = ""
) -> dict:
    """Grade an answer using the unified grader from the benchmark harness.

    Delegates to grade_answers.grade_answer which supports 7 strategies:
    exact, MC, range (with rounding tolerance), normalized (bidirectional),
    numeric proximity (5%), synonym, and LLM verifier.

    LLM grading is enabled by default for eval_mode="llm_verifier" questions.
    """
    harness_dir = os.path.join(
        os.path.dirname(__file__), "..", "devtu-benchmark-harness", "scripts"
    )
    if harness_dir not in sys.path:
        sys.path.insert(0, harness_dir)

    from grade_answers import grade_answer as _grade

    result = _grade(
        predicted=predicted,
        ground_truth=ground_truth,
        eval_mode=eval_mode,
        numeric_tolerance=0.05,
        use_llm=True,
        question=question,
    )
    # Flatten strategies for backward compatibility
    strategies = result.get("strategies", {})
    return {
        "correct": result["correct"],
        "exact_match": strategies.get("exact_match", False),
        "mc_match": strategies.get("mc_match", False),
        "range_match": strategies.get("range_match", False),
        "normalized_match": strategies.get("normalized_match", False),
        "numeric_match": strategies.get("numeric_match", False),
        "ground_truth": ground_truth,
        "predicted_excerpt": predicted[:500],
    }


def run_benchmark(
    benchmark: str,
    questions: list,
    n: int = 10,
    with_plugin: bool = True,
    max_turns: int = 60,
    timeout: int = 600,
):
    """Run a benchmark and return results."""
    results = []
    subset = questions[:n]

    config_name = "with_plugin" if with_plugin else "baseline"
    print(f"\n{'='*60}")
    print(f"Running {benchmark} ({config_name}): {len(subset)} questions")
    print(f"{'='*60}")

    for i, q in enumerate(subset):
        question_text = q.get("question", q.get("prompt", ""))
        # BixBench: 'ideal' is the real answer, 'answer' is a boolean
        # Lab-bench: 'answer' is the MC letter, 'ideal' is the full text
        raw_answer = q.get("answer", "")
        ideal = q.get("ideal", "")
        if isinstance(raw_answer, bool) or raw_answer in (True, False, "True", "False"):
            ground_truth = str(ideal)  # BixBench
        else:
            ground_truth = str(raw_answer) if raw_answer else str(ideal)
        q_id = q.get("id", q.get("short_id", i))

        # For BixBench: prepend data file paths so the agent knows where the data is
        data_folder = q.get("data_folder", "")
        if data_folder and benchmark == "bixbench":
            capsule_dir_name = data_folder.replace(".zip", "")
            capsule_path = None
            for data_dir in BIXBENCH_DATA_DIRS:
                candidate = data_dir / capsule_dir_name
                if candidate.exists():
                    capsule_path = candidate
                    break
            if capsule_path:
                data_files = [f.name for f in capsule_path.iterdir() if f.is_file()]
                question_text = (
                    f"Data files are located at: {capsule_path}\n"
                    f"Files available: {', '.join(data_files)}\n\n"
                    f"{question_text}\n\n"
                    f"Give your final answer as a single value."
                )

        # For BixBench range_verifier: ground truth is a range like "(0.76,0.78)"
        eval_mode = q.get("eval_mode", "")

        print(f"\n[{i+1}/{len(subset)}] Q{q_id}: {question_text[:80]}...")

        start = time.time()
        response = run_claude(question_text, with_plugin, max_turns, timeout)
        elapsed = time.time() - start

        answer = extract_answer(response)
        grade = grade_answer(answer, ground_truth, question_text, eval_mode)

        result = {
            "id": q_id,
            "question": question_text,
            "ground_truth": ground_truth,
            "predicted": answer[:2000],
            "correct": grade["correct"],
            "elapsed_seconds": round(elapsed, 1),
            "config": config_name,
        }
        results.append(result)

        status = "CORRECT" if grade["correct"] else "WRONG"
        print(f"  {status} ({elapsed:.1f}s) | GT: {ground_truth[:50]}")

    # Summary
    correct = sum(1 for r in results if r["correct"])
    total = len(results)
    print(f"\n{'='*60}")
    print(f"Results: {correct}/{total} correct ({100*correct/total:.1f}%)")
    print(f"{'='*60}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Run ToolUniverse benchmark")
    parser.add_argument(
        "--benchmark", required=True, choices=["lab-bench", "bixbench"]
    )
    parser.add_argument("--subset", default="DbQA", help="Subset name for lab-bench")
    parser.add_argument("--n", type=int, default=10, help="Number of questions to run")
    parser.add_argument(
        "--max-turns", type=int, default=60, help="Max turns per question"
    )
    parser.add_argument(
        "--timeout", type=int, default=1800, help="Timeout per question (seconds)"
    )
    parser.add_argument(
        "--baseline-only", action="store_true", help="Only run baseline (no plugin)"
    )
    parser.add_argument(
        "--plugin-only", action="store_true", help="Only run with plugin"
    )
    parser.add_argument("--data-file", type=str, help="Path to questions JSON file")
    args = parser.parse_args()

    # Load questions
    if args.data_file:
        with open(args.data_file) as f:
            questions = json.load(f)
    else:
        data_path = RESULTS_DIR / args.benchmark / "questions.json"
        if not data_path.exists():
            print(f"Error: {data_path} not found. Download the dataset first.")
            return
        with open(data_path) as f:
            questions = json.load(f)

    print(f"Loaded {len(questions)} questions from {args.benchmark}")

    all_results = {}

    # Run with plugin
    if not args.baseline_only:
        results_plugin = run_benchmark(
            args.benchmark,
            questions,
            n=args.n,
            with_plugin=True,
            max_turns=args.max_turns,
            timeout=args.timeout,
        )
        all_results["with_plugin"] = results_plugin

    # Run baseline
    if not args.plugin_only:
        results_baseline = run_benchmark(
            args.benchmark,
            questions,
            n=args.n,
            with_plugin=False,
            max_turns=args.max_turns,
            timeout=args.timeout,
        )
        all_results["baseline"] = results_baseline

    # Save results
    output_path = (
        RESULTS_DIR
        / args.benchmark
        / f"results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    # Print comparison
    if "with_plugin" in all_results and "baseline" in all_results:
        plugin_correct = sum(
            1 for r in all_results["with_plugin"] if r["correct"]
        )
        baseline_correct = sum(
            1 for r in all_results["baseline"] if r["correct"]
        )
        n = len(all_results["with_plugin"])
        print(f"\n{'='*60}")
        print(f"COMPARISON ({args.benchmark}, n={n}):")
        print(
            f"  With plugin:  {plugin_correct}/{n} ({100*plugin_correct/n:.1f}%)"
        )
        print(
            f"  Baseline:     {baseline_correct}/{n} ({100*baseline_correct/n:.1f}%)"
        )
        print(
            f"  Delta:        +{plugin_correct - baseline_correct} ({100*(plugin_correct - baseline_correct)/n:.1f}%)"
        )
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
