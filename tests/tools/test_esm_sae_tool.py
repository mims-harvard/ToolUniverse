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


def test_get_sae_features_rejects_overlong_sequence():
    """Forge SAE handles up to ~2700 AA. Longer should be caught with a
    clear error, not allowed to fail at the server."""
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
    too_long = "M" * 3000
    result = tool.run(
        {"operation": "get_sae_features", "sequence": too_long}
    )
    assert result["status"] == "error"
    assert "exceeds practical Forge SAE limit" in result["error"]
    assert "2700" in result["error"]


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


# ---------- describe_sae_feature ----------


def test_describe_sae_feature_rejects_bad_feature_id():
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
    # Out-of-range
    r = tool.run({"operation": "describe_sae_feature", "feature_id": -1})
    assert r["status"] == "error" and "out of range" in r["error"]
    r = tool.run({"operation": "describe_sae_feature", "feature_id": 16384})
    assert r["status"] == "error" and "out of range" in r["error"]
    # Wrong type
    r = tool.run({"operation": "describe_sae_feature", "feature_id": "abc"})
    assert r["status"] == "error" and "feature_id" in r["error"]
    # Missing
    r = tool.run({"operation": "describe_sae_feature"})
    assert r["status"] == "error" and "feature_id" in r["error"]


def test_describe_sae_feature_rejects_bad_n_proteins():
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
    r = tool.run(
        {"operation": "describe_sae_feature", "feature_id": 100, "n_proteins": 0}
    )
    assert r["status"] == "error" and "n_proteins" in r["error"]
    r = tool.run(
        {"operation": "describe_sae_feature", "feature_id": 100, "n_proteins": 50}
    )
    assert r["status"] == "error" and "n_proteins" in r["error"]


def test_describe_sae_feature_returns_uncategorized_when_no_overlap(
    mock_forge, tmp_path, monkeypatch
):
    """If SAE never activates on UniProt-annotated positions, label is
    'uncategorized'. Tests the no-evidence path."""
    # Point cache at tmp_path so we don't pollute the user's real cache
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Mock the UniProt fetch to return a protein with NO informative features
    bare_entry = {
        "sequence": {"value": "M" * mock_forge["seq_len"]},
        "features": [],  # no annotations
    }
    with mock.patch.object(
        ESMTool, "_fetch_uniprot_entry", return_value=bare_entry
    ):
        tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
        # Pick a feature_id we know our mock_forge tensor doesn't activate on
        # (fake tensor uses (r*7 + j*257) % 16384, so feature 0 is rarely hit)
        result = tool.run(
            {
                "operation": "describe_sae_feature",
                "feature_id": 12345,  # unlikely to be in our fake activations
                "n_proteins": 2,
                "use_cache": False,
            }
        )
    assert result["status"] == "success"
    data = result["data"]
    # No informative features → uncategorized
    assert data["category"] in ("uncategorized",)
    assert data["confidence"] == 0.0


def test_describe_sae_feature_caches_result(mock_forge, tmp_path, monkeypatch):
    """Second call with same feature_id reads from cache (no Forge call)."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    bare_entry = {
        "sequence": {"value": "M" * mock_forge["seq_len"]},
        "features": [],
    }

    fetch_counter = {"count": 0}

    def counting_fetch(self, accession):
        fetch_counter["count"] += 1
        return bare_entry

    with mock.patch.object(ESMTool, "_fetch_uniprot_entry", counting_fetch):
        tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

        # First call — should fetch UniProt for each panel protein
        r1 = tool.run(
            {
                "operation": "describe_sae_feature",
                "feature_id": 999,
                "n_proteins": 3,
            }
        )
        first_fetches = fetch_counter["count"]
        assert r1["status"] == "success"
        assert r1["metadata"]["from_cache"] is False
        assert first_fetches >= 3  # one per panel protein

        # Second call — should hit cache, no new fetches
        r2 = tool.run(
            {
                "operation": "describe_sae_feature",
                "feature_id": 999,
                "n_proteins": 3,
            }
        )
        assert r2["status"] == "success"
        assert r2["metadata"]["from_cache"] is True
        # No additional UniProt fetches
        assert fetch_counter["count"] == first_fetches


def test_describe_sae_feature_aggregates_categories(
    mock_forge, tmp_path, monkeypatch
):
    """Verify the voting logic: if N proteins each have a Modified residue at
    the activating position, category should be 'ptm'."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Build a fake protein entry whose annotation IS a Modified residue at
    # every position in [1, seq_len]
    seq_len = mock_forge["seq_len"]
    fake_entry = {
        "sequence": {"value": "M" * seq_len},
        "features": [
            {
                "type": "Modified residue",
                "location": {
                    "start": {"value": p},
                    "end": {"value": p},
                },
                "description": "Test PTM",
            }
            for p in range(1, seq_len + 1)
        ],
    }
    with mock.patch.object(
        ESMTool, "_fetch_uniprot_entry", return_value=fake_entry
    ):
        tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
        # Use a feature_id we know IS in mock_forge's fake tensor
        # mock_forge uses (r*7+j*257)%16384 — for r=1, j=0 gives col=7
        result = tool.run(
            {
                "operation": "describe_sae_feature",
                "feature_id": 7,
                "n_proteins": 3,
                "use_cache": False,
            }
        )
    assert result["status"] == "success"
    # Every activation overlaps a Modified residue, so category should be ptm
    assert result["data"]["category"] == "ptm"
    assert result["data"]["confidence"] == 1.0
    assert result["data"]["n_proteins_with_activation"] >= 1


