---
name: devtu-remote-provider
description: Bring up, standardise or debug a GPU-backed ToolUniverse remote tool in src/tooluniverse/remote/<slug>/ — the provider.toml manifest, the resident model worker, wrapping a third-party optimization kit, and reading what `tu remote setup` refuses. Use when adding a self-hosted model provider, converting one from per-request subprocess to resident, diagnosing a setup or launch refusal, or reviewing a provider against the standard.
---

# ToolUniverse remote provider

A remote tool is a model you host yourself, exposed over MCP. The contract lives
in `src/tooluniverse/remote_resident/STANDARD.md`; read it before changing a
provider. This page is how to apply it and how to read what it refuses.

## The shape

```
agent ──MCP──> remote/<slug>/<slug>_mcp_server.py     ToolUniverse's env, CPU only
                      │
                      │ Unix socket, one request at a time
                      ▼
               remote/<slug>/resident/<slug>_worker.py   the model's own env
```

Two environments because their pinned stacks conflict. Boltz-2 needs torch
2.12.0+cu130 / triton 3.7.0 / numpy 1.26.4, which cannot be installed alongside
ToolUniverse's other 600+ tools. **The MCP server must not import the model's
dependencies, and the worker must not import ToolUniverse** — the shared surface
is one dependency-free file (`remote_resident/protocol.py`) loaded by path.

## Top mistakes

1. **Requiring the model's CLI at tool construction.** `shutil.which("boltz")`
   in `__init__` fails on a correctly separated deployment. Accept either route.
2. **Trusting weights because the download exited 0.** A `boltz2_conf.ckpt`
   arrived as 1.2 % of itself and served predictions for a month. Declare
   `size` and `sha256`; nothing is fetched implicitly at request time.
3. **Starting the model per request.** Measured on a GB10: 110 s per call as a
   subprocess, ~54 s held. Most of the difference is not kernels — it is CUDA
   graphs captured on one request and replayed on the next, which a worker that
   exits cannot collect.
4. **Letting a worker outlive its server.** `start_new_session=True` keeps a
   Ctrl-C from killing a prediction, and also orphans the worker; SIGKILLing the
   MCP server left two processes holding the GPU. Workers need the idle timeout
   *and* the orphan watchdog.
5. **Claiming `status = "verified"` without hardware.** It must carry
   `verified_on`. A bare "verified" claims every machine.
6. **Hashing gigabytes on every check.** Use the digest memo; pass `deep=True`
   only in setup, where what is certified should have been read.
7. **Forgetting package data.** A built wheel carries only `.py` under
   `remote/`. Provider JSON, `provider.toml`, lock files, smoke inputs and the R
   halves of R-backed providers need globs in `pyproject.toml`.

## Adding a provider

```
src/tooluniverse/remote/<slug>/
├── provider.toml                    the declaration; see STANDARD.md
├── <slug>_client_tools.json         the MCP tool schemas
├── <slug>_mcp_server.py             thin, CPU-only
├── environment/requirements.lock    a complete freeze, installed --no-deps
├── resident/<slug>_worker.py        builds the model once, serves a socket
├── resident/launch.py               build_command(worker) -> (argv, env)
└── smoke/input.yaml                 the smallest input that exercises the path
```

Then `tu remote setup <slug>` → `tu remote check <slug>` → `tu remote run <slug>`.

Start `status = "untested"`. It becomes `verified` only after the smoke step has
run on hardware you then name in `verified_on`.

## Wrapping a third-party optimization kit

Anthropic's kits (`github.com/anthropics/uplifting-biomolecular-modeling`) are
referenced by pinned commit, never vendored: 473 MB, of which ~300 MB is
prebuilt kernels for architectures a given host may not even load, and their own
`pyproject.toml` says the install must stay editable.

**Wrap, do not patch.** Their launcher runs any script:

```
python -m <kit>_opt.worker_launch --route … --attach … -- your_worker.py …
```

so a resident worker is simply a different script in the position the kit's
batch worker occupies, and the kit's import hooks attach its levers to the model
your script builds. For Boltz-2 that is 25 of 28 levers; the three implemented
inside the kit's own worker script are forgone. Verify equivalence before
believing it: structure mean |dCA| and the affinity value should match the kit's
own `run.sh pred --mode <mode>` exactly.

Ask the kit for its own parameters rather than copying them — `launch.py` runs a
few lines in the *model's* interpreter to read `modes.resolve(mode)["env"]` and
`stack.launch_opts(...)`. A hard-coded copy drifts the first time the kit moves.

**An adapter in `--attach` whose switch is missing from the row refuses the whole
launch.** Keep the row intact and let the adapter decline by name instead.

## Reading a refusal

Every step names itself. Exit codes: `0` ok · `1` failed · `2` usage · `3`
refused · `5` accelerator absent.

| reason | what it means | what to do |
| --- | --- | --- |
| `compiler_missing` | no `cc`/`gcc`; Triton compiles kernels at run time | `apt-get install build-essential`; needs root, so ask whoever has it |
| `driver_old` | below the 580 series for CUDA 13.0 | upgrade the driver, or use a host that has it |
| `cc_below_floor` | compute capability under 8.0 | no configuration lowers it; different hardware |
| `disk_low` | under ~20 GB free | one provider is ~16 GB (weights + environment + kit) |
| `env_python_unset` | `[env] python`'s variable is not exported | the refusal prints the `uv venv` recipe |
| `lock_install_failed` | the pinned stack did not install | read the tail; usually a wheel missing for this architecture |
| `kit_wrong_commit` / `kit_modified` | the checkout is not the pin, or has been edited | left in place; remove by hand and re-run |
| `weights_off_pin` | a file is absent, short, or a different digest | **never deleted automatically**: upstream writes straight to the final name, so a truncated transfer and a corrupt file look alike. Remove the named file yourself and re-run |
| `smoke_*` | it installed and then did not run | the transcript is in `~/.cache/tooluniverse/remote-logs/<slug>-resident.log` |

## What only running reveals

Three of the four problems the first provider hit appeared at run time, and one
presented as a stall rather than an error:

- a kit lever whose zygote featurizer hung for the full loader timeout, then
  hung again after falling back, while a plain torch DataLoader was fine;
- a Triton kernel reporting `OutOfResources` on compute capability 12.1;
- `nvidia-smi --query-gpu=memory.total` returning `[N/A]` on unified memory,
  which silently zeroes the kits' MPS budget arithmetic.

So: the smoke step carries a deadline, and `provider.toml`'s numbers are the
reference they were measured against — the per-host record in
`~/.cache/tooluniverse/measured/<slug>.json` is what a scheduler should read.

## Design the failure out

Prefer making a failure impossible over documenting it. The kits do this: files
fetched over HTTP lose their executable bit, so every command in their READMEs
is `bash script.sh`, never `./script.sh`. Ours:

- an orphaned worker retires itself, rather than a note saying to kill it;
- the interpreter's directory is taken without `resolve()`, because a venv's
  `bin/python` is a symlink to the interpreter it was built from and following
  it lands in the wrong `bin`;
- the worker passes `num_workers=0`, so a 64 MB `/dev/shm` in a container is not
  a failure mode.

## Checks

```bash
tu remote check <slug>              # both environments, weights, GPU
tu remote setup <slug> --only smoke # re-run just the proof
pytest tests/unit/test_remote_resident.py -q
python -m ruff check src/tooluniverse/remote_resident src/tooluniverse/remote
```

After editing this skill run `bash plugin/sync-skills.sh`.
