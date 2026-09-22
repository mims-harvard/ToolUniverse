"""
EBI GWAS Summary Statistics REST API tool for ToolUniverse.

Provides access to full GWAS summary statistics deposited with the
GWAS Catalog. Unlike the main GWAS Catalog (which stores curated top hits),
this API gives access to variant-level summary statistics across the
entire genome for deposited studies.

API: https://www.ebi.ac.uk/gwas/api/v2
No authentication required.

The summary-statistics API these tools were built on
(/gwas/summary-statistics/api) now answers 410 on every path:

    This API has been deprecated.
    For ways to access summary statistics see:
    https://www.ebi.ac.uk/gwas/docs/methods/summary-statistics

Study listing and per-trait lookup moved to the GWAS Catalog v2 API. Region
queries did not: v2 serves associations only per study
(/studies/{accession}/associations) and ignores bp_lower, bp_upper,
chromosome and p_upper entirely -- confirmed live, a filtered request returns
the same 38 rows as an unfiltered one. Genome-region access is FTP/tabix only
now, so that tool is retired rather than repointed.
"""

import requests
from typing import Any, Dict, List
from .base_tool import BaseTool
from .tool_registry import register_tool

GWAS_BASE_URL = "https://www.ebi.ac.uk/gwas/api/v2"
#: Where the region-level data went when the old API was retired.
SUMSTATS_FTP_URL = "https://ftp.ebi.ac.uk/pub/databases/gwas/summary_statistics/"


def _study_record(entry: dict) -> dict:
    """Shape one v2 study into the fields a caller acts on."""
    return {
        "study_accession": entry.get("accessionId"),
        "reported_trait": entry.get("reportedTrait"),
        "efo_traits": [
            {"id": t.get("key"), "label": t.get("label")}
            for t in (entry.get("efoTraits") or [])
            if isinstance(t, dict)
        ],
        "pubmed_id": entry.get("pubmedId"),
        "publication_date": entry.get("publicationDate"),
        "first_author": entry.get("firstAuthor"),
        "association_count": entry.get("associationCount"),
    }


@register_tool("GWASSumStatsTool")
class GWASSumStatsTool(BaseTool):
    """
    Tool for querying EBI GWAS Summary Statistics API.

    Provides full variant-level summary statistics from deposited GWAS
    studies, including effect sizes, p-values, and allele frequencies
    for specific genomic regions.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "list_studies"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the GWAS Summary Statistics API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"GWAS Summary Statistics API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to GWAS Summary Statistics API",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"GWAS Summary Statistics API error: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        dispatch_map = {
            "list_studies": self._list_studies,
            "get_trait_studies": self._get_trait_studies,
            "get_region_associations": self._get_region_associations,
        }
        handler = dispatch_map.get(self.endpoint_type)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }
        return handler(arguments)

    def _list_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List GWAS Catalog studies."""
        size = arguments.get("size") or arguments.get("limit") or 20

        url = f"{GWAS_BASE_URL}/studies"
        params = {"size": min(size, 100)}
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        studies = [
            _study_record(entry)
            for entry in (data.get("_embedded", {}).get("studies") or [])
            if isinstance(entry, dict)
        ]

        return {
            "status": "success",
            "data": studies,
            "metadata": {
                "source": "GWAS Catalog v2",
                "returned": len(studies),
                "total_available": (data.get("page") or {}).get("totalElements"),
            },
        }

    def _get_trait_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get studies for a trait, matched on the EFO trait label.

        v2's ``efoTrait`` is a case-insensitive substring match on the label,
        not an exact one: 'alzheimer' returns 438 studies, 'Alzheimer disease'
        250, 'ALZHEIMER' the same 438, and an unmatched string 0.
        """
        trait = (arguments.get("trait") or arguments.get("trait_label") or "").strip()
        legacy_id = (arguments.get("trait_id") or "").strip()

        if not trait and legacy_id:
            # The v2 API filters on the trait *label*, not the ontology id, and
            # answers an id with zero studies rather than an error -- which
            # reads exactly like "this trait has no studies". Say what happened
            # instead of returning an empty list. Several ids callers still
            # hold are obsolete too: OLS resolves EFO_0000249 to
            # "obsolete_Alzheimer's disease".
            return {
                "status": "error",
                "error": (
                    f"This tool matches on the EFO trait label, not an id like "
                    f"'{legacy_id}'. Pass trait='Alzheimer disease', or a "
                    f"shorter substring like trait='alzheimer' to cast wider. "
                    f"Resolve an id to its label first if that is what you "
                    f"hold -- EBI OLS (ols_* tools) does this, and note that "
                    f"some older ids are now obsolete."
                ),
            }

        if not trait:
            return {
                "status": "error",
                "error": (
                    "trait is required, as an EFO trait label "
                    "(e.g., 'Alzheimer disease', 'body mass index')."
                ),
            }

        url = f"{GWAS_BASE_URL}/studies"
        size = arguments.get("size") or 20
        params = {"efoTrait": trait, "size": min(size, 100)}
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        studies = [
            _study_record(entry)
            for entry in (data.get("_embedded", {}).get("studies") or [])
            if isinstance(entry, dict)
        ]

        total = (data.get("page") or {}).get("totalElements")
        if not studies:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "source": "GWAS Catalog v2",
                    "trait": trait,
                    "num_studies": 0,
                    "note": (
                        "No studies matched. The match is a case-insensitive "
                        "substring of the EFO label, so a shorter term casts "
                        "wider -- 'alzheimer' matches where 'alzheimers' "
                        "barely does."
                    ),
                },
            }

        return {
            "status": "success",
            "data": studies,
            "metadata": {
                "source": "GWAS Catalog v2",
                "trait": trait,
                "num_studies": len(studies),
                "total_available": total,
            },
        }

    def _get_region_associations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Report that region-level access is no longer served over REST.

        This is kept as a named failure rather than removed so a caller that
        still asks for a genomic region learns where the data went. The
        capability itself is gone: v2 serves associations only per study, and
        ignores chromosome, bp_lower, bp_upper and p_upper -- a filtered
        request returns the same rows as an unfiltered one.
        """
        chromosome = arguments.get("chromosome")
        bp_lower = arguments.get("bp_lower")
        bp_upper = arguments.get("bp_upper")
        region = (
            f"chr{chromosome}:{bp_lower}-{bp_upper}"
            if chromosome and bp_lower is not None and bp_upper is not None
            else "a genomic region"
        )
        return {
            "status": "error",
            "error": (
                f"Summary statistics for {region} are no longer available over "
                f"REST. EBI retired /gwas/summary-statistics/api (410 on every "
                f"path) and the v2 API serves associations only per study, "
                f"without region or p-value filters. Download the per-study "
                f"files from {SUMSTATS_FTP_URL} and query them with tabix, or "
                f"use GWASSumStats_get_trait_studies to find the study "
                f"accessions to download."
            ),
            "metadata": {
                "retired_endpoint": (
                    "https://www.ebi.ac.uk/gwas/summary-statistics/api"
                    "/chromosomes/{chromosome}/associations"
                ),
                "replacement": SUMSTATS_FTP_URL,
                "docs": "https://www.ebi.ac.uk/gwas/docs/methods/summary-statistics",
            },
        }