# ---------------------------------------------------------------------- #
# Tests for the 3 new composite tools added in this PR:
#   score_variant_sae_batch / get_region_sae_features / explain_variant_mechanism
# ---------------------------------------------------------------------- #


def test_score_variant_sae_batch_runs_n_plus_one_forge_calls(mock_forge):
    """Batch scoring 3 variants should make 1 ref + 3 mut = 4 Forge calls,
    not 6 (2 per variant). This is the whole point of the batch tool."""
    seq_len = mock_forge["seq_len"]
    sequence = "M" * seq_len
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

    result = tool.run(
        {
            "operation": "score_variant_sae_batch",
            "sequence": sequence,
            "variants": [
                {"position": 5, "ref_aa": "M", "alt_aa": "A"},
                {"position": 10, "ref_aa": "M", "alt_aa": "V"},
                {"position": 15, "ref_aa": "M", "alt_aa": "L"},
            ],
            "window": 4,
            "top_k_features": 5,
        }
    )

    assert result["status"] == "success"
    data = result["data"]
    assert data["n_variants"] == 3
    assert data["n_succeeded"] == 3
    assert len(data["results"]) == 3
    # 1 ref + 3 mut = 4 calls; savings = 2 vs per-variant disruption
    assert result["metadata"]["forge_calls_made"] == 4
    assert result["metadata"]["forge_calls_saved_vs_per_variant"] == 2

    for v_result in data["results"]:
        assert v_result["status"] == "success"
        assert "variant" in v_result
        assert "top_features_lost" in v_result
        assert "top_features_gained" in v_result
        assert len(v_result["top_features_lost"]) <= 5
        for feat in v_result["top_features_lost"]:
            assert "feature_id" in feat
            assert "delta" in feat
            assert "ref_activation_sum" in feat
            assert "mut_activation_sum" in feat


def test_score_variant_sae_batch_rejects_oversize_list():
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
    result = tool.run(
        {
            "operation": "score_variant_sae_batch",
            "sequence": "MTEY",
            "variants": [
                {"position": 1, "ref_aa": "M", "alt_aa": "A"}
            ]
            * 101,
        }
    )
    assert result["status"] == "error"
    assert "too many" in result["error"]


def test_score_variant_sae_batch_rejects_ref_mismatch():
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
    result = tool.run(
        {
            "operation": "score_variant_sae_batch",
            "sequence": "MTEY",
            "variants": [{"position": 2, "ref_aa": "A", "alt_aa": "V"}],
        }
    )
    assert result["status"] == "error"
    assert "ref_aa" in result["error"]


def test_score_variant_sae_batch_rejects_missing_keys():
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
    result = tool.run(
        {
            "operation": "score_variant_sae_batch",
            "sequence": "MTEY",
            "variants": [{"position": 1, "ref_aa": "M"}],
        }
    )
    assert result["status"] == "error"
    assert "alt_aa" in result["error"]


def test_get_region_sae_features_aggregates_over_range(mock_forge):
    """Region tool should return top features ranked by total |activation|
    over the region, with hit-residue counts."""
    seq_len = mock_forge["seq_len"]
    sequence = "M" * seq_len
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

    result = tool.run(
        {
            "operation": "get_region_sae_features",
            "sequence": sequence,
            "start_position": 10,
            "end_position": 20,
            "top_k_features": 10,
        }
    )

    assert result["status"] == "success"
    data = result["data"]
    assert data["region"] == [10, 20]
    assert data["region_length"] == 11
    assert len(data["top_features"]) <= 10
    assert result["metadata"]["forge_calls_made"] == 1
    # Each top feature should have the required fields
    for feat in data["top_features"]:
        assert "feature_id" in feat
        assert "total_abs_activation" in feat
        assert "mean_activation" in feat
        assert "n_residues_active" in feat
        assert "fraction_residues_active" in feat
        assert "active_positions" in feat
        for pos in feat["active_positions"]:
            assert 10 <= pos <= 20
    # Ranking: total_abs_activation should be non-increasing
    abs_vals = [f["total_abs_activation"] for f in data["top_features"]]
    assert abs_vals == sorted(abs_vals, reverse=True)


def test_get_region_sae_features_rejects_bad_range():
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
    result = tool.run(
        {
            "operation": "get_region_sae_features",
            "sequence": "MTEY",
            "start_position": 3,
            "end_position": 10,  # past seq_len 4
        }
    )
    assert result["status"] == "error"
    assert "out of range" in result["error"]


def test_get_region_sae_features_rejects_oversize_region():
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})
    result = tool.run(
        {
            "operation": "get_region_sae_features",
            "sequence": "M" * 1000,
            "start_position": 1,
            "end_position": 600,
        }
    )
    assert result["status"] == "error"
    assert "exceeds" in result["error"]


def test_explain_variant_mechanism_without_descriptions_only_2_forge_calls(
    mock_forge,
):
    """include_descriptions=False should run only the 2-call disruption
    pipeline, no describe_sae_feature follow-up."""
    seq_len = mock_forge["seq_len"]
    sequence = "M" * seq_len
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

    result = tool.run(
        {
            "operation": "explain_variant_mechanism",
            "sequence": sequence,
            "position": 15,
            "ref_aa": "M",
            "alt_aa": "A",
            "window": 4,
            "top_k_features": 3,
            "include_descriptions": False,
        }
    )

    assert result["status"] == "success"
    data = result["data"]
    assert data["variant"] == "M15A"
    assert "mechanism_summary" in data
    assert "Descriptions skipped" in data["mechanism_summary"]
    assert result["metadata"]["disruption_forge_calls"] == 2
    assert result["metadata"]["describe_feature_calls"] == 0
    assert result["metadata"]["describe_forge_credits_used"] == 0


def test_explain_variant_mechanism_with_descriptions_categorizes(
    mock_forge, tmp_path, monkeypatch
):
    """include_descriptions=True: stub describe so it returns category
    labels and verify the summary string mentions them."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    seq_len = mock_forge["seq_len"]
    sequence = "M" * seq_len
    tool = ESMTool({"name": "test", "type": "ESMTool", "parameter": {}})

    # Stub describe_sae_feature to return alternating ptm / catalytic
    call_counter = {"i": 0}

    def fake_describe(self, args):
        call_counter["i"] += 1
        cat = "ptm" if call_counter["i"] % 2 == 0 else "catalytic"
        return {
            "status": "success",
            "data": {
                "feature_id": args["feature_id"],
                "category": cat,
                "confidence": 0.8,
            },
            "metadata": {"from_cache": True},
        }

    with mock.patch.object(ESMTool, "_describe_sae_feature", fake_describe):
        result = tool.run(
            {
                "operation": "explain_variant_mechanism",
                "sequence": sequence,
                "position": 15,
                "ref_aa": "M",
                "alt_aa": "A",
                "window": 4,
                "top_k_features": 3,
                "include_descriptions": True,
            }
        )

    assert result["status"] == "success"
    data = result["data"]
    # Summary should contain at least one of the stubbed categories
    summary = data["mechanism_summary"]
    assert ("catalytic" in summary) or ("ptm" in summary)
    # Every described feature should have category + confidence
    for feat in data["top_features_lost"]:
        assert "category" in feat
        assert "confidence" in feat
    # describe was called — credit count is 0 because we stubbed from_cache=True
    assert result["metadata"]["describe_feature_calls"] > 0
