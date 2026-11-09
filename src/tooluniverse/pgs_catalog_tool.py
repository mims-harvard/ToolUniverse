"""
PGS Catalog tool for ToolUniverse.

The PGS Catalog (pgscatalog.org, hosted by EMBL-EBI) is the open database of
published polygenic scores (PGS) — for each score it records the trait, the
number of variants, the development method, the publication, the training and
evaluation sample ancestries, and links to the downloadable scoring file.

This tool lets an agent (a) find the trait id for a phenotype, (b) list the
polygenic scores published for that trait, and (c) retrieve the full metadata
for a specific score. It complements the polygenic-risk-score skill, which
previously had no way to query published scores.

API: https://www.pgscatalog.org/rest (public, no key).
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

PGS_API = "https://www.pgscatalog.org/rest"
PGS_SOURCE = "PGS Catalog (pgscatalog.org, EMBL-EBI)"


# Score ids per trait. MONDO_0005010 carries 88 and 8; the cap guards an
# outlier rather than cutting a normal trait.
PGS_IDS_PER_TRAIT = 500


def _metric(m: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one performance metric record (effect size / accuracy / other)."""
    return {
        "name_short": m.get("name_short"),
        "name_long": m.get("name_long"),
        "estimate": m.get("estimate"),
        "ci_lower": m.get("ci_lower"),
        "ci_upper": m.get("ci_upper"),
        "se": m.get("se"),
    }


def _performance_summary(p: Dict[str, Any]) -> Dict[str, Any]:
    """Trim a raw PGS performance record to the useful evaluation fields.

    Flattens the three metric groups the PGS Catalog uses:
      - effect_sizes  -> OR (odds ratio), HR (hazard ratio), beta, ...
      - class_acc     -> AUROC, C-index (concordance), ...
      - othermetrics  -> R2, top-vs-bottom-quantile OR, ...
    and summarizes the evaluation sample set (ancestry + sample size) so an
    agent can judge how a published score was validated and in whom.
    """
    pm = p.get("performance_metrics") or {}
    pub = p.get("publication") or {}
    sampleset = p.get("sampleset") or {}
    samples = sampleset.get("samples") or []
    eval_samples = [
        {
            "sample_number": s.get("sample_number"),
            "sample_cases": s.get("sample_cases"),
            "sample_controls": s.get("sample_controls"),
            "ancestry_broad": s.get("ancestry_broad"),
            "ancestry_free": s.get("ancestry_free"),
            "ancestry_country": s.get("ancestry_country"),
            "phenotyping_free": s.get("phenotyping_free"),
            "cohorts": [
                c.get("name_short")
                for c in (s.get("cohorts") or [])
                if c.get("name_short")
            ],
        }
        for s in samples
    ]
    return {
        "ppm_id": p.get("id"),
        "pgs_id": p.get("associated_pgs_id"),
        "phenotyping_reported": p.get("phenotyping_reported"),
        "covariates": p.get("covariates"),
        "performance_comments": p.get("performance_comments"),
        "effect_sizes": [_metric(m) for m in (pm.get("effect_sizes") or [])],
        "classification_accuracy": [_metric(m) for m in (pm.get("class_acc") or [])],
        "other_metrics": [_metric(m) for m in (pm.get("othermetrics") or [])],
        "evaluation_sampleset_id": sampleset.get("id"),
        "evaluation_samples": eval_samples,
        "publication": {
            "first_author": pub.get("firstauthor"),
            "journal": pub.get("journal"),
            "year": pub.get("date_publication", "")[:4]
            if pub.get("date_publication")
            else None,
            "pmid": pub.get("PMID"),
            "doi": pub.get("doi"),
        },
    }


def _score_summary(s: Dict[str, Any]) -> Dict[str, Any]:
    """Trim a raw PGS score record to the useful summary fields."""
    pub = s.get("publication") or {}
    return {
        "pgs_id": s.get("id"),
        "name": s.get("name"),
        "trait_reported": s.get("trait_reported"),
        "variants_number": s.get("variants_number"),
        "method_name": s.get("method_name"),
        "genome_build": s.get("variants_genomebuild"),
        "weight_type": s.get("weight_type"),
        "publication": {
            "first_author": pub.get("firstauthor"),
            "journal": pub.get("journal"),
            "year": pub.get("date_publication", "")[:4]
            if pub.get("date_publication")
            else None,
            "pmid": pub.get("PMID"),
            "doi": pub.get("doi"),
        },
        "scoring_file": s.get("ftp_scoring_file"),
    }


