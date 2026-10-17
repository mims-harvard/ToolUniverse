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

### One command

```bash
export TOOLUNIVERSE_BOLTZ_PYTHON=~/boltz2-venv/bin/python   # where the model's own environment is
export BOLTZ_CACHE=~/.boltz                                 # where its weights are

tu remote setup boltz
```

Five steps, each idempotent — a re-run reports `present` for what is already
done and continues from wherever the last one stopped:

| | |
| --- | --- |
| **preflight** | driver, compute capability, a compiler for Triton, free disk. Refused here costs a second, not 16 GB. |
| **environment** | installs `environment/requirements.lock` into the interpreter above, `--no-deps`. It does not create the venv: see below. |
| **kit** | clones the pinned commit of the optimization kit into `~/.cache/tooluniverse/kits/<repo>@<sha>/`, refuses a modified tree, runs the kit's own install — which fetches the weights through upstream's downloader. |
| **weights** | every declared file re-read and compared to its SHA-256. |
| **smoke** | one real prediction under a deadline, recorded in `~/.cache/tooluniverse/measured/boltz.json`. |

Then:

```bash
tu remote check boltz     # what will engage on this machine
tu remote run   boltz     # serve it
```

### Running it in a container instead

The stack can be a venv, a Docker image or an Apptainer `.sif`, and the choice
changes one thing: the argv that starts the worker. Same script, same model,
same socket.

```toml
[env]
kind = "docker"
image = "tu-boltz2-kit:f4f62fa"
work_root = "/srv/tooluniverse/work"      # required: see below
```

`tu remote setup boltz` then builds the image from the kit's own
`environment/Dockerfile` and everything else is unchanged.

All three routes were measured here on the same input and the same card:

| route | one prediction | peak reserved |
| --- | --- | --- |
| venv | 15 s | 3.21 GiB |
| docker | 13 s | 3.21 GiB |
| apptainer | 22 s | 3.21 GiB |

The identical peak is the useful number: it says the three are running the same
model on the same stack, rather than three things that merely all finish.

Two things a container needs that a venv does not. `work_root` must be
declared, because a per-request output path the caller invents is not visible
inside unless something bound it. And the container is run as you rather than
as root, so it is given a synthetic two-line `passwd`, a home of its own, and
writable compiler caches — the host's `passwd` would expose every account on
the machine, and without the rest numba, Triton and Boltz-2's own parsing
zygote each fail in their own way.

For Apptainer, `[env] sif` names the image instead:

```toml
[env]
kind = "apptainer"
sif = "~/sif/boltz2-kit.sif"
work_root = "/srv/tooluniverse/work"
```

Its build needs privilege once and its run needs none, which is the point of
the route rather than a wart: a `.def` with a `%post` runs commands inside the
image, needing fakeroot, needing unprivileged user namespaces — and Ubuntu
24.04 ships `kernel.apparmor_restrict_unprivileged_userns=1`, so `unshare
--user` is denied even with `subuid`/`subgid` configured. So an administrator
builds the `.sif` once on a machine with Docker, and everyone else runs it
unprivileged, as themselves. That is also why Apptainer needs none of the
`--user`, synthetic `passwd` and container-home machinery Docker does.

`kind = "apptainer"` covers both Apptainer (Linux Foundation, 1.x) and
SingularityCE (Sylabs, 4.x) — forks of one project, and the kits' own `.def`
headers read "Apptainer / Singularity". Whichever is on `PATH` is used. What
was measured here was SingularityCE 4.1.1, because Ubuntu 24.04 packages that
one and upstream Apptainer publishes no aarch64 build.

### The one thing setup does not do

It installs into an interpreter, it does not build one — the outcome is what
matters, and uv, `python -m venv`, conda and pixi all reach it. If
`TOOLUNIVERSE_BOLTZ_PYTHON` is unset, setup refuses and prints the recipe. The
short version, with the full one in the lock file's own header:

```bash
uv venv --seed --managed-python --python 3.11.12 ~/boltz2-venv
export TOOLUNIVERSE_BOLTZ_PYTHON=~/boltz2-venv/bin/python
```

This environment is **not** ToolUniverse's and must not be installed into it:
torch 2.12.0+cu130, triton 3.7.0 and numpy 1.26.4 do not coexist with the rest
of the package. That separation is why the MCP server talks to the model over a
socket instead of importing it.

### What `setup` cannot promise

The bytes are deterministic and the host checks are exhaustive, but whether a
model *runs well* on an unseen card is not knowable before it runs. Three of the
four problems this provider hit on its first machine appeared only at run time,
and one of them presented as a stall. That is what the smoke step is for, and
why its record — not `provider.toml`'s numbers — is what a scheduler should
read. `provider.toml` says what was measured elsewhere; the record says what
this machine did.

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
