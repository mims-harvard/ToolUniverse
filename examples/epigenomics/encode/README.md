### ENCODE Examples (Epigenomics)

About ENCODE
- ENCODE provides comprehensive functional genomics data (experiments, files, biosamples) with a rich REST API. Common queries include experiment search and file listings filtered by assay, target, organism, etc.

Run:
```bash
python examples/epigenomics/encode/use_encode.py
```

What it does:
- ENCODE_search_experiments: search experiments by assay and limit
- ENCODE_list_files: list files with basic filters

Notes:
- Some endpoints return large payloads; limit results in examples.
- Tool names assume corresponding tools exist in ToolUniverse.
