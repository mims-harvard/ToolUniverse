# CellRank Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> CellRank dependencies, loopback discovery, and a bounded deterministic pseudotime-kernel fate call passed with aligned finite probabilities. Public publication, cross-user isolation, representative biology, broad concurrency, and recovery remain incomplete; keep this deployment private. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_cellrank_fate`
- Start: `python -m tooluniverse.remote.cellrank.cellrank_tool`
- Endpoint: `http://127.0.0.1:8028/mcp`
- Provider configuration: set `TOOLUNIVERSE_REMOTE_DATA_ROOT` to the provider-owned H5AD root; callers supply approved relative paths only.
- TOU check: `tu doctor --forward http://127.0.0.1:8028/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8028/mcp --name validation-cellrank --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation cellrank`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-cellrank-remote-tool/SKILL.md).

Serves [CellRank 2](https://cellrank.readthedocs.io/) (Weiler et al., *Nature Methods* 2024; original CellRank: Lange et al., *Nature Methods* 2022) — unified single-cell fate mapping — as the ToolUniverse remote tool `run_cellrank_fate`.

CellRank builds a Markov transition matrix over cells using a **kernel**, then coarse-grains it with a **GPCCA estimator** to find terminal macrostates and compute, for every cell, its probability of reaching each terminal state. The kernel is selectable:

- `connectivity` (default) — uses only the kNN graph, so it runs on any dataset (computed automatically if neighbors are absent).
- `pseudotime` — directs transitions along a precomputed pseudotime (`pseudotime_key` in `obs`, e.g. `dpt_pseudotime`).
- `velocity` — uses RNA velocity layers (requires scVelo-computed velocity).

Served remotely (not bundled) because `cellrank` pulls in scanpy/anndata + scikit-learn + pyGPCCA (+ scVelo for the velocity kernel). Small datasets run on CPU.

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
tu remote share cellrank
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
tu remote share cellrank --name my-cellrank-remote --workers 1
```

Use `tu remote run cellrank` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Deploy

```bash
pip install -r requirements.txt          # cellrank + scanpy
python cellrank_tool.py                   # starts the MCP server on 127.0.0.1:8028
```

Input is referenced by `adata_path` (a server-accessible `.h5ad`), since
single-cell matrices are large. Expose remotely only behind
`TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/cellrank_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
