# Tangram Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> Tangram dependencies, loopback discovery, and a bounded five-epoch single-cell/spatial mapping call passed with normalized proportions across 72 spots. Public publication, cross-user isolation, production epochs, representative accuracy, broad concurrency, and recovery remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_tangram_deconvolution`
- Start: `python -m tooluniverse.remote.tangram.tangram_tool`
- Endpoint: `http://127.0.0.1:8018/mcp`
- Provider configuration: set `TOOLUNIVERSE_REMOTE_DATA_ROOT` for provider-owned H5AD files; callers supply relative paths and a valid `cluster_label`.
- TOU check: `tu doctor --forward http://127.0.0.1:8018/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8018/mcp --name validation-tangram --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. The five-epoch fixture is not a production-quality training benchmark.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation tangram`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-tangram-remote-tool/SKILL.md).

Serves [Tangram](https://tangram-sc.readthedocs.io/) (Biancalani et al., *Nature Methods* 2021) — alignment of single-cell RNA-seq onto spatial transcriptomics — as a ToolUniverse remote tool: `run_tangram_deconvolution`, which maps cell-type clusters from a single-cell reference onto a spatial assay and returns per-spot cell-type proportions (spatial deconvolution).

Served remotely (not bundled) because `tangram-sc` pulls in PyTorch + scanpy. Mapping runs on CPU for the modest reference/spatial matrices typical of this workflow.

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
tu remote share tangram
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
tu remote share tangram --name my-tangram-remote --workers 1
```

Use `tu remote run tangram` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Deploy

```bash
pip install -r requirements.txt          # tangram-sc + scanpy
python tangram_tool.py                     # starts the MCP server on 127.0.0.1:8018
```

Inputs are referenced by paths (`sc_path`, `sp_path`): server-accessible `.h5ad`
files for the single-cell reference (with `cluster_label` in `obs`) and the
spatial assay. Expose remotely only behind `TOOLUNIVERSE_API_TOKEN`
(SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/tangram_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
