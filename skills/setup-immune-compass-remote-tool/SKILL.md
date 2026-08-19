---
name: setup-immune-compass-remote-tool
description: Set up, launch, validate, and troubleshoot the immune COMPASS ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up immune COMPASS as a remote tool

> Validation status (2026-08-16): working CPU deployment. The live MCP call ran the official all-cohort COMPASS checkpoint, converted to safetensors plus data-only preprocessing, on the official GIDE sample. In the pinned `torch==2.10.0` environment, the safe artifact and upstream checkpoint had zero difference in both class probabilities and all 44 concept scores. This is execution-equivalence evidence, not a clinical-accuracy benchmark. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- The validated deployment uses CPU. GPU availability alone does not justify changing the device without a separate equivalence and resource test.
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation immune-compass
~~~

After exporting provider resources, add `--check-provider-env`. After the
server starts, add `--live` to verify the exact MCP tool set without running
the model. Before sharing, add `--check-connect-prereqs`; this reports only
whether a key is set and never prints its value.

## Create an isolated environment

~~~bash
python3 -m venv .venvs/immune-compass
. .venvs/immune-compass/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r src/tooluniverse/remote/immune_compass/requirements.txt
~~~

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain data and provision safe model weights

- Obtain the official COMPASS source/checkpoint and confirm model/data terms. The validated source revision is `0e5c87665247e3a300f28282c8bbcc14e26973bd`; `example/model/finetuner_pft_all.pt` has SHA-256 `fc83d7b5eac3697bcd9d117acefa35b56cf4c4c3c5880de367c85a870aef4b0b`.
- In an isolated provisioning environment only, convert that reviewed whole-object checkpoint:

~~~bash
python src/tooluniverse/remote/immune_compass/convert_checkpoint.py \
  caches/compass/source/finetuner_pft_all.pt \
  caches/compass/safe-model \
  --expected-sha256 fc83d7b5eac3697bcd9d117acefa35b56cf4c4c3c5880de367c85a870aef4b0b \
  --upstream-revision 0e5c87665247e3a300f28282c8bbcc14e26973bd
export COMPASS_SAFE_MODEL_DIR="$PWD/caches/compass/safe-model"
~~~

The live server must never call `torch.load` or `loadcompass`. It verifies the emitted digests and loads only safetensors, JSON metadata, and an `allow_pickle=False` preprocessing NPZ.

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
tu remote share immune-compass
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
tu remote share immune-compass --name my-immune-compass-remote --workers 1
~~~

Use `tu remote check immune-compass` for a non-sharing readiness check and
`tu remote run immune-compass` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
mkdir -p caches/immune-compass runs/immune-compass
export COMPASS_SAFE_MODEL_DIR="$PWD/caches/compass/safe-model"
export COMPASS_DEVICE=cpu
python -m tooluniverse.remote.immune_compass.compass_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:7003/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:7003/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains run_compass_prediction; stop on empty, duplicate, or schema-drifted discovery.

## Connect to ToolUniverse Connect

The pinned `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed immutable GitHub revision below. Interactive sharing uses browser device authorization; no key copy/paste or private-repository access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ git+https://github.com/tooluniverse/tuplatform.git@6da7a8d8ee13423a27787642ccad6987f04a0786#subdirectory=sdk/tuplatform-connect"
tu doctor --forward http://127.0.0.1:7003/mcp --json
tu serve --share --forward http://127.0.0.1:7003/mcp --name validation-immune-compass --workers 1
~~~

Prefer browser device authorization. For CI or migration, supply
`TOOLUNIVERSE_SERVICE_KEY` only through a protected environment or use
`tu remote login --manual-key`; never put a key in shell arguments.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. All imports remained unpublished owner drafts and were invoked through `/expert-sessions/{id}/test`. This implementation's draft(s) used a 120-second timeout and remote max concurrency 1.

Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

## Run a verified example

Operation: run_compass_prediction

~~~json
{"gene_expression_data_path":"compass_gide_official_sample_1.tsv","threshold":0.5}
~~~

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads('''{"gene_expression_data_path":"compass_gide_official_sample_1.tsv","threshold":0.5}''')
    async with Client("http://127.0.0.1:7003/mcp") as client:
        result = await client.call_tool("run_compass_prediction", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: a finite `responder_probability`, the applied `threshold`, `is_responder`, at most 44 finite ranked `top_concepts`, and model provenance containing `artifact_format=compass-safe-v1`, the pinned source digest/revision, and device. The validated official sample returned a non-responder probability of approximately `1.2848061e-20` and ranked `Mast` first. This is not a clinical-validity claim.

## Tune GPU and concurrency

- Use one worker as a conservative, unmeasured default.
- Measure cold start, two warm calls, then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Import/executable failure: reactivate the isolated environment and reinstall its requirements.
- Missing artifact: inspect provider-only environment variables and approved relative files; never accept arbitrary caller model paths.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-immune-compass`.
- Revoke temporary keys. After confirmation, remove only .venvs/immune-compass, caches/immune-compass, and runs/immune-compass; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
