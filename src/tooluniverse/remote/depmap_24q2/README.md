# DepMap Gene Correlation Analysis Tool - MCP Server

## TOU validation and deployment status (2026-08-16)

> Loopback discovery and correlation retrieval passed against a deterministic safe artifact fixture with finite bounded output. Four simultaneous fixture calls passed with event-loop offloading and serialized provider state. Production DepMap 24Q2 data, public publication, cross-user isolation, scale, and scientific-value validation remain incomplete. Authenticated private Platform import and owner testing passed on 2026-08-16; public publication and independent-caller authorization/isolation remain untested.

- Operation: `compute_depmap24q2_gene_correlations`
- Start: `python -m tooluniverse.remote.depmap_24q2.depmap_24q2_mcp_tool`
- Endpoint: `http://127.0.0.1:7002/mcp`
- Provider configuration: set `DEPMAP_DATA_PATH` to the reviewed provider artifact root; it initializes once per process.
- TOU check: `tu doctor --forward http://127.0.0.1:7002/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:7002/mcp --name validation-depmap-24q2 --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. The current result is an artifact-contract pass, not production-dataset validation.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py --implementation depmap-24q2`. Add `--check-provider-env` before launch, `--live` after launch, and `--check-connect-prereqs` before sharing. Live preflight checks exact MCP discovery only; it does not run or validate a model. The pinned relay SDK is not on PyPI and currently requires authorized GitHub repository access plus a configured SSH key, so a working local MCP server does not by itself prove that a new operator can share it.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays online and all 41 operations discoverable. This implementation was imported as unpublished owner draft(s), configured with a 120-second timeout, and invoked through `/expert-sessions/{id}/test`. Across the set, 38 unique operations passed return-schema and semantic validation; the three USPTO operations returned exact provider HTTP 403 and remain credential-blocked. Public publication, independent-caller authorization/isolation, broad saturation, and persistent supervision were not tested.

See the [complete setup and verification guide](../../../../skills/setup-depmap-24q2-remote-tool/SKILL.md).

