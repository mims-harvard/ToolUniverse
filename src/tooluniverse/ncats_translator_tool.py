# ncats_translator_tool.py
"""
NCATS Biomedical Data Translator tool for ToolUniverse.

Translator is a federated knowledge-graph reasoning system spanning roughly
fifteen knowledge providers (SemMedDB, DrugCentral, CTD, Reactome, and more)
behind a shared Biolink Model and TRAPI query protocol. It answers one-hop
questions like "what chemicals treat this disease" or "what genes are
associated with this condition" by aggregating structured knowledge and
literature co-occurrence across all of them in a single query.

ToolUniverse already wraps most of the individual sources Translator draws
on (CTD, Monarch, Reactome) but has no way to ask a cross-source reasoning
question in one call. This tool queries Aragorn, one of Translator's TRAPI
reasoners, directly rather than through the Autonomous Relay System (ARS)
that fans a query out to all reasoners: the ARS is asynchronous and a full
aggregation can take several minutes, while Aragorn alone answers common
one-hop queries in seconds to tens of seconds.

APIs: https://aragorn.transltr.io/aragorn/query
      https://name-resolution-sri.renci.org/lookup
No authentication required.
"""

from typing import Dict, Any, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

ARAGORN_URL = "https://aragorn.transltr.io/aragorn/query"
NAME_RESOLUTION_URL = "https://name-resolution-sri.renci.org/lookup"


def _biolink(value: str) -> str:
    """Add the biolink: prefix if the caller left it off."""
    value = value.strip()
    return value if value.startswith("biolink:") else f"biolink:{value}"


def _primary_source(edge: Dict[str, Any]) -> Optional[str]:
    """Return the primary_knowledge_source infores id for one KG edge."""
    for source in edge.get("sources") or []:
        if source.get("resource_role") == "primary_knowledge_source":
            return source.get("resource_id")
    return None


def _publication_count(edge: Dict[str, Any]) -> int:
    """Count publications backing one KG edge, if any are attached."""
    for attribute in edge.get("attributes") or []:
        if attribute.get("attribute_type_id") == "biolink:publications":
            value = attribute.get("value")
            return len(value) if isinstance(value, list) else 0
    return 0


