# PAGA Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> Scanpy/PAGA, loopback discovery/call, and invalid-cluster rejection passed on connected deterministic trajectories, including a finite 3 x 3 matrix. A fully disconnected fixture still triggers a sanitized upstream failure. Public publication, cross-user isolation, representative accuracy, broad concurrency, and recovery remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_paga_trajectory`
- Start: `python -m tooluniverse.remote.paga.paga_tool`
- Endpoint: `http://127.0.0.1:8022/mcp`
- Provider configuration: set `TOOLUNIVERSE_REMOTE_DATA_ROOT`; `cluster_key` must contain bounded valid categories in an approved H5AD input.
- TOU check: `tu doctor --forward http://127.0.0.1:8022/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8022/mcp --name validation-paga --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. The disconnected-fixture failure is not counted as a pass.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation paga`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-paga-remote-tool/SKILL.md).

Serves [PAGA](https://scanpy.readthedocs.io/en/stable/generated/scanpy.tl.paga.html)
(Partition-based Graph Abstraction; Wolf et al., *Genome Biology* 2019) as a
ToolUniverse remote tool: `run_paga_trajectory` — estimates connectivity between
single-cell clusters and reports the strongest cluster pairs (the trajectory
backbone).

Served remotely (not bundled) because PAGA pulls in `scanpy` + anndata + igraph +
leidenalg. Computation is cheap once a neighbors graph exists; if one is absent
the tool log-normalizes, runs PCA, and builds neighbors before `sc.tl.paga`.

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
tu remote share paga
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
tu remote share paga --name my-paga-remote --workers 1
```

Use `tu remote run paga` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Deploy

```bash
pip install -r requirements.txt          # scanpy + igraph + leidenalg
python paga_tool.py                        # starts the MCP server on 127.0.0.1:8022
```

Inputs are referenced by `adata_path` (a server-accessible `.h5ad` whose `obs`
carries the requested `cluster_key`), since single-cell matrices are large. The
cluster x cluster connectivity matrix returned is small and bounded. Expose
remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/paga_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
