# ToolUniverse SDK Reference

Detailed reference for ToolUniverse Python SDK features and advanced usage.

## Installation Details

### Package Options

```bash
# Base installation (~200-300 MB)
pip install tooluniverse

# With embedding search (+1-2 GB for model weights)
pip install tooluniverse[embedding]

# With ML tools (+2-5 GB for model weights)
pip install tooluniverse[ml]

# All features
pip install tooluniverse[all]

# Minimal client for HTTP API access
pip install tooluniverse[client]
```

### Performance Metrics

- First `load_tools()`: 5-10 seconds (1000++ tools)
- Subsequent loads: 2-3 seconds (cached)
- Specific categories: <2 seconds
- Memory: 200-300 MB base, +1-2 GB with embeddings

## Initialization Options

```python
tu = ToolUniverse(
    use_cache=True,              # Global caching
    hooks_enabled=True,          # Auto-summarization
    log_level="INFO",            # Logging level
    tool_files={},               # Custom tool configs
    keep_default_tools=True      # Include defaults
)

# Load options
tu.load_tools(
    categories=["proteins", "drugs"],  # Specific categories
    tool_config_files={...}            # Custom configs
)
```

## Tool Discovery Methods

### Method 1: Keyword Search

**Best for**: Fast searches, exact matches, no API key

```python
tools = tu.run({
    "name": "Tool_Finder_Keyword",
    "arguments": {
        "description": "protein structure",
        "limit": 10
    }
})

# Always check structure
if isinstance(tools, dict) and 'tools' in tools:
    for tool in tools['tools']:
        print(f"{tool['name']}: {tool['description']}")
```

### Method 2: LLM Search

**Best for**: Complex queries, natural language, best matches  
**Requires**: `OPENAI_API_KEY`

```python
tools = tu.run({
    "name": "Tool_Finder_LLM",
    "arguments": {
        "description": "find genetic variants associated with Alzheimer's",
        "limit": 5
    }
})
```

### Method 3: Embedding Search

**Best for**: Semantic similarity, concept matching  
**Requires**: GPU for embedding model

```python
tools = tu.run({
    "name": "Tool_Finder",
    "arguments": {
        "description": "protein-protein interaction networks",
        "limit": 10,
        "return_call_result": False  # Only return info
    }
})
```

## Advanced Caching

### Cache Configuration

```python
import os
from pathlib import Path

cache_dir = Path.home() / ".tooluniverse" / "cache"
cache_dir.mkdir(parents=True, exist_ok=True)

os.environ["TOOLUNIVERSE_CACHE_PATH"] = str(cache_dir / "cache.sqlite")
os.environ["TOOLUNIVERSE_CACHE_ENABLED"] = "true"
os.environ["TOOLUNIVERSE_CACHE_PERSIST"] = "true"

tu = ToolUniverse(use_cache=True)
tu.load_tools()
```

### Cache Management

```python
# Get statistics
stats = tu.get_cache_stats()
print(f"Hits: {stats['hits']}, Misses: {stats['misses']}")

# Inspect cache
for entry in tu.dump_cache():
    print(f"Tool: {entry['tool_name']}")
    print(f"Hit count: {entry['hit_count']}")

# Clear cache
tu.clear_cache()

# Always close connections
tu.close()
```

### When to Cache

✅ **Good candidates:**
- ML model predictions (deterministic)
- Database queries (stable data)
- Protein structure predictions
- Literature searches (stable results)

❌ **Avoid:**
- Real-time data
- Time-sensitive queries
- User-specific data
- Rapidly changing data

## Hooks System

### Basic Hooks

```python
# Enable default summarization hook
tu = ToolUniverse(hooks_enabled=True)
tu.load_tools()

result = tu.tools.OpenTargets_get_target_gene_ontology_by_ensemblID(
    ensemblId="ENSG00000012048"
)

# Check if hook applied
if isinstance(result, dict) and "summary" in result:
    print(f"Original: {result['original_length']} chars")
    print(f"Summary: {len(result['summary'])} chars")
```

### Custom Hook Configuration

