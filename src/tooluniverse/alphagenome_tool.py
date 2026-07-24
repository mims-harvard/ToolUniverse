"""DeepMind AlphaGenome regulatory-genomics prediction tool.

AlphaGenome (Avsec et al., *Nature* 2026) is the hosted successor to Enformer /
Borzoi: a single DNA-sequence model that predicts multimodal genomic tracks
(RNA-seq, CAGE, ATAC, DNase, histone/TF ChIP, splicing, contact maps) over up to
1 Mb at single-base resolution, and scores regulatory variant effects.

Unlike Enformer/Borzoi (local weights), AlphaGenome is a **hosted API**: requests
go over gRPC through the official ``alphagenome`` Python SDK to DeepMind's
servers, so this is integrated as a normal key-gated tool rather than a remote
MCP server. It is free for non-commercial use; obtain a key at
https://deepmind.google.com/science/alphagenome and set ``ALPHA_GENOME_API_KEY``.

Operations (selected via the ``operation`` field):
  * score_variant    -> recommended ref-vs-alt variant-effect scores per track
  * predict_interval -> a compact summary of predicted tracks for an interval

The SDK (``pip install alphagenome``) is an optional dependency; ``run()`` returns
a clear error dict if it or the API key is missing, and never raises.

Reference
---------
Avsec Z, Latysheva N, Cheng J, et al. "Advancing regulatory variant effect
prediction with AlphaGenome." Nature 649, 1206-1218 (2026).
doi:10.1038/s41586-025-10014-0.
"""

import os
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

_ORGANISMS = {"human": "HOMO_SAPIENS", "mouse": "MUS_MUSCULUS"}
_SEQ_LENGTHS = {
    "16KB": "SEQUENCE_LENGTH_16KB",
    "100KB": "SEQUENCE_LENGTH_100KB",
    "500KB": "SEQUENCE_LENGTH_500KB",
    "1MB": "SEQUENCE_LENGTH_1MB",
}


@register_tool("AlphaGenomeTool")
class AlphaGenomeTool(BaseTool):
    """Predict genomic tracks / score variant effects via the AlphaGenome API."""

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None):
        super().__init__(tool_config)
        self.tool_config = tool_config or {}
        self.operation = (self.tool_config.get("fields", {}) or {}).get("operation", "")

    # ------------------------------------------------------------------ run
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        operation = self.operation or args.get("operation")

        client = self._make_client()
        if isinstance(client, dict):  # error dict from setup
            return client
        model, mods = client

        try:
            if operation == "score_variant":
                return self._score_variant(model, mods, args)
            if operation == "predict_interval":
                return self._predict_interval(model, mods, args)
            return self._err(
                f"Unknown operation {operation!r}. Use 'score_variant' or "
                "'predict_interval'."
            )
        except Exception as exc:  # never raise out of run()
            return self._err(f"AlphaGenome request failed: {type(exc).__name__}: {exc}")

    # -------------------------------------------------------------- helpers
    def _make_client(self):
        """Import the SDK, read the key, and build a client — or return an error dict."""
        try:
            from alphagenome.data import genome
            from alphagenome.models import dna_client, variant_scorers
        except ImportError:
            return self._err(
                "The 'alphagenome' package is required: pip install alphagenome."
            )
        api_key = os.environ.get("ALPHA_GENOME_API_KEY", "")
        if not api_key:
            return self._err(
                "Set ALPHA_GENOME_API_KEY (free non-commercial key at "
                "https://deepmind.google.com/science/alphagenome)."
            )
        model = dna_client.create(api_key)
        return model, (genome, dna_client, variant_scorers)

    @staticmethod
    def _organism(mods, name: str):
        _, dna_client, _ = mods
        return getattr(
            dna_client.Organism,
            _ORGANISMS.get((name or "human").lower(), "HOMO_SAPIENS"),
        )

    @staticmethod
    def _seq_length(mods, name: str):
        _, dna_client, _ = mods
        return getattr(
            dna_client, _SEQ_LENGTHS.get((name or "1MB").upper(), "SEQUENCE_LENGTH_1MB")
        )

    @staticmethod
    def _output_types(mods, names: List[str]):
        _, dna_client, _ = mods
        out = []
        for n in names or ["RNA_SEQ"]:
            ot = getattr(dna_client.OutputType, str(n).upper(), None)
            if ot is not None:
                out.append(ot)
        return out or [dna_client.OutputType.RNA_SEQ]

    # ------------------------------------------------------------- operations
    def _score_variant(self, model, mods, args: Dict[str, Any]) -> Dict[str, Any]:
        genome, _, variant_scorers = mods
        required = ["chromosome", "position", "reference_bases", "alternate_bases"]
        missing = [k for k in required if not args.get(k)]
        if missing:
            return self._err(f"Missing required parameter(s): {', '.join(missing)}")

        variant = genome.Variant(
            chromosome=str(args["chromosome"]),
            position=int(args["position"]),
            reference_bases=str(args["reference_bases"]),
            alternate_bases=str(args["alternate_bases"]),
        )
        interval = variant.reference_interval.resize(
            self._seq_length(mods, args.get("sequence_length"))
        )
        out_type = str(args.get("output_type") or "RNA_SEQ").upper()
        scorer = variant_scorers.RECOMMENDED_VARIANT_SCORERS[out_type]
        scores = model.score_variant(
            interval=interval,
            variant=variant,
            variant_scorers=[scorer],
            organism=self._organism(mods, args.get("organism")),
        )
        top_n = int(args.get("top_n") or 20)
        variant_label = (
            f"{variant.chromosome}:{variant.position}"
            f"{variant.reference_bases}>{variant.alternate_bases}"
        )
        return self._ok(
            {
                "variant": variant_label,
                "output_type": out_type,
                "scores": self._summarize_scores(scores, top_n),
            },
            task="score_variant",
        )

    def _predict_interval(self, model, mods, args: Dict[str, Any]) -> Dict[str, Any]:
        genome, _, _ = mods
        required = ["chromosome", "start", "end"]
        missing = [k for k in required if args.get(k) is None]
        if missing:
            return self._err(f"Missing required parameter(s): {', '.join(missing)}")

        interval = genome.Interval(
            chromosome=str(args["chromosome"]),
            start=int(args["start"]),
            end=int(args["end"]),
        ).resize(self._seq_length(mods, args.get("sequence_length")))
        output = model.predict_interval(
            interval=interval,
            requested_outputs=self._output_types(mods, args.get("output_types")),
            ontology_terms=args.get("ontology_terms") or None,
            organism=self._organism(mods, args.get("organism")),
        )
        return self._ok(
            {
                "interval": f"{interval.chromosome}:{interval.start}-{interval.end}",
                "tracks": self._summarize_outputs(output),
            },
            task="predict_interval",
        )

    # ------------------------------------------------------------- formatting
    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def _ok(data: Any, **meta: Any) -> Dict[str, Any]:
        m = {"source": "AlphaGenome", "provider": "Google DeepMind (hosted API)"}
        m.update(meta)
        return {"status": "success", "data": data, "metadata": m}

    @staticmethod
    def _err(message: str) -> Dict[str, Any]:
        return {"status": "error", "error": message, "source": "AlphaGenome"}
