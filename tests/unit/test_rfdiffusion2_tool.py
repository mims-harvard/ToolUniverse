import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastmcp import Client
from jsonschema import Draft202012Validator

from tooluniverse import rfdiffusion2_tool
from tooluniverse.default_config import default_tool_files
from tooluniverse.remote.rfdiffusion2 import rfdiffusion2_mcp_server
from tooluniverse.rfdiffusion2_tool import RFDiffusion2Tool

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "tooluniverse"
INTERNAL_CONFIG = (
    SOURCE_ROOT / "remote" / "rfdiffusion2" / "rfdiffusion2_client_tools.json"
)
PUBLISHED_CONFIG = SOURCE_ROOT / "data" / "remote_tools" / "rfdiffusion2_tools.json"
SERVER_SOURCE = SOURCE_ROOT / "remote" / "rfdiffusion2" / "rfdiffusion2_mcp_server.py"

BASE = {"contig_map": "150", "input_pdb": "mcsa_41/M0584_1ldm.pdb"}
ENZYME_DESIGN = {
    "contig_map": "46,A106-106,59,A166-166,2,A169-169,23,A193-193,46",
    "input_pdb": "mcsa_41/M0584_1ldm.pdb",
    "ligand": "NAD,OXM",
    "contig_atoms": {"A106": "NE,CD,CZ", "A166": "OD1,CG"},
    "contig_as_guidepost": True,
    "inference_steps": 50,
    "seed": 43,
}
# Shapes outside the closed contract. The validator and the published schema
# must both refuse every one of them.
REJECTED = [
    {},
    {"contig_map": "150"},
    {"input_pdb": "mcsa_41/M0584_1ldm.pdb"},
    {**BASE, "input_pdb": ""},
    {**BASE, "input_pdb": "/etc/passwd.pdb"},
    {**BASE, "input_pdb": "../secret.pdb"},
    {**BASE, "input_pdb": "mcsa_41/../../secret.pdb"},
    {**BASE, "input_pdb": "a,b.pdb"},
    {**BASE, "input_pdb": "${oc.env:HOME}.pdb"},
    {**BASE, "input_pdb": "a" * 600 + ".pdb"},
    {**BASE, "contig_map": ["150"]},
    {**BASE, "contig_map": "150'] inference.output_prefix=/tmp/x"},
    {**BASE, "extra_args": ["hydra.run.dir=/tmp/x"]},
    {**BASE, "output_prefix": "/tmp/x"},
    {**BASE, "ligand": "NAD' inference.ckpt_path=/tmp/x"},
    {**BASE, "contig_atoms": {"A106": "NE'}"}},
    {**BASE, "contig_atoms": {"A106'": "NE"}},
    {**BASE, "contig_atoms": {}},
    {**BASE, "num_designs": 5},
    {**BASE, "num_designs": True},
    {**BASE, "inference_steps": 100000},
    {**BASE, "seed": -1},
    {**BASE, "timeout_seconds": 901},
    {**BASE, "dry_run": "yes"},
]
# ``$`` in a Python regex also matches before a final newline, so these only
# stay out if the validator matches the whole string.
REJECTED_TRAILING_NEWLINE = [
    {**BASE, "contig_map": "150\n"},
    {**BASE, "input_pdb": "mcsa_41/M0584_1ldm.pdb\n"},
    {**BASE, "ligand": "NAD\n"},
    {**BASE, "contig_atoms": {"A106\n": "NE"}},
    {**BASE, "contig_atoms": {"A106": "NE\n"}},
]


def _atom(record, serial, name, residue, number, xyz=(1.0, 2.0, 3.0)):
    return (
        f"{record:<6}{serial:>5} {name:<4} {residue:>3} A{number:>4}    "
        f"{xyz[0]:>8.3f}{xyz[1]:>8.3f}{xyz[2]:>8.3f}  1.00  0.00"
    )


