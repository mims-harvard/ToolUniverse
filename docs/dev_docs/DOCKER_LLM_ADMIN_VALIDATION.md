# Docker LLM Administrator Provisioning

This integration gives an administrator a bounded way to start a reviewed local
container and publish one fixed ToolUniverse inference client. Container lifecycle
operations are deliberately absent from the agent tool registry.

## What Changed From PR #32

The earlier implementation exposed image selection, the Docker executable, volumes,
environment variables, extra Docker arguments, host binding, container ports, and
container replacement through an agent-callable compose tool. This implementation
does none of those things.

An administrator supplies a strict JSON profile. The CLI accepts only the profile,
a loopback host port, a constrained container name, and a lifecycle command. Unknown
profile fields fail validation, so volumes, arbitrary Docker flags, host networking,
privileged mode, alternate executables, and arbitrary server URLs have no input path.

## Required Policy

`TOOLUNIVERSE_DOCKER_ALLOWED_IMAGES` must contain the profile's exact image reference.
The provisioner uses `--pull never`, resolves the local image to its content ID before
start, and checks the running container against that ID afterward. It clears Docker
environment overrides and rejects saved contexts whose daemon endpoint is not a local
Unix socket or Windows named pipe.

Every new container has these enforced settings:

- host port published only on `127.0.0.1`
- read-only root filesystem plus a bounded `/tmp` tmpfs
- all Linux capabilities dropped
- `no-new-privileges` enabled
- privileged, host-network, host-PID, host-IPC, and bind-mount configurations rejected
- reviewed CPU, memory, process, health, prompt, response, and request-time limits

After Docker reports the expected labels, image ID, port binding, and isolation flags,
the provisioner performs a redirect-free, proxy-free JSON health request. The health
payload must return the exact reviewed service identity. Only then is a hash-bound
ToolUniverse client record written atomically with owner-only file permissions.

## Administration CLI

The fixture profile demonstrates the complete schema:
`tests/fixtures/docker_llm_smoke/profile.json`.

```console
export TOOLUNIVERSE_DOCKER_ALLOWED_IMAGES='registry.example/reviewed-llm@sha256:...'

tooluniverse-docker-llm-admin --profile reviewed-profile.json plan
tooluniverse-docker-llm-admin --profile reviewed-profile.json --host-port 9000 start
tooluniverse-docker-llm-admin --profile reviewed-profile.json --host-port 9000 status
tooluniverse-docker-llm-admin --profile reviewed-profile.json --host-port 9000 stop
tooluniverse-docker-llm-admin --profile reviewed-profile.json --host-port 9000 remove --yes
```

`plan` does not contact Docker. `start`, `status`, `stop`, and `remove` validate the
same profile and exact container identity. Removal requires `--yes` and refuses to
touch a container without the matching management labels, profile hash, image ID,
port binding, and security settings.

Loading the resulting inference tool is also explicit:

```python
from tooluniverse import ToolUniverse
from tooluniverse.remote.docker_llm import load_provisioned_tool

tu = ToolUniverse()
load_provisioned_tool(tu, "ReviewedDockerEvidenceTool")
result = tu.run_one_function(
    {
        "name": "ReviewedDockerEvidenceTool",
        "arguments": {"prompt": "Synthesize these reviewed evidence records..."},
    },
    use_cache=False,
)
```

The client can call only the generated `http://127.0.0.1:<port>/<reviewed-path>`
endpoint. Before every inference it rechecks the reviewed health endpoint on the same
port and requires the exact service and model identity, preventing a stopped container
from silently falling through to an unrelated loopback service. It disables proxy
inheritance and redirects, caps the response at 1 MB, requires JSON and exactly one
response choice, and reports image, profile, health, and payload evidence as provenance.

## Real Container Case

`examples/docker_llm/run_smoke_case.py` builds a non-root, dependency-free fixture
image and exercises this sequence:

1. plan the exact command;
2. start and inspect the constrained container;
3. verify service identity through `/health`;
4. publish and explicitly load the client into a fresh ToolUniverse instance;
5. send a long, six-section pharmacovigilance evidence prompt;
6. verify the service received the exact prompt SHA-256;
7. stop, re-inspect, remove, and confirm absence.

The fixture implements the same OpenAI-compatible transport contract but is
deterministic infrastructure, not a real language model. Therefore the case proves
lifecycle, isolation, registration, payload integrity, response bounds, and cleanup;
it does not claim model-quality or scientific validation.

The local development machine used for this change does not have Docker installed.
The dedicated GitHub Actions job completed the real container case on Docker 28.0.4.
Its validated outputs are checked in at `examples/docker_llm/artifacts/` and are also
uploaded by every run as `docker-llm-smoke-evidence`.

## Local Verification

```console
PYTHONPATH=src python -m pytest \
  tests/unit/test_docker_llm_provision.py \
  tests/unit/test_docker_llm_cli.py -q

PYTHONPATH=src python examples/docker_llm/run_smoke_case.py
```

Provision records use SHA-256 for tamper evidence, not digital signatures. Local
administrators who can change the workspace or allowlist remain inside the trust
boundary, as do the reviewed image contents and the local Docker daemon.
