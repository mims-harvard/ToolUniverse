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

Two processes, in two environments, on purpose.

```
agent ──MCP──> boltz_mcp_server.py          ToolUniverse's environment, CPU only
                      │
                      │  Unix socket, one request at a time
                      ▼
               resident/boltz_resident_worker.py   the model's own environment
                 run under the optimization kit's worker_launch;
                 Boltz-2 built once and held on the GPU
```

They are separated because their pinned stacks conflict: the model needs torch
2.12.0+cu130, triton 3.7.0 and numpy 1.26.4, which ToolUniverse cannot install
alongside the rest of its 600+ tools. `provider.toml` in this directory declares
the split, the weights and their digests, the measured device budget, and what
the deployment can and cannot isolate.

Holding the model is what makes it fast. Measured here (330-residue protein +
aspirin with an affinity pass, NVIDIA GB10):

| | per request |
| --- | --- |
| `boltz predict` in a subprocess, as this tool used to run it | 110 s |
| optimization kit `--mode fast`, a fresh worker per call | 102 s |
| **this worker, held, steady state** | **~54 s** |

Most of that is not the kit's kernels -- they are worth ~8 % on this card, and
three of its levers decline by name on compute capability 12.1 -- but the
holding: the structure pass alone falls from ~23 s to 5.8 s, because CUDA graphs
captured on one request are replayed on the next, which a worker that exits
after every call can never collect. Outputs are bit-for-bit those of
`run.sh pred --mode fast`: structure mean |dCA| 0.000 A, affinity identical.

If no resident worker is configured, the tool runs `boltz predict` in a
subprocess exactly as before. That path is slower, not different.

## Prerequisites

### Hardware Requirements
- A CUDA-capable GPU with at least the `vram_budget_gb` in `provider.toml`
  (5.54 GiB measured peak) free, plus head-room for anything sharing the card.
- An NVIDIA driver of the 580 series or newer (the pinned stack is CUDA 13.0).
- No CUDA toolkit: the CUDA libraries are wheels in the lock file.

### System Requirements
- Linux. A C compiler on `PATH` in the model environment (Triton compiles the
  kit's kernels at first use).
- Python 3.11 for the model environment; ToolUniverse's own may differ.

## Setup Instructions

### 1. Build the model's environment

This environment is **not** ToolUniverse's and must not be installed into it.
`environment/requirements.lock` is the exact stack the numbers above were
measured on; its header carries the full recipe. In short:

```bash
uv venv --seed --managed-python --python 3.11.12 ~/boltz2-venv
. ~/boltz2-venv/bin/activate
cd src/tooluniverse/remote/boltz/environment
grep -E '^(pip|wheel)==' requirements.lock > /tmp/pip.txt
python -m pip install --no-deps -r /tmp/pip.txt
printf 'setuptools==82.0.1\n' > /tmp/bc.txt
grep -v -E '^(#|pip==|wheel==)' requirements.lock > /tmp/stack.txt
python -m pip install --no-deps --build-constraint /tmp/bc.txt -r /tmp/stack.txt
export LD_LIBRARY_PATH=$(python -c 'import site; print(site.getsitepackages()[0])')/nvidia/cu13/lib
```

`--no-deps` is deliberate: the list is complete, and letting a resolver
re-derive it is how a stack stops being the one that was measured.

### 2. Install the optimization kit into it

```bash
git clone https://github.com/anthropics/uplifting-biomolecular-modeling
cd uplifting-biomolecular-modeling/boltz2
bash run.sh install --weights ~/.boltz     # also fetches and digest-checks the cache
```

The commit this provider was verified against is in `provider.toml` under
`[kit]`. Nothing in the kit is patched or vendored: the resident worker is
simply a different script in the position the kit's own batch worker occupies,
so its import hooks attach the levers of `--mode fast` to the model the worker
builds. 25 of the 28 arrive that way.

### 3. Point ToolUniverse at it

```bash
export TOOLUNIVERSE_BOLTZ_PYTHON=~/boltz2-venv/bin/python
export BOLTZ_CACHE=~/.boltz
# Optional: keep compiled Triton kernels across worker restarts. Worth ~22 s on
# the first request after one.
export MODEL_OPT_JIT_ROOT=~/.cache/tooluniverse/boltz-jit
```

Then check the whole deployment, both environments and the weights, in one
command:

```bash
tu remote check boltz
```

```
✓ implementation: boltz
  manifest: mode=resident vram_budget=5.54 GiB isolation=process
  weights: 4/4 at their pins under /home/you/.boltz
  ✓ model environment: /home/you/boltz2-venv/bin/python
    command boltz: yes
    module boltz2_opt: yes
    GPU: NVIDIA GB10 (cc 12.1, torch 2.12.0+cu130)
    CUDA tensor check: passed
```

The weights check is not ceremony. A `boltz2_conf.ckpt` on this box was once a
28.5 MB truncation of a 2,286 MB file and served predictions from it for over a
month, because nothing compared it to anything.

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

### Turning the resident worker off

`TOOLUNIVERSE_BOLTZ_RESIDENT=0` forces the subprocess path. The tool also falls
back to it on its own, logging the reason, whenever the worker cannot start.

### Giving the GPU back

The worker retires after `idle_timeout_s` (15 minutes) with no requests, so a
provider nobody is calling stops occupying the card. It also exits on its own if
the MCP server that started it dies without stopping it -- being reparented to
init, plus two minutes idle, is the signal.

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