```python
hook_config = {
    "exclude_tools": [
        "Tool_RAG",
        "ToolFinderEmbedding",
        "CustomTool_*"  # Wildcard pattern
    ],
    "hooks": [{
        "name": "summarization_hook",
        "type": "SummarizationHook",
        "enabled": True,
        "conditions": {
            "output_length": {"operator": ">", "threshold": 5000}
        },
        "hook_config": {
            "max_tokens": 2000,
            "summary_style": "concise"
        }
    }]
}

tu = ToolUniverse(hooks_enabled=True, hook_config=hook_config)
tu.load_tools()
```

### File Save Hook

```python
import tempfile

hook_config = {
    "hooks": [{
        "name": "file_save_hook",
        "type": "FileSaveHook",
        "enabled": True,
        "conditions": {
            "output_length": {"operator": ">", "threshold": 10000}
        },
        "hook_config": {
            "temp_dir": tempfile.gettempdir(),
            "file_prefix": "tool_output",
            "include_metadata": True
        }
    }]
}

tu = ToolUniverse(hooks_enabled=True, hook_config=hook_config)
tu.load_tools()

result = tu.tools.some_large_output_tool(param="value")
if isinstance(result, dict) and "file_path" in result:
    print(f"Saved to: {result['file_path']}")
```

## Remote HTTP API

Deploy ToolUniverse as a server for remote access.

### Server Setup

```bash
# Install on server
pip install tooluniverse

# Start server
tooluniverse-http-api --host 0.0.0.0 --port 8080
```

### Client Usage

```bash
# Install minimal client
pip install tooluniverse[client]
```

```python
from tooluniverse import ToolUniverseClient

client = ToolUniverseClient("http://server:8080")

# Use like local ToolUniverse
client.load_tools(tool_type=['uniprot', 'ChEMBL'])
result = client.run_one_function({
    "name": "UniProt_get_entry_by_accession",
    "arguments": {"accession": "P05067"}
})
```

**Benefits:**
- Minimal client dependencies (`requests` + `pydantic`)
- All computation on server
- Automatic method updates
- Shared instance across users

## Complex Workflows

### Multi-Step Pipeline

```python
def analyze_disease_targets(disease_efo_id):
    """Complete disease-to-drug pipeline"""
    tu = ToolUniverse(use_cache=True, hooks_enabled=True)
    tu.load_tools()
    
    try:
        # Step 1: Get targets
        targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
            efoId=disease_efo_id
        )
        
        if not targets or 'data' not in targets:
            return {"error": "No targets found"}
        
        # Step 2: Get target info (batch)
        target_ids = [t['target']['id'] for t in targets['data'][:5]]
        target_calls = [
            {"name": "UniProt_get_entry_by_accession", 
             "arguments": {"accession": tid}}
            for tid in target_ids
        ]
        target_info = tu.run_batch(target_calls)
        
        # Step 3: Find compounds (batch)
        compound_calls = [
            {"name": "ChEMBL_search_molecule_by_target",
             "arguments": {"target_id": tid, "limit": 10}}
            for tid in target_ids
        ]
        compounds = tu.run_batch(compound_calls)
        
        # Step 4: ADMET predictions
        all_smiles = []
        for comp_list in compounds:
            if comp_list and 'molecules' in comp_list:
                all_smiles.extend([m['smiles'] for m in comp_list['molecules'][:3]])
        
        admet_calls = [
            {"name": "ADMETAI_predict_admet", "arguments": {"smiles": s}}
            for s in all_smiles
        ]
        admet_results = tu.run_batch(admet_calls)
        
        # Step 5: Literature search
        gene_names = [t.get('gene_name', '') for t in target_info if t]
        lit_calls = [
            {"name": "PubMed_search_articles",
             "arguments": {"query": f"{gene} drug therapy", "max_results": 10}}
            for gene in gene_names[:3] if gene
        ]
        literature = tu.run_batch(lit_calls)
        
        return {
            "targets": targets,
            "target_info": target_info,
            "compounds": compounds,
            "admet": admet_results,
            "literature": literature
        }
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        tu.close()
```

### Error Handling Wrapper

