# scANVI Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> scANVI dependencies, GB10 execution, loopback discovery, and a bounded labeled/unlabeled annotation call passed with aligned predictions. Public publication, cross-user isolation, representative accuracy, broad concurrency, and recovery remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_scanvi_annotate`
- Start: `python -m tooluniverse.remote.scanvi.scanvi_tool`
- Endpoint: `http://127.0.0.1:8027/mcp`
- Provider configuration: set `TOOLUNIVERSE_REMOTE_DATA_ROOT`; `labels_key` and `unlabeled_category` must match the approved H5AD annotations.
- TOU check: `tu doctor --forward http://127.0.0.1:8027/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8027/mcp --name validation-scanvi --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation scanvi`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-scanvi-remote-tool/SKILL.md).

Serves [scANVI](https://www.embopress.org/doi/full/10.15252/msb.20209620) (Xu et al., *Molecular Systems Biology* 2021; [scvi-tools](https://www.nature.com/articles/s41587-021-01206-w), Gayoso et al., *Nature Biotechnology* 2022) — semi-supervised single-cell annotation / reference label transfer — as the ToolUniverse remote tool `run_scanvi_annotate`.

scANVI extends scVI: it pretrains scVI on raw UMI counts, then refines the model semi-supervised on the cells that already carry a known label, and predicts a cell type for every cell. Use it to transfer labels onto the unlabeled cells of a partially-annotated dataset.

Served remotely (not bundled) because `scvi-tools` pulls in PyTorch + Lightning + Pyro + scanpy. Small datasets train on CPU; large ones benefit from a GPU.

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
tu remote share scanvi
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
tu remote share scanvi --name my-scanvi-remote --workers 1
```

Use `tu remote run scanvi` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Deploy

```bash
pip install -r requirements.txt          # scvi-tools + scanpy
python scanvi_tool.py                       # starts the MCP server on 127.0.0.1:8027
```

Input is referenced by `adata_path` (a server-accessible `.h5ad` of raw UMI
counts), since single-cell matrices are large. The AnnData must carry a
`labels_key` obs column where some cells hold their known cell type and the
unlabeled cells hold the `unlabeled_category` sentinel (default `"Unknown"`).
Raw counts are preserved in a `counts` layer before training. Expose remotely
only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/scanvi_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
