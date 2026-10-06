"""Offline regressions for prediction outputs exposed through TU and its CLI."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from requests import Response
from jsonschema import validate

from tooluniverse import ToolUniverse
from tooluniverse import cli
from tooluniverse.nvidia_nim_tool import NvidiaNIMTool


pytestmark = pytest.mark.unit


FASTA = ">sample_1\nACDE\n>sample_2\nGHIK\n"
PDB = "ATOM      1  CA  ALA A   1       0.000   0.000   0.000\nEND\n"
CONFIGS = {
    item["name"]: item
    for item in json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "src/tooluniverse/data/nvidia_nim_tools.json"
        ).read_text()
    )
}


@pytest.fixture(autouse=True)
def offline_key_and_no_rate_limit(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "offline-test-key")
    monkeypatch.setattr(
        "tooluniverse.nvidia_nim_tool._enforce_rate_limit", lambda: None
    )


def response(body, content_type="application/json"):
    result = Response()
    result.status_code = 200
    result.headers["Content-Type"] = content_type
    result._content = body.encode("utf-8")
    return result


@pytest.mark.parametrize("content_type", ["text/plain", "text/plain; charset=utf-8"])
def test_proteinmpnn_plain_fasta_keeps_all_sequences(content_type):
    """Text FASTA remains sequence output, with every generated sequence."""
    tool = NvidiaNIMTool(CONFIGS["NvidiaNIM_proteinmpnn"])
    result = tool._parse_response(response(FASTA, content_type))
    assert result == {
        "status": "success",
        "data": {"mfasta": FASTA},
        "sequences": FASTA,
        "format": "mfasta",
    }
    validate(result["data"], CONFIGS["NvidiaNIM_proteinmpnn"]["return_schema"])


def test_proteinmpnn_json_keeps_sequences_and_scores():
    """JSON sequence output retains the entire native envelope and scores."""
    payload = {"mfasta": FASTA, "scores": [0.4, 0.6]}
    result = NvidiaNIMTool(CONFIGS["NvidiaNIM_proteinmpnn"])._parse_response(
        response(json.dumps(payload))
    )
    assert result == {"status": "success", "data": payload, "format": "mfasta"}


@pytest.mark.parametrize("name", ["NvidiaNIM_proteinmpnn", "NvidiaNIM_esmfold"])
@pytest.mark.parametrize("status", ["failed", "error", "errored"])
def test_prediction_inner_failure_is_an_error(name, status):
    """An inner failure cannot be counted as a successful prediction."""
    payload = {"status": status, "detail": "No predicted output"}
    result = NvidiaNIMTool(CONFIGS[name])._parse_response(response(json.dumps(payload)))
    assert result["status"] == "error"
    assert result["data"] == payload
    assert result["detail"] == payload["detail"]
    assert "structure" not in result
    assert "sequences" not in result


@pytest.mark.parametrize(
    "payload",
    [
        {"pdbs": []},
        {"pdb": ""},
        {"pdbs": [None]},
        {"pdbs": [PDB, ""]},
        {"message": "queued"},
        [PDB],
    ],
)
def test_missing_or_invalid_pdb_envelope_is_not_a_structure(payload):
    """JSON without usable coordinates cannot be emitted as PDB text."""
    result = NvidiaNIMTool(CONFIGS["NvidiaNIM_esmfold"])._parse_response(
        response(json.dumps(payload))
    )
    assert result["status"] == "error"
    assert "structure" not in result


@pytest.mark.parametrize("payload", [{"pdb": PDB}, {"pdbs": [PDB]}])
def test_pdb_json_envelope_preserves_single_structure(payload):
    """Both supported JSON envelope spellings return the original PDB."""
    result = NvidiaNIMTool(CONFIGS["NvidiaNIM_esmfold"])._parse_response(
        response(json.dumps(payload))
    )
    assert result["structure"] == PDB
    assert result["format"] == "pdb"
    validate(result["data"], CONFIGS["NvidiaNIM_esmfold"]["return_schema"])


def test_plain_pdb_remains_supported():
    """Plain PDB coordinates remain compatible and satisfy the tool schema."""
    result = NvidiaNIMTool(CONFIGS["NvidiaNIM_esmfold"])._parse_response(
        response(PDB, "text/plain")
    )
    assert result == {
        "status": "success",
        "data": PDB,
        "structure": PDB,
        "format": "pdb",
    }
    validate(result["data"], CONFIGS["NvidiaNIM_esmfold"]["return_schema"])


@pytest.mark.parametrize("name", ["NvidiaNIM_proteinmpnn", "NvidiaNIM_esmfold"])
def test_malformed_json_is_not_prediction_output(name):
    """Corrupted JSON cannot be emitted as sequence or structure text."""
    result = NvidiaNIMTool(CONFIGS[name])._parse_response(response('{"broken":'))
    assert result["status"] == "error"
    assert "parse JSON" in result["error"]


def test_cli_returns_fasta_and_rejects_failed_or_empty_pdb(monkeypatch, capsys):
    """CLI dispatch preserves output format and exits nonzero on failures."""
    # Use real TU loading/dispatch and CLI serialization, mocking only HTTP.
    tu = ToolUniverse()
    monkeypatch.setattr(cli, "_get_tu", lambda: tu)
    cases = [
        ("NvidiaNIM_proteinmpnn", {"input_pdb": PDB}, response(FASTA, "text/plain"), 0),
        (
            "NvidiaNIM_esmfold",
            {"sequence": "ACDE"},
            response(json.dumps({"status": "failed", "detail": "No coordinates"})),
            1,
        ),
        ("NvidiaNIM_esmfold", {"sequence": "ACDE"}, response('{"pdbs": []}'), 1),
    ]
    for name, arguments, http_response, expected_exit in cases:
        monkeypatch.setattr(
            "sys.argv", ["tu", "run", name, json.dumps(arguments), "--raw"]
        )
        with patch("requests.post", return_value=http_response) as post:
            if expected_exit:
                with pytest.raises(SystemExit) as exc:
                    cli.main()
                assert exc.value.code == expected_exit
            else:
                cli.main()
        result = json.loads(capsys.readouterr().out)
        post.assert_called_once()
        if expected_exit:
            assert result["status"] == "error"
            assert "structure" not in result
        else:
            assert result["format"] == "mfasta"
            assert result["sequences"] == FASTA


def test_pdb_envelope_keeps_every_structure():
    """Ensemble consumers can retrieve all outputs in their original order."""
    pdbs = [PDB, PDB.replace("ALA", "GLY")]
    result = NvidiaNIMTool(CONFIGS["NvidiaNIM_esmfold"])._parse_response(
        response(json.dumps({"pdbs": pdbs}))
    )
    assert result["structure"] == pdbs[0]
    assert result["structures"] == pdbs


def test_json_model_with_text_content_type_is_not_mislabeled_pdb():
    """A misleading content type does not override the model's output format."""
    payload = {"alignments": [">query\nACDE\n"]}
    result = NvidiaNIMTool(CONFIGS["NvidiaNIM_msa_search"])._parse_response(
        response(json.dumps(payload), "text/plain")
    )
    assert result == {"status": "success", "data": payload}


@pytest.mark.parametrize("name", ["NvidiaNIM_proteinmpnn", "NvidiaNIM_esmfold"])
def test_async_completion_checks_prediction_failure(name):
    """Polling applies the same failure checks as synchronous invocation."""
    accepted = response("")
    accepted.status_code = 202
    accepted.headers["nvcf-reqid"] = "offline-request-id"
    failed = response('{"status": "failed", "detail": "Prediction failed"}')
    arguments = {"input_pdb": PDB} if "proteinmpnn" in name else {"sequence": "ACDE"}
    with (
        patch("requests.post", return_value=accepted),
        patch("requests.get", return_value=failed) as get,
    ):
        result = NvidiaNIMTool(CONFIGS[name]).run(arguments)
    get.assert_called_once()
    assert result["status"] == "error"
    assert "structure" not in result
    assert "sequences" not in result