```python
from tooluniverse.exceptions import ToolError, ToolUnavailableError

def safe_tool_executor(tu, tool_name, arguments, fallback_tool=None):
    """Execute tool with comprehensive error handling"""
    try:
        return tu.run({
            "name": tool_name,
            "arguments": arguments
        })
    except ToolUnavailableError:
        if fallback_tool:
            print(f"⚠️ {tool_name} unavailable, trying {fallback_tool}")
            return tu.run({
                "name": fallback_tool,
                "arguments": arguments
            })
        return {"error": f"Tool {tool_name} unavailable"}
    except ToolError as e:
        print(f"❌ Tool error: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {"error": str(e)}

# Usage
result = safe_tool_executor(
    tu,
    "UniProt_get_entry_by_accession",
    {"accession": "P05067"},
    fallback_tool="AlternativeTool"
)
```

## Environment Variables

### API Keys

```bash
export OPENAI_API_KEY="sk-..."        # Required for LLM tools
export NCBI_API_KEY="..."             # Optional, higher rate limits
export USPTO_API_KEY="..."            # For patent tools
```

### Cache Configuration

```bash
export TOOLUNIVERSE_CACHE_ENABLED="true"
export TOOLUNIVERSE_CACHE_PERSIST="true"
export TOOLUNIVERSE_CACHE_PATH="/path/to/cache.sqlite"
```

### Performance Tuning

```bash
export TOOLUNIVERSE_LIGHT_IMPORT="1"   # Minimal imports
export TOOLUNIVERSE_LOAD_TIMEOUT="30"  # Load timeout (seconds)
export TOOLUNIVERSE_TIMEOUT="120"      # Execution timeout (seconds)
```

## Common Issues & Solutions

### Issue: Tool Not Loading

```python
# Check tool registry
from tooluniverse.tool_registry import get_tool_registry
registry = get_tool_registry()
print(f"Registered: {len(registry)}")

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
tu = ToolUniverse()
tu.load_tools()
```

### Issue: Slow Performance

```python
# Solution 1: Load specific categories
tu = ToolUniverse()
tu.load_tools(categories=["proteins", "drugs"])

# Solution 2: Enable caching
tu = ToolUniverse(use_cache=True)

# Solution 3: Use batch execution
results = tu.run_batch(calls)

# Solution 4: Disable validation (after testing)
result = tu.tools.tool_name(param="value", validate=False)
```

### Issue: High Memory Usage

```python
# Use light import mode
import os
os.environ["TOOLUNIVERSE_LIGHT_IMPORT"] = "1"

from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools(categories=["proteins"])

# Clear cache periodically
tu.clear_cache()

# Always close
tu.close()
```

### Issue: API Key Errors

```python
import os

# Check if set
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("⚠️ Set: export OPENAI_API_KEY='sk-...'")
else:
    print(f"✅ Key set: {api_key[:10]}...")

# Test key
try:
    tools = tu.run({
        "name": "Tool_Finder_LLM",
        "arguments": {"description": "test", "limit": 1}
    })
    print("✅ API key valid")
except Exception as e:
    print(f"❌ API key error: {e}")
```

## Best Practices Summary

1. **Always call `load_tools()`** after initialization
2. **Check result structures** (tool finders return nested dicts)
3. **Use caching** for expensive, deterministic operations
4. **Use batch execution** for parallel tasks
5. **Handle errors** with try/except blocks
6. **Close connections** with `tu.close()` when done
7. **Validate parameters** before execution (check tool schema)
8. **Use appropriate tool finder** (keyword for speed, LLM for accuracy)
9. **Enable hooks** for large outputs
10. **Document workflows** clearly

## Additional Resources

- **Main Documentation**: https://zitniklab.hms.harvard.edu/ToolUniverse/
- **API Reference**: https://zitniklab.hms.harvard.edu/ToolUniverse/api/modules.html
- **Tutorials**: https://zitniklab.hms.harvard.edu/ToolUniverse/guide/scientific_workflows.html
- **GitHub Examples**: https://github.com/mims-harvard/ToolUniverse/tree/main/examples
- **Community Slack**: https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ
