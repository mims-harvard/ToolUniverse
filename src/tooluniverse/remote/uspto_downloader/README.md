# USPTO Downloader Tool Setup

## TOU validation and deployment status (2026-08-16)

> Boundary/parser tests and live loopback discovery passed; all three current calls reached USPTO and received HTTP 403 for an invalid validation key. No patent content was retrieved, so functional content retrieval, public publication, cross-user isolation, and extraction/load behavior remain credential-blocked or unmeasured. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operations: `get_abstract_from_patent_app_number`, `get_claims_from_patent_app_number`, `get_full_text_from_patent_app_number`
- Start: `python -m tooluniverse.remote.uspto_downloader.uspto_downloader_mcp_server`
- Endpoint: `http://127.0.0.1:8081/mcp`
- Provider configuration: set `USPTO_API_KEY` only in the provider environment; keep bounded OCR caches outside Git. Only approved USPTO HTTPS hosts are fetched.
- TOU check: `tu doctor --forward http://127.0.0.1:8081/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8081/mcp --name validation-uspto-downloader --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. HTTP 403 proves provider reachability only; it is not a functional content-retrieval pass.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation uspto-downloader`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-uspto-downloader-remote-tool/SKILL.md).

This guide sets up the MCP server for USPTO patent-document retrieval. It
extracts text from DOCX/PDF documents and uses CPU OCR only when a PDF has no
extractable text.

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
tu remote share uspto-downloader
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
tu remote share uspto-downloader --name my-uspto-downloader-remote --workers 1
```

Use `tu remote run uspto-downloader` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Overview

This directory contains the following MCP server implementation:
- **uspto_downloader_mcp_server.py**: Enables patent document downloading and processing from USPTO

## Prerequisites

### Hardware Requirements
- **CPU**: required; OCR can be expensive and must be concurrency-tested.
- **GPU**: not required by the current provider implementation.

### System Requirements
- Linux-based system (tested on Ubuntu/CentOS)
- Network access for API calls

## Setup Instructions

### 1. Environment Setup
```bash
conda create -n tooluniverse-env python=3.11 -c conda-forge -y
conda activate tooluniverse-env

```

### 2. Install ToolUniverse and MCP Dependencies

```bash
# Install compatible NumPy version first
pip install "numpy==2.0"

# Install ToolUniverse
git clone https://github.com/mims-harvard/ToolUniverse.git
cd ToolUniverse

python -m pip install . --no-cache-dir

# Install additional dependencies
pip install requests pymupdf easyocr python-docx Pillow pyarrow fastparquet lxml aiohttp
pip install -U sentence-transformers
```

### 4. Environment Configuration

#### Set Environment Variables
Set the USPTO credential only on the provider machine. Callers must never
supply or receive the provider API key.

```bash
# Provider process only
export USPTO_API_KEY="your-uspto-api-key"
```

If a legacy direct client uses `USPTO_MCP_SERVER_HOST`, set that host variable
on the client separately; do not copy `USPTO_API_KEY` to the client.

**Finding your GPU hostname:**
```bash
# Get current hostname by running this command on the GPU where your MCP server will run.
hostname

# Example hostnames:
# - gpu-node-01
# - compute-a100-001.cluster.edu
# - localhost (if running locally)
```

## Running the MCP Servers

### 1. Start USPTO MCP Server

```bash
# Loopback is the safe default and is suitable for a local Connect relay.
python -m tooluniverse.remote.uspto_downloader.uspto_downloader_mcp_server

# Direct network exposure requires bearer authentication.
TOOLUNIVERSE_API_TOKEN="<provider-secret>" \
TOOLUNIVERSE_MCP_HOST="0.0.0.0" \
python -m tooluniverse.remote.uspto_downloader.uspto_downloader_mcp_server
```

The server starts on `http://127.0.0.1:8081` by default. A non-loopback bind
is refused unless `TOOLUNIVERSE_API_TOKEN` is set.

## Usage Examples
For comprehensive usage examples and testing patterns, please refer to the test file:

```bash
# View MCP tool usage examples
cat ToolUniverse/src/tooluniverse/test/test_mcp_tool.py
```

This test file contains detailed examples of how to interact with the USPTO patent downloader MCP server, including proper API calls and parameter formatting.
