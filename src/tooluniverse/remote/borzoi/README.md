# Borzoi Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> A fresh Python 3.12 service environment resolved borzoi-pytorch 0.4.4 with supported Transformers 4.50.3, loaded official weights on the GB10, and returned bounded finite prediction and variant-effect results through a strict loopback TOU endpoint. Four concurrent fixture calls passed with serialized model access. NVIDIA's aarch64 cusparselt wheel still reports incompatible platform metadata in `uv pip check`; public publication, saturation, recovery, cross-user isolation, and biological accuracy remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operations: `run_borzoi_predict`, `run_borzoi_variant_effect`
- Start: `python -m tooluniverse.remote.borzoi.borzoi_tool`
- Endpoint: `http://127.0.0.1:8012/mcp`
- Provider configuration: keep `HF_HOME` and `TORCH_HOME` under provider-owned caches. Install this directory's requirements in an isolated environment; Borzoi must use `transformers>=4.46,<4.51`.
- TOU check: `tu doctor --forward http://127.0.0.1:8012/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8012/mcp --name validation-borzoi --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation borzoi`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-borzoi-remote-tool/SKILL.md).

Serves [Borzoi](https://www.nature.com/articles/s41588-024-02053-6) (Linder et al., *Nature Genetics* 2025) — sequence → RNA-seq/multi-omic coverage prediction, the successor to Enformer — as ToolUniverse remote tools: `run_borzoi_predict` and `run_borzoi_variant_effect`.

Served remotely (not bundled) because it needs PyTorch + ~0.8 GB of weights per replicate (`johahi/borzoi-replicate-{0..3}`) and is GPU-recommended.

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
tu remote share borzoi
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
tu remote share borzoi --name my-borzoi-remote --workers 1
```

Use `tu remote run borzoi` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Deploy

```bash
pip install -r requirements.txt          # torch + borzoi-pytorch
python borzoi_tool.py                      # starts the MCP server on 127.0.0.1:8012
```

Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definitions: `src/tooluniverse/data/remote_tools/borzoi_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism. First call lazily downloads and caches the weights.
