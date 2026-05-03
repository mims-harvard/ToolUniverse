# ToolUniverse Profile Configurations

This directory contains pre-configured Profile configurations for various research domains. Profiles allow you to easily load, share, and manage tool configurations for ToolUniverse.

## Quick Start

All Profile configurations can be loaded directly from GitHub:

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
# Load from GitHub raw URL
config = tu.load_profile("https://raw.githubusercontent.com/mims-harvard/ToolUniverse/blob/main/examples/spaces/protein-research.yaml")

# Or load from local file
config = tu.load_profile("./examples/spaces/protein-research.yaml")
```

## Available Profile Configurations

### Drug Discovery & Pharmaceutical Research

#### `drug-discovery.yaml`
- **Description**: Essential tools for drug discovery research
- **Tools**: ~200 tools from ChEMBL, Clinical Trials, OpenTargets, FDA, PubChem, DrugBank, ADMET AI
- **Use Cases**: 
  - Chemical compound analysis
  - Clinical trial search
  - Drug safety assessment
  - ADMET property prediction
- **GitHub**: https://github.com/mims-harvard/ToolUniverse/blob/main/examples/spaces/drug-discovery.yaml

### Clinical Research

#### `clinical-research.yaml`
- **Description**: Comprehensive tools for clinical research and regulatory affairs
- **Tools**: ~100 tools from Clinical Trials, FDA, Clinical Guidelines, Monarch, EFO, HPA
- **Use Cases**:
  - Trial design and monitoring
  - Safety monitoring
  - Regulatory submissions
  - Clinical guideline access
- **GitHub**: https://github.com/mims-harvard/ToolUniverse/blob/main/examples/spaces/clinical-research.yaml

### Literature & Publications

#### `literature-search.yaml`
- **Description**: Scientific literature search and analysis tools
- **Tools**: ~40 tools from EuropePMC, Semantic Scholar, PubTator, arXiv, Crossref, PubMed
- **Use Cases**:
  - Paper search and discovery
  - Citation analysis
  - Systematic reviews
  - Literature annotation
- **GitHub**: https://github.com/mims-harvard/ToolUniverse/blob/main/examples/spaces/literature-search.yaml

### Protein Research

#### `protein-research.yaml`
- **Description**: Comprehensive tools for protein structure, function, and interaction research
- **Tools**: ~60 tools from UniProt, RCSB PDB, AlphaFold, HPA, InterPro
- **Use Cases**:
  - Protein structure analysis
  - Functional annotation
  - Protein-protein interactions
  - Domain analysis
  - Subcellular localization
- **GitHub**: https://github.com/mims-harvard/ToolUniverse/blob/main/examples/spaces/protein-research.yaml

### Genomics

#### `genomics.yaml`
- **Description**: Comprehensive tools for genomics research
- **Tools**: ~25 tools from GWAS, Ensembl, ClinVar, dbSNP, gnomAD, GTEx, ENCODE, GDC
- **Use Cases**:
  - Genome-wide association studies
  - Variant analysis
  - Gene expression analysis
  - Genomic data access
  - Clinical variant interpretation
- **GitHub**: https://github.com/mims-harvard/ToolUniverse/blob/main/examples/spaces/genomics.yaml

### Bioinformatics

#### `bioinformatics.yaml`
- **Description**: Bioinformatics analysis and pathway research tools
- **Tools**: ~15 tools from BLAST, Gene Ontology, KEGG, Reactome, Enrichr, HumanBase, WikiPathways
- **Use Cases**:
  - Pathway analysis
  - Functional annotation
  - Enrichment analysis
  - Sequence similarity search
  - Protein-protein interaction analysis
- **GitHub**: https://github.com/mims-harvard/ToolUniverse/blob/main/examples/spaces/bioinformatics.yaml

### Structural Biology

#### `structural-biology.yaml`
- **Description**: Protein and molecular structure analysis tools
- **Tools**: ~35 tools from RCSB PDB, AlphaFold, EMDB, 3D visualization
- **Use Cases**:
  - Protein structure analysis
  - Structure prediction
  - Electron microscopy data
  - Molecular visualization
  - Structure validation
- **GitHub**: https://github.com/mims-harvard/ToolUniverse/blob/main/examples/spaces/structural-biology.yaml

### Cheminformatics

#### `cheminformatics.yaml`
- **Description**: Chemical compound research and ADMET prediction tools
- **Tools**: ~20 tools from PubChem, ChEMBL, ADMET AI, molecular visualization
- **Use Cases**:
  - Compound search and discovery
  - ADMET property prediction
  - Molecular similarity
  - Chemical database queries
  - Molecular visualization
- **GitHub**: https://github.com/mims-harvard/ToolUniverse/blob/main/examples/spaces/cheminformatics.yaml

### Disease Research

#### `disease-research.yaml`
- **Description**: Disease research and target-disease association tools
- **Tools**: ~30 tools from OpenTargets, Monarch, disease target scoring, GWAS, HPA
- **Use Cases**:
  - Disease-target associations
  - Phenotype analysis
  - Disease scoring
  - Genetic associations
  - Disease ontology queries
- **GitHub**: https://github.com/mims-harvard/ToolUniverse/blob/main/examples/spaces/disease-research.yaml

### Comprehensive Workspace

#### `full-workspace.yaml`
- **Description**: Complete research environment with all major domains
- **Tools**: 449 tools from 32 categories
- **Features**: 
  - LLM configuration
  - Hooks for output processing
  - Comprehensive tool coverage
- **Use Cases**:
  - End-to-end research workflows
  - Multi-domain research
  - AI-powered analysis
- **GitHub**: https://github.com/mims-harvard/ToolUniverse/blob/main/examples/spaces/full-workspace.yaml

## Usage Examples

### Loading a Profile from GitHub

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()

# Load protein research toolkit from GitHub
config = tu.load_profile(
    "https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/examples/spaces/protein-research.yaml"
)

# Use the loaded tools
print(f"Loaded {len(tu.all_tools)} tools from {config.get('name')}")
```

