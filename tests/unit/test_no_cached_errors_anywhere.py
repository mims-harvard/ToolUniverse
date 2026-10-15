"""Follow-ups to #753/#754: the other places a failure could be cached.

1. #754 stopped *writing* error results to the result cache, but entries
   written before it are on disk with no expiry, and an upgrade does not clear
   them (the cache version comes from the tool class). Reads now treat a
   cached error as a miss.
2. SIGNOR's gene -> UniProt resolver was an lru_cache, so the "" it returns
   for a timeout or a 5xx was kept for the rest of the process.
3. The ESM SAE feature labeler skipped panel proteins it could not fetch and
   wrote whatever the rest voted to a cache file with no expiry -- with all
   ten unreachable, "uncategorized" was stored as the feature's label.
"""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool

pytestmark = pytest.mark.unit


# ---------- 1. cached errors written by older versions ----------


class OnceBrokenTool(BaseTool):
    calls = 0

    def run(self, arguments, **kwargs):
        OnceBrokenTool.calls += 1
        if OnceBrokenTool.calls == 1:
            return {"status": "error", "error": "upstream timed out"}
        return {"status": "success", "data": {"value": arguments["value"]}}


_CONFIG = {
    "name": "OnceBrokenToolTest",
    "type": "OnceBrokenTool",
    "description": "Fails on its first call",
    "parameter": {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
    },
}
_CALL = {"name": "OnceBrokenToolTest", "arguments": {"value": 3}}


def _tu_with_a_legacy_cached_error():
    """Write the error the way versions before #754 did, then restore."""
    OnceBrokenTool.calls = 0
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    tu.register_custom_tool(OnceBrokenTool, tool_config=_CONFIG)
    with patch.object(ToolUniverse, "_is_error_result", staticmethod(lambda r: False)):
        assert tu.run_one_function(dict(_CALL), use_cache=True)["status"] == "error"
    return tu


def test_a_cached_error_from_an_older_version_is_not_served(cache_env):
    tu = _tu_with_a_legacy_cached_error()

    result = tu.run_one_function(dict(_CALL), use_cache=True)

    assert result == {"status": "success", "data": {"value": 3}}
    assert OnceBrokenTool.calls == 2
    # and the good result replaced it
    assert tu.run_one_function(dict(_CALL), use_cache=True) == result
    assert OnceBrokenTool.calls == 2
    tu.close()


def test_the_async_path_does_not_serve_it_either(cache_env):
    tu = _tu_with_a_legacy_cached_error()

    result = asyncio.run(tu.run_one_function_async(dict(_CALL), use_cache=True))

    assert result == {"status": "success", "data": {"value": 3}}
    assert OnceBrokenTool.calls == 2
    tu.close()


# ---------- 2. SIGNOR's resolver ----------


