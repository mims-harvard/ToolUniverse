#!/usr/bin/env bash
# Run a SINGLE benchmark question and capture its result. The user-facing
# harness loop ("attempt → fail → fix → retest") wraps this: for each
# question, attempt once; if WRONG, the orchestrating session inspects the
# failure, applies a general fix, then re-invokes this script. The script
# itself does NOT auto-retry — that's the agent's job, so the fix can be
# applied between attempts.
#
# Usage:
#   bash scripts/solve_one.sh <question_id> <output_dir>
#
# Output:
#   <output_dir>/<question_id>.result.json      (parsed result)
#   <output_dir>/<question_id>.stdout.log       (raw runner output)
#   <output_dir>/<question_id>.attempts.log     (one line per attempt: ts, status, gt, pred-prefix)
set -euo pipefail

QID="${1:?question_id required, e.g. bix-12-q4}"
OUT_DIR="${2:?output dir required}"

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
RUNNER="$REPO_ROOT/skills/evals/run_benchmark.py"
QUESTIONS="$REPO_ROOT/skills/evals/bixbench/questions.json"

mkdir -p "$OUT_DIR"
IN="$OUT_DIR/$QID.in.json"
RESULT="$OUT_DIR/$QID.result.json"
STDOUT="$OUT_DIR/$QID.stdout.log"
ATTEMPTS="$OUT_DIR/$QID.attempts.log"

# Build single-question input
python3 -c "
import json
qs = json.load(open('$QUESTIONS'))
sel = [q for q in qs if q.get('question_id') == '$QID']
if not sel:
    raise SystemExit(f'question_id \"$QID\" not found')
json.dump(sel, open('$IN', 'w'))
"

PREV_LATEST=$(ls -t "$REPO_ROOT/skills/evals/bixbench/"results_*.json 2>/dev/null | head -1 || true)

echo "[$(date +%H:%M:%S)] solving $QID..."
python3 "$RUNNER" --benchmark bixbench --data-file "$IN" --n 1 --plugin-only \
    > "$STDOUT" 2>&1 || true

LATEST=$(ls -t "$REPO_ROOT/skills/evals/bixbench/"results_*.json 2>/dev/null | head -1 || true)
if [[ -z "$LATEST" || "$LATEST" = "$PREV_LATEST" ]]; then
    echo "  ERROR: runner produced no fresh result file"
    exit 2
fi
cp "$LATEST" "$RESULT"

# Print + log status
python3 - "$RESULT" "$ATTEMPTS" "$QID" <<'PYEOF'
import json, sys, datetime
result_path, attempts_path, qid = sys.argv[1], sys.argv[2], sys.argv[3]
r = json.load(open(result_path))
x = r.get('with_plugin', r.get('clean_plugin', []))[0]
status = 'CORRECT' if x.get('correct') else 'WRONG'
gt = str(x.get('ground_truth', ''))[:60]
pred = str(x.get('predicted', '')).strip().splitlines()
pred_first = next((line for line in pred if line.strip()), '')[:120]
ts = datetime.datetime.now().isoformat(timespec='seconds')
line = f'{ts}\t{status}\t{x.get("elapsed_seconds", "?")}s\tGT:{gt}\tPRED:{pred_first}'
with open(attempts_path, 'a') as f:
    f.write(line + '\n')
print(f'  {status} ({x.get("elapsed_seconds","?")}s) | GT: {gt}')
PYEOF
