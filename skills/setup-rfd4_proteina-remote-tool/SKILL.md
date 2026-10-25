---
name: setup-rfd4_proteina-remote-tool
description: Set up, launch, validate, and troubleshoot the RFD4-Proteina ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up RFD4-Proteina as a remote tool

> Validation status (2026-10-25): RFD4-Proteina ran on the NVIDIA GB10 (aarch64, cc 12.1, 128 GB unified), driver 580.173.02, through this provider's own path. `tu remote setup --only smoke` returned OK in 169 s with peak reserved 1.89 GiB and a design matched by the manifest's `outputs` glob; four requests through the worker's socket each returned a 100-residue design at 1.89-1.90 GiB; two live calls through the MCP endpoint returned 862 and 825 atoms at 185.9 s cold against 49.6 s warm, and three malformed inputs were refused by name. Every wall-clock figure is an upper bound measured under a host load average of 30-45 and is not the model's speed. Only the unconditional monomer mode was exercised; the six conditioned design shapes are the same call with different annotations but none has been run here. Design quality is unvalidated and nothing here checks it -- refolding metrics are off, and the unconditional input gave strikingly charged repetitive helices (glutamate 29-68% of residues against roughly 6% in natural proteins), which reproduces in a bare process and is the model on this input rather than a defect in the path. Public publication, cross-user isolation, concurrency, recovery and long inputs are untested; keep this deployment private.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required. This provider holds its model resident between requests; CPU is not a target.
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation rfd4_proteina
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
python3 -m venv .venvs/rfd4_proteina
. .venvs/rfd4_proteina/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_RFD4_PROTEINA_PYTHON` names,
and nothing above creates it. Create an empty interpreter there first --
`python3 -m venv ~/rfd4-proteina-venv`, or `uv venv` -- and
`tu remote setup --only environment` fills it from
`src/tooluniverse/remote/rfd4_proteina/environment/requirements.lock`
with `--no-deps`, so no version is silently resolved to something else.

**Two resolver traps are already recorded in that lock's header, and both cost
a failed install to find.** `uv` considers only the first index that carries a
package, so adding `--extra-index-url https://download.pytorch.org/whl/cu132`
for the CUDA 13.2 wheels makes it refuse to resolve `idna` and `cuda-python`
from PyPI; `--index-strategy unsafe-best-match` is the fix, and plain `pip`
does not have the behaviour at all.

**This provider wraps no optimization kit**, so its setup has four steps rather
than five -- there is no kit step. Upstream publishes the inference runtime
itself as `rfd4-proteina` on PyPI, and the levers a kit would add
(`inference_backend`, `compile_lengths`) are configuration the package already
owns. See the provider README for what that changes.

~~~bash
export TOOLUNIVERSE_RFD4_PROTEINA_PYTHON=~/rfd4-proteina-venv/bin/python
export RFD4_PROTEINA_HF_HOME=~/.cache/tooluniverse/rfd4_proteina-hf   # optional
tu remote setup rfd4_proteina
~~~

Run one step at a time with `--only preflight|environment|weights|smoke`
while bringing a machine up. The smoke step is the one that matters: it holds
the model, sends one request, asserts the provider produced what its manifest
says a successful run produces (`*_generated.cif`), and records the measured
peak VRAM to `~/.cache/tooluniverse/measured/rfd4_proteina.json`. A host
schedules on that file.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain credentials, data, and model weights

- No credential is needed. The weights are public on the Hugging Face Hub under BSD 3-Clause.
- `RFD4_PROTEINA_HF_HOME` names the Hub cache the pinned snapshot is fetched into; it defaults to `~/.cache/tooluniverse/rfd4_proteina-hf` and does not have to be set.
- **The flow model and the autoencoder are a matched pair.** Upstream is explicit that mixing one release's flow model with another's autoencoder "produces nonsense rather than an error", because the autoencoder defines the latent space the flow model generates in. The manifest pins one Hub revision and both digests are upstream's own `bundle_sha256` and `bundle_config_sha256`. `config.json` is pinned alongside the weights for the same reason: it carries the latent dimension and residue vocabulary size, which are exactly what changed between this release and the one it supersedes.
- Nothing is fetched at request time. The launch refuses if either file is off its pin.

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
tu remote share rfd4_proteina
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
tu remote share rfd4_proteina --name my-rfd4_proteina-remote --workers 1
~~~

Use `tu remote check rfd4_proteina` for a non-sharing readiness check and
`tu remote run rfd4_proteina` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.rfd4_proteina.rfd4_proteina_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8062/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8062/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains rfd4_proteina_design; stop on empty, duplicate, or schema-drifted discovery.