@register_tool("NCATSTranslatorTool")
class NCATSTranslatorTool(BaseTool):
    """
    Tool for querying the NCATS Biomedical Data Translator.

    Supports resolving free-text names to Translator-normalized identifiers,
    and one-hop biolink association queries (e.g. drugs that treat a
    disease, genes associated with a condition) via the Aragorn reasoner.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 90)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "query_associations"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Translator lookup."""
        try:
            if self.operation == "resolve_entity":
                return self._resolve_entity(arguments)
            if self.operation == "query_associations":
                return self._query_associations(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Translator request timed out after {self.timeout}s. "
                "One-hop queries with common categories can take 30s or more; "
                "narrowing the predicate or category can help.",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to NCATS Translator. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"Translator returned HTTP {code}"}
        except ValueError:
            return {
                "status": "error",
                "error": "Translator returned a non-JSON response",
            }
        except Exception as e:
            return {"status": "error", "error": f"Error querying Translator: {str(e)}"}

    def _resolve_entity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a free-text name to Translator-normalized identifiers."""
        name = (arguments.get("name") or "").strip()
        if not name:
            return {
                "status": "error",
                "error": "name is required: free text such as 'Alzheimer disease' "
                "or 'aspirin'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 10
        limit = min(limit, 20)

        response = requests.get(
            NAME_RESOLUTION_URL,
            params={"string": name, "limit": limit},
            timeout=self.timeout,
        )
        response.raise_for_status()
        matches = response.json() or []

        biolink_type = arguments.get("biolink_type")
        if biolink_type:
            wanted = _biolink(biolink_type)
            matches = [m for m in matches if wanted in (m.get("types") or [])]

        rows = [
            {
                "curie": m.get("curie"),
                "label": m.get("label"),
                "categories": (m.get("types") or [])[:6],
                "taxa": m.get("taxa") or [],
                "score": m.get("score"),
                "synonym_count": len(m.get("synonyms") or []),
                "example_synonyms": (m.get("synonyms") or [])[:5],
            }
            for m in matches
        ]

        if not rows:
            return {
                "status": "error",
                "error": f"No Translator-normalized identifier found for '{name}'"
                + (f" of type '{_biolink(biolink_type)}'" if biolink_type else "")
                + ".",
            }

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "name": name,
                "returned": len(rows),
                "note": "curie is the normalized identifier to use as entity_id "
                "in NCATSTranslator_query_associations.",
                "source": "SRI Name Resolution (NCATS Translator)",
            },
        }

    def _query_associations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run a one-hop biolink association query via Aragorn."""
        entity_id = (arguments.get("entity_id") or "").strip()
        target_category = (arguments.get("target_category") or "").strip()
        predicate = (arguments.get("predicate") or "").strip()
        if not entity_id or not target_category or not predicate:
            return {
                "status": "error",
                "error": "entity_id, target_category, and predicate are all "
                "required. Example: entity_id='MONDO:0004975' (Alzheimer "
                "disease), target_category='ChemicalEntity', "
                "predicate='treats'. Use NCATSTranslator_resolve_entity to "
                "find entity_id from a free-text name.",
            }

        target_role = (arguments.get("target_role") or "subject").strip().lower()
        if target_role not in ("subject", "object"):
            return {
                "status": "error",
                "error": "target_role must be 'subject' or 'object'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        target_category = _biolink(target_category)
        predicate = _biolink(predicate)

        edge = (
            {"subject": "n1", "object": "n0"}
            if target_role == "subject"
            else {"subject": "n0", "object": "n1"}
        )
        edge["predicates"] = [predicate]

        query_graph = {
            "nodes": {
                "n0": {"ids": [entity_id]},
                "n1": {"categories": [target_category]},
            },
            "edges": {"e0": edge},
        }

        response = requests.post(
            ARAGORN_URL,
            json={"message": {"query_graph": query_graph}},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        message = payload.get("message") or {}
        results = message.get("results") or []
        kg_nodes = (message.get("knowledge_graph") or {}).get("nodes") or {}
        kg_edges = (message.get("knowledge_graph") or {}).get("edges") or {}

        rows = []
        for result in results:
            bindings = result.get("node_bindings", {}).get("n1") or []
            if not bindings:
                continue
            target_id = bindings[0].get("id")
            node = kg_nodes.get(target_id, {})

            analyses = result.get("analyses") or []
            score = max((a.get("score") or 0.0) for a in analyses) if analyses else None

            sources = set()
            publications = 0
            for analysis in analyses:
                for edge_ids in (analysis.get("edge_bindings") or {}).values():
                    for edge_binding in edge_ids:
                        kg_edge = kg_edges.get(edge_binding.get("id"), {})
                        primary = _primary_source(kg_edge)
                        if primary:
                            sources.add(primary)
                        publications += _publication_count(kg_edge)

            rows.append(
                {
                    "id": target_id,
                    "name": node.get("name"),
                    "categories": node.get("categories") or [],
                    "score": score,
                    "knowledge_sources": sorted(sources),
                    "publication_count": publications,
                }
            )

        rows.sort(key=lambda r: r["score"] or 0.0, reverse=True)
        rows = rows[:limit]

        if not rows:
            warnings = [
                log.get("message")
                for log in payload.get("logs") or []
                if log.get("level") == "WARNING"
            ]
            hint = f" Reasoner said: {warnings[0]}" if warnings else ""
            return {
                "status": "error",
                "error": f"No '{predicate}' relationships found between "
                f"'{entity_id}' and '{target_category}' entities.{hint} Check "
                "the predicate direction (target_role), or that entity_id is "
                "a Translator-normalized CURIE from NCATSTranslator_resolve_entity.",
            }

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "entity_id": entity_id,
                "target_category": target_category,
                "predicate": predicate,
                "target_role": target_role,
                "total_matches": len(results),
                "returned": len(rows),
                "note": "Aggregated across Translator knowledge providers via "
                "the Aragorn reasoner; knowledge_sources lists the primary "
                "infores id backing each association.",
                "source": "NCATS Biomedical Data Translator (Aragorn)",
            },
        }
