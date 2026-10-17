---
name: setup-openfold3_ob0-remote-tool
description: Set up, launch, validate, and troubleshoot the OpenFold3 OpenBind-0 ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up OpenFold3 (OpenBind-0) as a remote tool

> Validation status (2026-10-01): OpenFold3 0.5.0 with the OpenBind-0 parameters, under the optimization kit's `fast` mode, ran on the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) with `pair_transition` ablated through the kit's own MODEL_OPT_LEVERS_OFF door, the kit's `post_release` gate forced on every item, and the data loader forced to 0 workers. All five `tu remote setup` steps green. Verified on the whole acceptance sequence, not a single smoke: an ascending 100/200/400-residue ladder (3/3), a mixed-shape sequence 100/100/200/100 (4/4), FOUR CONSECUTIVE IDENTICAL REQUESTS (4/4), and three consecutive 800-residue requests (3/3) -- five mmCIF models every time. TWO independent second-request defects had to be fixed first, one in the kit's shared core and one in upstream 0.5.0 itself, and only one of them was findable by repeating a shape. Peak reserved 2.20 GiB at 35 residues rising to 9.97 GiB at 800, which is the declared budget and the ceiling the tool enforces. Wall times were taken with one to three other providers' workers on the card and are not measurements; residency returns 1.25x at 35 residues and 1.13x at the 800-residue budget row against a fresh process per request, because ~30 s of each request is Lightning and featurisation rather than the model. Public publication, cross-user isolation, concurrency, recovery and biological accuracy are untested; keep this deployment private.

## Which OpenFold3 this is

The parameters are **OpenBind-0** (`of3-ob-2025-06-30-174k.pt`, registry name
`openbind-2025-06-30-174k`) and the upstream is **OpenFold3 0.5.0**. The
`openfold3` provider on port 8039 is 0.4.1 with the `of3-p2-155k.pt`
"preview-2" parameters. They are not two configurations of one thing:

- upstream version-gates every checkpoint, and OpenBind-0 declares
  `version_compatibility = ">=0.5.0"` while the preview checkpoints declare
  `">=0.4,<0.4.4dev0"` and are listed in `LEGACY_CHECKPOINTS`, which 0.5.0
  refuses to download;
- both releases are the same PyPI distribution, `openfold3`, so one
  interpreter holds one of them, and each optimization kit installs an
  autoload `.pth` whose hook refuses to share a process with the other's.

So this provider has its own environment, its own weights and its own port.
Running both at once is supported and costs two environments.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required. This provider holds its model resident between requests; CPU is not a target.
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation openfold3_ob0
~~~

After exporting provider resources, add `--check-provider-env`. After the
server starts, add `--live` to verify the exact MCP tool set without running
the model. Before sharing, add `--check-connect-prereqs`; this reports only
whether a key is set and never prints its value.

## Create the two environments

This provider is on the remote-tool standard, so it has two environments, not
one: the MCP server runs in ToolUniverse's, and the model runs in its own,
built from a pinned lock. They cannot import each other, and that is the point
-- the model's stack is not installable beside ToolUniverse's.

