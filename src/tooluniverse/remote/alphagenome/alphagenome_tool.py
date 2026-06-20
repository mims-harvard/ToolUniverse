"""
AlphaGenome regulatory-genomics prediction — MCP Server.

AlphaGenome (Avsec et al., Nature 2026) is DeepMind's hosted successor to
Enformer / Borzoi: a single DNA-sequence model that predicts multimodal genomic
tracks (RNA-seq, CAGE, ATAC, DNase, histone/TF ChIP, splicing, contact maps)
over up to 1 Mb at single-base resolution, and scores regulatory variant effects.

AlphaGenome is a **hosted API** reached over gRPC through the official
``alphagenome`` Python SDK. Served as a ToolUniverse *remote* tool so that the
SDK dependency and the ``ALPHA_GENOME_API_KEY`` credential live on the server,
keeping the core install light. It is free for non-commercial use; obtain a key
at https://deepmind.google.com/science/alphagenome.

Two operations:
  * run_alphagenome_score_variant    -> recommended ref-vs-alt variant-effect scores
  * run_alphagenome_predict_interval -> compact per-modality track summary for an interval

Reference
---------
Avsec Z, Latysheva N, Cheng J, et al. "Advancing regulatory variant effect
prediction with AlphaGenome." Nature 649, 1206-1218 (2026).
doi:10.1038/s41586-025-10014-0.
"""

import os
from typing import Any, Dict, List

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

_ORGANISMS = {"human": "HOMO_SAPIENS", "mouse": "MUS_MUSCULUS"}
_SEQ_LENGTHS = {
    "16KB": "SEQUENCE_LENGTH_16KB",
    "100KB": "SEQUENCE_LENGTH_100KB",
    "500KB": "SEQUENCE_LENGTH_500KB",
    "1MB": "SEQUENCE_LENGTH_1MB",
}


def _make_client():
    """Import the SDK, read the key, and build a client — or return an error dict."""
    try:
        from alphagenome.data import genome
        from alphagenome.models import dna_client, variant_scorers
    except ImportError:
        return {
            "error": "The 'alphagenome' package is required on the server: pip install alphagenome."
        }
    api_key = os.environ.get("ALPHA_GENOME_API_KEY", "")
    if not api_key:
        return {
            "error": "Set ALPHA_GENOME_API_KEY on the server (free non-commercial key at "
            "https://deepmind.google.com/science/alphagenome)."
        }
    model = dna_client.create(api_key)
    return model, (genome, dna_client, variant_scorers)


def _organism(mods, name: str):
    _, dna_client, _ = mods
    return getattr(
        dna_client.Organism, _ORGANISMS.get((name or "human").lower(), "HOMO_SAPIENS")
    )


def _seq_length(mods, name: str):
    _, dna_client, _ = mods
    return getattr(
        dna_client, _SEQ_LENGTHS.get((name or "1MB").upper(), "SEQUENCE_LENGTH_1MB")
    )


def _output_types(mods, names: List[str]):
    _, dna_client, _ = mods
    out = []
    for n in names or ["RNA_SEQ"]:
        ot = getattr(dna_client.OutputType, str(n).upper(), None)
        if ot is not None:
            out.append(ot)
    return out or [dna_client.OutputType.RNA_SEQ]


def _summarize_scores(scores, top_n: int) -> List[Dict[str, Any]]:
    """Flatten the AnnData score objects to the top |score| per-track entries."""
    rows: List[Dict[str, Any]] = []
    for adata in scores or []:
        values = adata.X
        names = list(getattr(adata, "var_names", []))
        flat = values.ravel().tolist() if hasattr(values, "ravel") else list(values)
        for name, val in zip(names, flat):
            rows.append({"track": str(name), "score": float(val)})
    rows.sort(key=lambda r: abs(r["score"]), reverse=True)
    return rows[:top_n]


def _summarize_outputs(output) -> List[Dict[str, Any]]:
    """Per requested modality: track count + shape (the raw tensors are huge)."""
    summary = []
    for attr in (
        "rna_seq",
        "atac",
        "dnase",
        "cage",
        "chip_histone",
        "chip_tf",
        "splice_sites",
        "contact_maps",
    ):
        td = getattr(output, attr, None)
        if td is None:
            continue
        values = getattr(td, "values", None)
        meta = getattr(td, "metadata", None)
        summary.append(
            {
                "modality": attr,
                "shape": list(getattr(values, "shape", []) or []),
                "n_tracks": int(len(meta)) if meta is not None else None,
            }
        )
    return summary


