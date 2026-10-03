#!/usr/bin/env bash
# Run BixBench against ToolUniverse end to end.
#
#   bash scripts/run_benchmark.sh --data-dir /path/with/25GB --out results.json
#
# Options:
#   --data-dir DIR   where capsules are downloaded and extracted (required)
#   --out FILE       results file (default: results.json)
#   --n N            number of questions (default: 205, the full set)
#   --skip-download  reuse capsules already present in --data-dir
#   --skip-preflight run without checking the setup (not recommended)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"

DATA_DIR=""; OUT="results.json"; N=205; SKIP_DL=0; SKIP_PRE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --data-dir) DATA_DIR="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --n) N="$2"; shift 2 ;;
    --skip-download) SKIP_DL=1; shift ;;
    --skip-preflight) SKIP_PRE=1; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[ -n "$DATA_DIR" ] || { echo "--data-dir is required" >&2; exit 2; }
mkdir -p "$DATA_DIR"

step() { printf '\n=== %s ===\n' "$1"; }

if [ "$SKIP_PRE" -eq 0 ]; then
  step "1/5 checking the setup"
  bash "$HERE/preflight.sh" || {
    echo "Preflight failed. Fix the reported check, or pass --skip-preflight to run anyway." >&2
    exit 1
  }
fi

step "2/5 questions"
if [ -f "$HERE/../questions.json" ]; then
  echo "using existing questions.json"
else
  python3 "$HERE/build_questions.py" --out "$HERE/../questions.json"
fi

if [ "$SKIP_DL" -eq 0 ]; then
  step "3/5 capsules (~19 GB, slow on first run)"
  python3 "$HERE/download_capsules.py" --data-dir "$DATA_DIR"
else
  echo "skipping download"
fi

step "4/5 reference values"
CAPSULE="$(find "$DATA_DIR" -maxdepth 2 -type d -name 'CapsuleFolder-964b67db*' | head -1)"
if [ -n "$CAPSULE" ]; then
  python3 "$HERE/verify_reference_values.py" --capsule "$CAPSULE" || {
    echo "Reference values differ from expected; phylogenetics questions will not reproduce." >&2
    exit 1
  }
else
  echo "capsule 964b67db not found under $DATA_DIR - skipping reference check" >&2
fi

step "5/5 running $N questions (6-10 h for the full set)"
python3 "$ROOT/skills/devtu-benchmark-harness/scripts/run_eval.py" \
    --benchmark bixbench --mode plugin-only --n "$N" \
    --data-file "$HERE/../questions.json" \
    --timeout 900 --max-turns 80 --full-skill-injection \
    --save-incremental "$OUT"

step "scoring"
python3 "$HERE/regrade_nearest_option.py" --results "$OUT" --questions "$HERE/../questions.json"
