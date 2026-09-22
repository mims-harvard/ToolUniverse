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
  Live model (``dna_client``, gRPC to DeepMind's servers, runs the model):
    * score_variant        -> recommended ref-vs-alt variant-effect scores per track
    * predict_variant      -> raw ref AND alt predicted tracks for one variant
    * predict_interval     -> a compact summary of predicted tracks for an interval
    * predict_sequence     -> predicted tracks for a raw DNA sequence (no genome
                               coordinates needed)
    * score_interval       -> default gene-mask scores for a whole interval
    * score_ism_variants   -> in-silico saturation mutagenesis: scores every
                               possible substitution in a short window, ranked
                               by peak effect (capped at 500 bp -- see the tool)
    * output_metadata      -> discovery: track counts + sample ontology_terms
                               per modality (what's valid to filter on)

  Atlas (``alphagenome.atlas``, precomputed lookup -- no live model run, much
  higher query rate; released Sep 2026, covers all ~9B possible human SNVs):
    * atlas_lookup_variant -> precomputed scores (incl. the unified AVI_SCORE)
                               for one single-nucleotide substitution
    * atlas_scan_interval  -> precomputed scores for every SNV in a region
                               (capped at 10,000 bp -- see the tool)
    * atlas_list_scorers   -> discovery: valid Atlas scorer names

The SDK (``pip install alphagenome``) is an optional dependency; ``run()`` returns
a clear error dict if it or the API key is missing, and never raises.

Reference
---------
Avsec Z, Latysheva N, Cheng J, et al. "Advancing regulatory variant effect
prediction with AlphaGenome." Nature 649, 1206-1218 (2026).
doi:10.1038/s41586-025-10014-0.
"""

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
    _ATLAS_OPERATIONS = (
        "atlas_lookup_variant",
        "atlas_scan_interval",
        "atlas_list_scorers",
    )
    _LIVE_OPERATIONS = (
        "score_variant",
        "predict_variant",
        "predict_interval",
        "predict_sequence",
        "score_interval",
        "score_ism_variants",
        "output_metadata",
    )

    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        operation = self.operation or args.get("operation")

        if operation == "atlas_lookup_variant":
            return self._run_atlas_lookup_variant(args)
        if operation == "atlas_scan_interval":
            return self._run_atlas_scan_interval(args)
        if operation == "atlas_list_scorers":
            return self._run_atlas_list_scorers(args)

        if operation not in self._LIVE_OPERATIONS:
            return self._err(
                f"Unknown operation {operation!r}. Use one of: "
                + ", ".join(self._ATLAS_OPERATIONS + self._LIVE_OPERATIONS)
            )

        client = self._make_client()
        if isinstance(client, dict):  # error dict from setup
            return client
        model, mods = client

        handler = {
            "score_variant": self._score_variant,
            "predict_variant": self._predict_variant,
            "predict_interval": self._predict_interval,
            "predict_sequence": self._predict_sequence,
            "score_interval": self._score_interval,
            "score_ism_variants": self._score_ism_variants,
            "output_metadata": self._run_output_metadata,
        }[operation]
        try:
            return handler(model, mods, args)
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
        api_key = self.credential("ALPHA_GENOME_API_KEY") or ""
        if not api_key:
            return self._err(
                "Set ALPHA_GENOME_API_KEY (free non-commercial key at "
                "https://deepmind.google.com/science/alphagenome)."
            )
        model = dna_client.create(api_key)
        return model, (genome, dna_client, variant_scorers)

    def _make_atlas_client(self):
        """Import the Atlas SDK, read the key, and build a client -- or an error dict."""
        try:
            from alphagenome.atlas import atlas
        except ImportError:
            return self._err(
                "AlphaGenome Atlas support requires an up-to-date SDK: "
                "pip install --upgrade alphagenome."
            )
        api_key = self.credential("ALPHA_GENOME_API_KEY") or ""
        if not api_key:
            return self._err(
                "Set ALPHA_GENOME_API_KEY (free non-commercial key at "
                "https://deepmind.google.com/science/alphagenome)."
            )
        return atlas.create(api_key)

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

    @staticmethod
    def _parse_top_n(args: Dict[str, Any], default: int = 20) -> int:
        """Parse/clamp `top_n` to a positive int.

        A non-positive value (found live: -3) must not reach a plain
        ``list[:top_n]`` slice -- Python's negative-index slicing silently
        returns "all but the last N" instead of erroring, so `top_n=-3`
        against a ~13,700-row result returned 13,724 rows, not a small
        top-N summary.
        """
        try:
            n = int(args.get("top_n") or default)
        except (TypeError, ValueError):
            return default
        return n if n > 0 else default

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
        top_n = self._parse_top_n(args)
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

    def _predict_variant(self, model, mods, args: Dict[str, Any]) -> Dict[str, Any]:
        """Raw ref-vs-alt predicted tracks (not the scorer-reduced summary).

        Distinct from score_variant: this is the full multimodal prediction
        for both alleles (same shape as predict_interval's Output, verified
        live), useful when you want the actual track values rather than a
        single recommended effect score per gene.
        """
        genome, _, _ = mods
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
        output = model.predict_variant(
            interval=interval,
            variant=variant,
            requested_outputs=self._output_types(mods, args.get("output_types")),
            ontology_terms=args.get("ontology_terms") or None,
            organism=self._organism(mods, args.get("organism")),
        )
        variant_label = (
            f"{variant.chromosome}:{variant.position}"
            f"{variant.reference_bases}>{variant.alternate_bases}"
        )
        return self._ok(
            {
                "variant": variant_label,
                "reference": self._summarize_outputs(output.reference),
                "alternate": self._summarize_outputs(output.alternate),
            },
            task="predict_variant",
        )

    def _predict_sequence(self, model, mods, args: Dict[str, Any]) -> Dict[str, Any]:
        """Predict tracks for a raw DNA sequence, with no genome coordinates."""
        sequence = args.get("sequence")
        if not sequence:
            return self._err("Missing required parameter(s): sequence")

        output = model.predict_sequence(
            sequence=str(sequence),
            requested_outputs=self._output_types(mods, args.get("output_types")),
            ontology_terms=args.get("ontology_terms") or None,
            organism=self._organism(mods, args.get("organism")),
        )
        return self._ok(
            {
                "sequence_length": len(str(sequence)),
                "tracks": self._summarize_outputs(output),
            },
            task="predict_sequence",
        )

    def _score_interval(self, model, mods, args: Dict[str, Any]) -> Dict[str, Any]:
        """Default gene-mask scores for a whole interval (no specific variant)."""
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
        scores = model.score_interval(
            interval=interval,
            organism=self._organism(mods, args.get("organism")),
        )
        top_n = self._parse_top_n(args)
        return self._ok(
            {
                "interval": f"{interval.chromosome}:{interval.start}-{interval.end}",
                "scores": self._summarize_scores(scores, top_n),
            },
            task="score_interval",
        )

    _MAX_ISM_WINDOW_BP = 500

    def _score_ism_variants(self, model, mods, args: Dict[str, Any]) -> Dict[str, Any]:
        """In-silico saturation mutagenesis: score every substitution in a window.

        Ranks candidate substitutions by their single most extreme per-gene,
        per-track effect (verified live: each candidate's AnnData has the same
        gene_name/name shape as score_variant's, tagged with the exact
        substitution in ``adata.uns["variant"]``) -- a "which bases matter
        most" scan, not a full per-track dump (that would be
        width_bp * 3 alternates * n_tracks values, far too much to return).
        """
        genome, _, variant_scorers = mods
        required = ["chromosome", "start", "end"]
        missing = [k for k in required if args.get(k) is None]
        if missing:
            return self._err(f"Missing required parameter(s): {', '.join(missing)}")

        ism_interval = genome.Interval(
            chromosome=str(args["chromosome"]),
            start=int(args["start"]),
            end=int(args["end"]),
        )
        width = ism_interval.end - ism_interval.start
        if width > self._MAX_ISM_WINDOW_BP:
            return self._err(
                f"ISM window too wide ({width} bp): keep start/end within "
                f"{self._MAX_ISM_WINDOW_BP} bp. score_ism_variants scores "
                "every possible substitution in the window (~3x width live "
                "model calls), so cost grows fast with window size."
            )

        context_interval = ism_interval.resize(
            self._seq_length(mods, args.get("sequence_length"))
        )
        out_type = str(args.get("output_type") or "RNA_SEQ").upper()
        scorer = variant_scorers.RECOMMENDED_VARIANT_SCORERS[out_type]
        results = model.score_ism_variants(
            interval=context_interval,
            ism_interval=ism_interval,
            variant_scorers=[scorer],
            organism=self._organism(mods, args.get("organism")),
            progress_bar=False,
        )
        top_n = self._parse_top_n(args)
        candidates: List[Dict[str, Any]] = []
        for per_scorer_results in results or []:
            for adata in per_scorer_results:
                peak = self._summarize_scores([adata], top_n=1)
                if not peak:
                    continue
                entry = dict(peak[0])
                entry["variant"] = str(getattr(adata, "uns", {}).get("variant", ""))
                candidates.append(entry)
        candidates.sort(key=lambda r: abs(r["score"]), reverse=True)
        return self._ok(
            {
                "ism_interval": f"{ism_interval.chromosome}:{ism_interval.start}-{ism_interval.end}",
                "output_type": out_type,
                "top_variants": candidates[:top_n],
            },
            task="score_ism_variants",
        )

    def _run_output_metadata(self, model, mods, args: Dict[str, Any]) -> Dict[str, Any]:
        """Discovery: per-modality track counts and sample ontology_terms.

        Answers "what can I even filter on" for the ontology_terms parameter
        shared by score_variant/predict_variant/predict_interval/predict_sequence.
        """
        om = model.output_metadata(organism=self._organism(mods, args.get("organism")))
        modalities = []
        for attr in (
            "rna_seq",
            "atac",
            "dnase",
            "cage",
            "chip_histone",
            "chip_tf",
            "splice_sites",
            "splice_site_usage",
            "splice_junctions",
            "contact_maps",
            "procap",
        ):
            df = getattr(om, attr, None)
            if df is None:
                continue
            sample_terms = None
            if hasattr(df, "columns") and "ontology_curie" in df.columns:
                sample_terms = sorted(set(df["ontology_curie"].dropna().tolist()))[:10]
            modalities.append(
                {
                    "modality": attr,
                    "n_tracks": int(len(df)) if hasattr(df, "__len__") else None,
                    "sample_ontology_terms": sample_terms,
                }
            )
        return self._ok({"modalities": modalities}, task="output_metadata")

    def _run_atlas_lookup_variant(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Look up precomputed AlphaGenome Atlas scores (incl. AVI_SCORE) for one SNV.

        Unlike score_variant/predict_interval, this queries a precomputed
        database rather than running the model live, so it has its own
        client (``alphagenome.atlas.atlas``) built lazily here.
        """
        try:
            from alphagenome.data import genome
        except ImportError:
            return self._err(
                "The 'alphagenome' package is required: pip install alphagenome."
            )

        atlas_client = self._make_atlas_client()
        if isinstance(atlas_client, dict):  # error dict from setup
            return atlas_client

        required = ["chromosome", "position", "reference_bases", "alternate_bases"]
        missing = [k for k in required if not args.get(k)]
        if missing:
            return self._err(f"Missing required parameter(s): {', '.join(missing)}")

        try:
            variant = genome.Variant(
                chromosome=str(args["chromosome"]),
                position=int(args["position"]),
                reference_bases=str(args["reference_bases"]),
                alternate_bases=str(args["alternate_bases"]),
            )
            scorers = [str(s).upper() for s in (args.get("scorers") or ["AVI_SCORE"])]
            results = atlas_client.query_variant(
                variant=variant, requested_scorers=scorers
            )
            top_n = self._parse_top_n(args)
            variant_label = (
                f"{variant.chromosome}:{variant.position}"
                f"{variant.reference_bases}>{variant.alternate_bases}"
            )
            scores_by_scorer = {
                name: self._summarize_scores([adata], top_n)
                for name, adata in (results or {}).items()
            }
            return self._ok(
                {
                    "variant": variant_label,
                    "scorers": scorers,
                    "scores": scores_by_scorer,
                },
                task="atlas_lookup_variant",
            )
        except Exception as exc:  # never raise out of run()
            return self._err(
                f"AlphaGenome Atlas request failed: {type(exc).__name__}: {exc}"
            )

    _MAX_ATLAS_SCAN_WINDOW_BP = 10_000

    def _run_atlas_scan_interval(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Precomputed Atlas scores for every SNV in a region (a DB read, not
        a live model run, but capped in width so the result stays reasonably
        sized -- a scorer with many tracks over 10kb would be n_variants x
        n_tracks rows, which is not useful to return as-is)."""
        try:
            from alphagenome.data import genome
        except ImportError:
            return self._err(
                "The 'alphagenome' package is required: pip install alphagenome."
            )

        atlas_client = self._make_atlas_client()
        if isinstance(atlas_client, dict):  # error dict from setup
            return atlas_client

        required = ["chromosome", "start", "end"]
        missing = [k for k in required if args.get(k) is None]
        if missing:
            return self._err(f"Missing required parameter(s): {', '.join(missing)}")

        try:
            interval = genome.Interval(
                chromosome=str(args["chromosome"]),
                start=int(args["start"]),
                end=int(args["end"]),
            )
            width = interval.end - interval.start
            if width > self._MAX_ATLAS_SCAN_WINDOW_BP:
                return self._err(
                    f"Scan window too wide ({width} bp): keep start/end within "
                    f"{self._MAX_ATLAS_SCAN_WINDOW_BP} bp per call."
                )

            scorers = [str(s).upper() for s in (args.get("scorers") or ["AVI_SCORE"])]
            results = atlas_client.query_interval(
                interval=interval, requested_scorers=scorers
            )
            top_n = self._parse_top_n(args)
            scores_by_scorer = {
                name: self._summarize_scores(
                    [adata], top_n, row_label_column="variant", row_label_key="variant"
                )
                for name, adata in (results or {}).items()
            }
            return self._ok(
                {
                    "interval": f"{interval.chromosome}:{interval.start}-{interval.end}",
                    "scorers": scorers,
                    "scores": scores_by_scorer,
                },
                task="atlas_scan_interval",
            )
        except Exception as exc:  # never raise out of run()
            return self._err(
                f"AlphaGenome Atlas request failed: {type(exc).__name__}: {exc}"
            )

    def _run_atlas_list_scorers(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Discovery: valid Atlas scorer names (what to pass as `scorers`)."""
        atlas_client = self._make_atlas_client()
        if isinstance(atlas_client, dict):  # error dict from setup
            return atlas_client
        try:
            meta = atlas_client.scorer_metadata()
            scorers = []
            for name, m in (meta or {}).items():
                track_metadata = getattr(m, "track_metadata", None)
                n_tracks = 0 if track_metadata is None else len(track_metadata)
                scorers.append(
                    {
                        "name": name,
                        "is_signed": bool(getattr(m, "is_signed", False)),
                        "n_tracks": int(n_tracks),
                    }
                )
            scorers.sort(key=lambda s: s["name"])
            return self._ok({"scorers": scorers}, task="atlas_list_scorers")
        except Exception as exc:  # never raise out of run()
            return self._err(
                f"AlphaGenome Atlas request failed: {type(exc).__name__}: {exc}"
            )

    # ------------------------------------------------------------- formatting
    @staticmethod
    def _summarize_scores(
        scores,
        top_n: int,
        row_label_column: str = "gene_name",
        row_label_key: str = "gene",
    ) -> List[Dict[str, Any]]:
        """Flatten AnnData score objects (rows x tracks) to top |score| entries.

        ``adata.X`` is a (n_rows, n_tracks) matrix -- not a single flat row --
        and ``var_names`` is just a numeric row index ("0", "1", ...); the
        human-readable track label lives in ``adata.var["name"]`` (verified
        against the live API: AlphaGenome's per-gene RNA_SEQ scoring returns
        one row per nearby gene). ``row_label_column``/``row_label_key`` let
        callers with a different per-row identity (e.g. Atlas's
        ``query_interval``, whose obs column is "variant" rather than
        "gene_name") reuse this same flattening logic.
        """
        rows: List[Dict[str, Any]] = []
        for adata in scores or []:
            values = adata.X
            if hasattr(values, "shape") and len(getattr(values, "shape", ())) == 2:
                matrix = values
            else:
                matrix = [list(values)]

            var = getattr(adata, "var", None)
            if var is not None and "name" in getattr(var, "columns", []):
                track_names = list(var["name"])
            else:
                track_names = list(getattr(adata, "var_names", []))

            obs = getattr(adata, "obs", None)
            row_labels = None
            if obs is not None and row_label_column in getattr(obs, "columns", []):
                row_labels = list(obs[row_label_column])

            for gi, row_values in enumerate(matrix):
                label = row_labels[gi] if row_labels and gi < len(row_labels) else None
                for track_name, val in zip(track_names, row_values):
                    entry = {"track": str(track_name), "score": float(val)}
                    if label is not None:
                        # str() covers non-string labels too, e.g. Atlas's
                        # obs["variant"] holds real Variant objects, not
                        # strings (found live) -- would break JSON output.
                        entry[row_label_key] = str(label)
                    rows.append(entry)
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
            "splice_site_usage",
            "splice_junctions",
            "contact_maps",
            "procap",
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
