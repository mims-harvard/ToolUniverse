from unittest.mock import Mock, patch

from tooluniverse.tark_tool import TarkTranscriptTool


def test_versioned_query_returns_only_exact_version_and_complete_record():
    records = [
        {
            "stable_id": "ENST00000380152",
            "stable_id_version": v,
            "assembly": "GRCh38",
            "sequence": f"SEQ{v}",
            "transcript_checksum": f"tx{v}",
            "exon_set_checksum": f"ex{v}",
            "loc_checksum": f"loc{v}",
            "five_prime_utr_seq": f"five{v}",
            "three_prime_utr_seq": f"three{v}",
            "transcript_release_set": [],
            "future": v,
        }
        for v in (7, 8)
    ]
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"count": 2, "results": records}
    tool = TarkTranscriptTool({"name": "tark", "fields": {"timeout": 30}})
    with patch("tooluniverse.tark_tool.requests.get", return_value=response) as get:
        result = tool.run({"stable_id": "enst00000380152.8"})
    assert result["status"] == "success"
    assert len(result["data"]) == 1
    record = result["data"][0]
    assert record["stable_id"] == "ENST00000380152.8"
    assert record["sequence"] == "SEQ8"
    assert record["five_prime_utr"]["seq"] == "five8"
    assert record["record"] == records[1]
    assert result["metadata"]["requested_version"] == 8
    assert get.call_args.kwargs["params"]["stable_id"] == "ENST00000380152"


def test_mismatched_returned_identity_is_error():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"results": [{"stable_id": "ENST00000000001"}]}
    tool = TarkTranscriptTool({"name": "tark", "fields": {"timeout": 30}})
    with patch("tooluniverse.tark_tool.requests.get", return_value=response):
        result = tool.run({"stable_id": "ENST00000380152"})
    assert result["status"] == "error"


def test_invalid_id_or_unknown_parameter_never_hits_network():
    tool = TarkTranscriptTool({"name": "tark", "fields": {"timeout": 30}})
    with patch("tooluniverse.tark_tool.requests.get") as get:
        assert tool.run({"stable_id": "ENSG1"})["status"] == "error"
        assert (
            tool.run({"stable_id": "ENST00000380152", "version": 8})["status"]
            == "error"
        )
    get.assert_not_called()