@register_tool("PGSCatalogTool")
class PGSCatalogTool(BaseTool):
    """Query the PGS Catalog (EBI) for published polygenic scores."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.operation: str = tool_config.get("fields", {}).get("operation", "")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation") or self.operation
        if operation == "search_traits":
            return self._search_traits(arguments)
        if operation == "get_scores_by_trait":
            return self._get_scores_by_trait(arguments)
        if operation == "get_score":
            return self._get_score(arguments)
        if operation == "get_performance_metrics":
            return self._get_performance_metrics(arguments)
        return {
            "status": "error",
            "error": f"Unknown operation: {operation}. Supported: "
            "search_traits, get_scores_by_trait, get_score, "
            "get_performance_metrics.",
        }

    def _request(self, path: str, params: Dict[str, Any] | None = None):
        try:
            resp = requests.get(
                f"{PGS_API}/{path}",
                params=params or {},
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
        except requests.Timeout:
            return None, {
                "status": "error",
                "error": f"PGS Catalog request timed out after {self.timeout}s.",
            }
        except requests.exceptions.RequestException as e:
            return None, {
                "status": "error",
                "error": f"Failed to reach PGS Catalog: {str(e)}",
            }
        if resp.status_code == 404:
            return None, {"status": "error", "error": "Not found in the PGS Catalog."}
        if resp.status_code != 200:
            return None, {
                "status": "error",
                "error": f"PGS Catalog returned HTTP {resp.status_code}",
            }
        try:
            return resp.json(), None
        except ValueError:
            return None, {
                "status": "error",
                "error": "PGS Catalog returned a non-JSON response.",
            }

    def _search_traits(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        term = arguments.get("query") or arguments.get("term")
        if not term or not str(term).strip():
            return {
                "status": "error",
                "error": "Parameter 'query' is required (a trait/phenotype term, e.g. 'coronary artery disease').",
            }
        body, err = self._request("trait/search", {"term": str(term)})
        if err:
            return err
        results: List[Dict[str, Any]] = (
            body.get("results", []) if isinstance(body, dict) else []
        )
        traits = [
            {
                "trait_id": t.get("id"),
                "label": t.get("label"),
                "description": t.get("description"),
                "n_scores": len(t.get("associated_pgs_ids", [])),
                # The scores themselves, already in hand. A trait search
                # exists to find them, and the row reported only how many.
                "associated_pgs_ids": [
                    i for i in (t.get("associated_pgs_ids") or []) if i
                ][:PGS_IDS_PER_TRAIT],
                # Scores attached to CHILD terms of the trait. Measured on
                # MONDO_0005010: 8 of them, and none is returned by
                # score/search?trait_id= -- so without this field they are
                # reachable through no call this tool makes.
                "child_associated_pgs_ids": [
                    i for i in (t.get("child_associated_pgs_ids") or []) if i
                ][:PGS_IDS_PER_TRAIT],
                "n_child_scores": len(t.get("child_associated_pgs_ids") or []),
                # Why the row matched: the query "coronary artery disease" is
                # a SYNONYM of the label "coronary artery disorder".
                "trait_synonyms": [
                    syn for syn in (t.get("trait_synonyms") or []) if syn
                ],
                "trait_categories": [
                    cat for cat in (t.get("trait_categories") or []) if cat
                ],
                "trait_mapped_terms": [
                    term_id for term_id in (t.get("trait_mapped_terms") or []) if term_id
                ],
                "url": t.get("url"),
            }
            for t in results
        ]
        return {
            "status": "success",
            "data": traits,
            "metadata": {
                "source": PGS_SOURCE,
                "query": str(term),
                "returned": len(traits),
                "pgs_ids_per_trait": PGS_IDS_PER_TRAIT,
                "note": "associated_pgs_ids are the trait's own scores; "
                "child_associated_pgs_ids belong to child terms and are not "
                "returned by get_scores_by_trait for this trait_id.",
            },
        }

    def _get_scores_by_trait(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        trait_id = arguments.get("trait_id") or arguments.get("efo_id")
        if not trait_id or not str(trait_id).strip():
            return {
                "status": "error",
                "error": "Parameter 'trait_id' is required (an EFO/MONDO id, e.g. "
                "'MONDO_0004989'; find one with operation 'search_traits').",
            }
        body, err = self._request("score/search", {"trait_id": str(trait_id).strip()})
        if err:
            return err
        results = body.get("results", []) if isinstance(body, dict) else []
        return {
            "status": "success",
            "data": [_score_summary(s) for s in results],
            "metadata": {
                "source": PGS_SOURCE,
                "trait_id": str(trait_id).strip(),
                "total": body.get("count") if isinstance(body, dict) else len(results),
                "returned": len(results),
            },
        }

    def _get_score(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pgs_id = arguments.get("pgs_id") or arguments.get("score_id")
        if not pgs_id or not str(pgs_id).strip():
            return {
                "status": "error",
                "error": "Parameter 'pgs_id' is required (e.g. 'PGS000001').",
            }
        pgs_id = str(pgs_id).strip().upper()
        body, err = self._request(f"score/{pgs_id}")
        if err:
            return err
        if not isinstance(body, dict) or not body.get("id"):
            return {
                "status": "error",
                "error": f"No PGS Catalog score found for '{pgs_id}'.",
            }

        summary = _score_summary(body)
        # add the richer fields available on the single-score endpoint
        summary["trait_efo"] = [
            {"id": t.get("id"), "label": t.get("label")}
            for t in (body.get("trait_efo") or [])
        ]
        summary["ancestry_distribution"] = body.get("ancestry_distribution")
        summary["samples_training"] = body.get("samples_training")
        # samples_training is where the weights were fitted; samples_variants
        # is the GWAS the variants were discovered in, with its ancestry, its
        # size and its GWAS Catalog accession. A score's transferability
        # depends on both, and this one reached no handler. PGS000018 has
        # seven, from East Asian 11,323 to Hispanic/Latin American 4,095.
        summary["samples_variants"] = [
            {
                "sample_number": v.get("sample_number"),
                "ancestry_broad": v.get("ancestry_broad"),
                "ancestry_free": v.get("ancestry_free"),
                "source_PMID": v.get("source_PMID"),
                "source_GWAS_catalog": v.get("source_GWAS_catalog"),
                "cohorts": [
                    c.get("name_short")
                    for c in (v.get("cohorts") or [])
                    if c.get("name_short")
                ],
            }
            for v in (body.get("samples_variants") or [])
        ]
        # The terms under which the scoring file above may be reused. The
        # tool returned a download URL and not the licence governing it.
        summary["license"] = body.get("license")
        # ftp_scoring_file is in the author's original build; these are
        # harmonized to GRCh37 and GRCh38, which is what a caller applying
        # the score to their own genotypes actually needs.
        summary["harmonized_scoring_files"] = body.get(
            "ftp_harmonized_scoring_files"
        )
        # Whether the Catalog's own curation matches the paper it cites.
        summary["matches_publication"] = body.get("matches_publication")
        # method_name without method_params is "we used C+T" with no
        # thresholds: PGS000746 is p=1.23^-3, r^2=0.21.
        summary["method_params"] = body.get("method_params")
        summary["date_release"] = body.get("date_release")
        summary["trait_additional"] = body.get("trait_additional")
        return {
            "status": "success",
            "data": summary,
            "metadata": {"source": PGS_SOURCE},
        }

    def _get_performance_metrics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pgs_id = arguments.get("pgs_id") or arguments.get("score_id")
        if not pgs_id or not str(pgs_id).strip():
            return {
                "status": "error",
                "error": "Parameter 'pgs_id' is required (e.g. 'PGS000001').",
            }
        pgs_id = str(pgs_id).strip().upper()
        body, err = self._request("performance/search", {"pgs_id": pgs_id})
        if err:
            return err
        results = body.get("results", []) if isinstance(body, dict) else []
        return {
            "status": "success",
            "data": [_performance_summary(p) for p in results],
            "metadata": {
                "source": PGS_SOURCE,
                "pgs_id": pgs_id,
                "total": body.get("count") if isinstance(body, dict) else len(results),
                "returned": len(results),
            },
        }
