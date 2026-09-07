# ChromBPNet Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> TensorFlow safely loaded a generated Keras-v3 fixture; loopback prediction and variant-effect calls returned bounded finite contract results. No reviewed trained ChromBPNet artifact was available, so scientific inference, public publication, cross-user isolation, and production performance remain unvalidated. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operations: `run_chrombpnet_predict`, `run_chrombpnet_variant_effect`
- Start: `python -m tooluniverse.remote.chrombpnet.chrombpnet_tool`
- Endpoint: `http://127.0.0.1:8032/mcp`
- Provider configuration: set `CHROMBPNET_MODEL_PATH` to one administrator-reviewed `.keras` artifact. Caller-selected paths and legacy `.h5` loading are rejected.
- TOU check: `tu doctor --forward http://127.0.0.1:8032/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8032/mcp --name validation-chrombpnet --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. The current result is an artifact-contract pass, not a trained-model pass.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation chrombpnet`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-chrombpnet-remote-tool/SKILL.md).

Serves [ChromBPNet](https://github.com/kundajelab/chrombpnet) (Pampari et al., *Nature Methods* 2025) — base-resolution, bias-corrected deep learning of chromatin accessibility from DNA sequence — as the ToolUniverse remote tools `run_chrombpnet_predict` and `run_chrombpnet_variant_effect`.

ChromBPNet predicts ATAC-seq/DNase-seq accessibility from a 2,114 bp sequence with the Tn5/DNase enzyme bias regressed out. It is the modern successor to DeepSEA/Basset for **non-coding regulatory variant interpretation** (GWAS/eQTL fine-mapping) and TF-motif discovery, and underlies the ENCODE accessibility model zoo. The model has two output heads: a 1,000 bp accessibility *profile* (shape) and a scalar *log total count* (magnitude).

> Note on DeepSEA: the classic DeepSEA model (and HumanBase/FUMA front-ends) is browser-only with no maintained programmatic API. ChromBPNet is the maintained, installable, bias-corrected equivalent and is what this tool wraps.

Served remotely because it carries a heavy TensorFlow/Keras stack and requires a trained, **cell-type-specific** model. The provider selects one reviewed Keras v3 `.keras` artifact with `CHROMBPNET_MODEL_PATH`; callers cannot select model files.

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
tu remote share chrombpnet
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
tu remote share chrombpnet --name my-chrombpnet-remote --workers 1
```

Use `tu remote run chrombpnet` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Operations

- `run_chrombpnet_predict` — predicted accessibility (log total counts + base-resolution profile) for one sequence.
- `run_chrombpnet_variant_effect` — ref-vs-alt **count log2 fold-change** (magnitude effect) + **profile Jensen-Shannon divergence** (shape effect), the canonical ChromBPNet variant scores.

## Models

Trained, cell-type-specific models live in the **HF ENCODE ChromBPNet zoo** — e.g. [`kundajelab/encode-chrombpnet-DNASE-ENCSR000EMK-ENCSR816AQM`](https://huggingface.co/kundajelab/encode-chrombpnet-DNASE-ENCSR000EMK-ENCSR816AQM). Those releases use legacy Keras `.h5` files, which this remotely callable service intentionally does not deserialize. A provider may review and convert a trusted model to the Keras v3 format in an isolated administrative workflow, then configure the resulting artifact. Unreviewed legacy models must not be loaded merely to convert them.

## Deploy

```bash
pip install -r requirements.txt             # TensorFlow/Keras 3 + NumPy
export CHROMBPNET_MODEL_PATH=/provider/models/reviewed-model.keras
python chrombpnet_tool.py                    # starts the MCP server on 127.0.0.1:8032
```

The server requires `.keras`, invokes `load_model(..., safe_mode=True)`, and fails closed for legacy or incompatible artifacts. GPU is recommended. Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard). Scientific execution still requires validation against a reviewed converted model; no such model was available in the current validation environment.

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/chrombpnet_tools.json`
(`type: RemoteTool`).
