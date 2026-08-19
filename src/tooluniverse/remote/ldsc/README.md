# LDSC Remote Tool (MCP Server)

## TOU validation and deployment status (2026-08-16)

> CBIIT LDSC and its official simulation ran through live loopback MCP; heritability and genetic-correlation calls returned finite parsed statistics. Real population panels, public publication, cross-user isolation, broad concurrency, and biological validation remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operations: `run_ldsc_heritability`, `run_ldsc_genetic_correlation`
- Start: `python -m tooluniverse.remote.ldsc.ldsc_tool`
- Endpoint: `http://127.0.0.1:8013/mcp`
- Provider configuration: set `TOOLUNIVERSE_REMOTE_DATA_ROOT`, `LDSC_DIR`, and `LDSC_REF_DIR` to reviewed provider resources; callers supply approved relative paths only.
- TOU check: `tu doctor --forward http://127.0.0.1:8013/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8013/mcp --name validation-ldsc --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation ldsc`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-ldsc-remote-tool/SKILL.md).

Serves [LDSC](https://github.com/CBIIT/ldsc) (LD Score regression; Bulik-Sullivan et al., *Nature Genetics* 2015) — SNP-heritability and genetic correlation from GWAS summary statistics — as ToolUniverse remote tools: `run_ldsc_heritability` and `run_ldsc_genetic_correlation`.

Served remotely (not bundled) because it needs the maintained Python-3 engine
(NCI `CBIIT/ldsc`, the successor to the frozen Python-2.7 `bulik/ldsc`) plus
multi-GB precomputed LD-score reference panels. Hosted alternative for users who
cannot stage the panels: NCI's [LDscore web tool](https://ldlink.nih.gov/ldscore).

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
tu remote share ldsc
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
tu remote share ldsc --name my-ldsc-remote --workers 1
```

Use `tu remote run ldsc` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Deploy

```bash
git clone -b ldsc39 https://github.com/CBIIT/ldsc.git /opt/ldsc   # Python-3 engine
pip install -r requirements.txt                                    # numpy scipy pandas bitarray
# Stage LD-score panels (Zenodo): eur_w_ld_chr (record 8182036),
#   S-LDSC baseline set (DOI 10.5281/zenodo.10515792) for partitioned h2.
export LDSC_DIR=/opt/ldsc
export LDSC_REF_DIR=/data/ldsc          # contains eur_w_ld_chr/, w_hm3.snplist, ...
python ldsc_tool.py                      # starts the MCP server on 127.0.0.1:8013
```

Sumstats must be pre-munged (`munge_sumstats.py --merge-alleles w_hm3.snplist`).
Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definitions: `src/tooluniverse/data/remote_tools/ldsc_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
