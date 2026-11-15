"""
Open Genes tools for ToolUniverse — curated aging/longevity gene database.

Open Genes is a manually-curated database of genes associated with aging and
longevity, each backed by experimental evidence (lifespan-change studies, longevity
associations, age-related expression changes, progeria associations). These tools
look up a gene's aging profile and browse the catalog.

API: https://open-genes.com/api  (public, no authentication, JSON)
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

OPEN_GENES_BASE = "https://open-genes.com/api"


def _names(items: Any, key: str = "name") -> List[str]:
    return (
        [i.get(key) for i in items if isinstance(i, dict) and i.get(key)]
        if isinstance(items, list)
        else []
    )


def _evidence_counts(researches: Any) -> Dict[str, int]:
    if not isinstance(researches, dict):
        return {}
    return {k: (len(v) if isinstance(v, list) else v) for k, v in researches.items()}


# What each kind of Open Genes evidence record actually says, by the fields
# that carry the answer rather than the measurement detail. GHR has 57
# longevity-association records and 14 lifespan studies, and the tool reported
# "57" and "14" -- counts for a tool whose description says to use it to
# assess "whether and HOW a gene is implicated in aging". Nothing else returns
# these records, so the how was unreachable.
_EVIDENCE_DIGEST_FIELDS = {
    "increaseLifespan": ("interventionResultForLifespan", "modelOrganism", "sex"),
    "geneAssociatedWithLongevityEffects": (
        "longevityEffect",
        "dataType",
        # What KIND of study found it, and in what kind of variant. Measured
        # over 183 association records across ten genes: studyType is filled
        # on 98% of them and polymorphismType on 97%, and a longevity
        # association from a GWAS is not the same claim as one from a
        # candidate-gene study.
        "studyType",
        "polymorphismType",
        "ethnicity",
        "sex",
    ),
    "ageRelatedChangesOfGene": ("changeType", "sample", "modelOrganism"),
    "interventionToGeneImprovesVitalProcesses": (
        "geneIntervention",
        "result",
        "vitalProcess",
        "modelOrganism",
    ),
    "proteinRegulatesOtherGenes": ("regulationType", "regulatedGene"),
    "additionalEvidences": (),
}
DOIS_PER_EVIDENCE_TYPE = 25
# How many individual longevity-association records come back per gene. The
# statistical fields only mean anything attached to their own record, so they
# cannot go in the distinct-value digest; they need the records.
ASSOCIATIONS_PER_GENE = 25
_ASSOCIATION_RECORD_FIELDS = (
    "longevityEffect",
    "polymorphismId",
    "polymorphismType",
    "studyType",
    "significance",
    "pValue",
    "associatedAllele",
    "nonAssociatedAllele",
    "nOfExperiment",
    "nOfControls",
    "ethnicity",
    "sex",
    "doi",
    "pmid",
)
VALUES_PER_EVIDENCE_FIELD = 25


def _distinct(records: List[Dict[str, Any]], field: str) -> List[str]:
    """The distinct non-empty values of one field, in first-seen order."""
    seen: List[str] = []
    for record in records:
        value = record.get(field) if isinstance(record, dict) else None
        if value in (None, "", []):
            continue
        text = str(value)
        if text not in seen:
            seen.append(text)
    return seen


def _evidence_digest(researches: Any) -> Dict[str, Any]:
    """Per evidence type: what the records say, not just how many there are."""
    if not isinstance(researches, dict):
        return {}
    digest: Dict[str, Any] = {}
    for key, records in researches.items():
        if not isinstance(records, list) or not records:
            continue
        rows = [r for r in records if isinstance(r, dict)]
        entry: Dict[str, Any] = {"count": len(records)}
        for field in _EVIDENCE_DIGEST_FIELDS.get(key, ()):
            values = _distinct(rows, field)
            if values:
                entry[field] = values[:VALUES_PER_EVIDENCE_FIELD]
                if len(values) > VALUES_PER_EVIDENCE_FIELD:
                    entry[f"{field}_truncated"] = True
                    entry[f"{field}_distinct_count"] = len(values)
        # The association records themselves, for the one evidence type whose
        # claim is statistical. A digest collects DISTINCT values per field,
        # which is right for categories and useless for a p-value: a list of
        # distinct p-values is detached from the associations they belong to.
        # Measured over 183 records: significance 98%, polymorphismId 98%,
        # nOfExperiment 98%, nOfControls 96%, pValue 95% -- so a caller got
        # the effect and could not tell whether to believe it, which cohort
        # it came from, or which variant to look up. Capped, with the cap
        # disclosed.
        if key == "geneAssociatedWithLongevityEffects":
            associations = []
            for row in rows[:ASSOCIATIONS_PER_GENE]:
                association = {
                    field: row.get(field)
                    for field in _ASSOCIATION_RECORD_FIELDS
                    if row.get(field) not in (None, "")
                }
                if association:
                    associations.append(association)
            if associations:
                entry["associations"] = associations
                entry["associations_returned"] = len(associations)
                entry["associations_truncated"] = len(rows) > ASSOCIATIONS_PER_GENE
        dois = _distinct(rows, "doi")
        if dois:
            entry["dois"] = dois[:DOIS_PER_EVIDENCE_TYPE]
            entry["doi_count"] = len(dois)
            entry["dois_truncated"] = len(dois) > DOIS_PER_EVIDENCE_TYPE
        digest[key] = entry
    return digest


def _fetch_json(
    path: str, timeout: int, params: Dict[str, Any] = None, not_found_ok: bool = False
) -> Any:
    """GET a JSON resource from Open Genes.

    Returns the parsed JSON on success, or a {"status": "error", ...} dict on
    any network/parse failure so callers can return it directly.

    Fix-R30D-5: for a single-resource lookup like gene/{symbol}, Open Genes
    signals "unknown symbol" via a genuine HTTP 404 (confirmed live:
    gene/FAKEGENE123 -> 404 with body {"message":"Gene FAKEGENE123 not
    found",...}) -- the same conceptual outcome as when it instead returns
    200 with a body missing the expected fields, which callers already
    handle gracefully. Without not_found_ok, a 404 was previously
    indistinguishable from a real network failure, giving two different
    envelopes for the same "not in Open Genes" case depending on which way
    the upstream happened to signal it. `not_found_ok=True` returns None on
    404 instead, letting the caller route it through its existing
    graceful-empty-result handling.
    """
    try:
        resp = requests.get(
            f"{OPEN_GENES_BASE}/{path}",
            params=params,
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        if not_found_ok and resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "error": f"Open Genes request timed out after {timeout}s",
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Open Genes request failed: {e}"}
    except ValueError:
        return {"status": "error", "error": "Open Genes returned a non-JSON response"}


def _summarize(g: Dict[str, Any]) -> Dict[str, Any]:
    conf = g.get("confidenceLevel")
    return {
        "symbol": g.get("symbol"),
        "name": g.get("name"),
        "ncbi_id": g.get("ncbiId"),
        "uniprot": g.get("uniprot"),
        "ensembl": g.get("ensembl"),
        "aging_mechanisms": _names(g.get("agingMechanisms")),
        "functional_clusters": _names(g.get("functionalClusters")),
        # diseaseCategories entries key their label as "icdCategoryName", not
        # "name" (confirmed live), so pass that key explicitly.
        "disease_categories": _names(g.get("diseaseCategories"), "icdCategoryName"),
        # Specific named disease associations (e.g. "Progeria", "Dilated
        # cardiomyopathy") -- a separate, more specific field from
        # diseaseCategories's broad ICD chapter groupings, and previously
        # not surfaced at all.
        "diseases": _names(g.get("diseases")),
        "confidence_level": conf.get("name") if isinstance(conf, dict) else conf,
        "expression_change": g.get("expressionChange"),
    }


@register_tool("OpenGenesGeneTool")
class OpenGenesGeneTool(BaseTool):
    """Get the aging/longevity profile of a gene by symbol from Open Genes."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        symbol = (arguments.get("symbol") or "").strip()
        if not symbol:
            return {
                "status": "error",
                "error": "'symbol' is required (e.g. 'GHR', 'FOXO3', 'TP53')",
            }

        g = _fetch_json(f"gene/{symbol}", self.timeout, not_found_ok=True)
        if isinstance(g, dict) and g.get("status") == "error":
            return g

        # Unknown symbols 404, or return a string/error page instead of a
        # gene object; both mean the same thing to a caller.
        if not isinstance(g, dict) or not g.get("symbol"):
            return {
                "status": "success",
                "data": {},
                "metadata": {
                    "query_symbol": symbol,
                    "note": f"'{symbol}' is not in Open Genes (not an annotated aging gene).",
                },
            }
        data = _summarize(g)
        data["evidence_counts"] = _evidence_counts(g.get("researches"))
        data["evidence_summary"] = _evidence_digest(g.get("researches"))
        data["protein_description"] = g.get("proteinDescriptionOpenGenes") or g.get(
            "proteinDescriptionUniProt"
        )
        return {
            "status": "success",
            "data": data,
            "metadata": {"query_symbol": symbol, "source": "Open Genes"},
        }


@register_tool("OpenGenesSearchTool")
class OpenGenesSearchTool(BaseTool):
    """Browse the Open Genes catalog of aging/longevity genes (paginated)."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        limit = arguments.get("limit", 20)
        page = arguments.get("page", 1)
        if limit is None:
            limit = 20
        if page is None:
            page = 1
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 1000
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 1000",
            }
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            return {
                "status": "error",
                "error": "page must be a positive integer",
            }
        params["pageSize"] = limit
        params["page"] = page

        payload = _fetch_json("gene/search", self.timeout, params=params)
        if isinstance(payload, dict) and payload.get("status") == "error":
            return payload

        items = payload.get("items", []) if isinstance(payload, dict) else []
        opts = payload.get("options", {}) if isinstance(payload, dict) else {}
        pagination = opts.get("pagination", {}) if isinstance(opts, dict) else {}
        total = opts.get("total") if isinstance(opts, dict) else None
        total_pages = pagination.get("pagesTotal")
        current_page = pagination.get("page", page)
        has_more = (
            isinstance(total_pages, int)
            and isinstance(current_page, int)
            and current_page < total_pages
        )
        return {
            "status": "success",
            "data": [_summarize(g) for g in items if isinstance(g, dict)],
            "metadata": {
                "total_aging_genes": total,
                "total_is_exact": isinstance(total, int),
                "page": current_page,
                "page_size": pagination.get("pageSize", limit),
                "total_pages": total_pages,
                "returned": len(items),
                "has_more": has_more,
                "truncated": has_more,
                "next_page": current_page + 1 if has_more else None,
                "source": "Open Genes",
            },
        }
