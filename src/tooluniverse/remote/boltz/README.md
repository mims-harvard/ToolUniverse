# Boltz2 Tool Setup

## TOU validation and deployment status (2026-08-16)

> Boltz 2.2.1 and the official checkpoints ran on the NVIDIA GB10 in one repaired direct MCP call and three authenticated Platform calls, each returning six finite affinity values in 63.6-66.5 seconds. The upstream MSA service timed out during validation, so those successful calls explicitly used bounded single-sequence mode. Missing, oversized, malformed, or non-finite affinity artifacts now fail closed. Public publication, cross-user isolation, broad concurrency, recovery, biological accuracy, and the live MSA path remain unvalidated; keep this deployment private.

- Operation: `boltz2_docking`
- Start: `python -m tooluniverse.remote.boltz.boltz_mcp_server`
- Endpoint: `http://127.0.0.1:8080/mcp`
- Provider configuration: keep Boltz/model caches outside Git. `use_msa_server=true` requires the upstream MSA service; set `use_msa_server=false` only when the documented lower-quality single-sequence mode is acceptable. Use one worker until broader GPU load and recovery are measured.
- TOU check: `tu doctor --forward http://127.0.0.1:8080/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8080/mcp --name validation-boltz --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation boltz`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-boltz-remote-tool/SKILL.md).

This tutorial will Tutorial you through setting up and running MCP (Model Context Protocol) server-based tools for Boltz2 molecular docking.

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
tu remote share boltz
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
tu remote share boltz --name my-boltz-remote --workers 1
```

Use `tu remote run boltz` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Overview

This directory contains the following MCP server implementations:
- **boltz_MCP.py**: Provides molecular docking capabilities using Boltz2

## Prerequisites

### Hardware Requirements
- **GPU**: a CUDA-capable GPU is strongly recommended; measure memory and
  concurrency with the model/input sizes used by your deployment.

### System Requirements
- Linux-based system (tested on Ubuntu/CentOS)
- CUDA-compatible GPU drivers
- Network access for API calls

## Setup Instructions

### 1. Environment Setup
```bash
# Create and activate conda environment for Boltz2
conda create -n tooluniverse-env python=3.11 -c conda-forge -y
conda activate tooluniverse-env

# Navigate to the Boltz repository
git clone https://github.com/jwohlwend/boltz.git
cd boltz

# Install Boltz2 in editable mode with CUDA support
pip install -e ".[cuda]"
```

### 2. Verify Boltz2 Installation

```bash
# Test Boltz2 installation
python -c "import boltz; print('Boltz2 installed successfully')"

# Verify CUDA support
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### 3. Install ToolUniverse and MCP Dependencies

```bash
# Return to parent directory from boltz subdirectory
cd ..
```

```bash
# Install compatible NumPy version first
pip install "numpy==2.0"

# Install ToolUniverse
git clone https://github.com/mims-harvard/ToolUniverse.git
cd ToolUniverse

python -m pip install . --no-cache-dir

# Install additional dependencies
pip install pyarrow fastparquet lxml
pip install -U sentence-transformers
```

### 4. Environment Configuration

#### Set Environment Variables
Set the required environment variables on the **client machine** where you're calling the MCP tool from ToolUniverse (not on the GPU server where the tool is running):

```bash
# For Boltz2 server (running on port 8080)
export BOLTZ_MCP_SERVER_HOST="your-gpu-hostname"
```

**Important**: Set this variable on the machine where you're executing your ToolUniverse code, even if the MCP server is running on a different GPU machine.

**Finding your GPU hostname:**
```bash
# Get current hostname by running this command on the GPU where your MCP server will run.
hostname

# Example hostnames:
# - gpu-node-01
# - compute-a100-001.cluster.edu
# - localhost (if running locally)
```

## Running the MCP Server

### 1. Start Boltz2 MCP Server

```bash
# Loopback is the safe default and is suitable for a local Connect relay.
python -m tooluniverse.remote.boltz.boltz_mcp_server

# Direct network exposure requires bearer authentication.
TOOLUNIVERSE_API_TOKEN="<provider-secret>" \
TOOLUNIVERSE_MCP_HOST="0.0.0.0" \
python -m tooluniverse.remote.boltz.boltz_mcp_server
```

The server starts on `http://127.0.0.1:8080` by default. A non-loopback bind
is refused unless `TOOLUNIVERSE_API_TOKEN` is set. Boltz runs locally and
does not require `NVIDIA_API_KEY`; its optional MSA service does require
provider network access.

## Usage Examples
For comprehensive usage examples and testing patterns, please refer to the test file:

```bash
# View MCP tool usage examples
cat ToolUniverse/src/tooluniverse/test/test_mcp_tool.py
```

This test file contains detailed examples of how to interact with the Boltz2 molecular docking MCP servers, including proper API calls and parameter formatting.
