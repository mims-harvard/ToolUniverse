# Boltz2 Tool Setup

This tutorial will Tutorial you through setting up and running MCP (Model Context Protocol) server-based tools for Boltz2 molecular docking.

## Overview

This directory contains the following MCP server implementations:
- **boltz_MCP.py**: Provides molecular docking capabilities using Boltz2

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
# Start the Boltz2 MCP server on the GPU where you want it to run.
python path/to/boltz_mcp_server.py
```

The server will start on `http://0.0.0.0:8080` but will be accessible via your GPU hostname (e.g., `http://your-gpu-hostname:8080`) and provide molecular docking capabilities.

## Usage Examples
For an example Boltz-2 tool call, please refer to the following examples file:

```bash
# View MCP tool usage examples
cat ToolUniverse/examples/mcp/mcp_tool_example.py
```

This test file contains a detailed example of how to interact with the Boltz2 molecular docking MCP server, including proper parameter formatting. For more details on how to use the Boltz2 prediction parameters, check out: `https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md`.