def _resp(status, payload=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload or {}
    return r


@pytest.fixture
def signor():
    from tooluniverse import signor_tool

    signor_tool._RESOLVED.clear()
    yield signor_tool
    signor_tool._RESOLVED.clear()


def test_a_failed_lookup_is_retried(signor):
    hit = _resp(200, {"results": [{"primaryAccession": "P04637"}]})

    with patch.object(signor.requests, "get", side_effect=[_resp(503), hit]) as get:
        assert signor._resolve_gene_to_uniprot("TP53") == ""
        assert signor._resolve_gene_to_uniprot("TP53") == "P04637"
    assert get.call_count == 2


def test_an_exception_is_retried(signor):
    hit = _resp(200, {"results": [{"primaryAccession": "P04637"}]})

    with patch.object(
        signor.requests, "get", side_effect=[TimeoutError("slow"), hit]
    ) as get:
        assert signor._resolve_gene_to_uniprot("TP53") == ""
        assert signor._resolve_gene_to_uniprot("TP53") == "P04637"
    assert get.call_count == 2


def test_answers_are_cached_including_a_definite_no_hit(signor):
    with patch.object(
        signor.requests,
        "get",
        side_effect=[
            _resp(200, {"results": [{"primaryAccession": "P04637"}]}),
            _resp(200, {"results": []}),
        ],
    ) as get:
        for _ in range(2):
            assert signor._resolve_gene_to_uniprot("TP53") == "P04637"
            assert signor._resolve_gene_to_uniprot("NOTAGENE") == ""
    assert get.call_count == 2


# ---------- 3. ESM SAE feature labels ----------


def _esm(tmp_path):
    from tooluniverse.esm_tool import ESMTool

    tool = ESMTool.__new__(ESMTool)
    tool._cache_path_for_feature = lambda model, fid: tmp_path / f"f{fid}.json"
    return tool


def test_a_label_with_failed_proteins_is_not_written(tmp_path):
    from tooluniverse.esm_tool import ESMTool

    assert ESMTool._label_was_cached_from_failures(
        {"data": {"n_proteins_failed": 2, "category": "binding"}}
    )
    assert not ESMTool._label_was_cached_from_failures(
        {"data": {"n_proteins_failed": 0, "category": "uncategorized"}}
    )


@pytest.mark.parametrize(
    ("data", "recompute"),
    [
        ({"category": "uncategorized", "n_proteins_with_activation": 0}, True),
        ({"category": "active_site", "n_proteins_with_activation": 4}, False),
    ],
)
def test_an_old_label_that_looks_like_an_outage_is_recomputed(data, recompute):
    from tooluniverse.esm_tool import ESMTool

    assert ESMTool._label_was_cached_from_failures({"data": data}) is recompute


def _labeler(tmp_path, reachable):
    """An ESMTool whose UniProt/Forge calls succeed only for `reachable`."""
    tool = _esm(tmp_path)

    def fetch(accession):
        if accession not in reachable:
            return None
        return {
            "sequence": {"value": "MKV"},
            "features": [
                {"type": "Binding site", "location": {"start": {"value": 1}, "end": {"value": 3}}}
            ],
        }

    tool._fetch_uniprot_entry = fetch
    tool._get_sae_features = lambda args: {
        "status": "success",
        "data": {
            "activations": [
                {"residue_idx_1based": 2, "active_features": [{"feature_id": 5, "activation": 1.5}]}
            ]
        },
    }
    return tool


def test_all_proteins_unreachable_is_an_error_not_a_label(tmp_path):
    tool = _labeler(tmp_path, reachable=set())

    result = tool._describe_sae_feature({"feature_id": 5, "n_proteins": 3})

    assert result["status"] == "error"
    assert "none of the 3 panel proteins" in result["error"]
    assert not (tmp_path / "f5.json").exists()


def test_a_partial_label_is_returned_flagged_and_not_written(tmp_path):
    from tooluniverse.esm_tool import ESMTool

    panel = ESMTool._SAE_LABELING_PANEL[:3]
    tool = _labeler(tmp_path, reachable={panel[0]})

    result = tool._describe_sae_feature({"feature_id": 5, "n_proteins": 3})

    assert result["status"] == "success"
    assert result["data"]["n_proteins_analyzed"] == 1
    assert result["data"]["n_proteins_failed"] == 2
    assert result["metadata"]["partial"] is True
    assert result["metadata"]["failed_proteins"] == list(panel[1:])
    assert not (tmp_path / "f5.json").exists()


def test_a_complete_label_is_written_and_then_served(tmp_path):
    from tooluniverse.esm_tool import ESMTool

    tool = _labeler(tmp_path, reachable=set(ESMTool._SAE_LABELING_PANEL))

    first = tool._describe_sae_feature({"feature_id": 5, "n_proteins": 3})
    assert first["data"]["n_proteins_failed"] == 0
    assert (tmp_path / "f5.json").exists()

    tool._fetch_uniprot_entry = lambda a: pytest.fail("should be served from cache")
    second = tool._describe_sae_feature({"feature_id": 5, "n_proteins": 3})
    assert second["metadata"]["from_cache"] is True
    assert second["data"]["category"] == first["data"]["category"]


def test_an_old_outage_label_on_disk_is_recomputed(tmp_path):
    from tooluniverse.esm_tool import ESMTool

    (tmp_path / "f5.json").write_text(
        json.dumps(
            {
                "status": "success",
                "data": {"category": "uncategorized", "n_proteins_with_activation": 0},
            }
        )
    )
    tool = _labeler(tmp_path, reachable=set(ESMTool._SAE_LABELING_PANEL))

    result = tool._describe_sae_feature({"feature_id": 5, "n_proteins": 3})

    assert result["metadata"]["from_cache"] is False
    assert result["data"]["n_proteins_with_activation"] == 3
