# USPTO Downloader Tool Setup

This guide explains how to deploy the MCP (Model Context Protocol) server for USPTO patent document downloading. Word documents and PDFs with an existing text layer do not use the GPU. Scanned PDFs fall back to GPU-backed optical character recognition (OCR).

## Overview

This directory contains:
- **uspto_downloader_mcp_server.py**: FastMCP server exposing the downloader tools
- **uspto_downloader_tool.py**: USPTO document download and text extraction implementation
- **requirements.txt**: Dependencies for this separately deployed server

## Prerequisites

### Hardware Requirements
- **GPU**: NVIDIA A100 or H100 GPU recommended

### System Requirements
- Linux-based system (tested on Ubuntu/CentOS)
- CUDA-compatible GPU drivers
- Network access for API calls

## Setup Instructions

### 1. Environment Setup
```bash
conda create -n tooluniverse-env python=3.11 -c conda-forge -y
conda activate tooluniverse-env

# Verify CUDA support
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### 2. Install ToolUniverse and Server Dependencies

```bash
# Install ToolUniverse
git clone https://github.com/mims-harvard/ToolUniverse.git
cd ToolUniverse

python -m pip install . --no-cache-dir

# Install a CUDA-compatible PyTorch build for this machine first. Follow the
# command generated at https://pytorch.org/get-started/locally/.

# Install only the dependencies owned by this remote service
python -m pip install -r src/tooluniverse/remote/uspto_downloader/requirements.txt
```

PyMuPDF is dual-licensed under AGPL-3.0 or a commercial Artifex license. Confirm that your deployment complies with the applicable license.

### 3. Environment Configuration

Set the USPTO API key on the **GPU server** before starting the MCP service:

```bash
export USPTO_API_KEY="your-uspto-api-key"
```

For a deployment on a trusted private network, set a shared Bearer token on
both the server and the ToolUniverse client. The USPTO loader sends this token
only to its configured MCP server:

```bash
export TOOLUNIVERSE_API_TOKEN="a-long-random-token"
```

When this variable is unset, the server remains unauthenticated for backward
compatibility.

The built-in loader uses plain HTTP, so do not expose port 8081 directly to the
public internet. Use a private network or a secure tunnel that provides a local
endpoint.

Set the server hostname on the **ToolUniverse client**. Supply only a hostname or IP address; the ToolUniverse configuration adds `http://`, port `8081`, and `/mcp`:

```bash
export USPTO_MCP_SERVER_HOST="your-gpu-hostname"
```

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

```bash
python -m tooluniverse.remote.uspto_downloader.uspto_downloader_mcp_server
```

The server listens on `http://0.0.0.0:8081/mcp` and is accessible to the client as `http://your-gpu-hostname:8081/mcp`.

## Usage Examples
When `USPTO_MCP_SERVER_HOST` is set, `mcp_auto_loader_uspto_downloader` discovers the three server tools and registers them locally as `mcp_get_abstract_from_patent_app_number`, `mcp_get_claims_from_patent_app_number`, and `mcp_get_full_text_from_patent_app_number`.

```bash
python scripts/test_new_tools.py uspto_downloader -v
```

The repository test suite covers server import, Word extraction, searchable-PDF extraction, per-page OCR fallback selection, authentication, and retrying alternative document versions. The OCR result itself must still be validated on the target GPU deployment.
