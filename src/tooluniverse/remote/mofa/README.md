# MOFA+ Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> MOFA+ 0.7.4, loopback discovery/call, and non-finite-input rejection passed; the 30-sample/two-view fixture returned two non-degenerate factors and variance components. Public publication, cross-user isolation, representative multi-omics accuracy, broad concurrency, and recovery remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_mofa_factors`
- Start: `python -m tooluniverse.remote.mofa.mofa_tool`
- Endpoint: `http://127.0.0.1:8024/mcp`
- Provider configuration: no credential is needed for inline views, but private matrices must not be sent to shared deployments. Inputs and outputs are bounded by the published schema.
- TOU check: `tu doctor --forward http://127.0.0.1:8024/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8024/mcp --name validation-mofa --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation mofa`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-mofa-remote-tool/SKILL.md).

Serves [MOFA+](https://biofam.github.io/MOFA2/) (Multi-Omics Factor Analysis v2; Argelaguet et al., *Genome Biology* 2020) — unsupervised integration of multiple omics layers measured on the **same** samples — as a ToolUniverse remote tool: `run_mofa_factors` (per-sample latent factor matrix + variance explained per view/factor).

Served remotely (not bundled) because `mofapy2` carries a heavy probabilistic Bayesian inference stack on top of numpy/scipy.

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
tu remote share mofa
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
tu remote share mofa --name my-mofa-remote --workers 1
```

Use `tu remote run mofa` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Deploy

```bash
pip install -r requirements.txt          # mofapy2 + numpy
python mofa_tool.py                        # starts the MCP server on 127.0.0.1:8024
```

Inputs are inlined as a `views` object — `{view_name: {feature: [value_per_sample]}}` — with one matrix per omics view over the shared sample set. Every feature list must have one value per sample, in the same sample order. Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/mofa_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
