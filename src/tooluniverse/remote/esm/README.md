# ESM Cambrian (ESMC) Protein Embedding Tool

## Overview

The [ESM Cambrian (ESMC)](https://github.com/evolutionaryscale/esm) tool from EvolutionaryScale provides contextualized protein embeddings using protein language models. ESM-C generates 960-dimensional embeddings (mean-pooled across tokens) that capture information about protein structure and function.

---

## For Researchers: Using ESM-C

### Quick Start (3 steps)

1. **Set the environment variable** on the machine where you're using ToolUniverse:
   ```bash
   export ESM_MCP_SERVER_HOST="<server-address>"
   ```
   Replace `<server-address>` with the hostname or IP address where the ESM MCP server is running.
   - Examples: `localhost`, `192.168.1.100`, or your server's hostname

2. **That's it!** ToolUniverse automatically discovers and loads the `esm_embed_sequence` tool.

3. **Use the tool** like any other ToolUniverse tool:
   - **Input**: Protein amino acid sequence (e.g., "MKTAYIAK...")
   - **Output**: 960-dimensional embedding vector
   ```json
   {
     "model": "esmc_300m",
     "embedding_dim": 960,
     "embedding": [0.123, -0.456, 0.789, ...]
   }
   ```

---

## For Server Operators: Deployment

### Prerequisites

- Python 3.10+
- Sufficient disk space for model weights

### Installation

```bash
# Create a virtual environment
uv venv esm --python 3.10
source esm/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

### Running the Server

```bash
python esm_tool.py
```

The server:
- Registers the ESM-C embedding tool via `@register_mcp_tool` decorator
- Starts on `http://0.0.0.0:8008`
- Lazy-loads the ESM-C model on first request
- Listens for embedding requests via HTTP/MCP protocol

### Advanced Configuration

#### Change Model Size

Edit `get_client()` in `esm_tool.py`:

```python
def get_client():
    global _ESM_CLIENT
    if _ESM_CLIENT is None:
        _ESM_CLIENT = ESMC.from_pretrained("esmc_600m")  # or esmc_6b
        _ESM_CLIENT.eval()
    return _ESM_CLIENT
```

#### Change Server Port

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
