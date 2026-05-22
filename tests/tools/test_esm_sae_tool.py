"""Unit tests for ESMTool.get_sae_features.

These tests mock the EvolutionaryScale Forge SDK so they run without a real
API key or the unmerged ishaan/sae branch installed.

End-to-end against a real Forge call was verified separately on a 209-AA
TP53 N-terminal fragment — position 175 ±8 window returned 17 residues × 64
features = 1088 sparse activations, k=64 exact sparsity maintained.
"""

from __future__ import annotations

from unittest import mock

import pytest

from tooluniverse.esm_tool import ESMTool


def _fake_sae_tensor(seq_len: int, n_features: int = 16384, k: int = 64):
    """Build a fake torch.sparse_coo_tensor matching the real Forge output.

    Shape: (seq_len + 2, n_features) — +2 for BOS/EOS tokens.
    Sparsity: k features active per row, deterministic positions.
    """
    import torch

    rows = []
    cols = []
    vals = []
    # Use rows 1..seq_len (skip 0=BOS and seq_len+1=EOS) so the tool's filter
    # finds residues to return.
    for r in range(1, seq_len + 1):
        for j in range(k):
            rows.append(r)
            cols.append((r * 7 + j * 257) % n_features)
            vals.append(0.5 + (j % 5) * 0.1)
    indices = torch.tensor([rows, cols])
    values = torch.tensor(vals)
    return torch.sparse_coo_tensor(
        indices, values, size=(seq_len + 2, n_features)
    )


@pytest.fixture
def mock_forge():
    """Stub esm.sdk.api + esm.sdk.forge so the tool can run without the SDK."""
    seq_len = 30

    fake_sae = _fake_sae_tensor(seq_len)
    fake_output = mock.MagicMock()
    fake_output.sae_outputs = {
        "esmc-6b-2024-12_k64_codebook16384_layer60": fake_sae
    }

    fake_client = mock.MagicMock()
    fake_client.encode.return_value = "fake_protein_tensor"
    fake_client.logits.return_value = fake_output

    fake_client_cls = mock.MagicMock(return_value=fake_client)
    fake_protein_cls = mock.MagicMock()
    fake_sae_config_cls = mock.MagicMock()
    fake_logits_config_cls = mock.MagicMock()

    with mock.patch.dict(
        "sys.modules",
        {
            "esm.sdk.api": mock.MagicMock(
                ESMProtein=fake_protein_cls,
                SAEConfig=fake_sae_config_cls,
                LogitsConfig=fake_logits_config_cls,
            ),
            "esm.sdk.forge": mock.MagicMock(
                ESMCForgeInferenceClient=fake_client_cls
            ),
        },
    ), mock.patch.dict("os.environ", {"ESM_API_KEY": "fake-test-key"}):
        yield {"client_cls": fake_client_cls, "seq_len": seq_len}


def test_get_sae_features_returns_success_shape(mock_forge):
    """Happy path: sequence + position+window returns correctly shaped output."""
    sequence = "M" * mock_forge["seq_len"]
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

    result = tool.run(
        {
            "operation": "get_sae_features",
            "sequence": sequence,
            "position": 15,
            "window": 4,
            "top_k_per_residue": 8,
        }
    )

    assert result["status"] == "success"
    data = result["data"]
    assert data["sequence_length"] == mock_forge["seq_len"]
    assert data["position"] == 15
    assert data["window"] == 4
    # ±4 window around position 15 → residues 11-19 = 9 residues
    assert data["residues_returned"] == 9
    assert len(data["activations"]) == 9
    # top_k_per_residue=8 should cap each residue's features at 8
    for r in data["activations"]:
        assert len(r["active_features"]) <= 8
        assert "residue_idx_1based" in r
        for feat in r["active_features"]:
            assert isinstance(feat["feature_id"], int)
            assert 0 <= feat["feature_id"] < 16384
            assert isinstance(feat["activation"], float)


def test_get_sae_features_full_sequence_when_no_position(mock_forge):
    """Without position arg, returns all seq_len residues."""
    sequence = "M" * mock_forge["seq_len"]
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

    result = tool.run(
        {
            "operation": "get_sae_features",
            "sequence": sequence,
        }
    )

    assert result["status"] == "success"
    assert result["data"]["residues_returned"] == mock_forge["seq_len"]


def test_get_sae_features_rejects_missing_sequence():
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
    result = tool.run({"operation": "get_sae_features"})
    assert result["status"] == "error"
    assert "sequence is required" in result["error"]


def test_get_sae_features_rejects_out_of_range_position():
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
    result = tool.run(
        {
            "operation": "get_sae_features",
            "sequence": "MKTAY",  # length 5
            "position": 99,
        }
    )
    assert result["status"] == "error"
    assert "out of range" in result["error"]


