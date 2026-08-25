# Transcriptformer Gene Embedding Tool

## TOU validation and deployment status (2026-08-16)

> Loopback discovery and retrieval passed against deterministic safe metadata/embedding fixtures with bounded TP53 and EGFR output. Four simultaneous fixture calls passed with event-loop offloading and serialized provider state. Production TranscriptFormer artifacts, public publication, cross-user isolation, scale, and scientific-value validation remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_transcriptformer_embedding_retrieval`
- Start: `python -m tooluniverse.remote.transcriptformer.transcriptformer_tool`
- Endpoint: `http://127.0.0.1:7000/mcp`
- Provider configuration: set `TRANSCRIPTFORMER_DATA_PATH` to a reviewed provider artifact root; metadata initializes once and matrices are safely memory-mapped.
- TOU check: `tu doctor --forward http://127.0.0.1:7000/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:7000/mcp --name validation-transcriptformer --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. The current result is an artifact-contract pass, not production-model validation.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation transcriptformer`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-transcriptformer-remote-tool/SKILL.md).

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
tu remote share transcriptformer
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
tu remote share transcriptformer --name my-transcriptformer-remote --workers 1
```

Use `tu remote run transcriptformer` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Overview

The [Transcriptformer](https://github.com/czi-ai/transcriptformer) tool provides access to contextualized gene embeddings learned from single-cell RNA sequencing data. Transcriptformer uses transformer architecture to capture cell-type-specific and disease-state-specific gene expression patterns, enabling precise analysis of gene behavior in relevant biological contexts. In Prism ToolSpace, we pre-inferenced the transcriptformer CGE (contextualized gene embeddings) across 5 single-cell disease atlas, while can be ealisy access and retrivel via this tool.

## Data Acquisition

### 1. Download Transcriptformer Embeddings

The Transcriptformer embeddings are hosted on Hugging Face at: https://huggingface.co/datasets/mims-harvard/ToolSpace

Use the following shell commands to download only the Transcriptformer files from the `transcriptformer_cge` directory:

```bash
# Install CLI if not already
uvx --from huggingface_hub hf

# Download only the transcriptformer_cge folder
uvx --from huggingface_hub hf download mims-harvard/ToolSpace \
  --repo-type dataset \
  --include "transcriptformer_cge/*" \
  --local-dir ./ToolSpace/
```

### File Structure

The Transcriptformer directory contains disease-specific embedding stores:

```
transcriptformer_cge/
├── follicular_lymphoma/
│   ├── metadata.json.gz
│   ├── b_cell_normal.npy
│   ├── b_cell_follicular_lymphoma.npy
│   ├── t_cell_normal.npy
│   ├── t_cell_follicular_lymphoma.npy
│   └── ... (other cell type × disease state combinations)
├── rheumatoid_arthritis/
├── type_1_diabetes_mellitus/
├── sjogren_syndrome/
└── hepatoblastoma/
```

### 2. Set Environment Variable

After downloading, set the `TRANSCRIPTFORMER_DATA_PATH` environment variable:

```bash
# Set environment variable to point to your data directory
export TRANSCRIPTFORMER_DATA_PATH="/path/to/ToolSpace"
```

## Tool Input and Output

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `disease` | string | Yes | Disease/dataset identifier (e.g., "follicular_lymphoma") |
| `state` | string | Yes | Disease state context ("normal", "disease_name", etc.) |
| `cell_type` | string | Yes | Cell type context for embeddings |
| `gene_names` | List[str] | Yes | Gene identifiers (symbols or Ensembl IDs) |

#### Supported Disease Contexts
Available disease datasets include:
- `follicular_lymphoma` - Follicular lymphoma vs normal tissue
- `rheumatoid_arthritis` - Rheumatoid arthritis vs healthy controls
- `type_1_diabetes_mellitus` - Type 1 diabetes vs normal pancreatic tissue
- `sjogren_syndrome` - Sjögren's syndrome vs healthy controls
- `hepatoblastoma` - Hepatoblastoma vs normal liver tissue

#### Disease State Options
- `normal` - Healthy/control condition
- `[disease_name]` - Disease-affected state (matches the disease identifier)


#### Gene Identifier Formats
- **Gene symbols**: `["TP53", "BRCA1", "EGFR", "MYC"]`
- **Ensembl IDs**: `["ENSG00000141510", "ENSG00000139618"]`
- **Mixed formats**: Supported in the same request
- **Request bound**: Supply 1 to 250 unique identifiers; bulk retrieval of all
  provider genes is intentionally disabled for bounded remote output.

### Output Format

The tool returns a JSON object with the following structure:

#### Successful Response
```json
{
  "embeddings": {
    "TP53": [0.1234, -0.5678, 0.9012, ...],
    "BRCA1": [-0.2345, 0.6789, -0.1234, ...],
    "EGFR": [0.3456, -0.7890, 0.2345, ...],
    "...": "..."
  },
  "context_info": [
    "Successfully retrieved 1247 gene embeddings for context: follicular_lymphoma - normal - b_cell",
    "Embedding dimensionality: 512 features per gene",
    "Disease context: follicular_lymphoma (validated and processed)"
  ]
}
```

#### Error Response
```json
{
  "error": "Disease 'unknown_disease' not found in available stores",
  "context_info": [
    "Available diseases: ['follicular_lymphoma', 'rheumatoid_arthritis', 'type_1_diabetes_mellitus', 'sjogren_syndrome', 'hepatoblastoma']",
    "Please check disease identifier and ensure data is downloaded"
  ]
}
```

### Embedding Properties

- **Dimensionality**: 512-dimensional vectors per gene
- **Format**: Dense numerical vectors (list of float32 values)
- **Context-specific**: Embeddings vary by cell type and disease state
- **Precision**: Float32 for optimal balance of accuracy and efficiency

## MCP Server Setup

### Prerequisites

```bash
# create a uv virtual enviroment
uv venv transcriptformer --python 3.10
source transcriptformer/bin/activate
uv pip install -r requirements.txt
```

### Configuration

1. **Set up the environment**:
```bash
# Ensure TRANSCRIPTFORMER_DATA_PATH points to your ToolSpace directory
export TRANSCRIPTFORMER_DATA_PATH="/path/to/ToolSpace"
```

2. **Verify embedding files exist**:
```bash
ls -la $TRANSCRIPTFORMER_DATA_PATH/transcriptformer_cge/
ls -la $TRANSCRIPTFORMER_DATA_PATH/transcriptformer_cge/follicular_lymphoma/
```

### Running the MCP Server

```bash
# Run the MCP server
python -m tooluniverse.remote.transcriptformer.transcriptformer_tool
```

### Server Configuration

- **Host**: `127.0.0.1` (loopback only)
- **Port**: `7000` (configured to avoid conflicts with other tools)
- **Transport**: `streamable-http`
- **Mode**: Stateless HTTP for scalability

Set `TOOLUNIVERSE_MCP_HOST` only for a reviewed direct network deployment. A
non-loopback bind requires `TOOLUNIVERSE_API_TOKEN`; the outbound Connect relay
does not require a public inbound port.
