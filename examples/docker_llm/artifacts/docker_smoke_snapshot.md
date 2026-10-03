# Docker LLM Administrator Smoke Validation

## Result

A locally built service image was allowlisted, started through the administrator-only provisioner, inspected for the reviewed security settings, called through a freshly registered ToolUniverse tool, stopped, and removed.

- Docker server: `28.0.4`
- Image ID: `sha256:6f9459d804c3546c24e184e5099fad16a9aea73c0e957bba4425c08824ded58a`
- Profile SHA-256: `5de381c0fe30a88ddd896b1e830a10ea40f794a09090cd9726e0de7c96fb81d8`
- Tool: `DockerEvidenceSynthesizer`
- Prompt SHA-256 verified by service: **true**
- Response payload SHA-256: `b2cce5603b057dedf95450141f3f60b98bb3dd1205a8dac3b656f3224a6a6dac`

## Inspected Container Policy

| Property | Observed |
| --- | --- |
| Host binding | `127.0.0.1:19090` |
| Read-only root filesystem | `True` |
| Linux capabilities dropped | `ALL` |
| No new privileges | `True` |
| Privileged | `False` |
| Bind mounts | `0` |
| CPU limit | `1.0` |
| Memory limit | `256 MB` |
| PID limit | `64` |

## Complicated Payload

The request contained `199` words across `6` labeled sections covering spontaneous reports, trials, observational evidence, mechanistic evidence, and explicit output constraints. The service returned the exact prompt hash through the OpenAI-compatible endpoint, proving that the complete payload crossed Docker and ToolUniverse without truncation or substitution.

## Boundary

The fixture validates Docker lifecycle, isolation flags, health identity, client publication, request transport, response limits, and cleanup. It is deterministic infrastructure, not a real language model, so it does not validate synthesis quality or scientific conclusions.
