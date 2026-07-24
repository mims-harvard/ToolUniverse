"""ProtVar API tools for contextualising human missense variants.

ProtVar (EBI) maps protein variants to genomic coordinates and provides
functional annotations, population frequencies, pathogenicity predictions
(AlphaMissense, EVE, ESM, SIFT, PolyPhen), and structural context.
"""

import json
import re
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tooluniverse.tool_registry import register_tool

_BASE = "https://www.ebi.ac.uk/ProtVar/api"


def _get_json(url: str, timeout: int = 30) -> Any:
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


@register_tool(
    "ProtVarTool",
    config={
        "name": "ProtVar_map_variant",
        "type": "ProtVarTool",
        "description": (
            "Map a human protein variant to genomic coordinates and get "
            "pathogenicity predictions (AlphaMissense, EVE, ESM, conservation). "
            "Accepted input formats: (1) protein variant 'ACCESSION CHANGE' e.g. "
            "'P04637 R175H'; (2) dbSNP rsID e.g. 'rs1799966'; "
            "(3) VCF-style genomic 'chr17 43057065 . T G'. "
            "Returns isoform mappings, consequence type, and variant effect scores."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "variant": {
                    "type": "string",
                    "description": (
                        "Variant identifier. Supported formats: "
                        "(1) Protein: 'UniProtAccession SingleLetterChange' e.g. 'P04637 R175H'; "
                        "(2) rsID: 'rs1799966'; "
                        "(3) VCF genomic: 'chr17 43057065 . REF ALT'. "
                        "Note: colon-separated 'chr:pos:ref:alt' format is NOT supported; "
                        "use space-separated VCF format instead."
                    ),
                },
                "assembly": {
                    "type": "string",
                    "description": "Genome assembly for genomic inputs/outputs: 'GRCh38' (default) or 'GRCh37'.",
                },
            },
            "required": ["variant"],
        },
        "test_examples": [{"variant": "P04637 R175H"}],
        "settings": {"base_url": _BASE, "timeout": 30},
    },
)
class ProtVarMapTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    @staticmethod
    def _normalize_variant(variant: str) -> str:
        """Convert colon-separated genomic 'chr:pos:ref:alt' to VCF 'chr pos . ref alt'."""

        if re.match(r"^chr\w+:\d+:[ACGT]+:[ACGT]+$", variant, re.IGNORECASE):
            parts = variant.split(":")
            if len(parts) == 4:
                return f"{parts[0]} {parts[1]} . {parts[2]} {parts[3]}"
        return variant

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        variant = arguments.get("variant", "").strip()
        if not variant:
            return {"status": "error", "error": "variant is required"}

        variant = self._normalize_variant(variant)
        assembly = arguments.get("assembly") or "GRCh38"

        base = self.tool_config.get("settings", {}).get("base_url", _BASE)
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))
        # ProtVar 2.x: GET /mapping?q=<input>&assembly=<GRCh38|GRCh37>. (The old
        # batch POST /mappings endpoint was removed when the API was restructured.)
        url = f"{base}/mapping?" + urlencode({"q": variant, "assembly": assembly})

        try:
            result = _get_json(url, timeout=timeout)
        except Exception as e:
            return {"status": "error", "error": f"ProtVar API error: {e}"}

        content = result.get("content") if isinstance(result, dict) else None
        inputs = content.get("inputs", []) if isinstance(content, dict) else []
        if not inputs:
            return {"status": "error", "error": f"No mapping found for '{variant}'"}

        # Surface any parser messages (e.g. unrecognised variant format).
        messages = [m for inp in inputs for m in (inp.get("messages") or [])]

        def _extract_isoform(iso, gene):
            entry = {
                "accession": iso.get("accession"),
                "canonical": iso.get("canonical"),
                "gene": gene.get("geneName"),
                "ensg": gene.get("ensg"),
                "consequence": iso.get("consequences"),
                "ref_aa": iso.get("refAA"),
                "alt_aa": iso.get("variantAA"),
                "position": iso.get("isoformPosition"),
                "codon_change": iso.get("codonChange"),
                "protein_name": iso.get("proteinName"),
                "cadd_score": gene.get("caddScore"),
            }
            am = iso.get("amScore")
            if am:
                entry["alphamissense"] = {
                    "score": am.get("amPathogenicity"),
                    "class": am.get("amClass"),
                }
            # ProtVar 2.x merges EVE/ESM-1v into a single popEveScore object.
            pev = iso.get("popEveScore")
            if pev:
                entry["eve_score"] = pev.get("eve")
                entry["esm1v_score"] = pev.get("esm1v")
                entry["popeve_score"] = pev.get("popeve")
            return entry

        mappings = []
        genomic: Dict[str, Any] = {}
        for inp in inputs:
            for gv in inp.get("derivedGenomicVariants", []):
                if not genomic:
                    genomic = {
                        "chr": gv.get("chromosome"),
                        "pos": gv.get("position"),
                        "ref": gv.get("refBase"),
                        "alt": gv.get("altBase"),
                    }
                for gene in gv.get("genes", []):
                    for iso in gene.get("isoforms", []):
                        mappings.append(_extract_isoform(iso, gene))

        if not mappings and not genomic:
            return {
                "status": "error",
                "error": f"No mapping found for '{variant}'"
                + (f": {messages[0]}" if messages else ""),
            }

        return {
            "status": "success",
            "data": {
                "input": variant,
                "assembly": assembly,
                "genomic_coordinates": genomic,
                "isoform_mappings": mappings,
                "messages": messages,
            },
        }