~~~bash
python3 -m venv .venvs/openfold3_ob0
. .venvs/openfold3_ob0/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_OPENFOLD3_OB0_PYTHON` names,
and nothing above creates it. **Create it with the standard library's `venv`
module, not with `uv venv`** -- this provider's lock header says so and the
reason is not cosmetic: `uv venv` seeds a `_virtualenv.pth` that puts a class
named `_Finder` on `sys.meta_path`, the kit reads that as a rival kit hook,
and every mode then refuses with "a kit hook is already installed in this
process".

~~~bash
"$(uv python find --managed-python 3.11)" -m venv ~/openfold3_ob0-venv
~~~

`tu remote setup --only environment` fills it from
`src/tooluniverse/remote/openfold3_ob0/environment/requirements.lock`
with `--no-deps`, so no version is silently resolved to something else.

The rest is built by `tu remote setup`, which reads
`src/tooluniverse/remote/openfold3_ob0/provider.toml` and runs five steps:
preflight, environment, kit, weights, smoke. Each refuses by name and carries
its fix.

~~~bash
export TOOLUNIVERSE_OPENFOLD3_OB0_PYTHON=~/openfold3_ob0-venv/bin/python
tu remote setup openfold3_ob0
~~~

Run one step at a time with `--only preflight|environment|kit|weights|smoke`
while bringing a machine up. The smoke step is the one that matters: it holds
the model, sends one request, asserts the provider produced what its manifest
says a successful run produces, and records the measured peak VRAM to
`~/.cache/tooluniverse/measured/openfold3_ob0.json`. A host schedules on that
file, not on the manifest.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain credentials, data, and model weights

- The weights are public: upstream's unsigned S3 bucket, fetched by the kit's own downloader through upstream's own client, then hashed. No credential and no licence acceptance. Upstream states no licence for the parameters themselves; the code and repository are Apache-2.0.
- Nothing is fetched at request time. The manifest declares the checkpoint with its size and sha256, and the launch refuses if it is off its pin.
- The kit step also places upstream's **full** Chemical Component Dictionary (`components.bcif`, 63,393,643 bytes) over the subset `biotite` ships inside its own package directory. An environment that skipped that step folds silently on biotite's subset and mis-builds any ligand or modified residue outside it. It is part of `run.sh install` and is hash-checked there.
- The resident worker forces the data loader to 0 workers. Upstream configures 10 and the kit's cap floors that at 1; a resident worker holding a built model and a CUDA context does not start loader children, whatever the start method.

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
tu remote share openfold3_ob0
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
tu remote share openfold3_ob0 --name my-openfold3-ob0-remote --workers 1
~~~

Use `tu remote check openfold3_ob0` for a non-sharing readiness check and
`tu remote run openfold3_ob0` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.openfold3_ob0.openfold3_ob0_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8052/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8052/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains openfold3_ob0_fold; stop on empty, duplicate, or schema-drifted discovery.

The first request after a restart pays the model build; the ones after it do
not. That is the whole reason this provider is resident, and a benchmark that
measures only the first call measures the wrong thing.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8052/mcp --json
tu serve --share --forward http://127.0.0.1:8052/mcp --name validation-openfold3-ob0 --workers 1
~~~

Prefer browser device authorization. For CI or migration, supply
`TOOLUNIVERSE_SERVICE_KEY` only through a protected environment or use
`tu remote login --manual-key`; never put a key in shell arguments.

This implementation was added after the authenticated 2026-08-16 Platform
matrix and was not part of it. That matrix imported each implementation it
covered as unpublished owner drafts and invoked them through
`/expert-sessions/{id}/test`; this provider was imported as no such draft and
invoked through no such route. It has not been exercised through the Platform
at all: the evidence above is local, on one card, through the loopback
endpoint. Public publication, independent-caller authorization/isolation,
saturation, and persistent supervision are untested.

## Run a verified example

Operation: openfold3_ob0_fold

~~~json
{"chains":[{"molecule_type":"protein","sequence":"LSDEDFKAVFGMTRSAFANLPLWKQQNLKKEKGLF"}]}
~~~

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads(r'''{"chains":[{"molecule_type":"protein","sequence":"LSDEDFKAVFGMTRSAFANLPLWKQQNLKKEKGLF"}]}''')
    async with Client("http://127.0.0.1:8052/mcp") as client:
        result = await client.call_tool("openfold3_ob0_fold", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: `n_structures` above zero and a `scores` object carrying each sample's `*_confidences_aggregated.json` (`avg_plddt`, `ptm`, `iptm`, `sample_ranking_score`, `has_clash`) -- with five diffusion samples, ranking them on those is the one thing a caller must do. Upstream also writes a per-residue `*_confidences.json` holding the full N x N PDE matrix; that one is 61 KB at 35 residues and 29 MB at 800, so the worker returns it only under 64 KiB and names it under `scores_omitted` otherwise, with the path to read it from. A short `scores` object on a long chain is the reply cap, not a missing confidence. A fold that fails on its input comes back as "OpenFold3 (OpenBind-0) could not fold this query: ..." carrying upstream's own words, which is different from the worker being unavailable. Check scientific meaning, output bounds, invalid-input behavior, and absence of paths, secrets, and traces.

## Tune GPU and concurrency

- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock rather than doubling peak VRAM.
- Read `vram_budget_gb` from the provider manifest and the measured file before co-tenanting anything else on the card. Peak here tracks input size as N^2, so the manifest states the envelope the figure was measured at; the tool refuses a query above that envelope rather than admitting a request no budget covers.
- Measure cold start, then **at least four consecutive identical requests**, then a mixed-shape sequence (small, small, large, small). Two warm calls of different shapes is not enough: the sibling `openfold3` provider passed exactly that and still died on the second request of the same shape, because a CUDA graph dropped for moved storage left its emptied pool handle behind. The defect is in the shared core this kit binds too, which is why `[kit] env` sets `OPENFOLD3_OB0_OPT_POST_RELEASE_NTOK = "0"`. A repeat and a shape change are different tests and a resident provider has to survive both.
- Then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/openfold3_ob0-resident.log`, and it holds the kit's full lever census. A lever reading `state=off reason=...` is the kit declining something, which is usually correct.
- Tracebacks are NOT in the request's output directory. Upstream binds `log_dir` to the lightning module at construction, so a resident worker's failures all land in its BIRTH directory, `/tmp/openfold3_ob0-resident-*/logs/predict_err_rank0.log`.
- `NOT ACTIVE: undeclared variable(s) OPENFOLD3_OB0_OPT_...` at interpreter start: the kit refuses any name under its own prefix that it does not read, in every process, with exit 3. Unset the misspelt variable; do not add it to the launch.
- Import/executable failure in the model half: re-run `tu remote setup openfold3_ob0 --only environment`. It rebuilds from the lock with `--no-deps` and will not silently resolve a different version.
- `version_compatibility` refusals at build time mean the wrong checkpoint: this provider loads OpenBind-0 only, and the sibling provider's `of3-p2-155k.pt` in the same cache directory is not interchangeable with it.
- Weights off their pin: the named file is left in place for inspection rather than deleted, because a truncated transfer and a corrupt file look alike. Remove it by hand and re-run `--only weights`.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-openfold3-ob0`.
- A worker outliving its server is a known shape: it has an idle timeout and an orphan watchdog, and it exits when its parent becomes init. Check with `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` before assuming the card is free.
- Revoke temporary keys. After confirmation, remove only .venvs/openfold3_ob0 and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