### Loading a Profile from Local File

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()

# Load from local file
config = tu.load_profile("./examples/spaces/protein-research.yaml")

# Use the loaded tools
print(f"Loaded {len(tu.all_tools)} tools")
```

### Using with MCP Server

```bash
# Load from GitHub URL
tooluniverse-smcp-stdio --load "https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/examples/spaces/protein-research.yaml"

# Load from local file
tooluniverse-smcp-stdio --load "./examples/spaces/protein-research.yaml"
```

## Profile Selection Guide

Choose a Profile based on your research needs:

- **Drug Discovery**: Use `drug-discovery.yaml` for pharmaceutical research
- **Protein Research**: Use `protein-research.yaml` for protein structure and function studies
- **Genomics**: Use `genomics.yaml` for genetic and genomic analysis
- **Bioinformatics**: Use `bioinformatics.yaml` for pathway and functional analysis
- **Structural Biology**: Use `structural-biology.yaml` for structure-focused research
- **Cheminformatics**: Use `cheminformatics.yaml` for chemical compound research
- **Disease Research**: Use `disease-research.yaml` for disease-related studies
- **Literature**: Use `literature-search.yaml` for paper search and analysis
- **Clinical Research**: Use `clinical-research.yaml` for clinical and regulatory work
- **Comprehensive**: Use `full-workspace.yaml` for multi-domain research

## Tool Configuration

### Recommended: Explicit Tool List (include_tools)
List specific tools for clarity and transparency:

```yaml
tools:
  include_tools:
    - "ChEMBL_search_molecule"
    - "ClinicalTrials_search_studies"
```

**Benefits**:
- Users know exactly what tools are loaded
- No surprises or hidden tools
- Easy to share and reproduce

### Alternative: Category Loading (categories)
Load all tools from categories (convenience method):

```yaml
tools:
  categories:
    - "ChEMBL"
    - "clinical_trials"
```

**Use when**:
- Exploring available tools
- Want all tools from a category
- Less control needed

### Optional: Exclusions (exclude_tools)
Remove specific tools:

```yaml
tools:
  categories: ["ChEMBL"]
  exclude_tools:
    - "ChEMBL_old_version"
```

**Rarely needed**, only when excluding problematic tools.

## LLM Configuration

**Note**: LLM configuration is only needed for complete workspace files (like `full-workspace.yaml`). 
Simple tool collections (like `literature-search.yaml`, `drug-discovery.yaml`) don't need LLM config.

### Default Mode (Recommended)
Profile LLM config provides defaults for AgenticTools:

```yaml
llm_config:
  mode: "default"  # Profile config as default
  # Direct AgenticTool api_type values
  # Supported values: CHATGPT, GEMINI, OPENROUTER, VLLM
  default_provider: "CHATGPT"
  models:
    default: "gpt-4o"           # Used by all AgenticTools
  temperature: 0.3              # 0.0-2.0 range
