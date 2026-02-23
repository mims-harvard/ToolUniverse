# ESM Cambrian (ESMC) Protein Embedding Tool

## Overview

The [ESM Cambrian (ESMC)](https://github.com/evolutionaryscale/esm) tool from EvolutionaryScale provides contextualized protein embeddings using protein language models. ESM-C generates 960-dimensional embeddings (mean-pooled across tokens) that capture information about protein structure and function.

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
uv pip install -r src/tooluniverse/remote/esm/requirements.txt
```

**Start the server:**

```bash
python src/tooluniverse/remote/esm/esm_tool.py
```

The server will start on port 8008. Leave it running in this terminal. If running locally, you are done here. If using a remote server, ask the server administrator to run these steps and provide you with the server's IP address.

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
mcp_config={"host": "0.0.0.0", "port": 8009}  # Change port number
```

Then update `src/tooluniverse/data/mcp_auto_loader_esm.json`:

```json
{
  "server_url": "http://localhost:8009/mcp"
}
```

## References

- [ESM Cambrian Blog](https://www.evolutionaryscale.ai/blog/esm-cambrian)
- [Official ESM Repository](https://github.com/evolutionaryscale/esm)
- [ESM-C Models on Hugging Face](https://huggingface.co/EvolutionaryScale)
- [ToolUniverse Remote Tools Tutorial](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/remote_tools/tutorial.html)

## Citation

For information on how to cite ESM-C, please refer to the [official EvolutionaryScale announcement](https://www.evolutionaryscale.ai/blog/esm-cambrian) and [ESM repository](https://github.com/evolutionaryscale/esm).
