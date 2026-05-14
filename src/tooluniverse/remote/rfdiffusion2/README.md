# RFdiffusion2 Remote Tool

This directory exposes RFdiffusion2 as a ToolUniverse MCP server.

## Server setup

Install RFdiffusion2 in the runtime environment, then point
`RFDIFFUSION2_COMMAND` at the RFdiffusion2 inference entry point:

```bash
export RFDIFFUSION2_COMMAND="python /opt/RFdiffusion2/scripts/run_inference.py"
export RFDIFFUSION2_WORKDIR=/opt/RFdiffusion2
python -m tooluniverse.remote.rfdiffusion2.rfdiffusion2_mcp_server
```

The MCP server listens on port `8080` and exposes `rfdiffusion2_design`.

## Client setup

Set `RFDIFFUSION2_MCP_SERVER_HOST` to the host running this server and load the
`mcp_auto_loader_rfdiffusion2` tool category.

Use `dry_run: true` to inspect the generated RFdiffusion2 command without
starting an inference job.
