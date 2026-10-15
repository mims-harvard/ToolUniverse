import json
import os
import threading
import time
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field, StrictBool, StrictInt

from tooluniverse.rfdiffusion2_tool import RFDiffusion2Tool
from tooluniverse.server_security import (
    get_fastmcp_token_auth,
    run_fastmcp_server,
)

# Read the tool config dicts from the JSON file
try:
    with open(
        os.path.join(os.path.dirname(__file__), "rfdiffusion2_client_tools.json"),
        "r",
        encoding="utf-8",
    ) as f:
        rfdiffusion2_tools = json.load(f)
except FileNotFoundError as exc:
    raise RuntimeError("RFdiffusion2 tool configuration is missing.") from exc

server = FastMCP("RFdiffusion2 MCP Server", auth=get_fastmcp_token_auth())
agents = {}
for tool_config in rfdiffusion2_tools:
    agents[tool_config["name"]] = RFDiffusion2Tool(tool_config=tool_config)

_RFDIFFUSION2_REQUEST_LOCK = threading.Lock()

# The limits and descriptions FastMCP advertises and enforces come from the
# tool manifest, so an auto-loading client sees the same contract as the
# published configuration.
_PROPERTIES = rfdiffusion2_tools[0]["parameter"]["properties"]
_FIELD_KEYWORDS = {
    "description": "description",
    "pattern": "pattern",
    "minimum": "ge",
    "maximum": "le",
    "minLength": "min_length",
    "maxLength": "max_length",
    "minProperties": "min_length",
    "maxProperties": "max_length",
}


def _field(name):
    return Field(
        **{
            _FIELD_KEYWORDS[keyword]: value
            for keyword, value in _PROPERTIES[name].items()
            if keyword in _FIELD_KEYWORDS
        }
    )


((_RESIDUE_PATTERN, _ATOMS_SCHEMA),) = _PROPERTIES["contig_atoms"][
    "patternProperties"
].items()
_ContigAtoms = dict[
    Annotated[str, Field(pattern=_RESIDUE_PATTERN)],
    Annotated[str, Field(pattern=_ATOMS_SCHEMA["pattern"])],
]


@server.tool()
def rfdiffusion2_design(
    contig_map: Annotated[str, _field("contig_map")],
    input_pdb: Annotated[str, _field("input_pdb")],
    ligand: Annotated[str | None, _field("ligand")] = None,
    contig_atoms: Annotated[_ContigAtoms | None, _field("contig_atoms")] = None,
    contig_as_guidepost: Annotated[StrictBool, _field("contig_as_guidepost")] = False,
    num_designs: Annotated[StrictInt, _field("num_designs")] = 1,
    inference_steps: Annotated[StrictInt | None, _field("inference_steps")] = None,
    seed: Annotated[StrictInt | None, _field("seed")] = None,
    return_structure: Annotated[StrictBool, _field("return_structure")] = True,
    timeout_seconds: Annotated[StrictInt, _field("timeout_seconds")] = 900,
    dry_run: Annotated[StrictBool, _field("dry_run")] = False,
):
    """Design protein backbones with RFdiffusion2.

    Returns
        dict: status plus either error (a sanitized message) or data with
            num_designs, runtime_seconds, and designs. Each design reports its
            name, residue and atom counts, chains, ligands, the motif residues
            that kept side-chain atoms, and the PDB text when requested.
        A missing, oversized, malformed, or non-finite design returns an error
        rather than a partial success.
    """
    arguments = {
        "contig_map": contig_map,
        "input_pdb": input_pdb,
        "ligand": ligand,
        "contig_atoms": contig_atoms,
        "contig_as_guidepost": contig_as_guidepost,
        "num_designs": num_designs,
        "inference_steps": inference_steps,
        "seed": seed,
        "return_structure": return_structure,
        "timeout_seconds": timeout_seconds,
        "dry_run": dry_run,
    }
    if dry_run:
        return agents["rfdiffusion2_design"].run(arguments)
    # One design fills a GPU for minutes, so requests run one at a time. The
    # wait for a running design counts against the caller's timeout: a client
    # stops listening after a fixed time whether or not its job has started.
    queued = time.monotonic()
    if not _RFDIFFUSION2_REQUEST_LOCK.acquire(timeout=timeout_seconds):
        return {
            "status": "error",
            "error": "RFdiffusion2 is busy with another design. Try again later.",
        }
    try:
        waited = int(time.monotonic() - queued)
        arguments["timeout_seconds"] = max(1, timeout_seconds - waited)
        return agents["rfdiffusion2_design"].run(arguments)
    finally:
        _RFDIFFUSION2_REQUEST_LOCK.release()


if __name__ == "__main__":
    run_fastmcp_server(
        server,
        host=os.getenv("TOOLUNIVERSE_MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("TOOLUNIVERSE_MCP_PORT", "8033")),
        stateless_http=True,
    )
