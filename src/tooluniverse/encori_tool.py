"""ENCORI / starBase RNA-interactome tools for ToolUniverse.

ENCORI (the Encyclopedia of RNA Interactomes, formerly starBase) aggregates
CLIP-seq-supported and computationally predicted RNA interactions and exposes
them through a public REST API (no authentication). The single registered
class ``ENCORITool`` serves several distinct ENCORI REST modules:

* ``miRNATarget/``   -> miRNA-target interactions (the original tool)
* ``RBPTarget/``     -> RBP-RNA binding sites from CLIP-seq
* ``ceRNA/``         -> competing-endogenous-RNA (miRNA-sponge) networks
* ``RNARNA/``        -> RNA-RNA duplex interactions (PARIS/LIGR/SPLASH)
* ``degradomeRNA/``  -> miRNA cleavage sites validated by degradome-seq
* ``RBPDisease/``    -> RBP binding correlated with somatic (COSMIC) mutations
* ``RBPMotifScan/``  -> RBP binding-motif enrichment scan

Which module a tool calls is selected purely from its JSON config via
``fields.encori_endpoint``; tools that omit it fall back to the historical
miRNA-target behaviour. This lets all ENCORI tools reuse the one registered
class with no extra registration.

API: https://rnasysu.com/encori/api/  (public, no authentication)
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

ENCORI_BASE = "https://rnasysu.com/encori/api/"
ENCORI_URL = ENCORI_BASE + "miRNATarget/"
# Columns flagged 1 when that prediction program supports the interaction.
_PROGRAMS = ["PITA", "RNA22", "miRmap", "microT", "miRanda", "PicTar", "TargetScan"]


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_num(value: Any) -> Any:
    """Best-effort numeric coercion: int -> float -> original string."""
    if value is None or value == "" or value == "NA":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


@register_tool("ENCORITool")
class ENCORITool(BaseTool):
    """ENCORI / starBase RNA-interactome lookups (config-selected module)."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields") or {}
        # Which ENCORI REST module this tool instance targets. When unset, the
        # tool keeps its original miRNA-target behaviour.
        self.encori_endpoint = fields.get("encori_endpoint")

    # ------------------------------------------------------------------
    # Shared HTTP + TSV parsing
    # ------------------------------------------------------------------
    def _fetch_tsv(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """GET an ENCORI module and return parsed {header, rows} or an error dict.

        ENCORI returns tab-separated text: comment lines start with '#', then a
        header line, then data rows. On a bad parameter the body is a single
        plain-language line (e.g. 'The "RNA" parameter haven't been set
        correctly!') instead of tabular data, so detect that explicitly.
        """
        url = ENCORI_BASE + endpoint
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
        except requests.exceptions.Timeout:
            return {"error": f"ENCORI API timed out after {self.timeout}s"}
        except requests.exceptions.RequestException as e:
            return {"error": f"ENCORI API request failed: {e}"}

        if resp.status_code != 200:
            return {"error": f"ENCORI API returned HTTP {resp.status_code}"}

        lines = [ln for ln in resp.text.splitlines() if ln and not ln.startswith("#")]
        if not lines:
            return {"error": "ENCORI API returned an empty response."}

        header = lines[0].split("\t")
        # A single non-tabular line is ENCORI's way of reporting a bad request.
        if len(header) < 2:
            return {
                "error": "ENCORI rejected the query: " + lines[0].strip(),
            }

        return {"header": header, "lines": lines}

    @staticmethod
    def _row_dicts(parsed: Dict[str, Any]) -> List[Dict[str, str]]:
        header = parsed["header"]
        out: List[Dict[str, str]] = []
        for ln in parsed["lines"][1:]:
            f = ln.split("\t")
            if len(f) < len(header):
                continue
            out.append(dict(zip(header, f)))
        return out

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        dispatch = {
            "RBPTarget/": self._run_rbp_target,
            "ceRNA/": self._run_cerna,
            "RNARNA/": self._run_rna_rna,
            "degradomeRNA/": self._run_degradome,
            "RBPDisease/": self._run_rbp_disease,
            "RBPMotifScan/": self._run_motif_scan,
        }
        handler = dispatch.get(self.encori_endpoint)
        if handler is not None:
            return handler(arguments)
        return self._run_mirna_target(arguments)

    # ------------------------------------------------------------------
    # 1. miRNA -> target / gene -> miRNA  (original behaviour)
    # ------------------------------------------------------------------
    def _run_mirna_target(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        mirna = (arguments.get("mirna") or "").strip()
        gene = (arguments.get("gene") or arguments.get("gene_symbol") or "").strip()
        if not mirna and not gene:
            return {
                "status": "error",
                "error": "Provide 'mirna' (e.g. 'hsa-miR-21-5p') to get its targets, "
                "or 'gene' (e.g. 'TP53') to get the miRNAs that target it.",
            }

        clip_min = _to_int(arguments.get("clip_min", 1), 1)
        program_min = _to_int(arguments.get("program_min", 1), 1)
        limit = max(1, min(_to_int(arguments.get("limit", 50), 50), 500))

        params = {
            "assembly": arguments.get("assembly", "hg38"),
            "geneType": "mRNA",
            "miRNA": mirna or "all",
            "target": gene or "all",
            "clipExpNum": clip_min,
            "degraExpNum": 0,
            "pancancerNum": 0,
            "programNum": program_min,
            "program": "None",
            "cellType": "all",
        }

        parsed = self._fetch_tsv("miRNATarget/", params)
        if "error" in parsed:
            return {"status": "error", "error": parsed["error"]}

        idx = {h: i for i, h in enumerate(parsed["header"])}
        rows = []
        for ln in parsed["lines"][1:]:
            f = ln.split("\t")
            if len(f) < len(parsed["header"]):
                continue
            programs = [p for p in _PROGRAMS if p in idx and f[idx[p]] == "1"]
            rows.append(
                {
                    "mirna": f[idx["miRNAname"]],
                    "gene": f[idx["geneName"]],
                    "gene_id": f[idx["geneID"]],
                    "clip_experiments": _to_int(f[idx["clipExpNum"]], 0),
                    "predicted_by": programs,
                    "n_programs": len(programs),
                    "pan_cancer_num": _to_int(f[idx["pancancerNum"]], 0)
                    if "pancancerNum" in idx
                    else None,
                }
            )

        rows.sort(key=lambda r: (r["clip_experiments"], r["n_programs"]), reverse=True)
        return {
            "status": "success",
            "data": rows[:limit],
            "metadata": {
                "source": "ENCORI (starBase)",
                "query": mirna or gene,
                "direction": "miRNA->targets" if mirna else "gene->miRNAs",
                "total": len(rows),
                "returned": min(len(rows), limit),
                "interpretation": (
                    "clip_experiments = number of CLIP-seq experiments supporting the "
                    "site (experimental evidence; higher = stronger). predicted_by lists "
                    "the algorithms predicting it. CLIP-supported targets outrank "
                    "prediction-only ones."
                ),
            },
        }

    # ------------------------------------------------------------------
    # 2. RBP -> RNA targets / gene -> RBPs  (RBPTarget/)
    # ------------------------------------------------------------------
    def _run_rbp_target(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rbp = (arguments.get("rbp") or arguments.get("RBP") or "").strip()
        gene = (arguments.get("gene") or arguments.get("gene_symbol") or "").strip()
        if not rbp and not gene:
            return {
                "status": "error",
                "error": "Provide 'rbp' (e.g. 'PTBP1') to get the RNAs it binds, "
                "or 'gene' (e.g. 'TP53') to get the RBPs that bind it.",
            }

        clip_min = _to_int(arguments.get("clip_min", 1), 1)
        limit = max(1, min(_to_int(arguments.get("limit", 100), 100), 500))

        params = {
            "assembly": arguments.get("assembly", "hg38"),
            "geneType": arguments.get("gene_type") or "mRNA",
            "RBP": rbp or "all",
            "target": gene or "all",
            "clipExpNum": clip_min,
            "pancancerNum": _to_int(arguments.get("pancancer_min", 0), 0),
            "cellType": arguments.get("cell_type") or "all",
        }

        parsed = self._fetch_tsv("RBPTarget/", params)
        if "error" in parsed:
            return {"status": "error", "error": parsed["error"]}

        rows = []
        for d in self._row_dicts(parsed):
            rows.append(
                {
                    "rbp": d.get("RBP"),
                    "gene": d.get("geneName"),
                    "gene_id": d.get("geneID"),
                    "gene_type": d.get("geneType"),
                    "cluster_num": _to_int(d.get("clusterNum"), 0),
                    "total_clip_experiments": _to_int(d.get("totalClipExpNum"), 0),
                    "total_clip_sites": _to_int(d.get("totalClipSiteNum"), 0),
                    "clip_experiments": _to_int(d.get("clipExpNum"), 0),
                    "chromosome": d.get("chromosome"),
                    "strand": d.get("strand"),
                    "narrow_start": _to_num(d.get("narrowStart")),
                    "narrow_end": _to_num(d.get("narrowEnd")),
                    "pancancer_num": _to_int(d.get("pancancerNum"), 0),
                    "cell_tissue": d.get("cellline/tissue"),
                }
            )

        rows.sort(
            key=lambda r: (r["total_clip_experiments"], r["total_clip_sites"]),
            reverse=True,
        )
        return {
            "status": "success",
            "data": rows[:limit],
            "metadata": {
                "source": "ENCORI (starBase) RBPTarget",
                "query": rbp or gene,
                "direction": "RBP->targets" if rbp else "gene->RBPs",
                "total": len(rows),
                "returned": min(len(rows), limit),
                "interpretation": (
                    "Each row is a CLIP-seq-supported binding cluster. "
                    "total_clip_experiments / total_clip_sites quantify how many "
                    "experiments and sites support the RBP-RNA binding."
                ),
            },
        }

    # ------------------------------------------------------------------
    # 3. ceRNA / miRNA-sponge network  (ceRNA/)
    # ------------------------------------------------------------------
    def _run_cerna(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene = (
            arguments.get("gene")
            or arguments.get("ceRNA")
            or arguments.get("gene_symbol")
            or ""
        ).strip()
        if not gene:
            return {
                "status": "error",
                "error": "Provide 'gene' (e.g. 'PTEN') to get its ceRNA / miRNA-sponge partners.",
            }

        limit = max(1, min(_to_int(arguments.get("limit", 100), 100), 500))

        params = {
            "assembly": arguments.get("assembly", "hg38"),
            "geneType": arguments.get("gene_type") or "mRNA",
            "ceRNA": gene,
            "miRNAnum": _to_int(arguments.get("shared_mirna_min", 5), 5),
            "pval": arguments.get("pval", 0.01),
            "fdr": arguments.get("fdr", 0.01),
        }

        parsed = self._fetch_tsv("ceRNA/", params)
        if "error" in parsed:
            return {"status": "error", "error": parsed["error"]}

        rows = []
        for d in self._row_dicts(parsed):
            rows.append(
                {
                    "gene": d.get("geneName"),
                    "gene_id": d.get("geneID"),
                    "partner": d.get("ceRNAname"),
                    "partner_id": d.get("ceRNAid"),
                    "partner_gene_type": d.get("ceRNAgeneType"),
                    "shared_mirna_families": _to_int(d.get("hitMiRNAFamilyNum"), 0),
                    "pval": _to_num(d.get("pval")),
                    "fdr": _to_num(d.get("fdr")),
                }
            )

        rows.sort(key=lambda r: r["shared_mirna_families"], reverse=True)
        return {
            "status": "success",
            "data": rows[:limit],
            "metadata": {
                "source": "ENCORI (starBase) ceRNA",
                "query": gene,
                "total": len(rows),
                "returned": min(len(rows), limit),
                "interpretation": (
                    "Each partner shares miRNA-binding families with the query gene, "
                    "making it a candidate competing-endogenous RNA (miRNA sponge). "
                    "shared_mirna_families = number of shared miRNA families; lower "
                    "pval/fdr = stronger ceRNA evidence."
                ),
            },
        }

    # ------------------------------------------------------------------
    # 4. RNA-RNA duplex interactions  (RNARNA/)
    # ------------------------------------------------------------------
    def _run_rna_rna(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rna = (
            arguments.get("rna") or arguments.get("RNA") or arguments.get("gene") or ""
        ).strip()
        if not rna:
            return {
                "status": "error",
                "error": "Provide 'rna' (e.g. 'MALAT1') to get its RNA-RNA duplex partners.",
            }

        limit = max(1, min(_to_int(arguments.get("limit", 100), 100), 500))

        params = {
            "assembly": arguments.get("assembly", "hg38"),
            # MALAT1 etc. are lncRNAs, so default geneType to lncRNA; ENCORI
            # silently returns an error body if geneType != the RNA's biotype.
            "geneType": arguments.get("gene_type") or "lncRNA",
            "RNA": rna,
            "interNum": _to_int(arguments.get("interaction_min", 1), 1),
            "expNum": _to_int(arguments.get("exp_min", 1), 1),
            "cellType": arguments.get("cell_type") or "all",
        }

        parsed = self._fetch_tsv("RNARNA/", params)
        if "error" in parsed:
            return {"status": "error", "error": parsed["error"]}

        rows = []
        for d in self._row_dicts(parsed):
            rows.append(
                {
                    "rna": d.get("geneName"),
                    "rna_id": d.get("geneID"),
                    "rna_type": d.get("geneType"),
                    "partner": d.get("pairGeneName"),
                    "partner_id": d.get("pairGeneID"),
                    "partner_type": d.get("pairGeneType"),
                    "interaction_num": _to_int(d.get("interactionNum"), 0),
                    "total_experiments": _to_int(d.get("totalExpNum"), 0),
                    "total_reads": _to_int(d.get("totalReadsNum"), 0),
                    "free_energy": _to_num(d.get("FreeEnergy")),
                    "align_score": _to_num(d.get("AlignScore(Smith-Waterman)")),
                    "cell_tissue": d.get("CellLine/Tissue"),
                }
            )

        rows.sort(
            key=lambda r: (r["total_experiments"], r["total_reads"]), reverse=True
        )
        return {
            "status": "success",
            "data": rows[:limit],
            "metadata": {
                "source": "ENCORI (starBase) RNARNA",
                "query": rna,
                "total": len(rows),
                "returned": min(len(rows), limit),
                "interpretation": (
                    "Each partner forms a base-pairing duplex with the query RNA, "
                    "detected by crosslinking (PARIS/LIGR/SPLASH). total_experiments / "
                    "total_reads quantify support; free_energy is the predicted "
                    "hybridisation energy (more negative = more stable)."
                ),
            },
        }

    # ------------------------------------------------------------------
    # 5. Degradome-seq miRNA cleavage  (degradomeRNA/)
    # ------------------------------------------------------------------
    def _run_degradome(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        mirna = (arguments.get("mirna") or "").strip()
        gene = (arguments.get("gene") or arguments.get("gene_symbol") or "").strip()
        if not mirna and not gene:
            return {
                "status": "error",
                "error": "Provide 'gene' (e.g. 'TP53') to get degradome-validated miRNA "
                "cleavage of it, or 'mirna' for a specific miRNA's cleavage targets.",
            }

        limit = max(1, min(_to_int(arguments.get("limit", 100), 100), 500))

        params = {
            # hg38 degradome data is not built; hg19 is the supported assembly.
            "assembly": arguments.get("assembly", "hg19"),
            "geneType": arguments.get("gene_type") or "mRNA",
            "miRNA": mirna or "all",
            "target": gene or "all",
            "degraExpNum": _to_int(arguments.get("degradome_exp_min", 1), 1),
            "clipExpNum": _to_int(arguments.get("clip_min", 1), 1),
            "cellType": arguments.get("cell_type") or "all",
        }

        parsed = self._fetch_tsv("degradomeRNA/", params)
        if "error" in parsed:
            return {"status": "error", "error": parsed["error"]}

        rows = []
        for d in self._row_dicts(parsed):
            rows.append(
                {
                    "mirna": d.get("miRNAname"),
                    "mirna_id": d.get("miRNAid"),
                    "gene": d.get("geneName"),
                    "gene_type": d.get("geneType"),
                    "cleave_event_num": _to_int(d.get("cleaveEventNum"), 0),
                    "degradome_experiments": _to_int(d.get("degraExpNum"), 0),
                    "degradome_sites": _to_int(d.get("degraSiteNum"), 0),
                    "total_reads": _to_int(d.get("totalReads"), 0),
                    "category": d.get("category"),
                }
            )

        rows.sort(
            key=lambda r: (r["degradome_experiments"], r["cleave_event_num"]),
            reverse=True,
        )
        return {
            "status": "success",
            "data": rows[:limit],
            "metadata": {
                "source": "ENCORI (starBase) degradomeRNA",
                "query": mirna or gene,
                "assembly": params["assembly"],
                "total": len(rows),
                "returned": min(len(rows), limit),
                "interpretation": (
                    "Each row is a degradome-seq (PARE)-validated slicer cleavage of "
                    "the target by the miRNA. cleave_event_num / degradome_experiments "
                    "quantify support; category (I-IV) ranks cleavage-signal confidence "
                    "(I strongest). hg19 is the only assembly with degradome data."
                ),
            },
        }

    # ------------------------------------------------------------------
    # 6. RBP-disease (COSMIC) associations  (RBPDisease/)
    # ------------------------------------------------------------------
    def _run_rbp_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rbp = (arguments.get("rbp") or arguments.get("RBP") or "").strip()
        gene = (arguments.get("gene") or arguments.get("gene_symbol") or "").strip()
        tissue = (arguments.get("tissue") or "").strip()
        disease = (arguments.get("disease") or "").strip()
        if not rbp and not gene and not tissue and not disease:
            return {
                "status": "error",
                "error": "Provide at least one of 'gene' (target, e.g. 'MYC'), 'rbp', "
                "'tissue' (e.g. 'breast'), or 'disease' (e.g. 'carcinoma').",
            }

        limit = max(1, min(_to_int(arguments.get("limit", 100), 100), 500))

        params = {
            "assembly": arguments.get("assembly", "hg38"),
            "RBP": rbp or "all",
            "target": gene or "all",
            "tissue": tissue or "all",
            "disease": disease or "all",
        }

        parsed = self._fetch_tsv("RBPDisease/", params)
        if "error" in parsed:
            return {"status": "error", "error": parsed["error"]}

        rows = []
        for d in self._row_dicts(parsed):
            rows.append(
                {
                    "rbp": d.get("RBP"),
                    "gene": d.get("geneName"),
                    "gene_id": d.get("geneID"),
                    "tissue": d.get("tissue"),
                    "disease_num": _to_int(d.get("diseaseNum"), 0),
                    "diseases": d.get("diseases"),
                    "disease_cosmic_id": d.get("diseaseCosmicID"),
                    "cosmic_num": _to_int(d.get("cosmicNum"), 0),
                    "sample_num": _to_int(d.get("sampleNum"), 0),
                    "mut_type_num": _to_int(d.get("mutTypeNum"), 0),
                    "clip_experiments": _to_int(d.get("clipExpNum"), 0),
                    "clip_sites": _to_int(d.get("clipSiteNum"), 0),
                }
            )

        rows.sort(key=lambda r: (r["cosmic_num"], r["sample_num"]), reverse=True)
        return {
            "status": "success",
            "data": rows[:limit],
            "metadata": {
                "source": "ENCORI (starBase) RBPDisease",
                "query": gene or rbp or disease or tissue,
                "total": len(rows),
                "returned": min(len(rows), limit),
                "interpretation": (
                    "Each row links an RBP binding site on a gene to somatic (COSMIC) "
                    "mutations in a tissue/disease. cosmic_num / sample_num quantify the "
                    "mutational burden overlapping the binding site."
                ),
            },
        }

    # ------------------------------------------------------------------
    # 7. RBP binding-motif enrichment scan  (RBPMotifScan/)
    # ------------------------------------------------------------------
    def _run_motif_scan(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        motif = (arguments.get("motif") or "").strip()
        rbp = (arguments.get("rbp") or arguments.get("RBP") or "").strip()
        if not motif and not rbp:
            return {
                "status": "error",
                "error": "Provide 'motif' (e.g. 'UGCAUG') to find RBPs/datasets whose "
                "CLIP peaks are enriched for it, or 'rbp' to list that RBP's motifs.",
            }

        rank_limit = max(1, min(_to_int(arguments.get("rank_limit", 10), 10), 100))
        limit = max(1, min(_to_int(arguments.get("limit", 100), 100), 500))

        params: Dict[str, Any] = {
            "assembly": arguments.get("assembly", "hg38"),
            "length": arguments.get("length") or "short",
            "rankLimit": rank_limit,
        }
        if motif:
            params["motif"] = motif
        if rbp:
            params["RBP"] = rbp

        parsed = self._fetch_tsv("RBPMotifScan/", params)
        if "error" in parsed:
            return {"status": "error", "error": parsed["error"]}

        rows = []
        for d in self._row_dicts(parsed):
            rows.append(
                {
                    "rbp": d.get("RBP"),
                    "dataset_id": d.get("DatasetID"),
                    "motif_rank": _to_int(d.get("MotifRank"), 0),
                    "identified_motif": d.get("IdentifiedMotif"),
                    "query_motif": d.get("QueryMotif"),
                    "target_peak_num": _to_int(d.get("targetPeakNum"), 0),
                    "target_percentage": _to_num(d.get("TargetPercentage(%)")),
                    "pvalue": _to_num(d.get("p-value")),
                    "pvalue_ln": _to_num(d.get("p-value(ln)")),
                    "motif_matrix": d.get("MotifMatrix"),
                    "region": d.get("Region"),
                    "cell_tissue": d.get("CellLine/Tissue"),
                    "main_accession": d.get("MainAccession"),
                }
            )

        rows.sort(key=lambda r: r["target_peak_num"], reverse=True)
        return {
            "status": "success",
            "data": rows[:limit],
            "metadata": {
                "source": "ENCORI (starBase) RBPMotifScan",
                "query": motif or rbp,
                "total": len(rows),
                "returned": min(len(rows), limit),
                "interpretation": (
                    "Each row is a sequence motif enriched in an RBP's CLIP peaks. "
                    "target_peak_num = number of peaks containing the motif; lower "
                    "pvalue = stronger enrichment. motif_matrix links to the HOMER "
                    "position-weight matrix."
                ),
            },
        }
