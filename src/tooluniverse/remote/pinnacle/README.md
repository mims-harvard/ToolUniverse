# PINNACLE Protein-Protein Interaction Tool

## TOU validation and deployment status (2026-08-16)

> Loopback discovery and retrieval passed against a deterministic safe weights-only fixture with three bounded embeddings. Four simultaneous fixture calls passed with event-loop offloading and serialized provider state. Production PINNACLE artifacts, public publication, cross-user isolation, scale, and scientific-value validation remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_pinnacle_ppi_retrieval`
- Start: `python -m tooluniverse.remote.pinnacle.pinnacle_tool`
- Endpoint: `http://127.0.0.1:7001/mcp`
- Provider configuration: set `PINNACLE_DATA_PATH` to the reviewed provider artifact root; the weights-only embedding checkpoint initializes once per process.
- TOU check: `tu doctor --forward http://127.0.0.1:7001/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:7001/mcp --name validation-pinnacle --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. The current result is an artifact-contract pass, not production-model validation.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation pinnacle`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-pinnacle-remote-tool/SKILL.md).

## Authorize once, then share with one short command

After installing this provider's dependencies and the pinned Connect relay SDK,
and exporting its required resources, run once per machine (and again after key rotation):

```bash
tu remote login
# Or import an existing protected 0600 file without sourcing it:
tu remote login --env-file /path/to/tooluniverse-service.env
```

Then each private share is:

```bash
tu remote share pinnacle
```

By default, `tu remote login` requests a short-lived device code, opens the TU
Platform approval page, and polls until the signed-in user approves. No key
copy/paste is required. On a headless machine, add `--no-browser` and open the
printed link elsewhere. The CLI exchanges approval for a computer-only key,
verifies `/remote-servers/preflight`, stores it in a local 0600 config file, and
never displays it.

The share command selects the reviewed environment, checks it, starts or reuses
the exact loopback MCP tool set, runs the TU Platform preflight, and keeps the
private relay in the foreground until Ctrl-C. Override defaults only when needed:

```bash
tu remote share pinnacle --name my-pinnacle-remote --workers 1
```

Use `tu remote run pinnacle` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Overview

The [PINNACLE](https://github.com/mims-harvard/PINNACLE) tool provides access to cell-type-specific protein-protein interaction embeddings. These embeddings capture functional relationships between proteins in different cellular contexts, enabling advanced analysis for drug discovery, disease research, and systems biology.

PINNACLE generates dense vector representations of proteins that encode both direct physical interactions and functional associations within specific cell types. This contextualization allows for more accurate modeling of biological processes in tissue-specific environments.

## Data Acquisition

### 1. Download PINNACLE Embeddings

The PINNACLE embeddings are hosted on Hugging Face at: https://huggingface.co/datasets/mims-harvard/ToolSpace

Use the following shell commands to download only the PINNACLE files from the `pinnacle_cge` directory:

```bash
# Install CLI if not already
uvx --from huggingface_hub hf

# Download only the pinnacle_cge folder
uvx --from huggingface_hub hf download mims-harvard/ToolSpace \
  --repo-type dataset \
  --include "pinnacle_cge/*" \
  --local-dir ./path/to/your/pinnacle/
```

### 2. Set Environment Variable

After downloading, set the `PINNACLE_DATA_PATH` environment variable:

```bash
export PINNACLE_DATA_PATH="/path/to/ToolSpace"
```

## Tool Input and Output

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cell_type` | string | Yes | Target cell type for embedding retrieval |
| `embed_path` | string | No | Custom path to embedding file (optional) |

The tool performs fuzzy matching to handle various naming conventions, spaces, hyphens, and capitalization differences.

### Output Format

The tool returns a JSON object with the following structure:

#### Successful Response
```json
{
  "embeddings": {
    "TP53": [0.1234, -0.5678, 0.9012, ...],
    "EGFR": [-0.2345, 0.6789, -0.1234, ...],
    "BRCA1": [0.3456, -0.7890, 0.2345, ...],
    "...": "..."
  },
  "context_info": [
    "Successfully retrieved embeddings for 15234 proteins/genes.",
    "Embedding dimensionality: 256 features per protein.",
    "Cell type context: b_cell (matched and processed)."
  ]
}
```


### Embedding Properties

- **Dimensionality**: A 328-dimensional vector (200 structure-based protein representation + 128 contextaware/-free protein representation)
- **Coverage**: 394,760 protein representations from 156 cell type contexts across 24 tissues
- **Format**: Dense numerical vectors (list of floats)

## MCP Server Setup

### Prerequisites

```bash
# create a uv virtual enviroment for COMPASS setup
uv venv pinnacle --python 3.10
source pinnacle/bin/activate
uv pip install -r requirements.txt
```

### Configuration

1. **Set up the environment**:
```bash
# Ensure PINNACLE_DATA_PATH points to your ToolSpace directory
export PINNACLE_DATA_PATH="/path/to/ToolSpace"
```

2. **Verify embedding files exist**:
```bash
ls -la $PINNACLE_DATA_PATH/pinnacle_embeds/ppi_embed_dict.pth
ls -la $PINNACLE_DATA_PATH/pinnacle_cge/
```

### Running the MCP Server
```bash
# Run the MCP server from the ToolUniverse repository root
python -m tooluniverse.remote.pinnacle.pinnacle_tool
```

### Server Configuration

- **Host**: `127.0.0.1` (loopback; use the outbound relay for Connect)
- **Port**: `7001` (configured to avoid conflicts)
- **Transport**: `streamable-http`
- **Mode**: Stateless HTTP for scalability

A deliberate non-loopback bind requires `TOOLUNIVERSE_API_TOKEN`; do not
expose the unauthenticated provider directly.
