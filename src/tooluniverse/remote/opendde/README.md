# OpenDDE remote tool

## TOU validation and deployment status (2026-08-16)

> OpenDDE 1.1.1 ran on the NVIDIA GB10 (aarch64, cc 12.1, 130.6 GB unified, driver 580.173.02) through the venv route on CPython 3.12.10 with torch 2.7.1+cu128, under kit mode `off`, reserving a measured 22.55 GiB of VRAM. `provider.toml`'s header carries the measurements and their caveats. Public publication, cross-user isolation, concurrency, recovery and biological accuracy are unvalidated; keep this deployment private.

- Operation: `opendde_fold`
- Start: `python -m tooluniverse.remote.opendde.opendde_tool`
- Endpoint: `http://127.0.0.1:8058/mcp`
- Provider configuration: `OPENDDE_ROOT_DIR` names the provider-owned tree holding the weights, and they are declared with a size and a sha256 and verified before the worker starts. Keep provider data, weights, caches and credentials outside Git. Use one worker: the resident worker serves one request at a time by design.
- TOU check: `tu doctor --forward http://127.0.0.1:8058/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8058/mcp --name validation-opendde --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation opendde`. Add `--check-provider-env` before launch, `--live`
after launch, and `--check-connect-prereqs` before sharing. Live preflight
checks exact MCP discovery only; it does not run or validate a model.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays
online and all 41 operations discoverable. It imported each implementation as
unpublished owner draft(s), configured a 120-second timeout, and invoked it
through `/expert-sessions/{id}/test`. **This implementation was added after
that matrix and was not part of it**, so none of that evidence covers it: it has
not been exercised through the Platform at all, and everything above was
measured locally, on one card, through the loopback endpoint. Public
publication, independent-caller authorization/isolation, broad saturation and
persistent supervision are unvalidated here.

See the [complete setup and verification guide](../../../../skills/setup-opendde-remote-tool/SKILL.md).

Serves [OpenDDE](https://github.com/aurekalabs/opendde) 1.1.1 (Aureka) — AlphaFold3-class all-atom structure prediction for a complex of protein, nucleic-acid, ligand and ion entities — as the ToolUniverse remote tool `opendde_fold`.

## Authorize once, then share with one short command

Run once per machine, and again after key rotation:

```bash
tu remote login
```

Then each private share is:

```bash
tu remote share opendde
```

Override the defaults only when needed:

```bash
tu remote share opendde --name my-opendde-remote --workers 1
```

Sharing automatically starts the browser flow when the key is missing,
expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced;
unset or correct it, then run `tu remote login`. Non-interactive jobs also
fail fast. Use `tu remote logout` to remove only the locally stored key.
