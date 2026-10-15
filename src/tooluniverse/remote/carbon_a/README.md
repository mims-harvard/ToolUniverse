# Carbon-A Remote Tool

## Validation and deployment status (2026-10-13)

> Carbon-A (`HuggingFaceBio/Carbon-A-1.2B`, weights sha256 `5e0a5818…`, with the
> repository's own `annotation_pipeline/`) ran on one NVIDIA GB10 (aarch64,
> compute 12.1) under torch 2.14.1+cu130 and Transformers 4.57.6, with
> `--attn-implementation sdpa` because `flash-attn` was not installed. Through a
> direct loopback MCP connection, ToolUniverse discovered `carbon_a_annotate_cds`
> and annotated the *Saccharomyces cerevisiae* benchmark genome
> (GCF_000146045.2, 12.16 Mbp over 17 records) in 1,169 s: 5,899 genes
> predicted, 5,791 at confidence ≥ 0.1, median confidence 0.968, 8,744,178
> coding bases over 16 records — 72 % coding density, and one 85 kb record (the
> mitochondrion) skipped by the pipeline's 100 kb record floor, as designed. The
> GPU Viterbi backend compiled and ran (5 Mbp/s). Of the 2,000 genes returned,
> 1,953 (97.7 %) have both endpoints equal to an NCBI protein-coding gene's, 45
> overlap one, 2 have no reference gene at the locus and none sit on a record
> the reference does not have.
>
> Run directly, the same prediction scored **nucleotide F1 0.9985, exon F1
> 0.9428, gene F1 0.9528** under the pipeline's own `run_evaluation.sh` against
> the NCBI reference annotation, matching the 0.998 / 0.943 / 0.953 the model
> card publishes for this genome. That is the check that the deployment is
> correct rather than merely running. `run_evaluation.sh` is not what the
> validation script calls, because it needs a `prediction.fna` of CDS
> nucleotides that this operation does not return: scoring those files would
> measure the pipeline, not whether the tool reports its output correctly, so
> the script compares the genes the tool actually returned against the
> reference instead.
>
> Not exercised: FlashAttention-2 (so bit-identical probabilities are
> unconfirmed), multi-GPU and concurrent load, genomes larger than yeast, the
> non-standard genetic code path on *Tetrahymena thermophila*, GenBank input,
> gzip-compressed input, platform relay sharing (`tu remote share`) and
> non-loopback binding. Keep this deployment private.

- Operation: `carbon_a_annotate_cds`
- Start: `python -m tooluniverse.remote.carbon_a.carbon_a_mcp_server`
- Endpoint: `http://127.0.0.1:8034/mcp`
- Provider configuration: `CARBON_A_PIPELINE` is required and must point at
  `annotation_pipeline/run_annotation.sh`. `CARBON_A_INPUT_ROOT` is required for
  `input_file` callers, and `CARBON_A_JOB_ROOT`, `CARBON_A_MODEL`,
  `CARBON_A_PYTHON` and `CARBON_A_ATTN_IMPLEMENTATION` are optional. Keep the
  4.6 GB of weights, the pipeline checkout and job scratch space outside Git.
  The server runs one annotation at a time; a call that cannot start within its
  own timeout gets a busy error.
- End-to-end check:
  `python scripts/remote_validation/carbon_a_live_validation.py --out carbon_a_validation --genome-dir "$CARBON_A_INPUT_ROOT/GCF_000146045.2"`
  (a genome directory that also holds the NCBI `genomic.gff` enables the
  reference comparison, which is what makes the run falsifiable)

`CARBON_A_PYTHON` exists because the provider process and the model usually live
in different environments: the pipeline invokes a bare `python`, so that
interpreter's directory is put first on `PATH` for the subprocess. The
validation above ran the server from a ToolUniverse environment with no torch in
it and the pipeline from a CUDA environment with no ToolUniverse in it.

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback.

This implementation is not in the `tu remote share` catalog or the shared
setup-skill preflight, because neither could be exercised without a Platform
service key.

The benchmark genomes this was validated against are reachable without a GPU
through `Carbon_A_list_benchmark_genomes` and `Carbon_A_get_benchmark_genome`.

See the [setup and usage guide](../../../../docs/tools/remote/carbon_a.md) for
installation, parameters, and output format.
