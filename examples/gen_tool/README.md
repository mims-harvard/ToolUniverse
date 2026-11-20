# Inspect a Gen repository

This example reports branch state, operation identifiers and timestamps, and
sample names and collections from an existing local Gen repository. The
`get_gen_info` entry describes installation and interfaces for the standalone
`gen` CLI, Python package `gen`, and R package `genr`.

Gen's Python package supports Python 3.11 and newer. Install ToolUniverse and
Gen separately, then point the provider root at a directory containing the
repositories the ToolUniverse process is authorized to inspect.

```bash
python -m pip install -e .
python -m pip install 'gen>=0.5.1'
export TOOLUNIVERSE_GEN_ROOT="$PWD/gen-repositories"
tu find 'genome version control repository' --limit 5
python examples/gen_tool/inspect_repository.py yeast-study
```

Run these Gen CLI commands from an existing workspace to inspect repository metadata.

```bash
gen --version
gen branch --list
gen operations
gen list-samples
```

The self-contained smoke example creates a temporary repository containing a
four-base synthetic sequence and inspects its branch through ToolUniverse.

```bash
python examples/gen_tool/inspect_repository.py --demo
```

The demo returns branch metadata in this shape, with a generated operation ID in `head`.

```json
{
  "status": "success",
  "data": {
    "view": "branches",
    "branch": null,
    "current_branch": "main",
    "items": [
      {"name": "main", "is_current": true, "head": "<operation ID>", "dirty": false}
    ],
    "returned": 1,
    "total_count": 1,
    "truncated": false
  }
}
```

Repository identifiers are paths relative to `TOOLUNIVERSE_GEN_ROOT`. Pass the
Gen workspace directory that contains `.gen`. The repository must already
contain non-empty `.gen/gen.db` and `.gen/default.db` files.

The Gen Python API opens the repository and may update internal database
metadata or run migrations. Configure the root only for repositories the
ToolUniverse server is authorized to open.
