import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cli_runtime as runtime
import preflight
import run_ablation


class ReproductionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plugin = self.root / "plugin"
        self.plugin.mkdir()
        (self.plugin / ".mcp.json").write_text('{"mcpServers":{"tooluniverse":{}}}')
        self.baseline = self.root / "baseline.toml"
        self.with_config = self.root / "with.toml"
        self.baseline.write_text('model="gpt-5.5"\n')
        self.with_config.write_text(
            'model="gpt-5.5"\n[mcp_servers.tooluniverse]\ncommand="tooluniverse"\nargs=[]\n'
        )
        self.args = Namespace(
            claude_bin="claude",
            codex_bin="codex",
            timeout=20,
            max_turns=10,
            model="claude-opus-4-8",
            plugin_dir=str(self.plugin),
            codex_with=str(self.with_config),
            codex_without=str(self.baseline),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def completed(self, events, returncode=0):
        return subprocess.CompletedProcess(
            [], returncode, "\n".join(json.dumps(x) for x in events), ""
        )

    def test_codex_uses_overrides_and_ignores_user_mcp(self):
        events = [
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "[ANSWER]B[/ANSWER]"},
            }
        ]
        with patch.object(
            runtime.subprocess, "run", return_value=self.completed(events)
        ) as run:
            self.assertEqual(
                runtime.codex("question", False, self.args), "[ANSWER]B[/ANSWER]"
            )
        cmd = run.call_args.args[0]
        self.assertIn("--ignore-user-config", cmd)
        self.assertIn("--skip-git-repo-check", cmd)
        self.assertIn('model="gpt-5.5"', cmd)
        self.assertNotIn(str(self.baseline), cmd)
        self.assertNotEqual(run.call_args.kwargs["cwd"], str(Path.cwd()))

    def test_codex_pair_rejects_model_difference(self):
        self.baseline.write_text('model="another-model"')
        with self.assertRaises(ValueError):
            runtime.validate_codex_pair(self.with_config, self.baseline)

    def test_codex_pair_rejects_baseline_mcp_leak(self):
        self.baseline.write_text(self.with_config.read_text())
        with self.assertRaises(ValueError):
            runtime.validate_codex_pair(self.with_config, self.baseline)

    def test_claude_print_mode_and_actual_tool_trace(self):
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "t1",
                            "name": "mcp__tooluniverse__execute_tool",
                            "input": {"id": "ENSG00000141510"},
                        }
                    ]
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_result", "tool_use_id": "t1", "content": "TP53"}
                    ]
                },
            },
            {"type": "result", "result": "[ANSWER]A[/ANSWER]", "is_error": False},
        ]
        with patch.object(
            runtime.subprocess, "run", return_value=self.completed(events)
        ) as run:
            runtime.claude("question", True, self.args)
        cmd = run.call_args.args[0]
        self.assertIn("--print", cmd)
        self.assertIn("--strict-mcp-config", cmd)
        self.assertIn(str((self.plugin / ".mcp.json").resolve()), cmd)
        self.assertEqual(self.args.tool_calls[0]["result"], "TP53")
        self.assertTrue(self.args.tool_calls[0]["completed"])

    def test_claude_baseline_has_no_plugin_or_mcp(self):
        with patch.object(
            runtime.subprocess,
            "run",
            return_value=self.completed(
                [{"type": "result", "result": "refused", "is_error": False}]
            ),
        ) as run:
            self.assertEqual(runtime.claude("question", False, self.args), "refused")
        cmd = run.call_args.args[0]
        self.assertNotIn("--plugin-dir", cmd)
        self.assertIn('{"mcpServers":{}}', cmd)

    def test_failed_turn_is_not_a_wrong_benchmark_answer(self):
        with patch.object(
            runtime.subprocess,
            "run",
            return_value=self.completed([{"type": "turn.failed"}]),
        ):
            with self.assertRaises(runtime.AgentExecutionError):
                runtime.codex("question", False, self.args)

    def test_timeout_aborts_instead_of_scoring_zero(self):
        with patch.object(
            runtime.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired("codex", 20),
        ):
            with self.assertRaises(runtime.AgentExecutionError):
                runtime.codex("question", False, self.args)

    def test_preflight_rejects_claim_without_observed_call(self):
        self.args.tool_calls = []
        with (
            patch.object(sys, "argv", ["preflight.py"]),
            patch.dict(
                preflight.AGENTS,
                {"claude": lambda *x: "SYMBOL: TP53\nTOOL: fabricated"},
            ),
        ):
            self.assertEqual(preflight.main(), 1)

    def test_refused_answers_are_included_in_denominator(self):
        self.assertIsNone(run_ablation.extract_answer("I cannot answer this question"))
        reps = [
            [{"correct": True, "parsed": True}, {"correct": False, "parsed": False}],
            [{"correct": True, "parsed": True}, {"correct": True, "parsed": True}],
        ]
        summary = run_ablation.summarize(reps)
        self.assertEqual(summary["accuracy"], 0.75)
        self.assertAlmostEqual(summary["accuracy_std"], 2**-0.5 / 2)


if __name__ == "__main__":
    unittest.main()