@register_tool(
    "ProtVarFunctionTool",
    config={
        "name": "ProtVar_get_function",
        "type": "ProtVarFunctionTool",
        "description": (
            "Get functional annotations for a protein position from ProtVar. "
            "Returns UniProt features (domains, active sites, PTMs), protein "
            "function description, and structural context at the queried position."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "accession": {
                    "type": "string",
                    "description": "UniProt accession (e.g. 'P04637' for TP53).",
                },
                "position": {
                    "type": "integer",
                    "description": "Amino acid position in the protein (1-based).",
                },
                "variant_aa": {
                    "type": "string",
                    "description": (
                        "Single-letter code for the variant amino acid "
                        "(e.g. 'H' for histidine). Optional but recommended."
                    ),
                },
            },
            "required": ["accession", "position"],
        },
        "settings": {"base_url": _BASE, "timeout": 30},
    },
)
class ProtVarFunctionTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        acc = arguments.get("accession", "").strip()
        pos = arguments.get("position")
        if not acc or pos is None:
            return {"status": "error", "error": "accession and position are required"}

        base = self.tool_config.get("settings", {}).get("base_url", _BASE)
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        url = f"{base}/function/{acc}/{pos}"
        variant_aa = arguments.get("variant_aa", "").strip()
        if variant_aa:
            url += f"?variantAA={variant_aa}"

        try:
            result = _get_json(url, timeout=timeout)
        except Exception as e:
            return {"status": "error", "error": f"ProtVar API error: {e}"}

        if not isinstance(result, dict):
            return {
                "status": "error",
                "error": f"No ProtVar function annotation for {acc} position {pos}",
            }

        # Extract key information
        data = {
            "accession": result.get("accession"),
            "position": result.get("position"),
            "protein_name": result.get("name"),
            "gene_names": result.get("geneNames") or [],
            "protein_existence": result.get("proteinExistence"),
        }

        # Extract features at this position. Use `or []` throughout: the upstream
        # UniProt-derived payload may carry explicit null for an absent list,
        # which `.get(key, [])` would not catch (it returns the null).
        features = []
        for f in result.get("features") or []:
            features.append(
                {
                    "type": f.get("type"),
                    "category": f.get("category"),
                    "description": f.get("description"),
                    "begin": f.get("begin"),
                    "end": f.get("end"),
                }
            )
        data["features"] = features

        # Extract function comments
        comments = []
        for c in result.get("comments") or []:
            ctype = c.get("type")
            if ctype == "FUNCTION":
                for t in c.get("text") or []:
                    comments.append({"type": ctype, "value": t.get("value")})
            elif ctype == "CATALYTIC_ACTIVITY":
                rxn = c.get("reaction") or {}
                if rxn:
                    comments.append({"type": ctype, "value": rxn.get("name")})
            elif ctype in ("SUBCELLULAR_LOCATION", "DISEASE", "TISSUE_SPECIFICITY"):
                for t in c.get("text") or []:
                    comments.append({"type": ctype, "value": t.get("value")})
        data["comments"] = comments

        return {"status": "success", "data": data}


