#!/usr/bin/env bash
# Orchestrated harness loop: RUN → ANALYZE → DIAGNOSE → (manual FIX step) → RETEST → DELTA
#
# Steps 1-3 and 5-6 are automated here. Step 4 (FIX) requires invoking
# devtu-* skills which only an interactive Claude session can do. This script
# outputs the diagnose recommendations so a human or a subagent can dispatch
# devtu skills, and then run this script again with --retest to measure delta.
#
# Usage:
#     # Initial run
#     bash scripts/run_harness_loop.sh --benchmark bixbench --n 20 --seed 42
#
#     # Retest after fixes applied
#     bash scripts/run_harness_loop.sh --retest /tmp/failures.json
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HARNESS="$REPO_ROOT/skills/devtu-benchmark-harness/scripts"
EVALS="$REPO_ROOT/skills/evals"

N=20
SEED=42
BENCHMARK=bixbench
MODE=plugin-only
RETEST_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --benchmark) BENCHMARK="$2"; shift 2;;
        --n) N="$2"; shift 2;;
        --seed) SEED="$2"; shift 2;;
        --mode) MODE="$2"; shift 2;;
        --retest) RETEST_FILE="$2"; shift 2;;
        *) echo "Unknown arg: $1"; exit 1;;
    esac
done

cd "$REPO_ROOT"

TS=$(date +%Y%m%d_%H%M%S)
WORK_DIR="$REPO_ROOT/temp_docs_and_tests/benchmark_tracking/run_$TS"
mkdir -p "$WORK_DIR"

# Step 0: check no BixBench memorization snuck in since last run
echo "== Step 0: Memorization audit =="
if ! python3 "$HARNESS/check_memorization.py" --all > "$WORK_DIR/memorization.log" 2>&1; then
    echo "FAIL: skills contain benchmark-specific content. See $WORK_DIR/memorization.log"
    cat "$WORK_DIR/memorization.log"
    exit 1
fi
echo "  clean"

# Step 1: rebuild plugin
echo "== Step 1: Rebuild plugin =="
bash "$REPO_ROOT/scripts/build-plugin.sh" > "$WORK_DIR/build.log" 2>&1
echo "  built"

# Step 2: run benchmark (either fresh sample or retest)
if [[ -n "$RETEST_FILE" ]]; then
    echo "== Step 2: Retest failures from $RETEST_FILE =="
    N_RETEST=$(python3 -c "import json; print(len(json.load(open('$RETEST_FILE'))))")
    python3 "$EVALS/run_benchmark.py" \
        --benchmark "$BENCHMARK" --data-file "$RETEST_FILE" \
        --n "$N_RETEST" --plugin-only 2>&1 | tee "$WORK_DIR/retest.log"
    RESULT_FILE=$(ls -t "$EVALS/$BENCHMARK"/results_*.json | head -1)
else
    echo "== Step 2: Run benchmark (n=$N, seed=$SEED) =="
    SAMPLE_FILE="$WORK_DIR/sample.json"
    python3 -c "
import json, random
random.seed($SEED)
with open('$EVALS/$BENCHMARK/questions.json') as f:
    qs = json.load(f)
sample = random.sample(qs, min($N, len(qs)))
with open('$SAMPLE_FILE', 'w') as f:
    json.dump(sample, f)
print(f'sample: {len(sample)} questions')
"
    MODE_FLAG="--plugin-only"
    case "$MODE" in
        baseline-only) MODE_FLAG="--baseline-only";;
        comparison)    MODE_FLAG="";;
        plugin-only)   MODE_FLAG="--plugin-only";;
    esac
    python3 "$EVALS/run_benchmark.py" \
        --benchmark "$BENCHMARK" --data-file "$SAMPLE_FILE" \
        --n "$N" $MODE_FLAG 2>&1 | tee "$WORK_DIR/run.log"
    RESULT_FILE=$(ls -t "$EVALS/$BENCHMARK"/results_*.json | head -1)
fi

echo "  results: $RESULT_FILE"
cp "$RESULT_FILE" "$WORK_DIR/results.json"

# Step 3: analyze + diagnose
echo "== Step 3: Analyze =="
python3 "$HARNESS/analyze_results.py" \
    --results "$WORK_DIR/results.json" \
    --questions "$EVALS/$BENCHMARK/questions.json" \
    --benchmark "$BENCHMARK" > "$WORK_DIR/analysis.log"
cat "$WORK_DIR/analysis.log"

echo ""
echo "== Step 4: Diagnose =="
python3 "$HARNESS/analyze_results.py" \
    --results "$WORK_DIR/results.json" \
    --questions "$EVALS/$BENCHMARK/questions.json" \
    --benchmark "$BENCHMARK" --diagnose > "$WORK_DIR/diagnose.log"
cat "$WORK_DIR/diagnose.log"

# Step 5: extract failures for retest
python3 "$HARNESS/analyze_results.py" \
    --results "$WORK_DIR/results.json" \
    --questions "$EVALS/$BENCHMARK/questions.json" \
    --extract-failures "$WORK_DIR/failures.json" 2>&1 | tail -5

echo ""
echo "=== HARNESS LOOP COMPLETE ==="
echo "  workspace: $WORK_DIR"
echo "  results:   $WORK_DIR/results.json"
echo "  analysis:  $WORK_DIR/analysis.log"
echo "  diagnose:  $WORK_DIR/diagnose.log"
echo "  failures:  $WORK_DIR/failures.json"
echo ""
echo "Next steps:"
echo "  1. Review diagnose.log for [HIGH]/[MEDIUM] recommendations"
echo "  2. For each recommendation, invoke the named devtu skill:"
echo "     e.g., 'Skill(\"devtu-optimize-skills\")' on tooluniverse-rnaseq-deseq2"
echo "  3. After fixes applied, run:"
echo "     bash scripts/run_harness_loop.sh --retest $WORK_DIR/failures.json"
echo "  4. Compare retest score vs original — a true improvement flips"
echo "     failures to correct without touching passing questions."
