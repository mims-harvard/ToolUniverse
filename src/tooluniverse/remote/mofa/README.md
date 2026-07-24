# MOFA+ Remote Tool (MCP Server)

Serves [MOFA+](https://biofam.github.io/MOFA2/) (Multi-Omics Factor Analysis v2; Argelaguet et al., *Genome Biology* 2020) — unsupervised integration of multiple omics layers measured on the **same** samples — as a ToolUniverse remote tool: `run_mofa_factors` (per-sample latent factor matrix + variance explained per view/factor).

Served remotely (not bundled) because `mofapy2` carries a heavy probabilistic Bayesian inference stack on top of numpy/scipy.

## Deploy

```bash
pip install -r requirements.txt          # mofapy2 + numpy
python mofa_tool.py                        # starts the MCP server on 127.0.0.1:8024
```

Inputs are inlined as a `views` object — `{view_name: {feature: [value_per_sample]}}` — with one matrix per omics view over the shared sample set. Every feature list must have one value per sample, in the same sample order. Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/mofa_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
