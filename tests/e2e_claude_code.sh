#!/usr/bin/env bash
# E2E tests for ToolUniverse MCP integration
set -euo pipefail

PASS=0; FAIL=0; TOTAL=0

assert() {
  TOTAL=$((TOTAL + 1))
  if eval "$2" 2>/dev/null; then
    echo "✓ $1"; PASS=$((PASS + 1))
  else
    echo "✗ $1"; FAIL=$((FAIL + 1))
  fi
}

# --- Infrastructure ---
assert "uv installed" "command -v uv >/dev/null"
assert "uvx installed" "command -v uvx >/dev/null"
assert "NCBI_API_KEY set" '[ -n "${NCBI_API_KEY:-}" ]'
assert "FDA_API_KEY set" '[ -n "${FDA_API_KEY:-}" ]'
assert "wrapper script exists" "[ -x $HOME/.claude/scripts/tooluniverse-mcp.sh ]"

# --- MCP Config ---
assert "MCP config exists" "[ -f $HOME/.config/claude/mcp_servers.json ]"
assert "tooluniverse in MCP config" "grep -q tooluniverse $HOME/.config/claude/mcp_servers.json"
assert "hooks config exists" "[ -f $HOME/.claude/tooluniverse-hooks.json ]"
assert "hooks JSON valid" "python3 -c 'import json; json.load(open(\"$HOME/.claude/tooluniverse-hooks.json\"))'"

# --- Skills ---
assert "setup-tooluniverse skill installed" "[ -d $HOME/.claude/skills/setup-tooluniverse ]"
assert "30+ skills present" '[ $(ls -d $HOME/.claude/skills/tooluniverse-* 2>/dev/null | wc -l) -ge 30 ]'

# --- Rules ---
assert "tooluniverse rules exist" "[ -f $HOME/.claude/rules/tooluniverse.md ]"
assert "query reference exists" "[ -f $HOME/.claude/rules/tooluniverse-query-reference.md ]"

# --- Router Skill ---
assert "tooluniverse command exists" "[ -f $HOME/.claude/commands/tooluniverse.md ]"

# --- Live Tool Calls: Core ---
assert "tu grep works" \
  "uvx --from tooluniverse tu grep PubMed --raw 2>/dev/null | grep -q PubMed"
assert "tu info works" \
  "uvx --from tooluniverse tu info PubMed_search_articles 2>/dev/null | grep -qi query"

# --- Live Tool Calls: Literature Search ---
assert "PubMed search" \
  'uvx --from tooluniverse tu run PubMed_search_articles '\''{"query": "CRISPR", "max_results": 1}'\'' 2>/dev/null | grep -qi crispr'
assert "ArXiv search" \
  'uvx --from tooluniverse tu run ArXiv_search_papers '\''{"query": "machine learning", "limit": 1, "sort_by": "relevance"}'\'' 2>/dev/null | grep -qi title'
assert "OpenAlex (search_keywords not query)" \
  'uvx --from tooluniverse tu run openalex_literature_search '\''{"search_keywords": "CRISPR", "max_results": 1}'\'' 2>/dev/null | grep -qi title'

# --- Live Tool Calls: Protein/Drug/Safety ---
assert "UniProt query" \
  'out=$(uvx --from tooluniverse tu run UniProt_get_entry_by_accession '\''{"accession": "P12345"}'\'' 2>/dev/null) && echo "$out" | grep -q primaryAccession'
assert "FAERS drug safety" \
  'uvx --from tooluniverse tu run FAERS_count_reactions_by_drug_event '\''{"medicinalproduct": "metformin"}'\'' 2>/dev/null | grep -q result'

# --- Live Tool Calls: Clinical ---
assert "ClinicalTrials search" \
  'uvx --from tooluniverse tu run ClinicalTrials_search_studies '\''{"query": "diabetes", "max_results": 1}'\'' 2>/dev/null | grep -qi diabet'

# --- Live Tool Calls: Chemistry ---
assert "PubChem compound" \
  'uvx --from tooluniverse tu run PubChem_get_CID_by_compound_name '\''{"name": "aspirin"}'\'' 2>/dev/null | grep -q CID'

# --- Claude Desktop Config ---
CLAUDE_DESKTOP="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
assert "Claude Desktop config exists" '[ -f "$CLAUDE_DESKTOP" ]'
assert "tooluniverse in Claude Desktop" 'grep -q tooluniverse "$CLAUDE_DESKTOP" 2>/dev/null'

# --- Summary ---
echo ""
echo "═══════════════════════════════════════"
echo "Results: $PASS/$TOTAL passed, $FAIL failed"
echo "═══════════════════════════════════════"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
