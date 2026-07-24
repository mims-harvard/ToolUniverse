"""CTD (Comparative Toxicogenomics Database) tool — backed by the RENCI Automat
mirror of CTD's knowledge graph.

CTD's native batchQuery.go now requires an altcha proof-of-work CAPTCHA, so
direct programmatic access via that endpoint is blocked. This tool uses the
NIH-NCATS-Translator-funded mirror at https://automat.renci.org/ctd/ instead.
That mirror is **chemical-centric** (June-2024 snapshot, 26k nodes / 166k
edges, biolink-categorized predicates) — it covers chemical↔gene and
chemical↔disease cleanly, but does NOT contain CTD's gene-disease inferred
edges. Gene→disease queries return an honest error pointing at OpenTargets.
"""

import re
import requests
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

RENCI_BASE = "https://automat.renci.org/ctd"
RENCI_HEADERS = {"Accept": "application/json", "User-Agent": "ToolUniverse CTDTool"}
DATA_AS_OF = "2024-06"  # RENCI snapshot version

_MESH_ID_RE = re.compile(r"^[CD]\d{6,9}$")  # D=descriptor, C=supplementary concept
_CAS_RN_RE = re.compile(r"^\d{1,7}-\d{2}-\d$")
_ALL_DIGITS_RE = re.compile(r"^\d+$")

# Per input_type, the (pattern, CURIE prefix) pairs to try in order when the
# bare term looks like a well-known, unambiguous ID format.
_CURIE_RULES = {
    "chem": ((_MESH_ID_RE, "MESH"), (_CAS_RN_RE, "CAS")),
    "gene": ((_ALL_DIGITS_RE, "NCBIGene"),),
    "disease": ((_MESH_ID_RE, "MESH"),),
}


def _candidate_curies(term: str, input_type: str) -> List[str]:
    """Fix-R18C-2/4: CTD's own tool descriptions promise bare CAS RN, bare
    MeSH ID, and bare NCBI Gene ID as valid input_terms formats, but the
    RENCI mirror's equivalent_identifiers only ever store the CURIE-prefixed
    form -- confirmed live that "D000082" (bare MeSH ID) and "80-05-7" (bare
    CAS RN) both fail to resolve while "MESH:D000082" and "CAS:80-05-7"
    succeed, and likewise a bare NCBI Gene ID needs "NCBIGene:" prepended.
    When input_terms matches one of these well-known, unambiguous ID
    formats and isn't already a CURIE, try the correctly-prefixed form
    first; the original string is always tried too so a name/CURIE that
    already works keeps working.
    """
    if ":" in term:
        return [term]
    candidates = [
        f"{prefix}:{term}"
        for pattern, prefix in _CURIE_RULES.get(input_type, ())
        if pattern.match(term)
    ]
    candidates.append(term)
    return candidates


# Maps the existing tool configs' (input_type, report_type) to RENCI
# (source_category, target_category). The gene→disease entry is None
# because RENCI's CTD ingestion is chemical-centric (no gene-disease edges).
_TYPE_MAP = {
    ("chem", "genes_curated"): ("biolink:SmallMolecule", "biolink:Gene"),
    ("chem", "diseases_curated"): ("biolink:SmallMolecule", "biolink:Disease"),
    ("gene", "diseases_curated"): None,
    ("gene", "chems_curated"): ("biolink:Gene", "biolink:SmallMolecule"),
    ("disease", "chems_curated"): ("biolink:Disease", "biolink:SmallMolecule"),
}


