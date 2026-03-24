"""
MaveDB Tool - Multiplexed Assay of Variant Effect Database

MaveDB stores and distributes results from Multiplexed Assays of Variant Effect
(MAVEs), including deep mutational scanning experiments. Score sets contain
functional impact scores for thousands of variants in a single protein/gene.

API: https://api.mavedb.org/api/v1/
Reference: Esposito et al. (2019) Genome Research
"""

import csv
import io

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

MAVEDB_API = "https://api.mavedb.org/api/v1"


@register_tool("MaveDBTool")
class MaveDBTool(BaseTool):
    """Search MaveDB for variant effect score sets and retrieve details."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search MaveDB score sets by text query."""
        query = params.get("query", "")
        limit = params.get("limit", 20)
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        resp = self.session.post(
            f"{MAVEDB_API}/score-sets/search",
            json={"text": query},
            timeout=30,
        )
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB search failed: HTTP {resp.status_code}",
            }

        data = resp.json()
        score_sets = data.get("scoreSets", [])[:limit]
        results = []
        for ss in score_sets:
            results.append(
                {
                    "urn": ss.get("urn"),
                    "title": ss.get("title"),
                    "short_description": ss.get("shortDescription"),
                    "num_variants": ss.get("numVariants"),
                    "published_date": ss.get("publishedDate"),
                }
            )
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": len(score_sets),
                "query": query,
            },
        }

    def _get_score_set(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific score set by URN."""
        urn = params.get("urn", "")
        if not urn:
            return {"status": "error", "error": "urn parameter is required"}

        resp = self.session.get(f"{MAVEDB_API}/score-sets/{urn}", timeout=30)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Score set '{urn}' not found in MaveDB",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB request failed: HTTP {resp.status_code}",
            }

        d = resp.json()
        target_genes = []
        for tg in d.get("targetGenes") or []:
            gene_info = {
                "name": tg.get("name"),
                "category": tg.get("category"),
            }
            ref = tg.get("targetSequence") or {}
            gene_info["uniprot_id"] = (
                ref.get("uniprot", {}).get("identifier") if ref.get("uniprot") else None
            )
            target_genes.append(gene_info)

        result = {
            "urn": d.get("urn"),
            "title": d.get("title"),
            "short_description": d.get("shortDescription"),
            "abstract": d.get("abstractText"),
            "method": d.get("methodText"),
            "num_variants": d.get("numVariants"),
            "published_date": d.get("publishedDate"),
            "license": (
                d.get("license", {}).get("shortName") if d.get("license") else None
            ),
            "target_genes": target_genes,
            "doi_identifiers": [
                doi.get("identifier") for doi in d.get("doiIdentifiers") or []
            ],
            "primary_publications": [
                pub.get("identifier")
                for pub in d.get("primaryPublicationIdentifiers") or []
            ],
        }
        return {
            "status": "success",
            "data": result,
            "metadata": {"urn": urn},
        }

    def _get_variant_scores(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get variant functional scores from a score set (CSV endpoint)."""
        urn = params.get("urn", "")
        if not urn:
            return {"status": "error", "error": "urn parameter is required"}

        hgvs_filter = (params.get("hgvs_pro") or "").strip()
        limit = min(int(params.get("limit", 50)), 500)

        try:
            resp = self.session.get(
                f"{MAVEDB_API}/score-sets/{urn}/scores",
                timeout=60,
                headers={"Accept": "text/csv"},
            )
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MaveDB API error: {e}"}

        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Score set '{urn}' not found in MaveDB",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB request failed: HTTP {resp.status_code}",
            }

        csv_text = resp.text
        if not csv_text.strip():
            return {
                "status": "error",
                "error": f"No scores available for '{urn}'",
            }

        reader = csv.DictReader(io.StringIO(csv_text))
        variants = []
        total_parsed = 0
        for row in reader:
            total_parsed += 1
            if hgvs_filter:
                hgvs_pro_val = row.get("hgvs_pro") or ""
                if hgvs_filter.lower() not in hgvs_pro_val.lower():
                    continue

            variant = {
                "hgvs_nt": row.get("hgvs_nt") or None,
                "hgvs_splice": row.get("hgvs_splice") or None,
                "hgvs_pro": row.get("hgvs_pro") or None,
            }
            for key, value in row.items():
                if key in ("accession", "hgvs_nt", "hgvs_splice", "hgvs_pro"):
                    continue
                if value and value != "NA":
                    try:
                        variant[key] = float(value)
                    except ValueError:
                        variant[key] = value

            variants.append(variant)
            if len(variants) >= limit:
                break

        return {
            "status": "success",
            "data": {
                "urn": urn,
                "total_variants_in_set": (
                    total_parsed
                    if len(variants) < limit
                    else f">{total_parsed} (truncated at {limit})"
                ),
                "returned": len(variants),
                "hgvs_filter": hgvs_filter or None,
                "variants": variants,
            },
        }

    def _search_experiments(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search MaveDB experiments by text query."""
        query = params.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            resp = self.session.post(
                f"{MAVEDB_API}/experiments/search",
                json={"text": query},
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MaveDB API error: {e}"}

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB search failed: HTTP {resp.status_code}",
            }

        raw = resp.json()
        if not isinstance(raw, list):
            raw = [raw] if raw else []

        experiments = []
        for exp in raw:
            urn = exp.get("urn", "")
            if urn.startswith("tmp:"):
                continue

            pubs = [
                {
                    "identifier": pub.get("identifier"),
                    "db_name": pub.get("dbName"),
                    "title": pub.get("title"),
                }
                for pub in exp.get("primaryPublicationIdentifiers") or []
            ]
            score_set_urns = exp.get("scoreSetUrns") or []
            experiments.append(
                {
                    "urn": urn,
                    "title": exp.get("title"),
                    "short_description": exp.get("shortDescription"),
                    "published_date": exp.get("publishedDate"),
                    "score_set_urns": score_set_urns,
                    "num_score_sets": len(score_set_urns),
                    "publications": pubs,
                }
            )

        return {
            "status": "success",
            "data": {
                "query": query,
                "total_experiments": len(experiments),
                "experiments": experiments,
            },
        }

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        operation = self.tool_config.get("fields", {}).get("operation", "")
        dispatch = {
            "search": self._search,
            "get_score_set": self._get_score_set,
            "get_variant_scores": self._get_variant_scores,
            "search_experiments": self._search_experiments,
        }
        handler = dispatch.get(operation)
        if handler:
            return handler(params)
        return {"status": "error", "error": f"Unknown operation: {operation}"}