def test_get_sae_features_missing_api_key_returns_error(mock_forge):
    """Without ESM_API_KEY env var, tool returns clear error (not crash)."""
    sequence = "M" * mock_forge["seq_len"]
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

    with mock.patch.dict("os.environ", {}, clear=True):
        result = tool.run(
            {"operation": "get_sae_features", "sequence": sequence}
        )

    assert result["status"] == "error"
    assert "ESM_API_KEY" in result["error"]


def test_get_sae_features_emits_license_metadata(mock_forge):
    """Output must include the Cambrian non-commercial license notice."""
    sequence = "M" * mock_forge["seq_len"]
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

    result = tool.run(
        {"operation": "get_sae_features", "sequence": sequence, "position": 15}
    )

    assert result["status"] == "success"
    assert "license" in result["metadata"]
    assert "non-commercial" in result["metadata"]["license"].lower()


def test_get_sae_features_metadata_has_codebook_size(mock_forge):
    sequence = "M" * mock_forge["seq_len"]
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

    result = tool.run(
        {"operation": "get_sae_features", "sequence": sequence, "position": 15}
    )

    assert result["metadata"]["total_features_in_codebook"] == 16384
    assert result["metadata"]["sparsity_k"] == 64


def test_unknown_operation_lists_get_sae_features_in_error():
    """Regression: dispatch error message must mention the new operations."""
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
    result = tool.run({"operation": "bogus"})
    assert result["status"] == "error"
    assert "get_sae_features" in result["error"]
    assert "score_variant_sae_disruption" in result["error"]


# ---------- score_variant_sae_disruption ----------


def test_score_variant_sae_disruption_happy_path(mock_forge):
    """Tool builds mutant, runs ref+mut, returns ranked lost/gained features."""
    seq_len = mock_forge["seq_len"]
    sequence = "M" * seq_len
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

    result = tool.run(
        {
            "operation": "score_variant_sae_disruption",
            "sequence": sequence,
            "position": 15,
            "ref_aa": "M",
            "alt_aa": "A",
            "window": 4,
            "top_k_features": 5,
        }
    )

    assert result["status"] == "success"
    data = result["data"]
    assert data["variant"] == "M15A"
    assert data["position"] == 15
    assert data["window"] == 4
    assert isinstance(data["n_unique_features_touched"], int)
    assert len(data["top_features_lost"]) <= 5
    assert len(data["top_features_gained"]) <= 5
    # Each entry has the 4 expected fields
    for entry in data["top_features_lost"] + data["top_features_gained"]:
        assert {"feature_id", "delta", "ref_activation_sum", "mut_activation_sum"} <= set(
            entry.keys()
        )


def test_score_variant_disruption_rejects_ref_aa_mismatch(mock_forge):
    """If ref_aa doesn't match sequence position, refuse — likely wrong isoform."""
    sequence = "MEEPQSDPSV"  # position 1 is M, not R
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

    result = tool.run(
        {
            "operation": "score_variant_sae_disruption",
            "sequence": sequence,
            "position": 1,
            "ref_aa": "R",  # WRONG — position 1 is actually M
            "alt_aa": "H",
        }
    )
    assert result["status"] == "error"
    assert "ref_aa mismatch" in result["error"]
    assert "'M'" in result["error"]  # tells you what's actually there


def test_score_variant_disruption_rejects_missing_args():
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
    # missing position
    r = tool.run(
        {
            "operation": "score_variant_sae_disruption",
            "sequence": "MEEPQ",
            "ref_aa": "M",
            "alt_aa": "A",
        }
    )
    assert r["status"] == "error"
    assert "position" in r["error"]
    # missing ref_aa
    r = tool.run(
        {
            "operation": "score_variant_sae_disruption",
            "sequence": "MEEPQ",
            "position": 1,
            "alt_aa": "A",
        }
    )
    assert r["status"] == "error"
    assert "ref_aa" in r["error"]


def test_score_variant_disruption_metadata_reports_call_count(mock_forge):
    """Composite tool makes exactly 2 Forge calls (1 ref + 1 mut)."""
    sequence = "M" * mock_forge["seq_len"]
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

    result = tool.run(
        {
            "operation": "score_variant_sae_disruption",
            "sequence": sequence,
            "position": 10,
            "ref_aa": "M",
            "alt_aa": "A",
        }
    )
    assert result["status"] == "success"
    assert result["metadata"]["forge_calls_made"] == 2
    assert "non-commercial" in result["metadata"]["license"].lower()
    # client_cls should have been instantiated (at least once)
    assert mock_forge["client_cls"].call_count >= 1
