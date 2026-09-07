# Monocle3 Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> R 4.4.3/Monocle3 1.4.27, loopback discovery, and two deterministic 240-cell calls passed with finite pseudotime for all cells; both disclosed the acyclic fallback after the upstream loop-closing bug. Public publication, cross-user isolation, representative biology, broad concurrency, and recovery remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_monocle3_pseudotime`
- Start: `python -m tooluniverse.remote.monocle3.monocle3_tool`
- Endpoint: `http://127.0.0.1:8031/mcp`
- Provider configuration: set `TOOLUNIVERSE_REMOTE_DATA_ROOT` and optionally `RSCRIPT_BIN`; choose scientifically defensible roots and approved relative H5AD inputs.
- TOU check: `tu doctor --forward http://127.0.0.1:8031/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8031/mcp --name validation-monocle3 --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. The disclosed `close_loop_false_fallback` is a real runtime fallback, not a concealed default-path pass.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation monocle3`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-monocle3-remote-tool/SKILL.md).

Serves [Monocle3](https://cole-trapnell-lab.github.io/monocle3/) (Cao et al., *Nature* 2019; Trapnell lab) — single-cell pseudotime / trajectory inference — as the ToolUniverse remote tool `run_monocle3_pseudotime`.

Monocle3 learns a **principal graph** through a UMAP embedding (capturing branches and loops) and orders cells in pseudotime from a chosen root. Unlike Slingshot (which orders pre-computed clusters), Monocle3 learns its own graph, and is the standard Trapnell-lab pseudotime tool.

Served remotely because the engine is **R/Bioconductor** (`monocle3`). The Python side reads the `.h5ad` with scanpy and hands the **raw count** matrix to the bundled `monocle3_pseudotime.R` (MatrixMarket interchange — no zellkonverter/basilisk). The R script runs the standard `new_cell_data_set → preprocess_cds → reduce_dimension → cluster_cells → learn_graph → order_cells` pipeline.

Root the trajectory with `root_cluster` (all cells of a named input cluster — requires `cluster_key`) or explicit `root_cells`.

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
tu remote share monocle3
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
tu remote share monocle3 --name my-monocle3-remote --workers 1
```

Use `tu remote run monocle3` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Deploy

```bash
pip install -r requirements.txt            # scanpy + scipy (Python side)
# R side — monocle3 needs Bioconductor deps + system libs (gdal/geos/proj via terra):
Rscript -e 'BiocManager::install(c("SingleCellExperiment","batchelor","terra","ggrastr","leidenbase"))'
Rscript -e 'remotes::install_github("cole-trapnell-lab/monocle3")'
python monocle3_tool.py                      # starts the MCP server on 127.0.0.1:8031
```

`Rscript` must be on `PATH` (or set `RSCRIPT_BIN`). Expose remotely only behind
`TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/monocle3_tools.json`
(`type: RemoteTool`).
