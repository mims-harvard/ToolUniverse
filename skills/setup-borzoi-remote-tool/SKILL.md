---
name: setup-borzoi-remote-tool
description: Set up, launch, validate, and troubleshoot the Borzoi ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up Borzoi as a remote tool

> Validation status (2026-08-16): a fresh Python 3.12 service environment resolved borzoi-pytorch 0.4.4 with its supported Transformers 4.50.3 dependency, loaded official weights on the GB10, and returned bounded finite prediction and variant-effect results through a strict loopback TOU endpoint. Four concurrent fixture calls also passed with serialized model access. NVIDIA's aarch64 cusparselt wheel still reports incompatible platform metadata in `uv pip check`; public publication, cross-user isolation, saturation, recovery, and biological accuracy remain incomplete, so keep this private. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- GPU recommended; CPU only for small checks.
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation borzoi
~~~

After exporting provider resources, add `--check-provider-env`. After the
server starts, add `--live` to verify the exact MCP tool set without running
the model. Before sharing, add `--check-connect-prereqs`; this reports only
whether a key is set and never prints its value.

## Create an isolated environment

~~~bash
python3 -m venv .venvs/borzoi
. .venvs/borzoi/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r src/tooluniverse/remote/borzoi/requirements.txt
~~~

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain credentials, data, and model weights

- Keep HF_HOME and TORCH_HOME below caches/borzoi. The provider selects the model; review model/output licenses.

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
tu remote share borzoi
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
tu remote share borzoi --name my-borzoi-remote --workers 1
~~~

Use `tu remote check borzoi` for a non-sharing readiness check and
`tu remote run borzoi` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
mkdir -p caches/borzoi runs/borzoi
python -m tooluniverse.remote.borzoi.borzoi_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8012/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8012/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains run_borzoi_predict; stop on empty, duplicate, or schema-drifted discovery.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8012/mcp --json
tu serve --share --forward http://127.0.0.1:8012/mcp --name validation-borzoi --workers 1
~~~

Prefer browser device authorization. For CI or migration, supply
`TOOLUNIVERSE_SERVICE_KEY` only through a protected environment or use
`tu remote login --manual-key`; never put a key in shell arguments.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. All imports remained unpublished owner drafts and were invoked through `/expert-sessions/{id}/test`. This implementation's draft(s) used a 120-second timeout and remote max concurrency 1.

Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

## Run a verified example

Operation: run_borzoi_predict

~~~json
{"sequence":"ACGTACGT","top_n":1}
~~~

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads('''{"sequence":"ACGTACGT","top_n":1}''')
    async with Client("http://127.0.0.1:8012/mcp") as client:
        result = await client.call_tool("run_borzoi_predict", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: model, organism, n_tracks, and a bounded tracks array. Check scientific meaning, finite values, output bounds, invalid-input behavior, and absence of paths, secrets, and traces. The success path is source-checked but not runtime-verified here unless the status note explicitly says otherwise.

## Tune GPU and concurrency

- Use one worker as a conservative, unmeasured default.
- Measure cold start, two warm calls, then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Import/executable failure: reactivate the isolated environment and reinstall its requirements.
- Missing artifact: inspect provider-only environment variables and approved relative files; never accept arbitrary caller model paths.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-borzoi`.
- Revoke temporary keys. After confirmation, remove only .venvs/borzoi, caches/borzoi, and runs/borzoi; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
