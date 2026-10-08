import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import download_capsules
import probe_tool_call
import regrade_nearest_option as scorer
import verify_reference_values


class ReproductionTests(unittest.TestCase):
    def test_tool_probe_rejects_text_claim(self):
        self.assertFalse(
            probe_tool_call.observed_sequence(
                [{"type": "result", "result": probe_tool_call.EXPECTED}]
            )
        )

    def test_tool_probe_accepts_completed_expected_call(self):
        events = [
            {
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "1",
                            "name": "mcp__tooluniverse__execute_tool",
                            "input": {"name": "UCSC_get_sequence"},
                        }
                    ]
                }
            },
            {
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "1",
                            "content": {"dna": probe_tool_call.EXPECTED},
                        }
                    ]
                }
            },
        ]
        self.assertTrue(probe_tool_call.observed_sequence(events))

    def test_scoring_recomputes_both_directions(self):
        questions = [
            {"id": 1, "ideal": ".57", "distractors": [".65", ".9"]},
            {"id": 2, "ideal": ".57", "distractors": [".65", ".9"]},
            {"id": 3, "ideal": "term", "distractors": []},
        ]
        records = [
            {"id": 1, "correct": False, "predicted": "Answer: 0.5396"},
            {"id": 2, "correct": True, "predicted": "Answer: 0.65"},
            {"id": 3, "correct": True, "predicted": "term"},
        ]
        result = scorer.regrade(records, questions)
        self.assertEqual([r["correct"] for r in result["results"]], [True, False, True])
        self.assertEqual(result["summary"]["correct"], 2)
        self.assertEqual(result["summary"]["accuracy"], 66.7)
        self.assertEqual(result["summary"]["changed_grades"], 2)
        self.assertFalse(records[0]["correct"])

    def test_ties_and_nonfinite_answers_fail(self):
        self.assertFalse(scorer.selects_gold(0.61, 0.57, [0.65, 0.9]))
        self.assertFalse(scorer.selects_gold(float("nan"), 0.57, [0.65]))
        self.assertFalse(scorer.selects_gold(float("inf"), 0.57, [0.65]))

    def test_scientific_notation_committed_answer(self):
        self.assertEqual(scorer.committed_value("The answer is **2.5e-4**"), 0.00025)

    def test_duplicate_and_unknown_evaluated_ids_fail(self):
        q = [{"id": 1, "ideal": "word"}]
        with self.assertRaises(ValueError):
            scorer.regrade([{"id": 1, "correct": True}] * 2, q)
        with self.assertRaises(ValueError):
            scorer.regrade([{"id": 2, "correct": True}], q)

    def test_ungraded_nonnumeric_answers_do_not_silently_pass(self):
        with self.assertRaises(ValueError):
            scorer.regrade([{"id": 1}], [{"id": 1, "ideal": "word"}])

    def test_empty_result_is_not_a_full_score(self):
        with self.assertRaises(ValueError):
            scorer.regrade([], [])

    def test_capsule_zip_rejects_traversal_before_replacing_existing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "capsule"
            old.mkdir()
            (old / "kept").write_text("original")
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("../escape.txt", "bad")
            with self.assertRaises(ValueError):
                download_capsules.extract_capsule(archive, old)
            self.assertEqual((old / "kept").read_text(), "original")
            self.assertFalse((root / "escape.txt").exists())

    def test_complete_download_has_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "capsule.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("data.csv", "x\n1\n")
            dest = root / "capsule"
            download_capsules.extract_capsule(archive, dest)
            self.assertEqual((dest / "data.csv").read_text(), "x\n1\n")
            self.assertTrue((dest / ".complete").exists())

    def test_gap_fraction_counts_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "aln"
            p.write_text(">a\nA--A\n>b\nAAAA\n")
            self.assertEqual(verify_reference_values.column_gap_fraction(p), 0.5)
            p.write_text(">a\nAAA\n>b\nAAAA\n")
            with self.assertRaises(ValueError):
                verify_reference_values.column_gap_fraction(p)

    def test_final_score_cli_preserves_raw_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qs = root / "questions.json"
            raw = root / "results.json"
            out = root / "graded.json"
            qs.write_text(
                json.dumps([{"id": 1, "ideal": ".57", "distractors": [".65", ".9"]}])
            )
            raw.write_text(
                json.dumps([{"id": 1, "correct": False, "predicted": "Answer: 0.5396"}])
            )
            before = raw.read_bytes()
            res = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/regrade_nearest_option.py"),
                    "--results",
                    str(raw),
                    "--questions",
                    str(qs),
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("1/1 (100.0%)", res.stdout)
            self.assertEqual(raw.read_bytes(), before)
            self.assertEqual(json.loads(out.read_text())["summary"]["correct"], 1)

    def test_harness_accepts_explicit_capsule_and_plugin_paths(self):
        path = ROOT.parents[1] / "skills/devtu-benchmark-harness/scripts/run_eval.py"
        spec = importlib.util.spec_from_file_location("bix_harness", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "capsules"
            data.mkdir()
            plugin = root / "plugin"
            plugin.mkdir()
            (plugin / ".mcp.json").write_text("{}")
            qs = root / "questions.json"
            qs.write_text('[ {"id": 1} ]')
            argv = [
                "run_eval.py",
                "--benchmark",
                "bixbench",
                "--data-file",
                str(qs),
                "--data-dir",
                str(data),
                "--plugin-dir",
                str(plugin),
                "--n",
                "1",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(
                    mod, "run_benchmark", return_value=[{"id": 1, "correct": True}]
                ),
                patch.object(mod, "EVALS_DIR", root / "output"),
            ):
                mod.main()
            self.assertEqual(mod.BIXBENCH_DATA_DIRS, [data.resolve()])
            self.assertEqual(mod.CLEAN_DATA_DIR, data.resolve())
            self.assertEqual(mod.PLUGIN_DIR, str(plugin.resolve()))
            self.assertEqual(mod.CHECKSUMS_FILE, data.resolve() / "checksums.json")


if __name__ == "__main__":
    unittest.main()
