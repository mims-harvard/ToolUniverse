from fastmcp import FastMCP
import os
from tooluniverse.boltz_tool import Boltz2DockingTool
from tooluniverse.server_security import (
    get_fastmcp_token_auth,
    run_fastmcp_server,
)
import json
import threading

# Read the tool config dicts from the JSON file
try:
    with open(
        os.path.join(os.path.dirname(__file__), "boltz_client_tools.json"), "r"
    ) as f:
        boltz_tools = json.load(f)
except FileNotFoundError as exc:
    raise RuntimeError("Boltz tool configuration is missing.") from exc

server = FastMCP("Boltz-2 MCP Server", auth=get_fastmcp_token_auth())
agents = {}
for tool_config in boltz_tools:
    agents[tool_config["name"]] = Boltz2DockingTool(tool_config=tool_config)

_BOLTZ_REQUEST_LOCK = threading.Lock()


@server.tool()
def boltz2_docking(
    sequence: str,
    ligands: list[dict],
    recycling_steps: int = 3,
    sampling_steps: int = 200,
    diffusion_samples: int = 1,
    step_scale: float = 1.638,
    use_potentials: bool = False,
    return_structure: bool = False,
    use_msa_server: bool = True,
):
    """Run the Boltz2 docking tool.
    Args:
        sequence: Protein sequence using single-letter amino acid codes.
        ligands: Ligand dictionaries with id and smiles fields.
    Returns
        dict: A dictionary containing the docking results with the following structure:
            - predicted_structure (str): The predicted protein-ligand complex structure in CIF format
            - structure_format (str): Format of the structure file (typically 'cif')
            - structure_error (str): Error message if structure file is missing
            - affinity_prediction (object): JSON object containing affinity predictions and related data
            - msa_mode (str): Either server or single_sequence
        Missing, oversized, malformed, or non-finite affinity artifacts return a
        sanitized error object rather than a partial success.
    """
    # The provider model is GPU-heavy and uses shared cache/work directories.
    # Queue requests in-process rather than allowing concurrent calls to race
    # or exhaust device memory.
    with _BOLTZ_REQUEST_LOCK:
        return agents["boltz2_docking"].run(
            {
                "sequence": sequence,
                "ligands": ligands,
                "recycling_steps": recycling_steps,
                "sampling_steps": sampling_steps,
                "diffusion_samples": diffusion_samples,
                "step_scale": step_scale,
                "use_potentials": use_potentials,
                "return_structure": return_structure,
                "use_msa_server": use_msa_server,
            }
        )


if __name__ == "__main__":
    run_fastmcp_server(
        server,
        host=os.getenv("TOOLUNIVERSE_MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("TOOLUNIVERSE_MCP_PORT", "8080")),
        stateless_http=True,
    )
