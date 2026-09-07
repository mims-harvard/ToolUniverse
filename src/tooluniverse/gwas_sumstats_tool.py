"""
EBI GWAS Summary Statistics REST API tool for ToolUniverse.

Provides access to full GWAS summary statistics deposited with the
GWAS Catalog. Unlike the main GWAS Catalog (which stores curated top hits),
this API gives access to variant-level summary statistics across the
entire genome for deposited studies.

API: https://www.ebi.ac.uk/gwas/summary-statistics/api/
No authentication required.
"""

import math
import numbers

import requests
from typing import Any, Dict, List
from .base_tool import BaseTool
from .tool_registry import register_tool

GWAS_SS_BASE_URL = "https://www.ebi.ac.uk/gwas/summary-statistics/api"


def _p_value_is_reported(p_value: Any) -> bool:
    """Is ``p_value`` an actual p-value rather than a missing-data sentinel?

    The GWAS Catalog summary-statistics store encodes "not reported" as the
    numeric sentinel ``-99.0`` (confirmed live: rows from GCST004415 in
    chr2:179000000-179600000 come back with ``p_value == -99.0`` *and*
    ``odds_ratio == -99.0``, neither of which is a legal value for its
    field). Those sentinel rows are served even when the caller asks the
    API for ``p_upper=5e-8``, because ``-99 <= 5e-8`` is numerically true.

    Note the upstream ``code`` field is *not* a usable discriminator here:
    it is the harmonisation code, and code 10 means "forward strand,
    alleles already in the correct orientation" (a success), while code 14
    means "invalid for harmonisation" -- observed live on rows carrying
    perfectly real p-values. So the test is on the value itself: a real
    p-value is a finite number in [0, 1]. ``0.0`` is kept because sumstats
    legitimately underflow to zero for extremely significant hits.
    """
    if isinstance(p_value, bool) or not isinstance(p_value, numbers.Real):
        return False
    value = float(p_value)
    if not math.isfinite(value):
        return False
    return 0.0 <= value <= 1.0


