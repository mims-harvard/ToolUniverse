# Carbon-A

[Carbon-A](https://huggingface.co/HuggingFaceBio/Carbon-A-1.2B) annotates
protein-coding genes in eukaryotic genomes. The 1.2B-parameter DNA model gives
every base a strand-specific coding probability, and the annotation pipeline
that ships with it decodes those probabilities into gene models with a
confidence score per gene. ToolUniverse reaches it as a remote tool: a provider
runs an MCP server next to the GPU, and clients call the
`carbon_a_annotate_cds` operation through that server.

The tool runs the annotation pipeline's genome-scale path: model inference, the
transition network, the Viterbi decode, and the confidence network. The
pipeline's reference-based evaluation (`run_evaluation.sh`) and BUSCO
evaluation (`run_busco.sh`) are separate stages this tool does not run; the
live-validation script below calls the first of them directly.

## What it returns

Per gene: the record it sits on, strand, 1-based start and end, the number of
CDS features, whether a record edge truncated it, and `confidence` — the
model's own probability that the gene's structure is exactly right. Optionally
the full GFF3 and each gene's translated protein.

Two pipeline behaviours are passed through rather than smoothed over:

- **Short records are skipped, not annotated.** The pipeline's floor is
  100,000 bp, because the model reads a 98,304 bp window. A sequence below
  `min_record_length` is refused with an explanation instead of returning no
  genes, which would be indistinguishable from a genome with no genes in it.
- **A genetic code that may not fit the sequence is flagged.** The pipeline
  checks its result and, on a likely mismatch, writes a warning and renames its
  output directory. The genes are still returned, with the warning in
  `warnings`.

## Provider setup

### Requirements

- Linux with a CUDA GPU. The model runs in bfloat16; the weights are 4.6 GB.
- Python 3.10 or later, a CUDA build of PyTorch (`torch>=2.7,<3`), and
  Transformers `>=4.56,<5`. Transformers 5 does not load the model with
  FlashAttention-2.
- A C++17 compiler with OpenMP, for the Viterbi CPU backend, which is compiled
  on first use. The GPU backend additionally needs a CUDA toolkit.
- `flash-attn` for the `flash_attention_2` default. `sdpa` needs no extra
  package and is not bit-identical.

### 1. Install the model and pipeline

```bash
pip install -U "huggingface_hub>=0.34"
hf download HuggingFaceBio/Carbon-A-1.2B \
    --exclude model.safetensors --local-dir Carbon-A-1.2B
pip install -r Carbon-A-1.2B/requirements.txt
pip install --no-build-isolation flash-attn   # optional; sdpa works without it
```

The weights download to the Hugging Face cache on first use.

### 2. Install ToolUniverse

```bash
pip install tooluniverse
```

### 3. Configure the provider

| Variable | Required | Meaning |
| --- | --- | --- |
| `CARBON_A_PIPELINE` | yes | Path to `annotation_pipeline/run_annotation.sh`. |
| `CARBON_A_INPUT_ROOT` | for `input_file` | Directory holding genome FASTA/GenBank files callers may name. |
| `CARBON_A_JOB_ROOT` | no | Parent for per-call scratch directories. Defaults to the system temporary directory. |
| `CARBON_A_MODEL` | no | Model id or local directory. Defaults to `HuggingFaceBio/Carbon-A-1.2B`. |
| `CARBON_A_PYTHON` | no | Interpreter whose directory is put first on `PATH`, so the pipeline resolves the Carbon-A environment. |
| `CARBON_A_ATTN_IMPLEMENTATION` | no | Default attention kernel when a caller does not pass one. |

Keep the weights, the pipeline checkout and job scratch space outside Git.

### 4. Start the server

```bash
python -m tooluniverse.remote.carbon_a.carbon_a_mcp_server
```

The endpoint is `http://127.0.0.1:8034/mcp`. Non-loopback binding requires
`TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback.

The server runs one annotation at a time, because a call holds the GPU and the
4.6 GB of weights for minutes. A caller that cannot start within its own
`timeout_seconds` gets a busy error rather than an unbounded wait.

### 5. Check it end to end

```bash
python scripts/remote_validation/carbon_a_live_validation.py \
    --out carbon_a_validation \
    --genome-dir "$CARBON_A_INPUT_ROOT/GCF_000146045.2"
```

With a genome directory that also holds the NCBI reference annotation
(`genomic.gff`), the script runs the pipeline's own evaluation and reports
nucleotide, exon and gene F1 so the deployment can be compared against the
numbers the model card publishes.

## Client use

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

tu.run_one_function(
    {
        "name": "carbon_a_annotate_cds",
        "arguments": {
            "input_file": "GCF_000146045.2/GCF_000146045.2_R64_genomic.fna",
            "max_genes": 5,
            "timeout_seconds": 3600,
        },
    }
)
```

Set `CARBON_A_MCP_SERVER_HOST` to the provider's host so
`mcp_auto_loader_carbon_a` can discover the operation.

Carbon-A runs at roughly 10 kbp per second on one GPU, so pick
`timeout_seconds` from the size of the record: a 12 Mbp genome takes about
20 minutes end to end, and the 3600 s ceiling covers roughly 35 Mbp. Larger
genomes belong in a provider-side batch run rather than a tool call.

## Benchmark genomes

The genomes Carbon-A is evaluated on, each with its NCBI reference annotation,
are published alongside the model and are reachable without a GPU through two
ordinary tools:

- `Carbon_A_list_benchmark_genomes` — the 41 genomes with organism, taxon id,
  assembly name and size.
- `Carbon_A_get_benchmark_genome` — one genome's files with download URLs and
  md5 checksums, plus its per-molecule sequence report.
