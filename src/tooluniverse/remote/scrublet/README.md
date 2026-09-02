# Scrublet Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> Installation, direct/live MCP calls, traversal rejection, and prior same-host concurrency levels 1, 2, and 4 passed. Two current 500-cell calls returned finite aligned results and 429 synthetic predictions; that 85.8% fixture rate is not an accuracy result. Public publication, cross-user isolation, representative accuracy, cancellation, and recovery remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_scrublet_doublets`
- Start: `python -m tooluniverse.remote.scrublet.scrublet_tool`
- Endpoint: `http://127.0.0.1:8015/mcp`
- Provider configuration: set `TOOLUNIVERSE_REMOTE_DATA_ROOT`; the approved H5AD input must contain suitable raw counts.
- TOU check: `tu doctor --forward http://127.0.0.1:8015/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8015/mcp --name validation-scrublet --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Synthetic doublet rate is recorded without an accuracy claim.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation scrublet`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-scrublet-remote-tool/SKILL.md).

Serves [Scrublet](https://github.com/swolock/scrublet) (Wolock et al., *Cell Systems* 2019) — single-cell RNA-seq doublet detection — as a ToolUniverse remote tool: `run_scrublet_doublets` (per-cell doublet scores + boolean predictions).

Served remotely (not bundled) because it pulls in the `scanpy`/`anndata` single-cell stack plus `scikit-image` for the KNN/UMAP machinery. Scrublet operates on **raw counts**, not normalized/log-transformed data.

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
tu remote share scrublet
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
tu remote share scrublet --name my-scrublet-remote --workers 1
```

Use `tu remote run scrublet` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Deploy

```bash
pip install -r requirements.txt          # scanpy + scikit-image + anndata
export TOOLUNIVERSE_REMOTE_DATA_ROOT=/srv/tooluniverse/scrublet-data
python scrublet_tool.py                    # starts the MCP server on 127.0.0.1:8015
```

Place raw-count `.h5ad` inputs below `TOOLUNIVERSE_REMOTE_DATA_ROOT` and pass
either a relative file name or an absolute path contained by that directory.
URLs, traversal, directories, other suffixes, and symlinks that escape the
directory are rejected. Expose remotely only behind `TOOLUNIVERSE_API_TOKEN`
(SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/scrublet_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
