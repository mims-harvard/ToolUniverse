# COMPASS immune-response remote tool

## TOU validation and deployment status (2026-08-16)

> The working CPU deployment ran the official all-cohort COMPASS checkpoint, converted to safetensors plus data-only preprocessing, on the official GIDE sample. In the pinned Torch 2.10.0 environment, the safe artifact and upstream checkpoint had zero difference in class probabilities and all 44 concept scores. This is execution-equivalence evidence, not a clinical-accuracy benchmark. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_compass_prediction`
- Start: `python -m tooluniverse.remote.immune_compass.compass_tool`
- Endpoint: `http://127.0.0.1:7003/mcp`
- Provider configuration: set `TOOLUNIVERSE_REMOTE_DATA_ROOT`, `COMPASS_SAFE_MODEL_DIR`, and `COMPASS_DEVICE=cpu`. The live service loads safetensors/JSON/data-only NPZ and never calls `torch.load`.
- TOU check: `tu doctor --forward http://127.0.0.1:7003/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:7003/mcp --name validation-immune-compass --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public publication, independent-caller testing, and clinical accuracy remain unvalidated.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation immune-compass`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-immune-compass-remote-tool/SKILL.md).

`run_compass_prediction` performs real inference with the official COMPASS
architecture and a provider-approved model artifact. The public service never
uses `torch.load`: it reconstructs the reviewed architecture and reads weights
from safetensors plus data-only preprocessing arrays.

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
tu remote share immune-compass
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
tu remote share immune-compass --name my-immune-compass-remote --workers 1
```

Use `tu remote run immune-compass` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Provision a model

The official checkpoint is a whole-object PyTorch pickle. Run the converter
only in an isolated administrator environment after reviewing the source and
pinning its digest. The official repository checkpoint used for validation is
`example/model/finetuner_pft_all.pt` at upstream revision
`0e5c87665247e3a300f28282c8bbcc14e26973bd`, with SHA-256
`fc83d7b5eac3697bcd9d117acefa35b56cf4c4c3c5880de367c85a870aef4b0b`.

```bash
python convert_checkpoint.py finetuner_pft_all.pt safe-compass \
  --expected-sha256 fc83d7b5eac3697bcd9d117acefa35b56cf4c4c3c5880de367c85a870aef4b0b \
  --upstream-revision 0e5c87665247e3a300f28282c8bbcc14e26973bd
```

The converter emits `model.safetensors`, `preprocessing.npz`, and
`metadata.json`, with cross-checked artifact digests. It is not imported by the
live service.

## Deploy

```bash
export TOOLUNIVERSE_REMOTE_DATA_ROOT=/srv/tooluniverse/data
export COMPASS_SAFE_MODEL_DIR=/srv/tooluniverse/compass-safe
export COMPASS_DEVICE=cpu
python -m tooluniverse.remote.immune_compass.compass_tool
```

Input is one sample in the official COMPASS TSV/CSV layout: `Index`, then
integer `cancer_code` (0 through 32), then TPM genes. The table must be inside
the provider data root and contain all 15,672 model genes. The server listens
on `http://127.0.0.1:7003/mcp`; a non-loopback bind requires
`TOOLUNIVERSE_API_TOKEN`.