def _p_sort_key(association: dict[str, Any]):
    """Ascending-by-significance sort key that never ranks a sentinel first.

    Rows with no reported p-value sort after every row that has one, instead
    of being lifted to the top by ``-99 < 5e-24``.
    """
    p_value = association.get("p_value")
    if _p_value_is_reported(p_value):
        return (0, float(p_value))
    return (1, 0.0)


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
        """List GWAS studies with deposited summary statistics."""
        size = arguments.get("size") or arguments.get("limit") or 20

        url = f"{GWAS_SS_BASE_URL}/studies"
        params = {"size": min(size, 100)}
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        studies_raw = data.get("_embedded", {}).get("studies", [])
        studies: List[Dict[str, Any]] = []
        for entry in studies_raw:
            # Each entry may be a list with one dict, or a dict
            if isinstance(entry, list):
                for s in entry:
                    studies.append({"study_accession": s.get("study_accession")})
            elif isinstance(entry, dict):
                studies.append({"study_accession": entry.get("study_accession")})

        return {
            "status": "success",
            "data": studies,
            "metadata": {
                "source": "EBI GWAS Summary Statistics",
                "returned": len(studies),
            },
        }

    def _get_trait_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get studies with summary statistics for a given EFO trait."""
        trait_id = arguments.get("trait_id", "")
        if not trait_id:
            return {
                "status": "error",
                "error": "trait_id is required (e.g., 'EFO_0000249' for Alzheimer's)",
            }

        url = f"{GWAS_SS_BASE_URL}/traits/{trait_id}/studies"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code == 404:
            error = f"No summary statistics found for trait '{trait_id}'"
            # This API only recognizes EFO ids. A disease looked up in a
            # different ontology (e.g. PGS Catalog's MONDO/HP ids) 404s
            # identically to a genuinely nonexistent EFO id, which silently
            # sends the caller down the wrong path -- confirmed live for
            # MONDO_0004975 (Alzheimer disease's MONDO id; EFO_0000249
            # works for the same disease). Name the likely cause when the
            # id doesn't look like an EFO id.
            if not trait_id.upper().startswith("EFO_"):
                error += (
                    ". This API only accepts EFO trait ids -- if this id "
                    "came from another ontology (e.g. MONDO, HP, DOID), "
                    "look up the equivalent EFO id instead."
                )
            return {"status": "error", "error": error}
        resp.raise_for_status()
        data = resp.json()

        studies_raw = data.get("_embedded", {}).get("studies", [])
        studies: List[Dict[str, Any]] = []
        for s in studies_raw:
            if isinstance(s, dict):
                studies.append({"study_accession": s.get("study_accession")})
            elif isinstance(s, list):
                for item in s:
                    studies.append({"study_accession": item.get("study_accession")})

        return {
            "status": "success",
            "data": studies,
            "metadata": {
                "source": "EBI GWAS Summary Statistics",
                "trait_id": trait_id,
                "num_studies": len(studies),
            },
        }

    def _get_region_associations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary statistics for variants in a chromosomal region."""
        chromosome = arguments.get("chromosome")
        bp_lower = arguments.get("bp_lower")
        bp_upper = arguments.get("bp_upper")
        p_upper = arguments.get("p_upper", 5e-8)
        study_accession = arguments.get("study_accession")
        size = arguments.get("size", 50)

        if not chromosome:
            return {
                "status": "error",
                "error": "chromosome is required (e.g., 19)",
            }
        if bp_lower is None or bp_upper is None:
            return {
                "status": "error",
                "error": "bp_lower and bp_upper are required",
            }

        url = f"{GWAS_SS_BASE_URL}/chromosomes/{chromosome}/associations"
        params = {
            "bp_lower": bp_lower,
            "bp_upper": bp_upper,
            "size": min(size, 1000),
        }
        if p_upper is not None:
            params["p_upper"] = p_upper
        if study_accession:
            params["study_accession"] = study_accession

        resp = requests.get(url, params=params, timeout=self.timeout)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"No associations found for chr{chromosome}:{bp_lower}-{bp_upper}",
            }
        resp.raise_for_status()
        data = resp.json()

        assocs_raw = data.get("_embedded", {}).get("associations", {})
        if isinstance(assocs_raw, dict):
            assoc_values = list(assocs_raw.values())
        else:
            assoc_values = list(assocs_raw or [])

        associations: List[Dict[str, Any]] = []
        sentinel_rows_excluded = 0
        for v in assoc_values:
            if not isinstance(v, dict):
                continue
            p_value = v.get("p_value")
            p_value_reported = _p_value_is_reported(p_value)

            # A row whose p-value is a missing-data sentinel (-99) is not a
            # significant association, so it must not satisfy a p_upper
            # threshold -- the upstream API lets it through because the
            # comparison -99 <= 5e-8 is numerically true.
            if p_upper is not None and not p_value_reported:
                sentinel_rows_excluded += 1
                continue

            associations.append(
                {
                    "variant_id": v.get("variant_id"),
                    "chromosome": v.get("chromosome"),
                    "position": v.get("base_pair_location"),
                    "p_value": p_value,
                    "p_value_reported": p_value_reported,
                    "code": v.get("code"),
                    "beta": v.get("beta"),
                    "odds_ratio": v.get("odds_ratio"),
                    "effect_allele": v.get("effect_allele"),
                    "other_allele": v.get("other_allele"),
                    "effect_allele_frequency": v.get("effect_allele_frequency"),
                    "study_accession": v.get("study_accession"),
                    "trait": v.get("trait"),
                    "ci_lower": v.get("ci_lower"),
                    "ci_upper": v.get("ci_upper"),
                }
            )

        # Most significant first; rows with no reported p-value always last.
        associations.sort(key=_p_sort_key)

        metadata: dict[str, Any] = {
            "source": "EBI GWAS Summary Statistics",
            "region": f"chr{chromosome}:{bp_lower}-{bp_upper}",
            "p_upper_filter": p_upper,
            "num_associations": len(associations),
            "sentinel_rows_excluded": sentinel_rows_excluded,
        }
        if sentinel_rows_excluded:
            metadata["sentinel_note"] = (
                f"{sentinel_rows_excluded} of {len(assoc_values)} rows returned by "
                "the API carried the GWAS Catalog missing-value sentinel "
                "(p_value = -99) instead of a p-value; they were excluded because "
                "a missing p-value cannot meet the p_upper threshold. Omit p_upper "
                "to see them, flagged with p_value_reported = false."
            )
        return {
            "status": "success",
            "data": associations,
            "metadata": metadata,
        }
