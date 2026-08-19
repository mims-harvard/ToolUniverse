# CellTypist Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> The working CPU deployment annotated 80 official-sample cells and completed majority voting. Its converted data-only model matched all 80 upstream labels with maximum probability delta 0.0. This is runtime-equivalence evidence, not an annotation-accuracy benchmark. Four simultaneous calls also passed through the one-worker strict endpoint; cancellation, saturation, soak, public publication, and cross-user isolation remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_celltypist_annotate`
- Start: `python -m tooluniverse.remote.celltypist.celltypist_tool`
- Endpoint: `http://127.0.0.1:8014/mcp`
- Provider configuration: set `TOOLUNIVERSE_REMOTE_DATA_ROOT`, `CELLTYPIST_SAFE_MODEL_DIR`, `CELLTYPIST_FOLDER`, `MPLCONFIGDIR`, and `TOOLUNIVERSE_CACHE_DIR` to reviewed, writable provider paths. The live service loads only the data-only NPZ.
- TOU check: `tu doctor --forward http://127.0.0.1:8014/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8014/mcp --name validation-celltypist --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Local TOU discovery passed; Public publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation celltypist`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-celltypist-remote-tool/SKILL.md).

`run_celltypist_annotate` performs real CellTypist inference without loading a
pickle in the live service. The provider converts an official, reviewed model
once into a data-only NPZ and pins the source SHA-256 during conversion.

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
tu remote share celltypist
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
tu remote share celltypist --name my-celltypist-remote --workers 1
```

Use `tu remote run celltypist` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Provision a model

Upstream CellTypist models are Python pickles. Run the converter only in an
isolated administrator provisioning environment after checking the source and
digest. The current official `Immune_All_Low.pkl` v2 artifact used in validation
has SHA-256
`290874d35dac039d4c9218c343fde4aac1077709b72a331ce7266f6828c36502`.

```bash
python convert_pickle_model.py Immune_All_Low.pkl safe-models/Immune_All_Low.npz \
  --expected-sha256 290874d35dac039d4c9218c343fde4aac1077709b72a331ce7266f6828c36502
```

The remotely callable module opens the resulting archive with
`numpy.load(..., allow_pickle=False)` and reconstructs only the known
logistic-regression and standard-scaler classes.

## Deploy

```bash
mkdir -p /srv/tooluniverse/runtime/celltypist \
  /srv/tooluniverse/runtime/matplotlib \
  /srv/tooluniverse/runtime/cache
export TOOLUNIVERSE_REMOTE_DATA_ROOT=/srv/tooluniverse/data
export CELLTYPIST_SAFE_MODEL_DIR=/srv/tooluniverse/celltypist-safe-models
export CELLTYPIST_FOLDER=/srv/tooluniverse/runtime/celltypist
export MPLCONFIGDIR=/srv/tooluniverse/runtime/matplotlib
export TOOLUNIVERSE_CACHE_DIR=/srv/tooluniverse/runtime/cache
python -m tooluniverse.remote.celltypist.celltypist_tool
```

Inputs must be `.h5ad` files inside `TOOLUNIVERSE_REMOTE_DATA_ROOT` and should
already contain CellTypist's expected log1p-normalized expression (10,000
counts per cell). The three runtime directories must be writable by the service
account; this is required on deployments with a read-only home directory. A
non-loopback bind requires `TOOLUNIVERSE_API_TOKEN`.

Tool definitions are in
`src/tooluniverse/data/remote_tools/celltypist_tools.json`.
