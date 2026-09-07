import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "src" / "tooluniverse" / "remote_sequence_input.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "remote_sequence_input_under_test", MODULE_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RemoteSequenceInputTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_module()

    def test_sequence_is_trimmed_and_normalized(self):
        self.assertEqual(
            self.module.validate_sequence(
                " acgtn ", name="sequence", alphabet="ACGTN", max_length=10
            ),
            "ACGTN",
        )

    def test_sequence_rejects_empty_wrong_type_and_unsupported_characters(self):
        for value in ("", "ACGT*", 7):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.module.validate_sequence(
                        value,
                        name="sequence",
                        alphabet="ACGTN",
                        max_length=10,
                    )

    def test_sequence_rejects_oversized_payload(self):
        with self.assertRaises(ValueError):
            self.module.validate_sequence(
                "A" * 11, name="sequence", alphabet="ACGTN", max_length=10
            )

    def test_variant_sequences_must_have_equal_length(self):
        with self.assertRaises(ValueError):
            self.module.validate_variant_sequences(
                "ACGT", "ACG", alphabet="ACGTN", max_length=10
            )

    def test_default_top_n_is_bounded(self):
        indices, top_n = self.module.validate_track_selection(
            None, None, n_tracks=100
        )
        self.assertIsNone(indices)
        self.assertEqual(top_n, 20)
        for value in (True, 0, 101, "10"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.module.validate_track_selection(
                        None, value, n_tracks=100
                    )

    def test_explicit_track_indices_are_strict_and_unique(self):
        indices, top_n = self.module.validate_track_selection(
            [0, 99], 5, n_tracks=100
        )
        self.assertEqual(indices, [0, 99])
        self.assertEqual(top_n, 5)
        for value in ([], [True], [-1], [100], [1, 1], ["1"]):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.module.validate_track_selection(
                        value, 5, n_tracks=100
                    )

    def test_explicit_track_output_count_is_bounded(self):
        with self.assertRaises(ValueError):
            self.module.validate_track_selection(
                list(range(11)), 5, n_tracks=100, max_items=10
            )


if __name__ == "__main__":
    unittest.main()
