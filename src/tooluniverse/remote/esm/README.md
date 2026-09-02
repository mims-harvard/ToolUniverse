# ESM Cambrian (ESMC) Protein Embedding Tool

## TOU validation and deployment status (2026-08-16)

> The pinned official ESM source and esmc_300m checkpoint loaded on the GB10; a live loopback call returned a finite 960-dimensional embedding. Public publication, cross-user isolation, broad concurrency, recovery, and embedding-quality validation remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `esm_embed_sequence`
- Start: `python -m tooluniverse.remote.esm.esm_tool`
- Endpoint: `http://127.0.0.1:8008/mcp`
- Provider configuration: keep `HF_HOME` and `TORCH_HOME` under provider-owned caches. Use the pinned official source revision and one worker until GPU load/recovery are measured.
- TOU check: `tu doctor --forward http://127.0.0.1:8008/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8008/mcp --name validation-esm --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public publication and independent-caller testing were not run. ESM is currently auto-discovered rather than represented by a per-operation remote manifest.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation esm`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-esm-remote-tool/SKILL.md).

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
tu remote share esm
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
tu remote share esm --name my-esm-remote --workers 1
```

Use `tu remote run esm` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Overview

The [ESM Cambrian (ESMC)](https://github.com/Biohub/esm) tool provides
contextualized protein embeddings. ESM-C generates 960-dimensional embeddings
mean-pooled over residue tokens (excluding BOS/EOS).

## Setup

### Step 1: Install and Start the ESM Server

**Prerequisites:**
- Python 3.10+
- Sufficient disk space for model weights

**Installation:**

```bash
# Clone the ToolUniverse repository
git clone https://github.com/mims-harvard/ToolUniverse.git
cd ToolUniverse

# Create a virtual environment
uv venv esm --python 3.10
source esm/bin/activate

# Install ToolUniverse package and ESM dependencies
uv pip install -e .
# requirements.txt pins the reviewed official Biohub/esm commit.
uv pip install -r src/tooluniverse/remote/esm/requirements.txt
```

**Start the server:**

```bash
python src/tooluniverse/remote/esm/esm_tool.py
```

The server starts on loopback port 8008, which is suitable for a local Connect
relay. Direct network exposure requires `TOOLUNIVERSE_API_TOKEN` and an
explicit non-loopback server configuration.

**In a new terminal**, navigate to the ToolUniverse directory and activate your virtual environment:

```bash
cd ToolUniverse  # Go back to the same ToolUniverse directory
source esm/bin/activate
```

Then follow one of the Usage Options below.


## Usage Options

### Option 1: Use ESM via LLM with MCP Support

Connect any LLM client that supports MCP by pointing it to ToolUniverse with your server location:

```bash
export ESM_MCP_SERVER_HOST=localhost  # or your server's IP if remote
```

Then configure your LLM client to use ToolUniverse as an MCP server with the `ESM_MCP_SERVER_HOST` environment variable set.

### Example: Using with Claude Code

Here's how to use ESM through Claude Code (an example of Option 1):

**1. Add the MCP Server to Claude:**

```bash
claude mcp add tooluniverse --env ESM_MCP_SERVER_HOST=$ESM_MCP_SERVER_HOST -- uvx tooluniverse
```

**2. Start Claude and use the tool:**

```bash
claude
```

Ask Claude:
```
Give me the embedding for the protein sequence: MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVV
```

Claude will automatically use the `esm_embed_sequence` tool to generate the embedding.

### Option 2: Use ESM via ToolUniverse Script (Direct Python)

Use ESM directly in Python scripts by setting the server location:

```bash
export ESM_MCP_SERVER_HOST=localhost  # or your server's IP if remote
```

**Python script example:**

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

embedding = tu.run_one_function({
    "name": "esm_embed_sequence",
    "arguments": {
        "sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVV"
    }
})

print(embedding)
```


The tool will return:

```json
{
  "model": "esmc_300m",
  "embedding_dim": 960,
  "embedding": [0.123, -0.456, 0.789, ...]
}
```

## Advanced Configuration

### Change Model Size

Edit `get_client()` in `esm_tool.py`:

```python
def get_client():
    global _ESM_CLIENT
    if _ESM_CLIENT is None:
        _ESM_CLIENT = ESMC.from_pretrained("esmc_600m")  # or esmc_6b
        _ESM_CLIENT.eval()
    return _ESM_CLIENT
```

### Change Server Port

Edit the `@register_mcp_tool` decorator in `esm_tool.py`:

```python
mcp_config={"host": "127.0.0.1", "port": 8009}  # Keep loopback; change only the port
```

Then update `src/tooluniverse/data/mcp_auto_loader_esm.json`:

```json
{
  "server_url": "http://localhost:8009/mcp"
}
```

## References

- [ESM Cambrian Blog](https://www.evolutionaryscale.ai/blog/esm-cambrian)
- [Official ESM Repository](https://github.com/Biohub/esm)
- [ESM-C Models on Hugging Face](https://huggingface.co/Biohub)
- [ToolUniverse Remote Tools Tutorial](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/remote_tools/tutorial.html)

## Citation

For information on how to cite ESM-C, please refer to the [official EvolutionaryScale announcement](https://www.evolutionaryscale.ai/blog/esm-cambrian) and [ESM repository](https://github.com/evolutionaryscale/esm).
