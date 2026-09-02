# MACS3 Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> Compiled MACS3 3.0.4, loopback discovery/call, and provider-root rejection passed; the documented no-model/fixed-extension synthetic BED call returned three peaks. Public publication, cross-user isolation, representative accuracy, broad concurrency, cancellation, and recovery remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `run_macs3_callpeak`
- Start: `python -m tooluniverse.remote.macs3.macs3_tool`
- Endpoint: `http://127.0.0.1:8021/mcp`
- Provider configuration: set `TOOLUNIVERSE_REMOTE_DATA_ROOT` for provider-owned BED/BAM inputs. Treatment/control paths are approved relative paths only.
- TOU check: `tu doctor --forward http://127.0.0.1:8021/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8021/mcp --name validation-macs3 --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation macs3`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-macs3-remote-tool/SKILL.md).

Serves [MACS3](https://macs3-project.github.io/MACS/) (Model-based Analysis of ChIP-Seq; Zhang et al., *Genome Biology* 2008; the macs3-project Python-3 successor) — the field-standard ChIP-seq / ATAC-seq peak caller — as a ToolUniverse remote tool: `run_macs3_callpeak`.

Served remotely (not bundled) because it shells out to the `macs3` command-line
engine (a compiled/Cython dependency) and operates on large provider-managed
alignment or fragment files rather than inlined data.

`run_macs3_callpeak` runs `macs3 callpeak -t <treatment> [-c <control>] -f <format> -g <genome_size> -n <name> --outdir <tmp> -q <qvalue>`, parses the resulting `<name>_peaks.narrowPeak` (ENCODE BED6+4), and returns the peak count, the top-N peaks by score, and summary statistics.

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
tu remote share macs3
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
tu remote share macs3 --name my-macs3-remote --workers 1
```

Use `tu remote run macs3` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Deploy

```bash
pip install -r requirements.txt   # macs3
export TOOLUNIVERSE_REMOTE_DATA_ROOT=/srv/tooluniverse-data/macs3
python macs3_tool.py              # starts the MCP server on 127.0.0.1:8021
```

Treatment/control names must resolve to regular files inside
`TOOLUNIVERSE_REMOTE_DATA_ROOT`; URLs, traversal, symlink escapes, and files
outside that directory are rejected. Supported MACS3 formats include
BAM/BED/SAM, BAMPE/BEDPE, legacy text formats, and FRAG data such as
`fragments.tsv.gz`. `AUTO` cannot detect BAMPE, BEDPE, or FRAG, so select those
formats explicitly. Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP
bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/macs3_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