@register_tool(
    "ProtVarPopulationTool",
    config={
        "name": "ProtVar_get_population",
        "type": "ProtVarPopulationTool",
        "description": (
            "Get population observation data for a protein variant position from "
            "ProtVar. Returns co-located variants with population allele "
            "frequencies (gnomAD, 1000Genomes), clinical significance (ClinVar), "
            "and computational predictions (SIFT, PolyPhen)."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "accession": {
                    "type": "string",
                    "description": "UniProt accession (e.g. 'P22304' for IDS).",
                },
                "position": {
                    "type": "integer",
                    "description": "Amino acid position in the protein (1-based).",
                },
                "genomic_location": {
                    "type": "integer",
                    "description": (
                        "Genomic coordinate (GRCh38) for the variant. "
                        "Obtain from ProtVar_map_variant output."
                    ),
                },
            },
            "required": ["accession", "position", "genomic_location"],
        },
        "settings": {"base_url": _BASE, "timeout": 30},
    },
)
class ProtVarPopulationTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        acc = arguments.get("accession", "").strip()
        pos = arguments.get("position")
        gloc = arguments.get("genomic_location")
        if not acc or pos is None or gloc is None:
            return {
                "status": "error",
                "error": "accession, position, and genomic_location are required",
            }

        base = self.tool_config.get("settings", {}).get("base_url", _BASE)
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        url = f"{base}/population/{acc}/{pos}?genomicLocation={gloc}"

        try:
            result = _get_json(url, timeout=timeout)
        except Exception as e:
            return {"status": "error", "error": f"ProtVar API error: {e}"}

        # Parse co-located variants
        variants = []
        for key in ("proteinColocatedVariant", "genomicColocatedVariant"):
            items = result.get(key)
            if not items:
                continue
            if not isinstance(items, list):
                items = [items]
            for v in items:
                entry = {
                    "source": key.replace("ColocatedVariant", ""),
                    "wild_type": v.get("wildType"),
                    "alt_sequence": v.get("alternativeSequence"),
                    "genomic_location": v.get("genomicLocation"),
                    "cytogenetic_band": v.get("cytogeneticBand"),
                }
                # Population frequencies
                freqs = []
                for pf in v.get("populationFrequencies", []):
                    freqs.append(
                        {
                            "population": pf.get("populationName"),
                            "frequency": pf.get("frequency"),
                            "source": pf.get("source"),
                        }
                    )
                entry["frequencies"] = freqs
                # Predictions
                preds = []
                for p in v.get("predictions", []):
                    preds.append(
                        {
                            "algorithm": p.get("predAlgorithmNameType"),
                            "prediction": p.get("predictionValType"),
                            "score": p.get("score"),
                        }
                    )
                entry["predictions"] = preds
                # Cross-references (ClinVar etc)
                xrefs = []
                for x in v.get("xrefs", []):
                    xrefs.append(
                        {
                            "database": x.get("name"),
                            "id": x.get("id"),
                            "url": x.get("url"),
                        }
                    )
                entry["xrefs"] = xrefs
                variants.append(entry)

        return {
            "status": "success",
            "data": {
                "accession": acc,
                "position": pos,
                "genomic_location": gloc,
                "colocated_variants": variants,
            },
        }
