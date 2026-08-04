# COMPASS Immunotherapy Treatment Prediction Tool - MCP Server

A MCP tool from [Prism ToolSpace](https://huggingface.co/datasets/mims-harvard/ToolSpace) for running immune checkpoint inhibitor (ICI) response predictions using the [COMPASS model](https://github.com/mims-harvard/COMPASS). This tool processes the pateint level mRNA's TPM (transcripts per million) tumor expression profile and cancer context to predict patient responsiveness for immunotherapy and provides interpretable insights through immune cell concept analysis.


## Prerequisites

### 1. Install COMPASS Library

First, install the COMPASS library from the official repository:

```bash
# create a uv virtual enviroment for COMPASS setup
uv venv compass --python 3.10
source compass/bin/activate
uv pip install -r requirements.txt

# Install COMPASS
uv pip install immuno-compass

```

### 2. GPU Support (Optional)

For GPU acceleration, install CUDA-enabled PyTorch before installing other dependencies:

```bash
# For CUDA 11.7 (adjust version as needed)
uv pip install torch==1.13.1+cu117 torchvision==0.14.1+cu117 torchaudio==0.13.1 --index-url https://download.pytorch.org/whl/cu117

```

## Model Weights Setup

### 1. Download Pre-trained Models

Download the pre-trained COMPASS models from the official repository. Available models include:

- **`pft_leave_IMVigor210.pt`** - Fine-tuned on IMVigor210 cohort (urothelial carcinoma) - *Default*
- **`pft_leave_Gide.pt`** - Fine-tuned on Gide cohort (melanoma)
- **`pretrainer.pt`** - Base pre-trained model
- **`finetuner_pft_all.pt`** - Fine-tuned on all available cohorts

You can download models from:
- **Official Download Page**: https://www.immuno-compass.com/download/
- **Direct Model Links**:
  - IMVigor210: https://www.immuno-compass.com/download/model/LOCO/pft_leave_IMVigor210.pt
  - Gide: https://www.immuno-compass.com/download/model/LOCO/pft_leave_Gide.pt
  - Pre-trainer: https://www.immuno-compass.com/download/model/pretrainer.pt

### 2. Directory Structure Setup

Create the following directory structure for your model weights:

```
/path/to/your/compass/
├── immune-compass/
│   └── checkpoint/        # Model weights directory
│       ├── pft_leave_IMVigor210.pt
│       ├── pft_leave_Gide.pt
│       ├── pretrainer.pt
│       └── finetuner_pft_all.pt
```

### 3. Set Environment Variable

Set the `COMPASS_MODEL_PATH` environment variable to point to your COMPASS installation:

```bash
# Add to your ~/.bashrc or ~/.zshrc
export COMPASS_MODEL_PATH="/path/to/your/compass"
```

**Example Setup:**
```bash
# Create directory structure
mkdir -p /path/to/your/compass/checkpoint
cd /path/to/your/compass/checkpoint

# Download model weights to checkpoint directory
wget https://www.immuno-compass.com/download/model/LOCO/pft_leave_IMVigor210.pt
wget https://www.immuno-compass.com/download/model/LOCO/pft_leave_Gide.pt

# Set environment variable
export COMPASS_MODEL_PATH="/path/to/your/compass"
```

## Input and Output Specifications

### Input Format

The tool expects patient level TPM gene expression data in **pickle format** (`.pkl` file) containing a pandas DataFrame with:

- **Rows**: Samples/patients
- **Columns**: Genes (standard gene symbols like "CD274", "PDCD1", "CTLA4")
- **Values**: Normalized expression in TPM (Transcripts Per Million)
- **Minimum**: ~100 genes recommended for reliable predictions

For specifiction of how to prepare the patient TPM profile data, please refer to [COMPASS page](https://www.immuno-compass.com/).

### Output Format

The tool returns a structured JSON response:

```json
{
  "prediction": {
    "is_responder": true,
    "top_concepts": [
      {
        "concept": "CD8+ T cells",
        "score": 0.85
      },
      {
        "concept": "NK cells",
        "score": 0.72
      },
      ...
    ]
  },
  "context_info": [
    "COMPASS prediction completed successfully.",
    "Sample classified as: RESPONDER",
    "Analysis based on 15672 input genes.",
    "Top 44 immune cell concepts identified."
  ]
}
```

**Output Fields:**
- `is_responder` (bool): True if predicted responder (probability ≥ threshold)
- `top_concepts` (list): Ranked immune cell concepts with importance scores
- `context_info` (list): Human-readable analysis summary
- `error` (optional): Error description if prediction failed

## Running the MCP Server

### 1. Start the Server

```bash
# Enable the uv environment
uv source compass/bin/activate

# Set environment variable (if not in bashrc)
export COMPASS_MODEL_PATH="/path/to/your/compass"

# Run the MCP server
python compass_tool.py
```

### 2. Server Configuration

The server runs with the following default settings:
- **Host**: `0.0.0.0` (accepts connections from any IP)
- **Port**: `7003` (configured to avoid conflicts)
- **Transport**: `streamable-http`
- **Mode**: Stateless HTTP

### 3. Server Logs

When starting successfully, you'll see:
```
Starting MCP server for COMPASS Immune Response Prediction Tool...
Model: COMPASS (COMprehensive Pathway Analysis for Single-cell Sequencing)
Application: Immune Checkpoint Inhibitor Response Prediction
Server: FastMCP with streamable HTTP transport
Port: 7003 (configured to avoid conflicts with other biomedical tools)
```

## Tool Usage

### MCP Tool Function

The server exposes one main tool function:

```python
run_compass_prediction(
    gene_expression_data_path: str,
    threshold: float = 0.5,
    root_path: str = None
)
```

**Parameters:**
- `gene_expression_data_path` (str): Path to the pickle file containing TPM expression data
- `threshold` (float): Probability threshold for responder classification (0.0-1.0)
  - Default: 0.5 (balanced sensitivity/specificity)
  - Lower values (~0.3): Higher sensitivity
  - Higher values (~0.7): Higher specificity
- `root_path` (str, optional): Custom path to model checkpoint directory


## Troubleshooting

### Common Issues

1. **Model Not Found Error**
   ```
   FileNotFoundError: COMPASS model checkpoint not found at /path/to/checkpoint
   ```
   - Ensure `COMPASS_MODEL_PATH` is set correctly
   - Verify model weights are downloaded to the `checkpoint/` directory

2. **Import Error**
   ```
   ModuleNotFoundError: No module named 'compass'
   ```
   - Install COMPASS: `uv pip install immuno-compass`
   - Ensure you're in the correct conda environment


3. **Input Data Format Error**
   ```
   ValueError: Input data must be a non-empty dictionary
   ```
   - Ensure input file is in pickle format with correct DataFrame structure
   - Check that gene symbols are standard (e.g., "CD274", not "PD-L1")


## References

- **COMPASS Paper**: [Generalizable AI predicts immunotherapy outcomes across cancers and treatments](https://github.com/mims-harvard/COMPASS)
- **Project Website**: https://www.immuno-compass.com/
- **GitHub Repository**: https://github.com/mims-harvard/COMPASS
- **Documentation**: https://compass.readthedocs.io/

## Citation

If you use this tool, please cite the COMPASS paper:

```bibtex
@article{shen2024compass,
  title={Generalizable AI predicts immunotherapy outcomes across cancers and treatments},
  author={Shen, Wanxiang and Nguyen, Thinh H. and Li, Michelle M. and Huang, Yepeng and Moon, Intae and Nair, Nitya and Marbach, Daniel and Zitnik, Marinka},
  journal={medRxiv},
  year={2024}
}
```

## License

This tool is released under the MIT License, consistent with the original COMPASS project.