def _design_pdb(skip=(), duplicate=None, bad_coordinate=False):
    """Three residues, the second a motif arginine, plus an NAD atom.

    ``skip`` drops (residue number, atom name) pairs and ``duplicate`` repeats
    one, the way an alternate location would.
    """
    lines, serial = [], 0
    for number in (1, 2, 3):
        residue = "ARG" if number == 2 else "ALA"
        names = ["N", "CA", "C", "O", "CB"] + (["NE"] if number == 2 else [])
        if duplicate and duplicate[0] == number:
            names.append(duplicate[1])
        for name in names:
            if (number, name) in skip:
                continue
            serial += 1
            lines.append(_atom("ATOM", serial, name, residue, number))
    lines.append(_atom("HETATM", serial + 1, "C1", "NAD", 4))
    if bad_coordinate:
        lines[0] = lines[0][:30] + f"{'nan':>8}" + lines[0][38:]
    return "\n".join(lines) + "\nEND\n"


def _call(arguments):
    """Call the operation through FastMCP, as a remote client does."""

    async def call():
        async with Client(rfdiffusion2_mcp_server.server) as client:
            return await client.call_tool("rfdiffusion2_design", arguments)

    return asyncio.run(call()).data


def _advertised_schema():
    async def list_tools():
        async with Client(rfdiffusion2_mcp_server.server) as client:
            return await client.list_tools()

    (tool,) = asyncio.run(list_tools())
    return tool.inputSchema


def _process_is_gone(pid):
    try:
        # A killed process whose new parent has not reaped it still has a PID.
        with open(f"/proc/{pid}/stat", encoding="utf-8") as stat:
            return stat.read().rsplit(")", 1)[1].split()[0] == "Z"
    except OSError:
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


