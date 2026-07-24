#!/usr/bin/env bash
# Run a sample of benchmark questions one at a time, each in a fresh Claude
# subprocess. This avoids the multi-question cascade failure we observed where
# one timeout causes subsequent questions to return empty ERRORs. Each
# question's result is saved as its own JSON so progress is visible.
#
# Usage:
#     bash skills/devtu-benchmark-harness/scripts/run_one_by_one.sh SAMPLE.json OUTPUT_DIR
set -euo pipefail

SAMPLE="${1:?sample JSON path required}"
OUT_DIR="${2:?output directory required}"
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
RUNNER="$REPO_ROOT/skills/evals/run_benchmark.py"

mkdir -p "$OUT_DIR"
N=$(python3 -c "import json; print(len(json.load(open('$SAMPLE'))))")
echo "Running $N questions one at a time → $OUT_DIR"

for i in $(seq 0 $((N - 1))); do
    QID=$(python3 -c "
import json
s = json.load(open('$SAMPLE'))
print(s[$i]['question_id'])
")
    OUT="$OUT_DIR/q${i}_${QID}"
    if [[ -s "$OUT.result.json" ]]; then
        echo "[$((i + 1))/$N] $QID — already done, skipping"
        continue
    fi
    # Write single-question JSON
    python3 -c "
import json
s = json.load(open('$SAMPLE'))
json.dump([s[$i]], open('$OUT.in.json', 'w'))
"
    echo "[$((i + 1))/$N] $QID — running..."
    # Snapshot the latest results file BEFORE running so we can tell if a
    # fresh one was produced. Portable across macOS BSD find / GNU find
    # (which differ on `-newermt "@timestamp"` — BSD silently returns empty).
    PREV_LATEST=$(ls -t "$REPO_ROOT/skills/evals/bixbench/"results_*.json 2>/dev/null | head -1 || true)
    START=$(date +%s)
    python3 "$RUNNER" --benchmark bixbench --data-file "$OUT.in.json" --n 1 --plugin-only \
        > "$OUT.stdout.log" 2>&1 || true
    LATEST=$(ls -t "$REPO_ROOT/skills/evals/bixbench/"results_*.json 2>/dev/null | head -1 || true)
    if [[ -z "$LATEST" || "$LATEST" = "$PREV_LATEST" ]]; then
        echo "  (runner produced no new result file — skipping)"
        continue
    fi
    cp "$LATEST" "$OUT.result.json"
    ELAPSED=$(($(date +%s) - START))
    # Quick status print
    python3 -c "
import json
r = json.load(open('$OUT.result.json'))
for x in r.get('with_plugin', r.get('clean_plugin', [])):
    status = 'CORRECT' if x.get('correct') else 'WRONG'
    gt = str(x.get('ground_truth', ''))[:40]
    print(f'  {status} (${ELAPSED}s) | GT: {gt}')
"
done

# Merge all into one results file
python3 << EOF
import json, glob, os
merged = []
for p in sorted(glob.glob('$OUT_DIR/q*_*.result.json')):
    with open(p) as f:
        r = json.load(f)
    for x in r.get('with_plugin', r.get('clean_plugin', [])):
        merged.append(x)
out = '$OUT_DIR/all_results.json'
with open(out, 'w') as f:
    json.dump({'with_plugin': merged}, f, indent=2)
correct = sum(1 for x in merged if x.get('correct'))
print(f'\nMerged: {correct}/{len(merged)} = {100*correct/len(merged):.1f}%')
print(f'Saved: {out}')
EOF
