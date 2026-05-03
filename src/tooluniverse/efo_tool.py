from __future__ import annotations

from typing import Any, Dict, Optional
import urllib.parse

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("EFOTool")
class EFOTool(BaseTool):
    """
    Tool to lookup Experimental Factor Ontology (EFO) IDs for diseases via the
    EMBL-EBI OLS API.
    """

    def __init__(self, tool_config, base_url="https://www.ebi.ac.uk/ols4/api/search"):
        super().__init__(tool_config)
        self.base_url = base_url

    def run(self, arguments):
        disease = arguments.get("disease")
        rows = arguments.get("rows", 1)
        if not disease:
            return {"status": "error", "error": "`disease` parameter is required."}
        return self._search(disease, rows)

    def _search(self, disease, rows):
        params = {"ontology": "efo", "q": disease, "rows": rows}
        try:
            response = requests.get(self.base_url, params=params, timeout=20)
            response.raise_for_status()
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": "OLS API request failed.",
                "details": str(e),
            }

        data = response.json().get("response", {})
        docs = data.get("docs", [])
        if not docs:
            return None

        if rows == 1:
            doc = docs[0]
            return {"efo_id": doc.get("short_form"), "name": doc.get("label")}

        return [
            {"efo_id": doc.get("short_form"), "name": doc.get("label")} for doc in docs
        ]


