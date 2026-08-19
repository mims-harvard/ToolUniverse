---
name: setup-harmony-remote-tool
description: Set up, launch, validate, and troubleshoot the Harmony ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up Harmony as a remote tool

> Validation status (2026-08-16): Harmony 2.0, loopback discovery/call, and invalid-input checks passed; the current deterministic two-batch call returned an aligned finite 240 x 10 embedding. Public publication, cross-user isolation, representative correction accuracy, broad concurrency, and recovery remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- CPU is normally sufficient; size RAM for the expression matrix.
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation harmony
~~~

After exporting provider resources, add `--check-provider-env`. After the
server starts, add `--live` to verify the exact MCP tool set without running
the model. Before sharing, add `--check-connect-prereqs`; this reports only
whether a key is set and never prints its value.

## Create an isolated environment

~~~bash
python3 -m venv .venvs/harmony
. .venvs/harmony/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r src/tooluniverse/remote/harmony/requirements.txt
~~~

The clean-install commands passed in the validation workspace; rerun them on the deployment host and retain the resulting lock/install evidence.

## Obtain credentials, data, and model weights

- Set TOOLUNIVERSE_REMOTE_DATA_ROOT. batch_key must exist in obs; verify dataset rights.

## Authorize once, then share with one short command

After installing dependencies, exporting the provider resources above, and
installing the pinned relay SDK described under Connect below, run from the
repository root. Log in only once per machine (and again after key
rotation):

~~~bash
tu remote login
# Or import an existing protected 0600 file without sourcing it:
tu remote login --env-file /path/to/tooluniverse-service.env
~~~

Then each private share is one short command:

~~~bash
tu remote share harmony
~~~

By default, `tu remote login` requests a short-lived device code, opens the
TU Platform approval page, and polls until the signed-in user approves. No key
copy/paste is required. On a headless machine, add `--no-browser` and open the
printed link elsewhere. The CLI exchanges the approval for a computer-only key,
verifies `/remote-servers/preflight`, stores it in a local 0600 config file, and
never displays it.

The share command runs environment and TU Platform preflights, starts or reuses
the exact loopback endpoint, validates discovery, and keeps the relay in the
foreground until Ctrl-C. It automatically uses the reviewed Python, name,
and worker count. Override them only when needed:

~~~bash
tu remote share harmony --name my-harmony-remote --workers 1
~~~

Use `tu remote check harmony` for a non-sharing readiness check and
`tu remote run harmony` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
mkdir -p caches/harmony runs/harmony
python -m tooluniverse.remote.harmony.harmony_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8026/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8026/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains run_harmony_integrate; stop on empty, duplicate, or schema-drifted discovery.

## Connect to ToolUniverse Connect

The pinned `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed immutable GitHub revision below. Interactive sharing uses browser device authorization; no key copy/paste or private-repository access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ git+https://github.com/tooluniverse/tuplatform.git@6da7a8d8ee13423a27787642ccad6987f04a0786#subdirectory=sdk/tuplatform-connect"
tu doctor --forward http://127.0.0.1:8026/mcp --json
tu serve --share --forward http://127.0.0.1:8026/mcp --name validation-harmony --workers 1
~~~

Prefer browser device authorization. For CI or migration, supply
`TOOLUNIVERSE_SERVICE_KEY` only through a protected environment or use
`tu remote login --manual-key`; never put a key in shell arguments.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. All imports remained unpublished owner drafts and were invoked through `/expert-sessions/{id}/test`. This implementation's draft(s) used a 120-second timeout and remote max concurrency 1.

Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

## Run a verified example

Operation: run_harmony_integrate

~~~json
{"adata_path":"tiny.h5ad","batch_key":"batch","n_pcs":2}
~~~

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads('''{"adata_path":"tiny.h5ad","batch_key":"batch","n_pcs":2}''')
    async with Client("http://127.0.0.1:8026/mcp") as client:
        result = await client.call_tool("run_harmony_integrate", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: n_cells, n_pcs, batch metadata, and a bounded corrected_embedding. The validation fixture returned a finite 300 x 10 embedding across two batches; treat this as runtime/transport evidence, not representative batch-correction accuracy. Check scientific meaning, output bounds, invalid-input behavior, and absence of paths, secrets, and traces on deployment data.

## Tune GPU and concurrency

- Use one worker as a conservative, unmeasured default.
- Measure cold start, two warm calls, then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Import/executable failure: reactivate the isolated environment and reinstall its requirements.
- Missing artifact: inspect provider-only environment variables and approved relative files; never accept arbitrary caller model paths.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-harmony`.
- Revoke temporary keys. After confirmation, remove only .venvs/harmony, caches/harmony, and runs/harmony; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