@register_tool("CTDTool")
class CTDTool(BaseTool):
    """Query CTD curated relationships via the RENCI Automat mirror."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        fields = tool_config.get("fields") or {}
        self.input_type = fields.get("input_type", "chem")
        self.report_type = fields.get("report_type", "genes_curated")
        self.timeout = int(fields.get("timeout", 30))

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"RENCI CTD mirror timed out after {self.timeout}s",
                "metadata": {"backend": "RENCI Automat CTD", "data_as_of": DATA_AS_OF},
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to the RENCI CTD mirror. Check network.",
                "metadata": {"backend": "RENCI Automat CTD", "data_as_of": DATA_AS_OF},
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"RENCI CTD mirror HTTP error: {e.response.status_code}",
                "metadata": {"backend": "RENCI Automat CTD", "data_as_of": DATA_AS_OF},
            }
        except Exception as e:  # noqa: BLE001
            return {
                "status": "error",
                "error": f"Unexpected error querying RENCI CTD mirror: {e}",
                "metadata": {"backend": "RENCI Automat CTD", "data_as_of": DATA_AS_OF},
            }

    # -- internals -----------------------------------------------------------

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        input_terms = (
            arguments.get("input_terms")
            or arguments.get("query")
            or arguments.get("gene_symbol")
            or arguments.get("chemical_name")
            or arguments.get("disease_name")
            or ""
        ).strip()
        if not input_terms:
            return {"status": "error", "error": "input_terms parameter is required"}

        input_type = arguments.get("input_type", self.input_type)
        report_type = arguments.get("report_type", self.report_type)
        metadata = {
            "backend": "RENCI Automat CTD",
            "data_as_of": DATA_AS_OF,
            "input_terms": input_terms,
            "input_type": input_type,
            "report_type": report_type,
        }

        if (input_type, report_type) == ("gene", "diseases_curated"):
            return {
                "status": "error",
                "error": (
                    "Gene→disease relationships are not available in the RENCI CTD "
                    "mirror (chemical-centric snapshot, no gene-disease edges)."
                ),
                "suggestion": (
                    "Use OpenTargets_get_associated_diseases (live, more sources) "
                    "or DGIdb_search_interactions for gene-disease associations."
                ),
                "metadata": metadata,
            }

        mapping = _TYPE_MAP.get((input_type, report_type))
        if not mapping:
            return {
                "status": "error",
                "error": (
                    f"Unsupported query: input_type={input_type!r}, "
                    f"report_type={report_type!r}."
                ),
                "metadata": metadata,
            }
        source_cat, target_cat = mapping

        canonical = None
        for candidate in _candidate_curies(input_terms, input_type):
            canonical = self._resolve_curie(candidate)
            if canonical:
                break
        if not canonical:
            return {
                "status": "error",
                "error": (
                    f"'{input_terms}' was not found in the RENCI CTD mirror "
                    f"(searched by id, equivalent_identifiers, and name)."
                ),
                "metadata": metadata,
            }
        metadata["canonical_curie"] = canonical
        metadata["source_category"] = source_cat
        metadata["target_category"] = target_cat

        url = f"{RENCI_BASE}/{source_cat}/{target_cat}/{canonical}"
        resp = requests.get(url, headers=RENCI_HEADERS, timeout=self.timeout)
        resp.raise_for_status()
        raw_edges = resp.json()
        if not isinstance(raw_edges, list):
            return {
                "status": "error",
                "error": "RENCI CTD mirror returned unexpected (non-list) payload",
                "metadata": metadata,
            }
        formatted = [self._format_edge(e) for e in raw_edges]
        formatted = [e for e in formatted if e]
        metadata["total_results"] = len(formatted)
        return {"status": "success", "data": formatted, "metadata": metadata}

    def _resolve_curie(self, term: str) -> Optional[str]:
        """Resolve an input (name or any CURIE) to the graph's canonical id.

        Uses RENCI's /cypher endpoint to search by `id`, `equivalent_identifiers`,
        or case-insensitive `name`. Returns the canonical `id` or None. Callers
        should try candidates from `_candidate_curies()` in order -- this does
        a single lookup and does not itself retry with a CURIE prefix.
        """
        return self._cypher_lookup(term)

    def _cypher_lookup(self, term: str) -> Optional[str]:
        safe = term.replace('"', "").replace("\\", "")
        query = (
            'MATCH (n) WHERE n.id = "' + safe + '" OR "' + safe + '" IN '
            'n.equivalent_identifiers OR toLower(n.name) = toLower("' + safe + '") '
            "RETURN n.id AS id LIMIT 1"
        )
        resp = requests.post(
            f"{RENCI_BASE}/cypher",
            headers={"Content-Type": "application/json"},
            json={"query": query},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["results"][0]["data"][0]["row"][0]
        except (KeyError, IndexError, TypeError):
            return None

    @staticmethod
    def _format_edge(edge: Any) -> Optional[Dict[str, Any]]:
        """RENCI returns each edge as [source_node, edge_props, target_node]."""
        if not isinstance(edge, list) or len(edge) < 3:
            return None
        src, props, tgt = edge[0], edge[1], edge[2]
        s = src if isinstance(src, dict) else {}
        t = tgt if isinstance(tgt, dict) else {}
        p = props if isinstance(props, dict) else {}
        return {
            "source_id": s.get("id"),
            "source_name": s.get("name"),
            "target_id": t.get("id"),
            "target_name": t.get("name"),
            "predicate": p.get("predicate"),
            "qualified_predicate": p.get("qualified_predicate"),
            "object_direction_qualifier": p.get("object_direction_qualifier"),
            "knowledge_level": p.get("knowledge_level"),
            "agent_type": p.get("agent_type"),
            "primary_knowledge_source": p.get("primary_knowledge_source"),
        }