@register_mcp_tool(
    tool_type_name="run_alphagenome_score_variant",
    config={
        "description": (
            "Score a regulatory variant's effect with DeepMind AlphaGenome (Avsec, "
            "Nature 2026), the hosted successor to Enformer/Borzoi. Predicts ref vs "
            "alt over up to 1 Mb at single-base resolution and returns the "
            "recommended per-track effect scores (sorted by |effect|). The hosted "
            "SDK call and ALPHA_GENOME_API_KEY live on the server."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "chromosome": {
                    "type": "string",
                    "description": "Chromosome, e.g. 'chr22'.",
                },
                "position": {
                    "type": "integer",
                    "description": "1-based variant position.",
                },
                "reference_bases": {
                    "type": "string",
                    "description": "Reference allele, e.g. 'A'.",
                },
                "alternate_bases": {
                    "type": "string",
                    "description": "Alternate allele, e.g. 'C'.",
                },
                "output_type": {
                    "type": "string",
                    "description": "Modality to score: RNA_SEQ (default), ATAC, DNASE, CAGE, CHIP_HISTONE, CHIP_TF, SPLICE_SITES, CONTACT_MAPS.",
                },
                "organism": {
                    "type": "string",
                    "description": "'human' (default) or 'mouse'.",
                },
                "sequence_length": {
                    "type": "string",
                    "description": "Context window: 16KB, 100KB, 500KB, or 1MB (default).",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top |effect| tracks to return (default 20).",
                },
            },
            "required": [
                "chromosome",
                "position",
                "reference_bases",
                "alternate_bases",
            ],
        },
    },
    mcp_config={
        "server_name": "AlphaGenome MCP Server",
        "host": "127.0.0.1",
        "port": 8033,
        "transport": "http",
    },
)
class AlphagenomeScoreVariantTool:
    """Score a regulatory variant's effect via the AlphaGenome hosted API."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        args = arguments or {}
        required = ["chromosome", "position", "reference_bases", "alternate_bases"]
        missing = [k for k in required if not args.get(k)]
        if missing:
            return {"error": f"Missing required parameter(s): {', '.join(missing)}"}
        client = _make_client()
        if isinstance(client, dict):
            return client
        model, mods = client
        genome, _, variant_scorers = mods
        try:
            variant = genome.Variant(
                chromosome=str(args["chromosome"]),
                position=int(args["position"]),
                reference_bases=str(args["reference_bases"]),
                alternate_bases=str(args["alternate_bases"]),
            )
            interval = variant.reference_interval.resize(
                _seq_length(mods, args.get("sequence_length"))
            )
            out_type = str(args.get("output_type") or "RNA_SEQ").upper()
            scorer = variant_scorers.RECOMMENDED_VARIANT_SCORERS[out_type]
            scores = model.score_variant(
                interval=interval,
                variant=variant,
                variant_scorers=[scorer],
                organism=_organism(mods, args.get("organism")),
            )
        except Exception as exc:  # never raise out of run()
            return {"error": f"AlphaGenome request failed: {type(exc).__name__}: {exc}"}
        return {
            "model": "AlphaGenome",
            "provider": "Google DeepMind (hosted API)",
            "variant": f"{args['chromosome']}:{args['position']}{args['reference_bases']}>{args['alternate_bases']}",
            "output_type": out_type,
            "scores": _summarize_scores(scores, int(args.get("top_n") or 20)),
        }


@register_mcp_tool(
    tool_type_name="run_alphagenome_predict_interval",
    config={
        "description": (
            "Predict multimodal genomic tracks for a genomic interval with DeepMind "
            "AlphaGenome (single DNA-sequence model; up to 1 Mb at single-base "
            "resolution). Returns a compact per-modality summary (track counts and "
            "shapes) for the requested outputs. The hosted SDK call and "
            "ALPHA_GENOME_API_KEY live on the server."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "chromosome": {
                    "type": "string",
                    "description": "Chromosome, e.g. 'chr19'.",
                },
                "start": {
                    "type": "integer",
                    "description": "Interval start (0-based).",
                },
                "end": {"type": "integer", "description": "Interval end."},
                "output_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Modalities to predict, e.g. ['RNA_SEQ','ATAC'] (default ['RNA_SEQ']).",
                },
                "ontology_terms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tissue/cell ontology terms (e.g. ['UBERON:0001114'] = liver) to restrict tracks.",
                },
                "organism": {
                    "type": "string",
                    "description": "'human' (default) or 'mouse'.",
                },
                "sequence_length": {
                    "type": "string",
                    "description": "Context window: 16KB, 100KB, 500KB, or 1MB (default).",
                },
            },
            "required": ["chromosome", "start", "end"],
        },
    },
    mcp_config={
        "server_name": "AlphaGenome MCP Server",
        "host": "127.0.0.1",
        "port": 8033,
        "transport": "http",
    },
)
class AlphagenomePredictIntervalTool:
    """Predict multimodal genomic tracks for an interval via the AlphaGenome API."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        args = arguments or {}
        required = ["chromosome", "start", "end"]
        missing = [k for k in required if args.get(k) is None]
        if missing:
            return {"error": f"Missing required parameter(s): {', '.join(missing)}"}
        client = _make_client()
        if isinstance(client, dict):
            return client
        model, mods = client
        genome, _, _ = mods
        try:
            interval = genome.Interval(
                chromosome=str(args["chromosome"]),
                start=int(args["start"]),
                end=int(args["end"]),
            ).resize(_seq_length(mods, args.get("sequence_length")))
            output = model.predict_interval(
                interval=interval,
                requested_outputs=_output_types(mods, args.get("output_types")),
                ontology_terms=args.get("ontology_terms") or None,
                organism=_organism(mods, args.get("organism")),
            )
        except Exception as exc:
            return {"error": f"AlphaGenome request failed: {type(exc).__name__}: {exc}"}
        return {
            "model": "AlphaGenome",
            "provider": "Google DeepMind (hosted API)",
            "interval": f"{interval.chromosome}:{interval.start}-{interval.end}",
            "tracks": _summarize_outputs(output),
        }


if __name__ == "__main__":
    start_mcp_server()
