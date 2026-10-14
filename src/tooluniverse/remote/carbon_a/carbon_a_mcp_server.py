import json
import os
import threading
import time
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field, StrictBool, StrictFloat, StrictInt

from tooluniverse.carbon_a_tool import CarbonATool
from tooluniverse.server_security import (
    get_fastmcp_token_auth,
    run_fastmcp_server,
)

# Read the tool config dicts from the JSON file
try:
    with open(
        os.path.join(os.path.dirname(__file__), "carbon_a_client_tools.json"),
        "r",
        encoding="utf-8",
    ) as f:
        carbon_a_tools = json.load(f)
except FileNotFoundError as exc:
    raise RuntimeError("Carbon-A tool configuration is missing.") from exc

server = FastMCP("Carbon-A MCP Server", auth=get_fastmcp_token_auth())
agents = {}
for tool_config in carbon_a_tools:
    agents[tool_config["name"]] = CarbonATool(tool_config=tool_config)

_CARBON_A_REQUEST_LOCK = threading.Lock()

# The limits and descriptions FastMCP advertises and enforces come from the
# tool manifest, so an auto-loading client sees the same contract as the
# published configuration.
_PROPERTIES = carbon_a_tools[0]["parameter"]["properties"]
_FIELD_KEYWORDS = {
    "description": "description",
    "pattern": "pattern",
    "minimum": "ge",
    "maximum": "le",
    "minLength": "min_length",
    "maxLength": "max_length",
}


def _field(name):
    return Field(
        **{
            _FIELD_KEYWORDS[keyword]: value
            for keyword, value in _PROPERTIES[name].items()
            if keyword in _FIELD_KEYWORDS
        }
    )


@server.tool()
def carbon_a_annotate_cds(
    sequence: Annotated[str | None, _field("sequence")] = None,
    sequence_id: Annotated[str | None, _field("sequence_id")] = None,
    input_file: Annotated[str | None, _field("input_file")] = None,
    genetic_code: Annotated[str | None, _field("genetic_code")] = "standard",
    min_confidence: Annotated[StrictFloat | StrictInt, _field("min_confidence")] = 0.1,
    min_record_length: Annotated[StrictInt, _field("min_record_length")] = 100000,
    attn_implementation: Annotated[str | None, _field("attn_implementation")] = None,
    max_genes: Annotated[StrictInt, _field("max_genes")] = 200,
    return_gff: Annotated[StrictBool, _field("return_gff")] = False,
    return_proteins: Annotated[StrictBool, _field("return_proteins")] = False,
    timeout_seconds: Annotated[StrictInt, _field("timeout_seconds")] = 900,
    dry_run: Annotated[StrictBool, _field("dry_run")] = False,
):
    """Annotate protein-coding genes in eukaryotic DNA with Carbon-A.

    Returns
        dict: status plus either error (a sanitized message) or data with the
            gene counts, the predicted coding bases, the records annotated and
            the genes themselves, each with coordinates, strand, exon count and
            the model's confidence that its structure is exactly right.
        A record shorter than min_record_length is refused rather than reported
        as having no genes, because the pipeline skips such records. A genetic
        code that may not fit the sequence returns the genes together with the
        pipeline's warning.
    """
    arguments = {
        "sequence": sequence,
        "sequence_id": sequence_id,
        "input_file": input_file,
        "genetic_code": genetic_code,
        "min_confidence": min_confidence,
        "min_record_length": min_record_length,
        "attn_implementation": attn_implementation,
        "max_genes": max_genes,
        "return_gff": return_gff,
        "return_proteins": return_proteins,
        "timeout_seconds": timeout_seconds,
        "dry_run": dry_run,
    }
    arguments = {
        name: value
        for name, value in arguments.items()
        if value is not None or name in ("sequence", "input_file")
    }
    if dry_run:
        return agents["carbon_a_annotate_cds"].run(arguments)
    # One annotation holds the GPU and 4.6 GB of weights for minutes, so
    # requests run one at a time. The wait for a running annotation counts
    # against the caller's timeout: a client stops listening after a fixed time
    # whether or not its job has started.
    queued = time.monotonic()
    if not _CARBON_A_REQUEST_LOCK.acquire(timeout=timeout_seconds):
        return {
            "status": "error",
            "error": "Carbon-A is busy with another annotation. Try again later.",
        }
    try:
        waited = int(time.monotonic() - queued)
        arguments["timeout_seconds"] = max(1, timeout_seconds - waited)
        return agents["carbon_a_annotate_cds"].run(arguments)
    finally:
        _CARBON_A_REQUEST_LOCK.release()


if __name__ == "__main__":
    run_fastmcp_server(
        server,
        host=os.getenv("TOOLUNIVERSE_MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("TOOLUNIVERSE_MCP_PORT", "8034")),
        stateless_http=True,
    )
