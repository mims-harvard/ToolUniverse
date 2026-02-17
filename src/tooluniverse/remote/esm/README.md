# ESM Cambrian (ESMC) Protein Embedding Tool

## Overview

The [ESM Cambrian (ESMC)](https://github.com/evolutionaryscale/esm) tool from EvolutionaryScale provides contextualized protein embeddings using state-of-the-art protein language models. ESM-C uses transformer architecture trained on billions of diverse protein sequences to generate high-quality 960-dimensional embeddings (mean-pooled across tokens) that capture biologically meaningful information about protein structure and function.

### Available Models

- **esmc_300m** - 300M parameters (recommended for most use cases, open weight)
- **esmc_600m** - 600M parameters (higher quality embeddings, open weight)
- **esmc_6b** - 6B parameters (highest quality, requires Forge for academic use or AWS SageMaker for commercial use)

## Installation

### Prerequisites

- Python 3.10+
- CUDA 11.8+ (for GPU acceleration, optional but recommended)
- Sufficient disk space for model weights (size varies by model selected)
- For GPU acceleration: NVIDIA GPU with sufficient VRAM (8GB+ recommended for esmc_300m)

### Setup

```bash
# Create a uv virtual environment
uv venv esm --python 3.10
source esm/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

## Tool Input and Output

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sequence` | string | Yes | Protein amino acid sequence using standard 20 amino acids (A, C, D, E, F, G, H, I, K, L, M, N, P, Q, R, S, T, V, W, Y) |

### Output Format

#### Successful Response
```json
{
  "model": "esmc_300m",
  "embedding_dim": 960,
  "embedding": [0.123, -0.456, 0.789, -0.234, 0.567, ...]
}
```

#### Output Properties
- **Dimensionality**: 960-dimensional vectors (mean-pooled across tokens)
- **Format**: List of float32 values
- **Data Type**: float32

## MCP Server Setup

### Running the MCP Server

```bash
# Start the MCP server on localhost:8008
python esm_tool.py
```

The server will:
1. Initialize the FastMCP server on `http://0.0.0.0:8008`
2. Lazy-load the ESM-C 300M model on first request
3. Listen for embedding requests via HTTP/MCP protocol

### Server Configuration

- **Host**: `0.0.0.0` (accepts connections from any IP)
- **Port**: `8008` (default, can be changed in esm_tool.py)
- **Transport**: `http` (stateless HTTP for scalability)
- **Model**: esmc_300m (can be modified in `get_client()` function)

### Performance Notes

- Model lazy-loads on first request (initial model download and initialization)
- Performance depends on hardware (GPU vs CPU), sequence length, and model size
- For performance benchmarks, refer to the [ESM repository](https://github.com/evolutionaryscale/esm)

## Usage Examples

### Basic Usage via ToolUniverse

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()

# Use the remote ESM tool
result = tu.run({
    "name": "esm_embed_sequence",
    "arguments": {
        "sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVV"
    }
})

print(f"Model: {result['model']}")
print(f"Embedding dimension: {result['embedding_dim']}")
print(f"First 10 embedding values: {result['embedding'][:10]}")
```

### Direct MCP Request

```python
import requests
import json

# Assuming ESM server is running on localhost:8008
response = requests.post(
    "http://localhost:8008/mcp",
    json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "esm_embed_sequence",
            "arguments": {
                "sequence": "MKFLKFSLLTAVLLSVVFAFSSCGDDDDTGPPAPAPAPAPAPAPAPAPAPAP"
            }
        },
        "id": 1
    }
)

embedding_result = response.json()
print(json.dumps(embedding_result, indent=2))
```

## Troubleshooting

### Port Already in Use
```bash
# If port 8008 is already in use, modify esm_tool.py:
# Change: port=8008
# To:     port=8009 (or another available port)
```

### Model Download Fails
- Check internet connection
- Verify sufficient disk space
- Models are cached in `~/.cache/huggingface/hub/` after first download
- Subsequent runs will load from cache

### GPU Out of Memory
- Use smaller model size (esmc_300m instead of esmc_600m)

### Slow Embeddings
- Verify GPU is being used: Check NVIDIA output with `nvidia-smi`

### Connection Refused
- Verify server is running: `python esm_tool.py`
- Check correct host/port in ToolUniverse configuration
- Verify firewall isn't blocking port 8008

## Advanced Configuration

### Using Different ESM-C Models

Edit `esm_tool.py` in the `get_client()` function:

```python
def get_client():
    global _ESM_CLIENT
    if _ESM_CLIENT is None:
        # Change from "esmc_300m" to desired model
        _ESM_CLIENT = ESMC.from_pretrained("esmc_600m")  # Higher quality
        _ESM_CLIENT.eval()
    return _ESM_CLIENT
```

Then update `esm_tools.json` to reflect the new model in the response.

### Custom Server Port

Edit `esm_tool.py` in the `if __name__ == "__main__"` section:

```python
if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=9999,  # Change to desired port
    )
```

## References

- **ESM Cambrian Blog Post**: https://www.evolutionaryscale.ai/blog/esm-cambrian
- **Official ESM Repository**: https://github.com/evolutionaryscale/esm
- **ESM-C Models on Hugging Face**: https://huggingface.co/EvolutionaryScale
- **Model Context Protocol**: https://modelcontextprotocol.io/

## Citation

For information on how to cite ESM-C, please refer to the [official EvolutionaryScale announcement](https://www.evolutionaryscale.ai/blog/esm-cambrian) and [ESM repository](https://github.com/evolutionaryscale/esm).
