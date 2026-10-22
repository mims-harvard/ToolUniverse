"""Regression tests for the sign-conditioned nominal GSEA p-value."""

import numpy as np
import pytest

from tooluniverse.gsea_prerank_tool import GSEAPrerankTool

pytestmark = pytest.mark.unit

SCORES = [5, 4, 3, 2, 0, 0, -2, -3, -4, -5]
RANKED = {f"G{i}": score for i, score in enumerate(SCORES)}
# These rank pairs have ES 1, 7/8, 3/4, -1, -7/8, -3/4, and 0.
MIXED_DRAWS = [(0, 1), (0, 2), (1, 3), (8, 9), (7, 9), (6, 8), (4, 5)]


@pytest.mark.parametrize(
    "members, draws, expected_es, expected_p",
    [
        pytest.param((0, 2), MIXED_DRAWS, 7 / 8, 3 / 5, id="positive-ties-and-zero"),
        pytest.param(
            (7, 9), MIXED_DRAWS, -7 / 8, 3 / 4, id="negative-ties-exclude-zero"
        ),
        pytest.param((0, 2), [(8, 9), (6, 8)], 7 / 8, 1, id="no-positive-null"),
        pytest.param(
            (7, 9), [(0, 1), (1, 3), (4, 5)], -7 / 8, 1, id="no-negative-null"
        ),
        pytest.param(
            (0, 2), [(1, 3), (4, 5), (8, 9)], 7 / 8, 1 / 3, id="positive-pseudocount"
        ),
        pytest.param(
            (7, 9), [(6, 8), (4, 5), (0, 1)], -7 / 8, 1 / 2, id="negative-pseudocount"
        ),
        pytest.param((4, 5), MIXED_DRAWS, 0, 1, id="zero-observed-es"),
    ],
)
def test_nominal_p_uses_only_the_matching_sign_null(
    monkeypatch, members, draws, expected_es, expected_p
):
    """Keep real ES scoring; control only permutation draws at the RNG boundary."""

    class FixedDraws:
        def __init__(self):
            self.remaining = iter(draws)

        def choice(self, population, size, replace):
            assert (population, size, replace) == (10, 2, False)
            return np.asarray(next(self.remaining))

    monkeypatch.setattr(
        "tooluniverse.gsea_prerank_tool.np.random.default_rng",
        lambda seed: FixedDraws(),
    )
    out = GSEAPrerankTool().run(
        {
            "ranked_genes": RANKED,
            "gene_set": [f"G{i}" for i in members],
            "n_permutations": len(draws),
        }
    )
    assert out["status"] == "success"
    result = out["data"]["results"][0]
    assert result["es"] == pytest.approx(expected_es)
    assert result["p_value"] == pytest.approx(expected_p)


def test_seeded_p_does_not_cross_significance_threshold_with_opposite_sign_null():
    """A simulated fixture has 661 extreme draws among 9,999 nonnegative draws."""
    out = GSEAPrerankTool().run(
        {
            "genes": [f"G{i}" for i in range(1, 21)],
            "scores": np.linspace(2, -2, 20).tolist(),
            "gene_set": ["G1", "G2", "G3", "G18"],
            "n_permutations": 20_000,
        }
    )
    result = out["data"]["results"][0]
    assert result["p_value"] == pytest.approx(662 / 10_000)
    assert result["p_value"] > 0.05
