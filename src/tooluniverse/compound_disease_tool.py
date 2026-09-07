"""Compound tool: gather a comprehensive disease profile from multiple databases.

Queries Orphanet, OMIM, DisGeNET, OpenTargets, and OLS for a given disease,
returning identifiers, associated genes, phenotypes, and prevalence data
in a single call.
"""

import re
from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_registry import register_tool

# Disease nomenclature mixes Roman and Arabic subtype numbers freely --
# "Mucopolysaccharidosis type I" (query), "Mucopolysaccharidosis Type I"
# (NCIT) and "Mucopolysaccharidosis type 1" (Orphanet) are one disease.
_ROMAN_TO_ARABIC = {
    "i": "1",
    "ii": "2",
    "iii": "3",
    "iv": "4",
    "v": "5",
    "vi": "6",
    "vii": "7",
    "viii": "8",
    "ix": "9",
    "x": "10",
}


def _normalize_disease_label(text: str) -> str:
    """Fold a disease name to a comparable form: lowercase, punctuation-free,
    with Roman subtype numerals rewritten as Arabic."""
    tokens = re.split(r"[^0-9a-z]+", (text or "").lower())
    return " ".join(_ROMAN_TO_ARABIC.get(t, t) for t in tokens if t)


def _labels_match(query: str, label: str) -> bool:
    """True when `label` names the same disease the caller asked for."""
    normalized_query = _normalize_disease_label(query)
    return (
        bool(normalized_query) and _normalize_disease_label(label) == normalized_query
    )


def _truncate_msg(msg: str, limit: int = 240) -> str:
    """Truncate an error message on a word boundary, never mid-word.

    Sub-tool error messages are the only actionable guidance a caller gets
    on a failed source; cutting them off mid-word at a fixed character
    count silently drops that guidance (e.g. DisGeNET's "...resolve first
    (e.g. umls_search_concepts)..." hint used to get cut to "umls_search_").
    """
    if len(msg) <= limit:
        return msg
    head = msg[:limit].rsplit(" ", 1)[0]
    return head + "..."


