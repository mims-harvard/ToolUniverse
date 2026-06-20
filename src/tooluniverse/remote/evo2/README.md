# Evo 2 Remote Tool (MCP Server)

Serves **Evo 2** (Arc Institute; Brixi et al., 2025) zero-shot variant-effect scoring as the ToolUniverse remote tool `run_evo2_variant_effect`.

Evo 2 is a genome foundation model with a 1 Mb context, hosted by NVIDIA as a NIM. This tool runs the model's **`/forward`** endpoint on the reference and alternate DNA windows, reduces the returned logits to an autoregressive sequence log-likelihood, and returns the delta:

```
delta_loglik = loglik(alt) - loglik(ref)
```

A **negative** delta means the variant makes the sequence less likely under the genome model — a candidate deleterious change. (Complements `NvidiaNIM_evo2`, which only *generates* sequences.)

Served remotely so the **hosted-model call and `NVIDIA_API_KEY` live on the server**, not the client — the tool itself does no local heavy compute (it forwards to NVIDIA's hosted model), but isolating the credential + endpoint on a server is the right boundary for a hosted foundation-model call.

## Deploy

```bash
pip install -r requirements.txt            # numpy + requests
export NVIDIA_API_KEY=...                   # free key at https://build.nvidia.com
python evo2_tool.py                         # starts the MCP server on 127.0.0.1:8034
```

Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/evo2_tools.json` (`type: RemoteTool`).
