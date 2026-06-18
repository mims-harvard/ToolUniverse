# Enformer Remote Tool (MCP Server)

Serves [Enformer](https://www.nature.com/articles/s41592-021-01252-x) (Avsec et al., *Nature Methods* 2021) — sequence → genomic-track prediction — as ToolUniverse remote tools: `run_enformer_predict` and `run_enformer_variant_effect`.

Enformer is served remotely (not bundled) because it needs PyTorch + ~1 GB of weights (`EleutherAI/enformer-official-rough`) and benefits from a GPU.

## Deploy

```bash
pip install -r requirements.txt          # torch + enformer-pytorch
python enformer_tool.py                   # starts the MCP server on 127.0.0.1:8011
```

Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (the SMCP bind guard enforces this for non-loopback hosts).

## Register in ToolUniverse

The tool definitions live in `src/tooluniverse/data/remote_tools/enformer_tools.json`
(`type: RemoteTool`). Point the loader at your server host via the standard
`MCPAutoLoaderTool`/`server_url` mechanism (see the remote-tools tutorial).

First call lazily downloads and caches the weights.
