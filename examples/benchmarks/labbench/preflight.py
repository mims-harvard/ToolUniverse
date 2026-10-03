"""Verify the with-ToolUniverse condition really has ToolUniverse before you spend a run.

The failure this catches is silent. If the MCP server does not finish starting, or the
plugin directory is stale, or an editable install resolves the package to a different
working copy, the agent still runs and still answers every question. The result looks
like a complete, plausible with-ToolUniverse measurement, and it is not one.

The check is a live tool call whose correct answer is known, not a question about
capabilities. Asking an agent whether it can call a tool is unreliable in both
directions: it answers from priors in a second or two and is confident either way.
Calling the tool either produces the expected value or it does not.

Usage:
    python preflight.py --agent claude --plugin-dir /path/to/tooluniverse-plugin
    python preflight.py --agent codex --codex-with codex_config/with_tooluniverse.toml
"""

import argparse
import sys

from run_ablation import AGENTS

# A question that cannot be answered from memory alone with this precision, and whose
# answer is stable: the tool call must actually happen.
PROBE = (
    "Use your ToolUniverse tools to look up the official HGNC gene symbol for the "
    "Ensembl gene identifier ENSG00000141510. Do not answer from memory and do not "
    "read any local file: make the tool call. Reply with exactly two lines:\n"
    "SYMBOL: <symbol>\n"
    "TOOL: <name of the tool you called>"
)
EXPECTED_SYMBOL = "TP53"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=sorted(AGENTS), default="claude")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--claude-bin", default="claude")
    ap.add_argument("--model", default="claude-opus-4-8")
    ap.add_argument("--max-turns", type=int, default=20)
    ap.add_argument("--plugin-dir", default=None)
    ap.add_argument("--codex-bin", default="codex")
    ap.add_argument("--codex-with", default=None)
    ap.add_argument("--codex-without", default=None)
    args = ap.parse_args()

    print(f"Probing the with-ToolUniverse condition using {args.agent} ...")
    response = AGENTS[args.agent](PROBE, True, args)
    text = (response or "").upper()

    ok_symbol = EXPECTED_SYMBOL in text
    named_tool = "TOOL:" in text and len(text.split("TOOL:")[-1].strip()) > 2

    print("-" * 60)
    print((response or "")[-600:])
    print("-" * 60)
    print(f"expected symbol {EXPECTED_SYMBOL} present : {'yes' if ok_symbol else 'NO'}")
    print(f"named the tool it called            : {'yes' if named_tool else 'NO'}")

    if not ok_symbol:
        print("\nFAIL: the with-condition did not return the expected value. Do not start a "
              "run until this passes. Check that the plugin directory or MCP config points "
              "at the build you intend to measure, and that the MCP start-up timeout is "
              "long enough for the tool catalogue to load.")
        return 1
    if not named_tool:
        print("\nWARNING: the value is right but no tool was named, so it may have been "
              "answered from memory. Re-run before trusting the with-condition.")
        return 1
    print("\nPASS: ToolUniverse is attached and answering.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