A MCP tool from [Prism ToolSpace](https://huggingface.co/datasets/mims-harvard/ToolSpace) for analyzing gene-gene correlations from the [DepMap (Dependency Map)](https://depmap.org/) CRISPR knockout screening dataset. This tool processes systematic CRISPR-Cas9 knockout data from over 1,320 cancer cell lines from DepMap 24Q2 to identify genetic dependencies and co-essential gene pairs.

## Authorize once, then share with one short command

After installing this provider's dependencies and the pinned Connect relay SDK,
and exporting its required resources, run once per machine (and again after key rotation):

```bash
tu remote login
# Or import an existing protected 0600 file without sourcing it:
tu remote login --env-file /path/to/tooluniverse-service.env
```

Then each private share is:

```bash
tu remote share depmap-24q2
```

By default, `tu remote login` requests a short-lived device code, opens the TU
Platform approval page, and polls until the signed-in user approves. No key
copy/paste is required. On a headless machine, add `--no-browser` and open the
printed link elsewhere. The CLI exchanges approval for a computer-only key,
verifies `/remote-servers/preflight`, stores it in a local 0600 config file, and
never displays it.

The share command selects the reviewed environment, checks it, starts or reuses
the exact loopback MCP tool set, runs the TU Platform preflight, and keeps the
private relay in the foreground until Ctrl-C. Override defaults only when needed:

```bash
tu remote share depmap-24q2 --name my-depmap-24q2-remote --workers 1
```

Use `tu remote run depmap-24q2` for local-only operation. Sharing does not publish a
tool or prove scientific accuracy.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the locally stored key.

## Prerequisites

### 1. Install Required Dependencies

Install the required Python packages for the DepMap correlation analysis:

```bash
# Create a virtual environment for DepMap setup
uv venv depmap --python 3.10
source depmap/bin/activate
uv pip install -r requirements.txt

```

## Data Setup

### 1. Download DepMap 24Q2 Dataset

Download the preprocessed DepMap correlation data from the Prism ToolSpace or prepare your own correlation matrices:

```bash
# Install CLI if not already
uvx --from huggingface_hub hf

# Download only the depmap_24q2 folder
uvx --from huggingface_hub hf download mims-harvard/ToolSpace \
  --repo-type dataset \
  --include "depmap_24q2/*" \
  --local-dir ./path/to/your/depmap/
```
**Required Files:**
- **Gene correlation matrix** - Pairwise correlations between genes
- **P-value matrix** - Statistical significance of correlations
- **Gene index** - Mapping of gene symbols to matrix indices
- **Adjusted p-values** (optional) - FDR-corrected p-values

**Data Sources:**
- **DepMap Portal**: https://depmap.org/portal/download/
- **DepMap 24Q2 Release**: Contains CRISPR knockout data for 1,320+ cell lines
- **CERES Algorithm**: Standardized gene effect scores for dependency analysis

### 2. Directory Structure Setup

Create the following directory structure for your DepMap data:

```
/path/to/your/depmap/
├── depmap_24q2/              # DepMap data directory
│   ├── corr_matrix.npy       # Gene correlation matrix (dense format)
│   ├── p_val_matrix.npy      # P-value matrix (dense format)
│   ├── p_adj_matrix.npy      # Adjusted p-values (optional)
│   ├── gene_idx_array.npy    # Gene symbol index array
│   └── gene_names.txt        # Gene symbols (alternative format)
│
│   # Alternative sparse format for large datasets:
│   └── gene_correlations.h5  # HDF5 sparse matrices
```

### 3. Set Environment Variable

Set the `DEPMAP_DATA_PATH` environment variable to point to your DepMap installation:

```bash
# Add to your ~/.bashrc or ~/.zshrc
export DEPMAP_DATA_PATH="/path/to/your/depmap"
```

## Input and Output Specifications

### Input Format

The tool accepts gene symbol pairs for correlation analysis:

- **Gene Symbols**: Standard HUGO gene nomenclature (e.g., "BRAF", "TP53", "MAPK1")
- **Case Insensitive**: Tool automatically standardizes gene symbols
- **Validation**: Checks gene availability in the correlation matrix

### Output Format

The tool returns a structured JSON response with comprehensive correlation analysis:

```json
{
  "correlation_data": {
    "correlation": 0.756,
    "p_value": 1.23e-15,
    "adjusted_p_value": 4.56e-12
  },
  "interpretation": {
    "strength": "strong",
    "significance": "significant (FDR corrected)",
    "direction": "similar",
    "biological_relationship": "co-dependent relationship (shared essential functions)",
    "summary": "DepMap analysis reveals a strong, similar correlation (r=0.756) in knockout effects between BRAF and MAPK1, suggesting co-dependent relationship (shared essential functions). This finding is significant (FDR corrected)."
  },
  ...
}
```

**Output Fields:**
- `correlation_data` (dict): Statistical measures
  - `correlation` (float): Pearson correlation coefficient (-1.0 to 1.0)
  - `p_value` (float): Statistical significance of correlation
  - `adjusted_p_value` (float, optional): FDR-corrected p-value
- `interpretation` (dict): Biological and statistical context
  - `strength` (str): Correlation strength classification
  - `significance` (str): Statistical significance interpretation
  - `direction` (str): Relationship type (similar vs opposing effects)
  - `biological_relationship` (str): Biological interpretation
  - `summary` (str): Comprehensive analysis summary
- `context_info` (list): Analysis metadata and messages
- `error` (str, optional): Error description if analysis failed

## Running the MCP Server

### 1. Start the Server

```bash
# Activate the virtual environment
source depmap/bin/activate

# Set environment variable (if not in bashrc)
export DEPMAP_DATA_PATH="/path/to/your/depmap"

# Run the MCP server from the ToolUniverse repository root
python -m tooluniverse.remote.depmap_24q2.depmap_24q2_mcp_tool
```

### 2. Server Configuration

The server runs with the following default settings:
- **Host**: `127.0.0.1` (loopback; use the outbound relay for Connect)
- **Port**: `7002` (configured to avoid conflicts)
- **Transport**: `streamable-http`
- **Mode**: Stateless HTTP

A deliberate non-loopback bind requires `TOOLUNIVERSE_API_TOKEN`; do not
expose the unauthenticated provider directly.


### Common Issues

1. **Data Directory Not Found**
   ```
   FileNotFoundError: DepMap data directory not found at /path/to/data
   ```
   - Ensure `DEPMAP_DATA_PATH` is set correctly
   - Verify the `depmap_24q2/` subdirectory exists
   - Check that correlation matrices are properly downloaded

2. **Gene Symbol Not Found**
   ```
   KeyError: Gene 'INVALID' not available in the DepMap correlation matrix
   ```
   - Verify gene symbol spelling (use standard HUGO nomenclature)
   - Check if gene is present in the DepMap 24Q2 dataset
   - Try alternative gene symbols or aliases

3. **Missing Correlation Data**
   ```
   FileNotFoundError: No correlation data found in directory
   ```
   - Ensure correlation matrices are in the correct format (.npy or .h5)
   - Verify gene index files are present (`gene_idx_array.npy` or `gene_names.txt`)
   - Check file permissions and accessibility


## References

- **DepMap Project**: [Broad Institute DepMap Portal](https://depmap.org/)
- **DepMap Paper**: [Mapping the Cancer Dependency Map](https://www.nature.com/articles/s41586-019-1103-9)
- **CERES Algorithm**: [Computational correction of copy number effect improves specificity of CRISPR-Cas9 essentiality screens in cancer cells](https://www.nature.com/articles/s41588-018-0194-x)
- **Data Portal**: https://depmap.org/portal/download/
