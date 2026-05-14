# RFdiffusion2

RFdiffusion2 is exposed through a ToolUniverse MCP server that wraps a
server-side RFdiffusion2 command.

## Server

Configure the command on the RFdiffusion2 host:

```bash
export RFDIFFUSION2_COMMAND="python /opt/RFdiffusion2/scripts/run_inference.py"
export RFDIFFUSION2_WORKDIR=/opt/RFdiffusion2
python -m tooluniverse.remote.rfdiffusion2.rfdiffusion2_mcp_server
```

The server listens on port `8080` and exposes `rfdiffusion2_design`.

## Client

Set the host and load the MCP auto-loader category:

```bash
export RFDIFFUSION2_MCP_SERVER_HOST=your-server-host
```

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(tool_type=["mcp_auto_loader_rfdiffusion2"])
```

## Example

```python
result = tu.run(
    {
        "name": "rfdiffusion2_design",
        "arguments": {
            "contig_map": "150-150",
            "num_designs": 1,
            "output_prefix": "outputs/design",
            "dry_run": True,
        },
    }
)
```

Use `dry_run: true` to inspect the generated command before launching an
RFdiffusion2 job.