def _wait_until_gone(pid, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if _process_is_gone(pid):
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def tool():
    return RFDiffusion2Tool(json.loads(INTERNAL_CONFIG.read_text(encoding="utf-8"))[0])


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    """A provider input directory, with one file outside it."""
    root = tmp_path / "inputs"
    (root / "mcsa_41").mkdir(parents=True)
    (root / "mcsa_41" / "M0584_1ldm.pdb").write_text("ATOM\n", encoding="utf-8")
    (tmp_path / "secret.pdb").write_text("ATOM\n", encoding="utf-8")
    monkeypatch.setenv("RFDIFFUSION2_INPUT_ROOT", str(root))
    for name in ("COMMAND", "WORKDIR", "CHECKPOINT", "CONFIG_NAME", "JOB_ROOT"):
        monkeypatch.delenv(f"RFDIFFUSION2_{name}", raising=False)
    return root


@pytest.fixture
def provider(tmp_path, monkeypatch, inputs):
    """A configured provider whose RFdiffusion2 command is replaced by a fake."""
    workdir = tmp_path / "RFdiffusion2"
    weights = workdir / "rf_diffusion" / "model_weights"
    jobs = tmp_path / "jobs"
    weights.mkdir(parents=True)
    jobs.mkdir()
    (weights / "RFD_173.pt").write_bytes(b"weights")
    monkeypatch.setenv("RFDIFFUSION2_COMMAND", "apptainer exec --nv rfd2.sif run.py")
    monkeypatch.setenv("RFDIFFUSION2_WORKDIR", str(workdir))
    monkeypatch.setenv("RFDIFFUSION2_JOB_ROOT", str(jobs))

    state = {
        "calls": [],
        "returncode": 0,
        "designs": {"design_0-atomized-bb-False.pdb": _design_pdb()},
        "log": "Traceback: /provider/secret/path\n",
        "workdir": workdir,
        "inputs": inputs,
        "jobs": jobs,
    }

    def fake_run(command, cwd, env, log_path, timeout):
        state["calls"].append(
            {"command": command, "cwd": cwd, "env": env, "timeout": timeout}
        )
        log_path.write_text(state["log"], encoding="utf-8")
        if state.get("raise"):
            raise state["raise"]
        for name, text in state["designs"].items():
            (log_path.parent / name).write_text(text, encoding="utf-8")
        return state["returncode"]

    monkeypatch.setattr(rfdiffusion2_tool, "_run_provider_command", fake_run)
    return state


def test_dry_run_reports_overrides_without_a_configured_command(tool, inputs):
    result = tool.run({**ENZYME_DESIGN, "dry_run": True})

    assert result == {
        "status": "success",
        "data": {
            "dry_run": True,
            "overrides": [
                "contigmap.contigs=['46,A106-106,59,A166-166,2,A169-169,23,A193-193,46']",
                "inference.num_designs=1",
                "inference.contig_as_guidepost=True",
                "inference.input_pdb=mcsa_41/M0584_1ldm.pdb",
                "inference.ligand='NAD,OXM'",
                "contigmap.contig_atoms=\"{'A106':'NE,CD,CZ','A166':'OD1,CG'}\"",
                "diffuser.T=50",
                "inference.deterministic=True",
                "inference.seed_offset=43",
            ],
        },
    }


def test_dry_run_checks_that_the_input_file_exists(tool, inputs):
    result = tool.run({**BASE, "input_pdb": "missing.pdb", "dry_run": True})

    assert result == {
        "status": "error",
        "error": "'input_pdb': the requested data file does not exist.",
    }


@pytest.mark.parametrize("arguments", REJECTED + REJECTED_TRAILING_NEWLINE)
def test_rejects_arguments_outside_the_closed_contract(tool, provider, arguments):
    for extra in ({}, {"dry_run": True}):
        if "dry_run" in arguments and extra:
            continue
        result = tool.run({**arguments, **extra})

        assert result["status"] == "error"
        assert "data" not in result
    assert provider["calls"] == []


def test_published_schema_refuses_the_same_shapes_as_the_validator(tool, inputs):
    published = json.loads(PUBLISHED_CONFIG.read_text(encoding="utf-8"))[0]
    internal = json.loads(INTERNAL_CONFIG.read_text(encoding="utf-8"))[0]
    assert published["parameter"] == internal["parameter"]
    assert "required_api_keys" not in published

    validator = Draft202012Validator(published["parameter"])
    assert list(validator.iter_errors(BASE)) == []
    for example in published["test_examples"]:
        assert list(validator.iter_errors(example)) == []
        assert tool.run({**example, "dry_run": True})["status"] == "success"
    for arguments in REJECTED:
        assert list(validator.iter_errors(arguments)) != [], arguments


def test_mcp_server_advertises_the_published_schema():
    published = json.loads(PUBLISHED_CONFIG.read_text(encoding="utf-8"))[0]["parameter"]

    def normalize(node):
        if not isinstance(node, dict):
            return node
        node = {key: value for key, value in node.items() if key != "title"}
        if "anyOf" in node:
            # Pydantic writes an optional argument as "X or null, default null".
            (inner,) = [
                option for option in node["anyOf"] if option != {"type": "null"}
            ]
            assert node.pop("default") is None
            del node["anyOf"]
            node = {**inner, **node}
        return {key: normalize(value) for key, value in node.items()}

    expected = json.loads(json.dumps(published))
    # Pydantic enforces the residue pattern on every key without saying so.
    del expected["properties"]["contig_atoms"]["additionalProperties"]

    assert normalize(_advertised_schema()) == expected


@pytest.mark.parametrize(
    "arguments",
    [
        {**BASE, "num_designs": True},
        {**BASE, "num_designs": "2"},
        {**BASE, "num_designs": 2.0},
        {**BASE, "dry_run": "true"},
        {**BASE, "num_designs": 5},
        {**BASE, "extra_args": ["x"]},
        {**BASE, "contig_atoms": {"A106'": "NE"}},
        *REJECTED_TRAILING_NEWLINE,
    ],
)
def test_mcp_boundary_does_not_coerce_or_widen_arguments(provider, arguments):
    with pytest.raises(Exception, match="validation error|Unexpected keyword"):
        _call(arguments)

    assert provider["calls"] == []


def test_mcp_call_forwards_the_arguments_and_the_callers_time_budget(provider):
    result = _call({**ENZYME_DESIGN, "timeout_seconds": 600})

    assert result["status"] == "success"
    assert result["data"]["designs"][0]["residues_with_side_chain_atoms"] == ["A2:ARG"]
    assert provider["calls"][0]["timeout"] == 600
    assert "inference.ligand='NAD,OXM'" in provider["calls"][0]["command"]


def test_mcp_call_reports_busy_when_another_design_holds_the_gpu(provider):
    lock = rfdiffusion2_mcp_server._RFDIFFUSION2_REQUEST_LOCK
    assert lock.acquire(blocking=False)
    try:
        started = time.monotonic()
        result = _call({**BASE, "timeout_seconds": 1})
        waited = time.monotonic() - started
        dry_run = _call({**BASE, "dry_run": True})
    finally:
        lock.release()

    assert result == {
        "status": "error",
        "error": "RFdiffusion2 is busy with another design. Try again later.",
    }
    assert 1 <= waited < 5
    assert dry_run["status"] == "success"
    assert provider["calls"] == []
    assert not lock.locked()


def test_reports_missing_provider_configuration_without_running(tool, inputs):
    result = tool.run(BASE)

    assert result == {
        "status": "error",
        "error": "The provider must configure RFDIFFUSION2_COMMAND and "
        "RFDIFFUSION2_WORKDIR.",
    }


def test_runs_the_provider_command_and_returns_the_validated_design(
    tool, provider, monkeypatch
):
    monkeypatch.setenv("TOOLUNIVERSE_API_TOKEN", "must-not-reach-the-container")

    result = tool.run({**ENZYME_DESIGN, "timeout_seconds": 600})

    assert result["status"] == "success"
    call = provider["calls"][0]
    command = call["command"]
    assert command[:5] == ["apptainer", "exec", "--nv", "rfd2.sif", "run.py"]
    assert command[5] == "--config-name=aa"
    checkpoint = provider["workdir"] / "rf_diffusion" / "model_weights" / "RFD_173.pt"
    assert command[6] == f"inference.ckpt_path={checkpoint}"
    output_prefix = Path(command[7].split("=", 1)[1])
    assert output_prefix.name == "design"
    assert output_prefix.parent.parent == provider["jobs"]
    assert command[8] == f"hydra.run.dir={output_prefix.parent / 'hydra'}"
    resolved_input = provider["inputs"] / "mcsa_41" / "M0584_1ldm.pdb"
    assert f"inference.input_pdb={resolved_input}" in command
    assert call["cwd"] == str(provider["workdir"])
    assert call["env"]["PYTHONPATH"].split(os.pathsep)[0] == str(provider["workdir"])
    assert "TOOLUNIVERSE_API_TOKEN" not in call["env"]
    assert call["timeout"] == 600

    data = result["data"]
    assert data["num_designs"] == 1
    assert data["designs"] == [
        {
            "name": "design_0-atomized-bb-False",
            "pdb_bytes": len(_design_pdb().encode("utf-8")),
            "num_residues": 3,
            "num_atoms": 17,
            "chains": ["A"],
            "ligands": ["NAD"],
            "residues_with_side_chain_atoms": ["A2:ARG"],
            "pdb": _design_pdb(),
        }
    ]
    assert list(provider["jobs"].iterdir()) == []


def test_relative_provider_paths_are_resolved_before_the_command_runs(
    tool, provider, monkeypatch
):
    monkeypatch.chdir(provider["workdir"].parent)
    monkeypatch.setenv("RFDIFFUSION2_WORKDIR", "RFdiffusion2")
    monkeypatch.setenv("RFDIFFUSION2_JOB_ROOT", "jobs")

    result = tool.run(BASE)

    assert result["status"] == "success"
    call = provider["calls"][0]
    assert call["cwd"] == str(provider["workdir"])
    assert Path(call["command"][7].split("=", 1)[1]).parent.parent == provider["jobs"]


def test_return_structure_false_omits_the_pdb_text(tool, provider):
    result = tool.run({**BASE, "return_structure": False})

    assert result["status"] == "success"
    assert "pdb" not in result["data"]["designs"][0]
    assert result["data"]["designs"][0]["num_residues"] == 3


def test_rejects_a_link_that_leaves_the_provider_input_root(tool, provider):
    (provider["inputs"] / "link.pdb").symlink_to(
        provider["inputs"].parent / "secret.pdb"
    )

    result = tool.run({**BASE, "input_pdb": "link.pdb"})

    assert result == {
        "status": "error",
        "error": "'input_pdb': the requested file is outside the provider data "
        "directory.",
    }
    assert provider["calls"] == []


@pytest.mark.parametrize(
    "setting", ["RFDIFFUSION2_JOB_ROOT", "RFDIFFUSION2_INPUT_ROOT"]
)
def test_refuses_provider_paths_hydra_would_reinterpret(
    tool, provider, monkeypatch, setting
):
    source = provider["jobs"] if setting.endswith("JOB_ROOT") else provider["inputs"]
    renamed = source.with_name("a,b")
    source.rename(renamed)
    monkeypatch.setenv(setting, str(renamed))

    result = tool.run(BASE)

    assert result == {
        "status": "error",
        "error": "The provider must use a plain path, without spaces or "
        f"punctuation, for {setting}.",
    }
    assert provider["calls"] == []


def test_failed_command_returns_a_sanitized_error(tool, provider):
    provider["returncode"] = 1

    result = tool.run(BASE)

    assert result == {
        "status": "error",
        "error": "RFdiffusion2 failed on the provider.",
    }
    assert list(provider["jobs"].iterdir()) == []


def test_input_without_an_ori_atom_gets_an_actionable_error(tool, provider):
    provider["returncode"] = 1
    provider["log"] = (
        "AssertionError: ORI HETATM token is required for centering input "
        "correctly but was not provided\n/provider/secret/path\n"
    )

    result = tool.run(BASE)

    assert result == {
        "status": "error",
        "error": "RFdiffusion2 needs an ORI HETATM atom in 'input_pdb' to "
        "position the design.",
    }


def test_command_that_cannot_start_is_reported_as_a_provider_fault(tool, provider):
    provider["raise"] = FileNotFoundError(2, "No such file", "/provider/apptainer")

    result = tool.run(BASE)

    assert result == {
        "status": "error",
        "error": "The provider must fix RFDIFFUSION2_COMMAND.",
    }


@pytest.mark.parametrize(
    "designs",
    [
        {},
        {"design_1.pdb": _design_pdb()},
        {"design_0.pdb": _design_pdb(), "design_0-variant.pdb": _design_pdb()},
        {"design_0.pdb": _design_pdb(bad_coordinate=True)},
        {"design_0.pdb": "ATOM  garbage\n"},
        {"design_0.pdb": "REMARK no atoms\n"},
        {"design_0.pdb": _design_pdb(skip={(3, "CA")})},
        {"design_0.pdb": _design_pdb(skip={(1, "N")})},
        # Two CA atoms in one residue must not make up for a residue without one.
        {"design_0.pdb": _design_pdb(skip={(3, "CA")}, duplicate=(1, "CA"))},
        {"design_0.pdb": _design_pdb(duplicate=(2, "NE"))},
    ],
)
def test_missing_or_malformed_designs_fail_closed(tool, provider, designs):
    provider["designs"] = designs

    result = tool.run(BASE)

    assert result["status"] == "error"
    assert "data" not in result


@pytest.mark.parametrize(
    ("limit", "value"), [("_MAX_PDB_BYTES", 100), ("_MAX_PDB_ATOMS", 5)]
)
def test_oversized_designs_fail_closed(tool, provider, monkeypatch, limit, value):
    assert tool.run(BASE)["status"] == "success"
    monkeypatch.setattr(rfdiffusion2_tool, limit, value)

    result = tool.run(BASE)

    assert result == {
        "status": "error",
        "error": "RFdiffusion2 produced an invalid design.",
    }


def test_requires_every_requested_design(tool, provider):
    provider["designs"] = {"design_0.pdb": _design_pdb()}

    result = tool.run({**BASE, "num_designs": 2})

    assert result == {
        "status": "error",
        "error": "RFdiffusion2 did not produce the requested number of designs.",
    }


def test_timeout_returns_a_sanitized_error(tool, provider):
    provider["raise"] = subprocess.TimeoutExpired(cmd="apptainer", timeout=1)

    result = tool.run({**BASE, "timeout_seconds": 1})

    assert result == {
        "status": "error",
        "error": "RFdiffusion2 timed out on the provider.",
    }


posix_only = pytest.mark.skipif(
    sys.platform == "win32", reason="process groups are POSIX-only"
)


def _shell_with_grandchild(tmp_path, child, then):
    """A shell that starts ``child`` in the background, records its PID, and
    then runs ``then``, like a container runtime forking the real process."""
    pid_file = tmp_path / "grandchild.pid"
    script = f'"{sys.executable}" -c "{child}" & echo $! > "{pid_file}"; {then}'
    return ["/bin/sh", "-c", script], pid_file


@posix_only
def test_provider_command_output_goes_to_the_log_and_the_exit_code_is_returned(
    tmp_path,
):
    log_path = tmp_path / "provider.log"

    returncode = rfdiffusion2_tool._run_provider_command(
        ["/bin/sh", "-c", "echo to-stdout; echo to-stderr >&2; exit 3"],
        str(tmp_path),
        dict(os.environ),
        log_path,
        timeout=30,
    )

    assert returncode == 3
    assert log_path.read_text(encoding="utf-8") == "to-stdout\nto-stderr\n"


@posix_only
@pytest.mark.parametrize(
    "child",
    [
        "import time; time.sleep(60)",
        # A child that ignores SIGTERM must still be stopped.
        (
            "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "time.sleep(60)"
        ),
    ],
)
def test_timeout_stops_the_whole_process_group(tmp_path, monkeypatch, child):
    monkeypatch.setattr(rfdiffusion2_tool, "_TERMINATE_GRACE_SECONDS", 0.5)
    command, pid_file = _shell_with_grandchild(tmp_path, child, "wait")

    with pytest.raises(subprocess.TimeoutExpired):
        rfdiffusion2_tool._run_provider_command(
            command, str(tmp_path), dict(os.environ), tmp_path / "log", timeout=2
        )

    assert _wait_until_gone(int(pid_file.read_text(encoding="utf-8")))


@posix_only
def test_processes_left_behind_by_a_finished_command_are_stopped(tmp_path):
    command, pid_file = _shell_with_grandchild(
        tmp_path, "import time; time.sleep(60)", "exit 0"
    )

    returncode = rfdiffusion2_tool._run_provider_command(
        command, str(tmp_path), dict(os.environ), tmp_path / "log", timeout=30
    )

    assert returncode == 0
    assert _wait_until_gone(int(pid_file.read_text(encoding="utf-8")))


def test_loader_category_is_registered_with_its_own_port():
    loader = json.loads(
        Path(default_tool_files["mcp_auto_loader_rfdiffusion2"]).read_text(
            encoding="utf-8"
        )
    )[0]

    assert loader["type"] == "MCPAutoLoaderTool"
    assert loader["server_url"] == "http://${RFDIFFUSION2_MCP_SERVER_HOST}:8033/mcp"
    assert set(loader["api_key_info"]) == set(loader["required_api_keys"])
    assert 'os.getenv("TOOLUNIVERSE_MCP_PORT", "8033")' in SERVER_SOURCE.read_text(
        encoding="utf-8"
    )