@register_tool("OLSRESTTool")
class OLSRESTTool(BaseTool):
    """
    Generic tool for the EMBL-EBI OLS v4 REST API.

    This is a JSON-config driven tool. Each tool config supplies:
    - fields.kind: "search" | "term" | "children" | "ontology" | "ontologies"
    - fields.base_url: optional override (defaults to OLS4 API root)
    - fields.ontology_id: optional ontology scope (e.g., "efo")
    """

    DEFAULT_BASE_URL = "https://www.ebi.ac.uk/ols4/api"

    @staticmethod
    def _double_urlencode(value: str) -> str:
        # OLS term endpoints use the term IRI as a path segment and require
        # double URL-encoding to avoid routing issues with slashes.
        once = urllib.parse.quote(value, safe="")
        return urllib.parse.quote(once, safe="")

    @staticmethod
    def _obo_id_to_efo_iri(obo_id: str) -> str:
        # Common EFO IDs come as "EFO:0000400" from search results.
        # Convert to IRI used by term endpoints.
        if ":" in obo_id:
            prefix, num = obo_id.split(":", 1)
            if prefix.upper() == "EFO":
                return f"http://www.ebi.ac.uk/efo/EFO_{num}"
        return obo_id

    def _resolve_term_iri(
        self, *, iri: Optional[str] = None, obo_id: Optional[str] = None
    ) -> Optional[str]:
        if iri:
            return iri
        if obo_id:
            return self._obo_id_to_efo_iri(obo_id)
        return None

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        fields = self.tool_config.get("fields") or {}
        kind = fields.get("kind")
        base_url = fields.get("base_url") or self.DEFAULT_BASE_URL
        ontology_id = fields.get("ontology_id")
        timeout_s = fields.get("timeout", 20)

        try:
            if kind == "search":
                query = arguments.get("query")
                rows = arguments.get("rows", 10)
                if not query:
                    return {
                        "status": "error",
                        "error": "`query` parameter is required.",
                    }
                params: Dict[str, Any] = {"q": query, "rows": rows}
                if ontology_id:
                    params["ontology"] = ontology_id
                url = f"{base_url}/search"
                resp = request_with_retry(
                    requests, "GET", url, params=params, timeout=timeout_s
                )
                if not (200 <= resp.status_code < 300):
                    return {
                        "status": "error",
                        "url": resp.url,
                        "status_code": resp.status_code,
                        "error": "HTTP request failed",
                        "detail": resp.text[:2000],
                    }
                j = resp.json()
                docs = (j.get("response") or {}).get("docs") or []
                terms = [
                    {
                        "iri": d.get("iri"),
                        "obo_id": d.get("obo_id"),
                        "short_form": d.get("short_form"),
                        "label": d.get("label"),
                        "description": d.get("description"),
                        "ontology_name": d.get("ontology_name"),
                        "ontology_prefix": d.get("ontology_prefix"),
                        "type": d.get("type"),
                    }
                    for d in docs
                ]
                result = {
                    "status": "success",
                    "url": resp.url,
                    "count": len(terms),
                    "terms": terms,
                }
                return {"status": "success", "data": result}

            if kind in {"term", "children"}:
                if not ontology_id:
                    return {
                        "status": "error",
                        "error": "Tool misconfigured: missing fields.ontology_id",
                    }
                iri = self._resolve_term_iri(
                    iri=arguments.get("iri"), obo_id=arguments.get("obo_id")
                )
                if not iri:
                    return {
                        "status": "error",
                        "error": "Provide either `iri` or `obo_id`.",
                    }
                encoded = self._double_urlencode(iri)
                term_url = f"{base_url}/ontologies/{ontology_id}/terms/{encoded}"

                if kind == "term":
                    resp = request_with_retry(
                        requests, "GET", term_url, timeout=timeout_s
                    )
                    if not (200 <= resp.status_code < 300):
                        return {
                            "status": "error",
                            "url": resp.url,
                            "status_code": resp.status_code,
                            "error": "HTTP request failed",
                            "detail": resp.text[:2000],
                        }
                    t = resp.json()
                    term = {
                        "iri": t.get("iri"),
                        "obo_id": t.get("obo_id"),
                        "short_form": t.get("short_form"),
                        "label": t.get("label"),
                        "description": t.get("description"),
                        "synonyms": t.get("synonyms"),
                        "has_children": t.get("has_children"),
                        "is_obsolete": t.get("is_obsolete"),
                        "ontology_name": t.get("ontology_name"),
                        "ontology_prefix": t.get("ontology_prefix"),
                    }
                    result = {"status": "success", "url": resp.url, "term": term}
                    return {"status": "success", "data": result}

                # children
                size = arguments.get("size", 20)
                params = {"size": size}
                resp = request_with_retry(
                    requests,
                    "GET",
                    f"{term_url}/children",
                    params=params,
                    timeout=timeout_s,
                )
                if not (200 <= resp.status_code < 300):
                    return {
                        "status": "error",
                        "url": resp.url,
                        "status_code": resp.status_code,
                        "error": "HTTP request failed",
                        "detail": resp.text[:2000],
                    }
                j = resp.json()
                children = ((j.get("_embedded") or {}).get("terms")) or []
                out = [
                    {
                        "iri": c.get("iri"),
                        "obo_id": c.get("obo_id"),
                        "short_form": c.get("short_form"),
                        "label": c.get("label"),
                    }
                    for c in children
                ]
                result = {
                    "status": "success",
                    "url": resp.url,
                    "count": len(out),
                    "children": out,
                }
                return {"status": "success", "data": result}

            if kind == "ontology":
                if not ontology_id:
                    return {
                        "status": "error",
                        "error": "Tool misconfigured: missing fields.ontology_id",
                    }
                url = f"{base_url}/ontologies/{ontology_id}"
                resp = request_with_retry(requests, "GET", url, timeout=timeout_s)
                if not (200 <= resp.status_code < 300):
                    return {
                        "status": "error",
                        "url": resp.url,
                        "status_code": resp.status_code,
                        "error": "HTTP request failed",
                        "detail": resp.text[:2000],
                    }
                o = resp.json()
                ontology = {
                    "ontologyId": o.get("ontologyId"),
                    "version": o.get("version"),
                    "status": o.get("status"),
                    "numberOfTerms": o.get("numberOfTerms"),
                    "updated": o.get("updated"),
                    "title": (o.get("config") or {}).get("title"),
                    "description": (o.get("config") or {}).get("description"),
                    "homepage": (o.get("config") or {}).get("homepage"),
                }
                result = {"status": "success", "url": resp.url, "ontology": ontology}
                return {"status": "success", "data": result}

            if kind == "ontologies":
                size = arguments.get("size", 20)
                url = f"{base_url}/ontologies"
                resp = request_with_retry(
                    requests, "GET", url, params={"size": size}, timeout=timeout_s
                )
                if not (200 <= resp.status_code < 300):
                    return {
                        "status": "error",
                        "url": resp.url,
                        "status_code": resp.status_code,
                        "error": "HTTP request failed",
                        "detail": resp.text[:2000],
                    }
                j = resp.json()
                onts = ((j.get("_embedded") or {}).get("ontologies")) or []
                out = [
                    {
                        "ontologyId": o.get("ontologyId"),
                        "title": (o.get("config") or {}).get("title"),
                        "numberOfTerms": o.get("numberOfTerms"),
                        "status": o.get("status"),
                    }
                    for o in onts
                ]
                result = {
                    "status": "success",
                    "url": resp.url,
                    "count": len(out),
                    "ontologies": out,
                }
                return {"status": "success", "data": result}

            return {
                "status": "error",
                "error": "Tool misconfigured: unknown fields.kind",
                "detail": f"Unsupported kind={kind!r}",
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}
