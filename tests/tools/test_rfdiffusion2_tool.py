import json
from pathlib import Path
from types import SimpleNamespace

from tooluniverse import ToolUniverse
from tooluniverse.rfdiffusion2_tool import RFDiffusion2Tool


CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "rfdiffusion2_tools.json"
)


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))[0]


def test_dry_run_builds_rfdiffusion2_command(monkeypatch):
    monkeypatch.delenv("RFDIFFUSION2_COMMAND", raising=False)
    tool = RFDiffusion2Tool(load_config())

    result = tool.run(
        {
            "contig_map": ["A1-100/0 50-100"],
            "input_pdb": "inputs/target.pdb",
            "output_prefix": "outputs/design",
            "num_designs": 2,
            "inference_steps": 50,
            "hotspot_residues": ["A30", "A33"],
            "extra_args": ["potentials.guiding_potentials=[]"],
            "dry_run": True,
        }
    )

    assert result["status"] == "success"
    command = result["data"]["command"]
    assert command[0] == "run_inference.py"
    assert "contigmap.contigs=[A1-100/0 50-100]" in command
    assert "inference.input_pdb=inputs/target.pdb" in command
    assert "inference.output_prefix=outputs/design" in command
    assert "inference.num_designs=2" in command
    assert "diffuser.T=50" in command
    assert "ppi.hotspot_res=[A30,A33]" in command
    assert "potentials.guiding_potentials=[]" in command


def test_non_dry_run_requires_configured_command(monkeypatch):
    monkeypatch.delenv("RFDIFFUSION2_COMMAND", raising=False)
    tool = RFDiffusion2Tool(load_config())

    result = tool.run({"contig_map": "150-150"})

    assert result["status"] == "error"
    assert "RFDIFFUSION2_COMMAND is not set" in result["error"]


def test_runs_configured_command(monkeypatch):
    monkeypatch.setenv("RFDIFFUSION2_COMMAND", "python run_inference.py")
    tool = RFDiffusion2Tool(load_config())
    calls = []

    def fake_run(args, **kwargs):
        calls.append({"args": args, **kwargs})
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("tooluniverse.rfdiffusion2_tool.subprocess.run", fake_run)

    result = tool.run({"contig_map": "150-150", "timeout_seconds": 5})

    assert result["status"] == "success"
    assert calls[0]["timeout"] == 5
    assert calls[0]["args"][0:2] == ["python", "run_inference.py"]
    assert "contigmap.contigs=[150-150]" in calls[0]["args"]


def test_tooluniverse_loads_rfdiffusion2_config(monkeypatch):
    monkeypatch.setenv("RFDIFFUSION2_COMMAND", "python run_inference.py")
    tu = ToolUniverse()
    tu.load_tools(tool_type=["rfdiffusion2"])

    assert "rfdiffusion2_design" in tu.all_tool_dict
    assert tu.all_tool_dict["rfdiffusion2_design"]["type"] == "RFDiffusion2Tool"
