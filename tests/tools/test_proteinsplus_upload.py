"""ProtoSS raw PDBs must take the documented upload route, not pdbData."""

import asyncio
import copy
import json
from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace

import jsonschema
import pytest

from tooluniverse.proteinsplus_tool import ProteinsPlusRESTTool

ROOT = Path(__file__).resolve().parents[2]
CONFIG = next(
    c
    for c in json.loads(
        (ROOT / "src/tooluniverse/data/proteinsplus_tools.json").read_text()
    )
    if c["name"] == "ProteinsPlus_protonate_structure"
)
PDB = "ATOM      1  N   HIS A  68      23.803  30.279  22.798  1.00 10.00           N\nEND\n"
LOCATION = "https://proteins.plus/api/pdb_files_rest/upload-id"


def response(code, payload):
    return Mock(status_code=code, json=Mock(return_value=payload))


def test_raw_pdb_upload_then_poll_then_protoss(monkeypatch):
    post = Mock(
        side_effect=[
            response(202, {"location": LOCATION}),
            response(202, {"location": "https://proteins.plus/api/protoss_rest/job"}),
        ]
    )
    get = Mock(
        side_effect=[
            response(202, {}),
            response(200, {"id": "loaded-id"}),
            response(
                200,
                {"protein": "protein.pdb", "ligands": "ligands.sdf", "log": "log.txt"},
            ),
        ]
    )
    monkeypatch.setattr("tooluniverse.proteinsplus_tool.requests.post", post)
    monkeypatch.setattr("tooluniverse.proteinsplus_tool.requests.get", get)
    monkeypatch.setattr(
        "tooluniverse.proteinsplus_tool.time.sleep", lambda seconds: None
    )
    arguments = {"pdb_content": PDB, "pdb_id": None}
    original = copy.deepcopy(arguments)
    result = asyncio.run(ProteinsPlusRESTTool(CONFIG).run(arguments))
    assert result["status"] == "success" and result["data"]["protein"] == "protein.pdb"
    upload = post.call_args_list[0]
    assert upload.args[0].endswith("/pdb_files_rest")
    assert upload.kwargs["files"]["pdb_file[pathvar]"][1] == PDB.encode()
    assert "Content-Type" not in upload.kwargs["headers"]
    assert post.call_args_list[1].kwargs["json"] == {
        "protoss": {"pdbCode": "loaded-id"}
    }
    assert arguments == original


@pytest.mark.parametrize(
    "args",
    [
        {},
        {"pdb_id": None},
        {"pdb_id": ""},
        {"pdb_id": "1cbs", "pdb_content": PDB},
        {"pdb_content": ">FASTA\nAAAA"},
        {"pdb_id": "1cbs", "ligand_content": "SDF"},
    ],
)
def test_invalid_input_rejected_before_network(monkeypatch, args):
    post = Mock(side_effect=AssertionError("Invalid input reached HTTP"))
    monkeypatch.setattr("tooluniverse.proteinsplus_tool.requests.post", post)
    result = asyncio.run(ProteinsPlusRESTTool(CONFIG).run(args))
    assert result["status"] == "error"
    post.assert_not_called()


def test_pdb_id_keeps_existing_route(monkeypatch):
    post = Mock(
        return_value=response(
            200, {"location": "https://proteins.plus/api/protoss_rest/job"}
        )
    )
    monkeypatch.setattr("tooluniverse.proteinsplus_tool.requests.post", post)
    ProteinsPlusRESTTool(CONFIG).submit_job({"pdb_id": "1cbs"})
    post.assert_called_once()
    assert post.call_args.kwargs["json"] == {"protoss": {"pdbCode": "1cbs"}}


@pytest.mark.parametrize(
    "reply,fragment",
    [
        (response(500, {}), "HTTP 500"),
        (response(200, {}), "no id"),
        (response(202, {}), "no polling"),
        (response(202, {"location": "https://other.example/steal"}), "Unexpected"),
    ],
)
def test_upload_errors_never_submit_protoss(monkeypatch, reply, fragment):
    post = Mock(return_value=reply)
    monkeypatch.setattr("tooluniverse.proteinsplus_tool.requests.post", post)
    result = asyncio.run(ProteinsPlusRESTTool(CONFIG).run({"pdb_content": PDB}))
    assert fragment in result["error"]["message"]
    post.assert_called_once()


def test_upload_deadline_is_bounded(monkeypatch):
    post = Mock(return_value=response(202, {"location": LOCATION}))
    monkeypatch.setattr("tooluniverse.proteinsplus_tool.requests.post", post)
    monkeypatch.setattr(
        "tooluniverse.proteinsplus_tool.time",
        SimpleNamespace(monotonic=Mock(side_effect=[0, 121])),
    )
    result = asyncio.run(ProteinsPlusRESTTool(CONFIG).run({"pdb_content": PDB}))
    assert "within 120" in result["error"]["message"]
    post.assert_called_once()


def test_schema_accepts_explicit_null_unused_source():
    jsonschema.validate({"pdb_id": "1cbs", "pdb_content": None}, CONFIG["parameter"])
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"pdb_id": "1cbs", "pdb_content": PDB}, CONFIG["parameter"])