```

**Priority**: Profile config > Built-in default

**Use case**: You want to standardize LLM settings across all tools.

**Note for vLLM**: When using `default_provider: "VLLM"`, you must also set the `VLLM_SERVER_URL` environment variable:
```bash
export VLLM_SERVER_URL=http://your-vllm-server:8000
```
See the `docs/guide/vllm_support.rst` guide for complete vLLM setup instructions.

### Fallback Mode
Profile LLM config as backup when tool's API fails:

```yaml
llm_config:
  mode: "fallback"  # Profile config as fallback
  default_provider: "CHATGPT"
  models:
    default: "gpt-4o"           # Used by all AgenticTools
  temperature: 0.3
```

**Priority**: Built-in default, then fallback to Profile if API unavailable

**Use case**: Tools have specific LLM preferences, but you want a reliable fallback.

### Environment Override Mode
Environment variables have highest priority, overriding both tool configs and Profile configs:

```yaml
llm_config:
  mode: "env_override"  # Environment variables override everything
  default_provider: "CHATGPT"  # Used only if env vars not set
  models:
    default: "gpt-4o"  # Used only if env vars not set
  temperature: 0.3
```

**Priority**: Environment variables > Tool config > Profile config > Built-in default

**Use case**: You want to override all LLM settings via environment variables (e.g., for different deployments, testing, or when using vLLM with custom models).

**Example with vLLM**:
```bash
# Set environment variables to override all configs with vLLM
export TOOLUNIVERSE_LLM_CONFIG_MODE=env_override
export TOOLUNIVERSE_LLM_DEFAULT_PROVIDER=VLLM
export TOOLUNIVERSE_LLM_MODEL_DEFAULT=meta-llama/Llama-3.1-8B-Instruct
export VLLM_SERVER_URL=http://localhost:8000
export TOOLUNIVERSE_LLM_TEMPERATURE=0.7
```

**Example with other providers**:
```bash
# Override with OpenRouter
export TOOLUNIVERSE_LLM_CONFIG_MODE=env_override
export TOOLUNIVERSE_LLM_DEFAULT_PROVIDER=OPENROUTER
export TOOLUNIVERSE_LLM_MODEL_DEFAULT=openai/gpt-5
export OPENROUTER_API_KEY=your-key-here
```

## Configuration Structure

### Basic Preset
```yaml
name: "Preset Name"
version: "1.0.0"
description: "Description"
tools:
  # Recommended: explicit tool list
  include_tools:
    - "ChEMBL_search_molecule"
    - "ClinicalTrials_search_studies"
  # Optional: exclude problematic tools
  exclude_tools:
    - "problematic_tool"
```

### Full Workspace
```yaml
name: "Complete Research Workspace"
version: "1.0.0"
description: "Complete research environment with tools, LLM configuration, hooks, and workflow templates"
tags: ["research", "comprehensive", "workspace", "ai-powered", "multi-domain"]

tools:
  # Use categories for comprehensive coverage
  categories:
    - "agents"                    # AI agents and analysis tools
    - "drug_discovery_agents"     # Drug discovery AI agents
    - "fda_drug_label"           # FDA drug information
    - "opentarget"               # OpenTargets drug-target-disease data
    # ... 28 more categories

llm_config:
  mode: "default"
  default_provider: "CHATGPT"
  models:
    default: "gpt-4o"
  temperature: 0.3

hooks:
  - type: "SummarizationHook"
    enabled: true
    config:
      max_length: 500
      include_key_points: true
  - type: "FileSaveHook"
    enabled: true
    config:
      output_dir: "./outputs"
      file_prefix: "analysis"
```

## Contributing

To contribute new Profile configurations:

1. Create a new YAML file in `examples/spaces/`
2. Follow the existing Profile configuration format
3. Use explicit tool lists (`include_tools`) for clarity
4. Add a GitHub link comment at the top
5. Update this README.md file

## Support

For questions or issues:
- GitHub Issues: https://github.com/mims-harvard/ToolUniverse/issues
- Documentation: https://zitniklab.hms.harvard.edu/ToolUniverse/
- Website: https://aiscientist.tools
