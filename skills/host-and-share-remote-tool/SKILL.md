---
name: host-and-share-remote-tool
description: Host, validate, and privately share a user's own model, Python function, workflow, or existing Streamable HTTP MCP endpoint through ToolUniverse Platform. Use when turning a local CPU/GPU workload or lab endpoint into a stable TU remote tool, diagnosing its setup, or preparing it for controlled sharing.
---

# Host and share a remote tool

Use this workflow for user-owned code and infrastructure. Keep the workload on the user's computer or lab server; ToolUniverse Platform receives only the MCP tool manifest and relayed calls.

## Choose the shortest path

- Python function, model, database query, or workflow: wrap only the callable with `@remote_tool`, then use `tu serve ... --share`.
- Existing Streamable HTTP MCP server: keep it running on loopback and use `tuplatform-relay --forward ...`.
- One of ToolUniverse's 30 reviewed scientific implementations: use its implementation-specific `setup-<name>-remote-tool` skill and `tu remote share <name>` instead.

Do not treat an arbitrary REST endpoint as MCP. Wrap it in a typed Python function first, or put a reviewed MCP adapter in front of it.

## 1. Install the reviewed clients

Open ToolUniverse Connect, go to **My Computers → Connect a computer**, choose the Python or existing-MCP path, and copy the immutable install command shown there. Run it in a new Python 3.12 virtual environment. The command pins both the ToolUniverse and relay sources; do not replace the pins with a moving branch.

Confirm the expected commands exist:

~~~bash
tu --help
tuplatform-relay --help
~~~

Stop if installation or source access fails. A locally working model does not prove that sharing works.

## 2A. Wrap a Python model or function

Create `my_tool.py`. Load fixed model artifacts from provider-owned configuration; do not accept arbitrary caller-controlled filesystem paths or model identifiers.

~~~python
from tooluniverse import remote_tool

@remote_tool
def predict(sequence: str, threshold: float = 0.5) -> dict:
    """Score one sequence with the locally hosted model."""
    if not isinstance(sequence, str) or not 1 <= len(sequence) <= 10_000:
        raise ValueError("sequence must contain 1 to 10,000 characters")
    score = min(len(sequence) / 100.0, 1.0)  # replace with the real model call
    return {"score": score, "passes": score >= threshold}
~~~

Use bounded, JSON-serializable inputs and outputs. Return stable field names and sanitized errors; never return secrets, local paths, stack traces, raw model objects, or unbounded tensors/files.

For a GPU model, verify the actual provider environment before launch:

~~~bash
python -c 'import torch; assert torch.cuda.is_available(); x=torch.arange(8, device="cuda"); print(torch.cuda.get_device_name(0), x.sum().item())'
~~~

This proves only CUDA tensor execution. Run a small, real inference below before claiming the model works.

## 2B. Use an existing MCP endpoint

Start the Streamable HTTP MCP server on loopback, for example `http://127.0.0.1:8080/mcp`. Confirm it implements MCP initialization, `tools/list`, and `tools/call`; a health endpoint alone is insufficient.

Do not forward a public endpoint containing embedded credentials. Keep provider API keys in the provider process and use the relay only for MCP traffic.

## 3. Validate locally before sharing

For Python mode, start without `--share`:

~~~bash
tu serve my_tool.py --host 127.0.0.1 --port 8080
~~~

From a second terminal, perform exact discovery and one semantic call:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8080/mcp") as client:
        tools = await client.list_tools()
        print([tool.name for tool in tools])
        result = await client.call_tool("predict", {"sequence": "ACGT", "threshold": 0.01})
        print(result)

asyncio.run(main())
PY
~~~

Check the exact tool name and schema, meaningful finite output, invalid-input behavior, latency, and the absence of secrets or local paths. For a real ML model, record evidence that the model loaded and executed on the intended CPU/GPU; discovery alone is not model validation.

## 4. Share privately with browser authorization

Stop the local-only command, then use one foreground command.

Python path:

~~~bash
tu serve my_tool.py --share --name "My Model" --service https://tooluniverse-backend.onrender.com
~~~

Existing MCP path:

~~~bash
tuplatform-relay --forward http://127.0.0.1:8080 --name "My Server" --service https://tooluniverse-backend.onrender.com
~~~

When no valid key is stored, the CLI opens a browser authorization link. Approve the matching computer name and code. No copy/paste is required; the computer-only key is verified and stored in a local `0600` file without being displayed. On a headless server add `--no-browser` and open the printed link elsewhere. If the first request expires, the CLI creates one replacement link automatically.

An explicit invalid `TOOLUNIVERSE_SERVICE_KEY` and all non-interactive jobs fail fast. Fix or unset the environment value; do not silently replace production secrets. Use protected secret injection only for unattended service accounts.

## 5. Verify through TU Platform

Wait until **My Computers** shows the server online. As its owner, import or open the remote tool and make one small semantic call through TU Platform. Confirm the platform result matches the local result. Record local discovery, local call, online status, platform discovery, platform call, model/device evidence, and timestamps separately.

Keep the connection private by default. Public marketplace publication, another user's authorization/isolation, load behavior, and long-running supervision are separate validations; do not claim them from an owner-only smoke test.

## 6. Stabilize and operate

- Start with one relay worker for GPU or stateful workloads. Increase only after measuring cold start, warm latency, RAM/VRAM, queueing, timeouts, cancellation, and recovery at parallel levels 1, 2, 4, and 8.
- Load the model once per provider process and bound input size, response size, download size, runtime, and concurrency.
- Bind locally to loopback. The relay is outbound; no public IP or firewall change is needed.
- Keep model weights, data, caches, and credentials outside Git. Pin dependencies and document licenses.
- Stop foreground sharing with Ctrl-C. For persistent operation, use the `tuplatform-service install` command shown by the website, then verify its user service and logs.

Remove only the local login with `tu remote logout`. Revoke the computer-only platform connection and then remove the local copy with:

~~~bash
tu remote logout --revoke
~~~

For an SDK-only existing-MCP setup, use `tuplatform-auth logout --revoke`. Revocation intentionally leaves the server record offline for owner inspection; delete that record separately in **My Computers** if desired.

## Failure reporting

Classify outcomes precisely: installation blocked, provider dependency blocked, GPU unavailable, credential rejected, local discovery passed, real inference passed, relay passed, or platform semantic call passed. Never convert a blocked or discovery-only result into "working."