@register_tool("CompoundDiseaseProfileTool")
class CompoundDiseaseProfileTool(BaseTool):
    """Gather a comprehensive disease profile from Orphanet, OMIM, DisGeNET, OpenTargets, and OLS."""

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        disease = arguments.get("disease")
        if not disease:
            return {"status": "error", "error": "'disease' parameter is required."}

        from .execute_function import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()

        sections: Dict[str, Any] = {}
        sources_failed: List[str] = []

        def _try_tool(source_name, tool_name, args):
            try:
                r = tu.run_one_function({"name": tool_name, "arguments": args})
                if isinstance(r, dict) and r.get("status") == "error":
                    sources_failed.append(
                        f"{source_name}: {_truncate_msg(r.get('error', ''))}"
                    )
                return r
            except Exception as e:
                sources_failed.append(f"{source_name}: {_truncate_msg(str(e))}")
                return {"status": "error"}

        # 1. Orphanet
        r = _try_tool(
            "Orphanet", "Orphanet_search_diseases", {"query": disease, "language": "en"}
        )
        sections["orphanet"] = self._parse_orphanet(r, disease)

        # 2. OMIM
        r = _try_tool("OMIM", "OMIM_search", {"query": disease, "limit": 5})
        sections["omim"] = self._parse_omim(r)

        # 3. DisGeNET
        r = _try_tool(
            "DisGeNET", "DisGeNET_search_disease", {"disease": disease, "limit": 20}
        )
        sections["disgenet"] = self._parse_disgenet(r)

        # 4. OpenTargets
        r = _try_tool(
            "OpenTargets", "OpenTargets_get_disease_ids_by_name", {"name": disease}
        )
        sections["opentargets"] = self._parse_opentargets(r)

        # 5. OLS
        r = _try_tool("OLS", "ols_search_terms", {"query": disease, "rows": 5})
        sections["ols"] = self._parse_ols(r)

        # Build unified profile
        profile = self._build_profile(disease, sections)

        return {
            "status": "success",
            "data": {
                "query": disease,
                "sources_queried": list(sections.keys()),
                "sources_failed": sources_failed,
                "profile": profile,
                "per_source": sections,
            },
        }

    @staticmethod
    def _entry_label(entry: Dict[str, Any]) -> str:
        return entry.get(
            "Preferred term", entry.get("preferred_term", entry.get("name", ""))
        )

    def _parse_orphanet(self, result: Any, query: str) -> Dict[str, Any]:
        if not isinstance(result, dict) or result.get("status") == "error":
            return {}
        data = result.get("data", {})
        results_list = data.get("results", data) if isinstance(data, dict) else data
        if not isinstance(results_list, list) or not results_list:
            return {}
        entries = [e for e in results_list if isinstance(e, dict)]
        if not entries:
            return {}
        # Orphanet's search is ranked by its own relevance, not by name
        # equality: "mucopolysaccharidosis type I" puts MPS VI (ORPHA:583)
        # first and the real MPS I (ORPHA:579) fourth. Taking results[0]
        # therefore stamped a different disease's ORPHA code onto the
        # profile. Prefer the hit whose name actually matches the query.
        exact = next(
            (e for e in entries if _labels_match(query, self._entry_label(e))), None
        )
        entry = exact or entries[0]
        return {
            "orpha_code": str(entry.get("ORPHAcode", entry.get("orpha_code", ""))),
            "name": self._entry_label(entry),
            "prevalence": entry.get("prevalence", ""),
            "inheritance": entry.get("inheritance", ""),
            "match": "exact" if exact is not None else "approximate",
        }

    def _parse_omim(self, result: Any) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {}
        data = result.get("data", {})
        entries = []
        if isinstance(data, dict):
            data = data.get("results", data.get("entries", []))
        if isinstance(data, list):
            for entry in data[:5]:
                if isinstance(entry, dict):
                    entries.append(
                        {
                            "mim_number": entry.get(
                                "mim_number", entry.get("mimNumber", "")
                            ),
                            "title": entry.get(
                                "title", entry.get("preferredTitle", "")
                            ),
                            "type": entry.get("type", entry.get("entryType", "")),
                        }
                    )
        return {"entries": entries}

    def _parse_disgenet(self, result: Any) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {}
        data = result.get("data", {})
        genes = []
        items = (
            data
            if isinstance(data, list)
            else data.get("results", data.get("genes", []))
            if isinstance(data, dict)
            else []
        )
        if isinstance(items, list):
            for item in items[:20]:
                if isinstance(item, dict):
                    symbol = item.get(
                        "gene_symbol", item.get("geneName", item.get("gene", ""))
                    )
                    score = item.get("score", item.get("gda_score", None))
                    if symbol:
                        genes.append({"gene": str(symbol), "score": score})
        return {"associated_genes": genes}

    def _parse_opentargets(self, result: Any) -> Dict[str, Any]:
        if not isinstance(result, dict) or result.get("status") == "error":
            return {}
        data = result.get("data", {})
        # OpenTargets search returns {search: {hits: [...]}}
        if isinstance(data, dict) and "search" in data:
            hits = data["search"].get("hits", [])
            if hits and isinstance(hits[0], dict):
                entry = hits[0]
                obj = entry.get("object", entry)
                return {
                    "efo_id": obj.get("id", entry.get("id", "")),
                    "name": obj.get("name", entry.get("name", "")),
                    "description": str(obj.get("description", ""))[:300],
                    "dbXRefs": obj.get("dbXRefs", [])[:10],
                }
        if isinstance(data, dict):
            return {
                "efo_id": data.get("id", data.get("efoId", "")),
                "name": data.get("name", ""),
            }
        return {}

    def _parse_ols(self, result: Any) -> Dict[str, Any]:
        if not isinstance(result, dict) or result.get("status") == "error":
            return {}
        # OLS returns "terms" at top level or inside "data"
        terms_raw = result.get("terms", [])
        if not terms_raw:
            data = result.get("data", {})
            if isinstance(data, dict):
                terms_raw = data.get("terms", data.get("docs", data.get("results", [])))
            elif isinstance(data, list):
                terms_raw = data
        terms = []
        if isinstance(terms_raw, list):
            for doc in terms_raw[:5]:
                if isinstance(doc, dict):
                    terms.append(
                        {
                            "id": doc.get(
                                "oboId",
                                doc.get(
                                    "obo_id",
                                    doc.get("shortForm", doc.get("short_form", "")),
                                ),
                            ),
                            "label": doc.get("label", doc.get("name", "")),
                            "ontology": doc.get(
                                "ontologyName", doc.get("ontology_name", "")
                            ),
                        }
                    )
        return {"terms": terms}

    def _build_profile(self, disease: str, sections: Dict[str, Any]) -> Dict[str, Any]:
        """Build a unified disease profile from all sources.

        `identifiers` is the block downstream callers treat as "the IDs for
        this disease", so only cross-references whose own label names the
        queried disease belong in it. Every source is a ranked search, and
        their top hits routinely disagree: for "mucopolysaccharidosis type I"
        the unfiltered version emitted Orphanet 583 (MPS VI), MeSH D009085
        (MPS IV) and ORDO 217085 (MPS II severe) side by side under one
        disease name. Non-matching hits stay visible in `per_source` -- they
        are just not promoted to identifiers.
        """
        profile: Dict[str, Any] = {"disease": disease, "identifiers": {}}

        orphanet = sections.get("orphanet", {})
        if orphanet.get("orpha_code") and orphanet.get("match") == "exact":
            profile["identifiers"]["orphanet"] = orphanet["orpha_code"]
        if orphanet.get("prevalence"):
            profile["prevalence"] = orphanet["prevalence"]
        if orphanet.get("inheritance"):
            profile["inheritance"] = orphanet["inheritance"]

        omim = sections.get("omim", {})
        if omim.get("entries"):
            mim = omim["entries"][0].get("mim_number", "")
            if mim:
                profile["identifiers"]["omim"] = mim

        ot = sections.get("opentargets", {})
        if ot.get("efo_id") and _labels_match(disease, ot.get("name", "")):
            profile["identifiers"]["efo"] = ot["efo_id"]
        if ot.get("description"):
            profile["description"] = ot["description"]

        ols = sections.get("ols", {})
        if ols.get("terms"):
            for term in ols["terms"]:
                ont = term.get("ontology", "").lower()
                if (
                    ont
                    and term.get("id")
                    and _labels_match(disease, term.get("label", ""))
                ):
                    profile["identifiers"][ont] = term["id"]

        disgenet = sections.get("disgenet", {})
        if disgenet.get("associated_genes"):
            profile["top_genes"] = [
                g["gene"] for g in disgenet["associated_genes"][:10]
            ]

        return profile
