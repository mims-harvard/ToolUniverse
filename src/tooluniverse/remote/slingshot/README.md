# Slingshot Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> R 4.4.3/Slingshot 2.14.0, loopback discovery, and a deterministic call passed with two lineages and bounded aligned pseudotime for 240 cells. Public publication, cross-user isolation, representative biology, broad concurrency, and recovery remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_slingshot_trajectory`
- Start: `python -m tooluniverse.remote.slingshot.slingshot_tool`
- Endpoint: `http://127.0.0.1:8030/mcp`
- Provider configuration: set `TOOLUNIVERSE_REMOTE_DATA_ROOT` and optionally `RSCRIPT_BIN`; required `obs`/`obsm` keys must exist in the approved H5AD input.
- TOU check: `tu doctor --forward http://127.0.0.1:8030/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8030/mcp --name validation-slingshot --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation slingshot`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-slingshot-remote-tool/SKILL.md).

Serves [Slingshot](https://bioconductor.org/packages/slingshot/) (Street et al., *BMC Genomics* 2018) — single-cell lineage and pseudotime inference — as the ToolUniverse remote tool `run_slingshot_trajectory`.

Given a low-dimensional embedding and cluster labels, Slingshot builds a minimum spanning tree on the cluster centroids to order them into smooth lineages, fits simultaneous principal curves, and assigns each cell a pseudotime along every lineage it belongs to. It is robust for tree-shaped differentiation and a standard trajectory method.

Served remotely because the engine is **R/Bioconductor** (`slingshot`). The Python side reads the `.h5ad` with scanpy, extracts the chosen embedding (`obsm`) and cluster labels (`obs`), and hands them to the bundled `slingshot_trajectory.R` (CSV interchange — no zellkonverter/basilisk required).

Anchor directionality with `start_cluster` (the known root) and/or `end_clusters` (known terminal fates) when available — strongly recommended, since otherwise lineage orientation is arbitrary.

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
tu remote share slingshot
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
tu remote share slingshot --name my-slingshot-remote --workers 1
```

Use `tu remote run slingshot` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Deploy

```bash
pip install -r requirements.txt            # scanpy + numpy (Python side)
Rscript -e 'BiocManager::install(c("slingshot","jsonlite"))'   # R side
python slingshot_tool.py                    # starts the MCP server on 127.0.0.1:8030
```

`Rscript` must be on `PATH` (or set `RSCRIPT_BIN`). Expose remotely only behind
`TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/slingshot_tools.json`
(`type: RemoteTool`).
