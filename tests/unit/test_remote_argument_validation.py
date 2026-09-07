import importlib.util
import math
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "src" / "tooluniverse" / "remote_argument_validation.py"
SPEC = importlib.util.spec_from_file_location("remote_argument_validation_under_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RemoteArgumentValidationTests(unittest.TestCase):
    def test_argument_payload_must_be_an_object(self):
        self.assertEqual(MODULE.require_argument_object({"ok": True}), {"ok": True})
        for value in (None, [], "value", 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MODULE.require_argument_object(value)

    def test_integer_validation_is_strict_and_bounded(self):
        self.assertEqual(
            MODULE.bounded_integer(None, "epochs", default=5, minimum=1, maximum=10),
            5,
        )
        self.assertEqual(
            MODULE.bounded_integer(10, "epochs", minimum=1, maximum=10), 10
        )
        for value in (True, 1.0, "1", 0, 11):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MODULE.bounded_integer(value, "epochs", minimum=1, maximum=10)

    def test_number_validation_rejects_nonfinite_and_bool(self):
        self.assertEqual(
            MODULE.bounded_number(
                0.5,
                "fraction",
                minimum=0,
                maximum=1,
                exclusive_minimum=True,
                exclusive_maximum=True,
            ),
            0.5,
        )
        for value in (True, "0.5", 0, 1, math.nan, math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MODULE.bounded_number(
                    value,
                    "fraction",
                    minimum=0,
                    maximum=1,
                    exclusive_minimum=True,
                    exclusive_maximum=True,
                )

    def test_text_validation_bounds_and_allowlist(self):
        self.assertEqual(
            MODULE.bounded_text("cpu", "accelerator", allowed={"auto", "cpu"}),
            "cpu",
        )
        for value in ("", "x" * 5, 1, "gpu"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MODULE.bounded_text(
                    value,
                    "accelerator",
                    maximum=4,
                    allowed={"auto", "cpu"},
                )


if __name__ == "__main__":
    unittest.main()
