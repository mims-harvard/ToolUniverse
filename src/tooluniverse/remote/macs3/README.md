# MACS3 Remote Tool (MCP Server)

Serves [MACS3](https://macs3-project.github.io/MACS/) (Model-based Analysis of ChIP-Seq; Zhang et al., *Genome Biology* 2008; the macs3-project Python-3 successor) — the field-standard ChIP-seq / ATAC-seq peak caller — as a ToolUniverse remote tool: `run_macs3_callpeak`.

Served remotely (not bundled) because it shells out to the `macs3` command-line
engine (a compiled/Cython dependency) and operates on large server-side
alignment files (BAM / BED / BED-PE) rather than inlined data.

`run_macs3_callpeak` runs `macs3 callpeak -t <treatment> [-c <control>] -f <format> -g <genome_size> -n <name> --outdir <tmp> -q <qvalue>`, parses the resulting `<name>_peaks.narrowPeak` (ENCODE BED6+4), and returns the peak count, the top-N peaks by score, and summary statistics.

## Deploy

```bash
pip install -r requirements.txt   # macs3
python macs3_tool.py              # starts the MCP server on 127.0.0.1:8021
```

Treatment/control files must be aligned reads in a MACS3-supported format
(BAM/BED/SAM, or BAMPE/BEDPE for paired-end such as ATAC-seq). Expose remotely
only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/macs3_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
