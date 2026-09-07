# scVelo Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> scVelo dependencies, loopback discovery, and deterministic-mode execution passed on the upstream simulation with aligned finite pseudotime/confidence for 300 cells. Public publication, cross-user isolation, representative biology, broad concurrency, and recovery remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_scvelo_velocity`
- Start: `python -m tooluniverse.remote.scvelo.scvelo_tool`
- Endpoint: `http://127.0.0.1:8025/mcp`
- Provider configuration: set `TOOLUNIVERSE_REMOTE_DATA_ROOT`; approved H5AD inputs need scientifically suitable spliced/unspliced layers.
- TOU check: `tu doctor --forward http://127.0.0.1:8025/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8025/mcp --name validation-scvelo --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation scvelo`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-scvelo-remote-tool/SKILL.md).

Serves [scVelo](https://scvelo.readthedocs.io/)
(RNA velocity; Bergen et al., *Nature Biotechnology* 2020) as a ToolUniverse
remote tool: `run_scvelo_velocity` — infers RNA velocity from spliced/unspliced
mRNA and returns a velocity-derived pseudotime ordering of cells plus a per-cell
velocity confidence, and (with a `cluster_key`) the mean pseudotime per cluster
as a coarse trajectory ordering.

Served remotely (not bundled) because `scvelo` pulls in scanpy + anndata +
numba. The input `.h5ad` **must** carry `spliced` and `unspliced` count layers
(e.g. from velocyto, kb-python / kallisto|bustools, or STARsolo); without them
RNA velocity cannot be estimated and the tool returns a clear error.

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
tu remote share scvelo
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
tu remote share scvelo --name my-scvelo-remote --workers 1
```

Use `tu remote run scvelo` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Deploy

```bash
pip install -r requirements.txt          # scvelo + scanpy + anndata
python scvelo_tool.py                      # starts the MCP server on 127.0.0.1:8025
```

Pipeline: `scv.pp.filter_and_normalize` -> `scv.pp.moments` -> `scv.tl.velocity`
-> `scv.tl.velocity_graph` -> `scv.tl.velocity_pseudotime` +
`scv.tl.velocity_confidence`.

Inputs are referenced by `adata_path` (a server-accessible `.h5ad` with
spliced/unspliced layers), since single-cell matrices are large. Only bounded
summaries (mean/min/max/std, per-cluster means) are returned; full per-cell
arrays are included only for small datasets (n_cells <= 500). Expose remotely
only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/scvelo_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