The first request after a restart pays the model build; the ones after it do
not. That is the whole reason this provider is resident, and a benchmark that
measures only the first call measures the wrong thing. Here the gap is unusually
large and it is **not** the weight load: `Proteina.from_pretrained` returns in
seconds, and what the first request pays is compilation and warm-up.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8062/mcp --json
tu serve --share --forward http://127.0.0.1:8062/mcp --name validation-rfd4_proteina --workers 1
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

Operation: rfd4_proteina_design

~~~json
{"input_cif": "data_monomer\n_entry.id monomer\nloop_\n_atom_site.group_PDB\n", "num_replicates": 1, "seed": 0}
~~~

That fragment shows the **shape of the request, not a request that works**: an
mmCIF header with an empty atom loop carries no design specification, and the
model returns nothing for it. The input the evidence above was measured on
ships with the provider at
`src/tooluniverse/remote/rfd4_proteina/smoke/monomer.cif`, and the call below
reads it rather than inlining 3 KB of mmCIF into a JSON literal.

The argument is an **annotated mmCIF**, and the annotations are the design
specification -- what to hold fixed by coordinate and by sequence, which
residues are hotspots, which regions to generate. There is one tool rather than
seven because, in upstream's own words, "`task` selects how the sampler runs
the trajectory, not which design problem is being solved": a binder, a
scaffolded motif and an enzyme active site differ in the input, not in the
call. Upstream's `examples/` directory has one input per design shape, and
this provider ships the unconditional 100-residue monomer it was smoked on at
`src/tooluniverse/remote/rfd4_proteina/smoke/monomer.cif`.

~~~bash
python - <<'PY'
import asyncio
from pathlib import Path
from fastmcp import Client

SPEC = Path("src/tooluniverse/remote/rfd4_proteina/smoke/monomer.cif").read_text()

async def main():
    async with Client("http://127.0.0.1:8062/mcp") as client:
        result = await client.call_tool(
            "rfd4_proteina_design",
            {"input_cif": SPEC, "num_replicates": 1, "seed": 0},
        )
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: `n_designs`, a `designs` array whose entries carry
`design_id`, per-chain `chains` sequences and `n_atoms`, plus `timing`,
`peak_reserved_gib` and `weights_held_by`. The designed mmCIF text is returned
only when `return_structures` is true; it is off by default because replicates
of mmCIF are megabytes and a transport truncates an oversized reply into
invalid JSON rather than refusing it. Check scientific meaning, output bounds,
invalid-input behavior, and absence of paths, secrets, and traces.

**Refolding metrics are not computed.** The worker passes `~metrics`, because
the oracle-backed metrics need AlphaFold2 or AlphaFold3 with their own
environment and weights. Upstream's own hosted deployment makes the same choice
and says so. The numbers returned are read out of the design itself.

## Tune GPU and concurrency

- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock rather than doubling peak VRAM. This matters more here than for a predictor: `num_replicates` makes one request an arbitrary amount of work.
- Read `vram_budget_gb` from the provider manifest and the measured file before co-tenanting anything else on the card. The manifest's figure was measured at 100 residues; upstream caps a design at 1024 tokens, and a longer input has not been measured here.
- **Measure the two backends at your own size before choosing one.** `inference_backend` and `compile_lengths` are the levers, and on the verified card neither paid at 100 residues -- compilation cost more up front and ran no faster warm, and `bioir` cost more still. That is not "the levers do not work": CUDA graph capture is capped at 511 tokens and upstream's figures were measured on an H100 across a range of sizes. The crossover is very likely at larger designs and nobody has measured where. Upstream's default is left alone and the backend is a per-request argument for exactly this reason.
- Measure cold start, then **at least four consecutive identical requests**, then a mixed-shape sequence (small, small, large, small). Two warm calls of different shapes is not enough: openfold3 passed exactly that and still died on the second request of the same shape, because a CUDA graph captured on the first replay attempt left a failed capture behind. A repeat and a shape change are different tests and a resident provider has to survive both.
- Then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/rfd4_proteina-resident.log`.
- **"upstream wrote no design"** is almost always an input that is a structure but carries no design annotation. The tool refuses an input with no `data_` block and no `_atom_site.` loop up front, but it cannot tell an annotated specification from an ordinary structure without running the model.
- Import/executable failure in the model half: re-run `tu remote setup rfd4_proteina --only environment`. It rebuilds from the lock with `--no-deps` and will not silently resolve a different version. If you are building the lock by hand instead, read its header first -- see the two resolver traps above.
- Weights off their pin: the named file is left in place for inspection rather than deleted, because a truncated transfer and a corrupt file look alike. Remove it by hand and re-run `--only weights`.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-rfd4_proteina`.
- A worker outliving its server is a known shape: it has an idle timeout and an orphan watchdog, and it exits when its parent becomes init. Check with `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` before assuming the card is free.
- Revoke temporary keys. After confirmation, remove only .venvs/rfd4_proteina and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
