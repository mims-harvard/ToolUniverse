---
name: setup-esm_if1-remote-tool
description: Set up, launch, validate, and troubleshoot the ESM-IF1 inverse-folding ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up ESM-IF1 inverse folding as a remote tool

> Validation status (2026-10-01): ESM-IF1 sequence design ran on the NVIDIA GB10 host (aarch64, 20 cores, cc 12.1, driver 580.173.02) **on the CPU**, under the optimization kit's `fast` mode (lever `batched_sampling`). **This is the first provider on the standard with `[gpu] policy = "none"`, and that is a measurement rather than a fallback.** The kit pins torch 2.4.0, whose CUDA generation predates this card: cuBLAS 12.4 for aarch64 carries cubins only through sm_90. It does carry **sm_90 PTX**, so a forward JIT is not ruled out and the honest status of that route is **unmeasured rather than impossible** — `provider.toml`'s `[gpu]` section has the `cuobjdump` output and the three reasons the route was not taken anyway, the first being that the kit's pinned PyG companions have no aarch64 build at any version. Four consecutive identical requests produced **byte-identical** FASTA files, and the same sha256 as the kit's own CLI. Peak RSS is flat in length and driven by the product of length and sample rows: 2.45 GiB from 64 through 395 residues, 3.65 at 800x2, and **11.22 GiB at the worst request the declared ceilings admit together** (1600 tokens x 4 rows, 757.7 s). Schedule on 11.22 unless the deployment caps the input; the smoke's 2.45 would under-budget an ordinary request by 4.6x. Public publication, cross-user isolation, concurrency, recovery and design quality are untested; keep this deployment private.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- **No GPU is required**, and none is used. `[gpu] policy = "none"` makes the preflight step skip every GPU check, which is what makes that honest rather than merely quiet. The worker still chooses the GPU when `torch.cuda.is_available()` is true, so the same worker drives a card on a host whose torch has one.
- The model environment needs **Python 3.11 exactly** (the kit's own requirement: cp311 wheels, and numpy 1.26.4 / scipy 1.11.4 / torch 2.4.0 publish no cp312). A C/C++ compiler is needed once, because biotite 0.39.0 publishes no linux-aarch64 wheel and is built from its pinned sdist (4m37s on 20 cores, then cached).
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation esm_if1
~~~

After exporting provider resources, add `--check-provider-env`. After the
server starts, add `--live` to verify the exact MCP tool set without running
the model. Before sharing, add `--check-connect-prereqs`; this reports only
whether a key is set and never prints its value.

## Create the two environments

This provider is on the remote-tool standard, so it has two environments, not
one: the MCP server runs in ToolUniverse's, and the model runs in its own,
built from a pinned lock. They cannot import each other, and that is the point.

~~~bash
python3 -m venv .venvs/esm_if1
. .venvs/esm_if1/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_ESM_IF1_PYTHON` names, and
nothing above creates it. Create a **Python 3.11** interpreter there first --
`uv venv --seed --python 3.11 ~/esm_if1-venv` -- and `tu remote setup --only
environment` fills it from
`src/tooluniverse/remote/esm_if1/environment/requirements.lock` with
`--no-deps`, so no version is silently resolved to something else. `uv venv` is
used rather than the stdlib `python -m venv` because this kit scans no `.pth`
files at all (it ships no autoload `.pth`), so uv's `_virtualenv.pth` -- which
broke openfold3's hook detection -- has nothing here to confuse. **The venv
must be seeded** (`--seed`): the environment step installs with
`python -m pip`.

The rest is built by `tu remote setup`, which reads
`src/tooluniverse/remote/esm_if1/provider.toml` and runs five steps: preflight,
environment, kit, weights, smoke. Each refuses by name and carries its fix.

~~~bash
export TOOLUNIVERSE_ESM_IF1_PYTHON=~/esm_if1-venv/bin/python
export TOOLUNIVERSE_ESM_IF1_WEIGHTS=~/.esm_if1          # optional; this is the default
tu remote setup esm_if1
~~~

Run one step at a time with `--only preflight|environment|kit|weights|smoke`
while bringing a machine up. The smoke step is the one that matters: it holds
the model, sends one request, asserts the provider produced what its manifest
says a successful run produces (`outputs = ["*.fasta"]` plus
`output_keys = ["sequences", "native_seq"]`), and records what this machine did
to `~/.cache/tooluniverse/measured/esm_if1.json`. A host schedules on that file.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain credentials, data, and model weights

- No credentials. One weight file, 1.7 GB: `esm_if1_gvp4_t16_142M_UR50.pt`, declared in the manifest with the size and sha256 the kit's own `stock/PINS.json` carries. `tu remote setup --only weights` fetches it with the kit's own downloader (`python -m esm_if1_opt.weights DIR`, which runs `torch.hub.download_url_to_file` -- the transfer upstream's own loader uses) and checks both. 37 s on this host.
- Nothing is fetched at request time, and the worker proves it twice. Before loading, it compares `torch.hub.get_dir()` against the directory the checkpoint is staged into and refuses `torch_hub_elsewhere` if they differ; after loading, it runs the kit's own `stack.cache_word()` and refuses `weights_replaced` on anything but `hit`. **Both checks exist because a probe caught the failure**: `stage_torch_home()` links the checkpoint into `$MODEL_OPT_STATE/torch_home`, `torch.hub` reads `TORCH_HOME`, and with the first set and the second unset the staging reports `linked` -- truthfully, about a directory torch never looks in -- while upstream downloads 1.7 GB into `~/.cache/torch/`.

## Authorize once, then share with one short command

After installing dependencies, exporting the provider resources above, and
installing the pinned relay SDK described under Connect below, run from the
repository root. Log in only once per machine (and again after key rotation):

~~~bash
tu remote login
# Or import an existing protected 0600 file without sourcing it:
tu remote login --env-file /path/to/tooluniverse-service.env
~~~

Then each private share is one short command:

~~~bash
tu remote share esm_if1
~~~

By default, `tu remote login` requests a short-lived device code, opens the
TU Platform approval page, and polls until the signed-in user approves. No key
copy/paste is required. On a headless machine, add `--no-browser` and open the
printed link elsewhere. The CLI exchanges the approval for a computer-only key,
verifies `/remote-servers/preflight`, stores it in a local 0600 config file, and
never displays it.

The share command runs environment and TU Platform preflights, starts or reuses
the exact loopback endpoint, validates discovery, and keeps the relay in the
foreground until Ctrl-C. Override the defaults only when needed:

~~~bash
tu remote share esm_if1 --name my-esm-if1-remote --workers 1
~~~

Use `tu remote check esm_if1` for a non-sharing readiness check and
`tu remote run esm_if1` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.esm_if1.esm_if1_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8050/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8050/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains esm_if1_design; stop on empty, duplicate, or schema-drifted discovery.

The first request after a restart pays the model build; the ones after it do
not. That is the whole reason this provider is resident, and here the fixed cost
is a 1.7 GB `torch.load` rather than a compile trace -- the same argument as
ESMFold2's, at a twentieth of the weight.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8050/mcp --json
tu serve --share --forward http://127.0.0.1:8050/mcp --name validation-esm-if1 --workers 1
~~~

Prefer browser device authorization. For CI or migration, supply
`TOOLUNIVERSE_SERVICE_KEY` only through a protected environment or use
`tu remote login --manual-key`; never put a key in shell arguments.

This implementation was added after the authenticated 2026-08-16 Platform
matrix and was not part of it. That matrix imported each implementation it
covered as unpublished owner drafts and invoked them through
`/expert-sessions/{id}/test`; this provider was imported as no such draft and
invoked through no such route. It has not been exercised through the Platform
at all: the evidence above is local, on one host, through the loopback
endpoint. Public publication, independent-caller authorization/isolation,
saturation, and persistent supervision are untested.

## Run a verified example

Operation: esm_if1_design

The input is a STRUCTURE, which is what makes this provider the inverse of the
folding ones beside it. `src/tooluniverse/remote/esm_if1/smoke/input.json`
carries the first 64 residues of chain C of 5YH2 -- the example structure the
kit's own README designs with -- inline, and
`smoke/input-multichain.json` is upstream's second route for the same file.

The example below is a **ten-residue excerpt of that same chain, N/CA/C only**,
which is all upstream reads. It is short enough to put in a document and it
runs; it is not a design worth interpreting. The scientifically meaningful call
is the 64-residue smoke file in the snippet after it, and the recovery figures
quoted in `provider.toml` come from the whole 395-residue chain.

~~~json
{"structure": "ATOM   3461  N   SER C 134      -5.555  22.103 -75.953  1.00 70.85           N\nATOM   3462  CA  SER C 134      -4.121  21.850 -75.885  1.00 74.77           C\nATOM   3463  C   SER C 134      -3.849  20.353 -75.765  1.00 85.14           C\nATOM   3467  N   VAL C 135      -4.510  19.712 -74.797  1.00 88.32           N\nATOM   3468  CA  VAL C 135      -4.308  18.282 -74.566  1.00 85.66           C\nATOM   3469  C   VAL C 135      -4.707  17.486 -75.801  1.00 86.60           C\nATOM   3474  N   LEU C 136      -5.911  17.750 -76.317  1.00 83.95           N\nATOM   3475  CA  LEU C 136      -6.370  17.079 -77.527  1.00 79.86           C\nATOM   3476  C   LEU C 136      -5.490  17.441 -78.714  1.00 79.96           C\nATOM   3482  N   GLN C 137      -5.102  18.713 -78.812  1.00 78.74           N\nATOM   3483  CA  GLN C 137      -4.166  19.129 -79.848  1.00 81.85           C\nATOM   3484  C   GLN C 137      -2.866  18.340 -79.753  1.00 85.22           C\nATOM   3491  N   SER C 138      -2.378  18.113 -78.528  1.00 90.62           N\nATOM   3492  CA  SER C 138      -1.123  17.387 -78.341  1.00 88.57           C\nATOM   3493  C   SER C 138      -1.299  15.896 -78.588  1.00 84.29           C\nATOM   3497  N   LEU C 139      -2.460  15.345 -78.217  1.00 83.51           N\nATOM   3498  CA  LEU C 139      -2.689  13.915 -78.395  1.00 83.46           C\nATOM   3499  C   LEU C 139      -2.560  13.523 -79.859  1.00 77.50           C\nATOM   3505  N   PHE C 140      -3.298  14.207 -80.735  1.00 77.84           N\nATOM   3506  CA  PHE C 140      -3.184  13.933 -82.159  1.00 74.98           C\nATOM   3507  C   PHE C 140      -1.818  14.331 -82.701  1.00 75.13           C\nATOM   3516  N   GLU C 141      -1.067  15.152 -81.961  1.00 78.09           N\nATOM   3517  CA  GLU C 141       0.297  15.501 -82.332  1.00 81.27           C\nATOM   3518  C   GLU C 141       1.306  14.447 -81.899  1.00 77.28           C\nATOM   3525  N   HIS C 142       0.877  13.444 -81.128  1.00 71.75           N\nATOM   3526  CA  HIS C 142       1.757  12.361 -80.722  1.00 72.48           C\nATOM   3527  C   HIS C 142       2.204  11.564 -81.947  1.00 76.35           C\nATOM   3535  N   PRO C 143       3.322  10.836 -81.850  1.00 78.08           N\nATOM   3536  CA  PRO C 143       3.702   9.912 -82.929  1.00 79.13           C\nATOM   3537  C   PRO C 143       2.972   8.578 -82.900  1.00 72.64           C\nEND", "structure_format": "pdb", "chain": "C", "num_samples": 2, "temperature": 1.0, "seed": 37}
~~~

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

doc = json.load(open("src/tooluniverse/remote/esm_if1/smoke/input.json"))
arguments = {
    "structure": doc["structure"],
    "structure_format": "pdb",
    "chain": "C",
    "num_samples": 2,
    "temperature": 1.0,
    "seed": 37,
}

async def main():
    async with Client("http://127.0.0.1:8050/mcp") as client:
        result = await client.call_tool("esm_if1_design", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape, with the reply's own key names: `sequences` (one string
per requested sample, each the length of the designed chain), `native_seq`,
`recovery` (one fraction per sample), `n_tokens`, `designed_length`, `route`
(`singlechain` or `multichain`), `device`, `kit_levers` and
`weights_held_by = "worker"`. Note `peak_reserved_gib` is **null** on a CPU
host and `timing.peak_rss_gib` is the figure to schedule on. `sequences` is
deliberately EMPTY when a backbone's rows were not all sampled, which is what
`[runtime] output_keys` branches on -- so an empty list is a failed request,
not an empty answer. Run above, on the ten-residue example: two 10-character
sequences and one `ex.fasta`. Check scientific meaning,
output bounds, invalid-input behavior, and absence of paths, secrets, and
traces.

## Tune CPU and concurrency

- **One thread, and it is measured.** torch's default is `os.cpu_count()` = 20, which is the slowest setting tested: 64 residues x 2 samples, min of three repeats, reads 8.66 s at one thread and 13.91 s at twenty (7.50 vs 11.52 pinned to the ten Cortex-X925 performance cores), and the ordering holds at 256 residues. ESM-IF1's decoder takes one sequential step per designed position over tensors too small for a thread barrier to pay for itself. `[kit.env] OMP_NUM_THREADS = "1"` and `torch.set_num_threads(1)` both state it; `ESM_IF1_RESIDENT_THREADS` overrides it for a host that measures otherwise. **This is the same setting boltzgen needed for an unrelated reason** -- there it stopped a library forking a pool `fork()` would not carry over; nothing forks here.
- **The axis that does pay is the kit's lever.** `batched_sampling` stacks (backbone, sample) rows into one forward pass: 11.14 s per sequence at one row, 1.94 s at eight -- 5.7x, drawn from the same distribution. Raise `num_samples` rather than issuing N requests.
- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock.
- Read `peak_rss_gib` from the measured file before co-tenanting, and read the manifest for the row it was declared at. Length alone moves it little -- 2.45 GiB from 64 through 395 residues, 3.65 at 800 -- because the constant 1.7 GB checkpoint dominates; what moves it is the PRODUCT of length and sample rows, which is why the worker bounds that product and why the declared figure is 11.22 GiB at 1600 tokens x 4 rows. Time is not flat either: 5.4 / 16.0 / 43.9 / 72.9 / 172.2 s over 64 / 128 / 256 / 395 / 800 residues at two samples, and 757.7 s at the ceiling. The peak is a spike, not a plateau: RSS read during that 757.7 s request went 5.38 -> 9.08 -> 1.48 GiB and stayed near 1.48 for the remaining ~500 s, because the peak is the GVP encoder's kNN graph early in the request and the long decode loop is small. A high-water mark cannot tell a co-tenant that, so the manifest does.
- Measure cold start, then **at least four consecutive identical requests**, then a mixed-shape sequence (small, small, large, small). Two warm calls of different shapes is not enough: openfold3 passed exactly that and still died on the second request of the same shape. For this provider both passed and the four identical requests also produced byte-identical files, which is a stronger statement and was only measurable because it was written down falsifiably first.
- Then parallel levels 1, 2, 4, 8. Record successes/errors, p50/p95, peak RSS, utilization, queueing, cancellation cleanup, and recovery.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/esm_if1-resident.log`.

| refusal | what it means | what to do |
| --- | --- | --- |
| `kit_missing:esm_if1_opt` | the kit is not installed on the model interpreter | `tu remote setup esm_if1 --only kit`, which runs the kit's own `bash run.sh install` |
| `kit_activation_refused` | the kit declined the mode: fair-esm or torch absent, or a second mode resolved in this process | read the sentence; it is `esm_if1_opt.stack.enable`'s own |
| `core_missing:opt_core` / `core_mismatch` | the kit's shared core is absent or older than its pin | `--only kit` reinstalls both editable, core first |
| `weights_not_linked` | the checkpoint is not symlinked into torch.hub's cache entry | set `TOOLUNIVERSE_ESM_IF1_WEIGHTS`; remove any **regular file** at that cache entry by hand (it is never deleted automatically: a truncated transfer and a different checkpoint look alike) |
| `torch_hub_elsewhere` | torch.hub will read a different directory than the one the checkpoint was staged into | unset `TORCH_HOME`, or point it at the directory the message names |
| `weights_replaced` | after the load, the cache entry no longer resolves to the verified file | something replaced it mid-load; remove it and re-run `--only weights` |
| `weights_off_pin` | the 1.7 GB file is absent, short, or a different digest | the named file is left in place for inspection; remove it by hand and re-run `--only weights` |
| `lock_install_failed` | the pinned stack did not install | check the interpreter is Python **3.11**; biotite builds from source and needs `cc` |
| `ESM_IF1_OPT=... disagrees with --mode` | the kit's mode variable is in the worker's environment | `launch.py` strips it, so something set it after the launch; unset it and restart |
| `smoke_produced_nothing` | the model answered and wrote no FASTA | the glob is `*.fasta` and the worker writes `input.pdb` and `opt_manifest.json` on every request, successful or not, so this means the pass really did not complete; read the transcript |

- Import/executable failure in the model half: re-run `tu remote setup esm_if1 --only environment`. It rebuilds from the lock with `--no-deps` and will not silently resolve a different version.
- The `UserWarning: Regression weights not found, predicting contacts will not produce correct results.` at every model load is expected and upstream's own: the checkpoint has no contact head and nothing here predicts contacts.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-esm-if1`.
- A worker outliving its server is a known shape: it has an idle timeout and an orphan watchdog, and it exits when its parent becomes init. This one holds no GPU, so check with `pgrep -af esm_if1_resident_worker` rather than `nvidia-smi`.
- Revoke temporary keys. After confirmation, remove only .venvs/esm_if1 and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
