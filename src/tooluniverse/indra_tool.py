"""
INDRA DB API tool for ToolUniverse.

INDRA (Integrated Network and Dynamical Reasoning Assembler) provides
literature-mined biological statements about molecular interactions,
regulatory relationships, and modifications extracted from PubMed articles.

API: https://db.indra.bio
No authentication required.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

INDRA_DB_URL = "https://db.indra.bio"


@register_tool("INDRADBTool")
class INDRADBTool(BaseTool):
    """
    Tool for querying the INDRA Database of biological statements.

    Provides literature-mined statements about:
    - Activation / Inhibition relationships
    - Phosphorylation and other modifications
    - Complex formation
    - Increase/Decrease Amount
    Each statement includes evidence with source text and PubMed IDs.
    """

    # Valid INDRA statement types
    STATEMENT_TYPES = [
        "Activation",
        "Inhibition",
        "Phosphorylation",
        "Dephosphorylation",
        "Ubiquitination",
        "Deubiquitination",
        "Acetylation",
        "Deacetylation",
        "IncreaseAmount",
        "DecreaseAmount",
        "Complex",
        "Translocation",
        "Autophosphorylation",
    ]

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 60)
        self.parameter = tool_config.get("parameter", {})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute INDRA DB API call based on operation type."""
        operation = arguments.get("operation", "")
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "get_statements":
            return self._get_statements(arguments)
        elif operation == "get_evidence_count":
            return self._get_evidence_count(arguments)
        elif operation == "get_statement_by_hash":
            return self._get_statement_by_hash(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: get_statements, get_evidence_count, get_statement_by_hash",
            }

    def _get_statements(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get biological statements for an agent (gene/protein/chemical)."""
        agent = arguments.get("agent", "")
        if not agent:
            return {
                "status": "error",
                "error": "Parameter 'agent' is required (e.g., 'TP53', 'EGFR', 'gefitinib')",
            }
        params: Dict[str, Any] = {
            "agent": agent,
            "format": "json",
            "ev_limit": arguments.get("ev_limit", 2),
            "limit": arguments.get("limit", 10),
        }
        stmt_type = arguments.get("type")
        if stmt_type:
            if stmt_type not in self.STATEMENT_TYPES:
                return {
                    "status": "error",
                    "error": f"Invalid type '{stmt_type}'. Valid types: {', '.join(self.STATEMENT_TYPES)}",
                }
            params["type"] = stmt_type

        agent2 = arguments.get("agent2")
        if agent2:
            params["agent1"] = agent2

        try:
            url = f"{INDRA_DB_URL}/statements/from_agents"
            resp = requests.get(url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HTTP {resp.status_code} from INDRA DB",
                }
            data = resp.json()
            statements = data.get("statements", {})
            results: List[Dict[str, Any]] = []
            for hash_key, stmt in statements.items():
                entry: Dict[str, Any] = {
                    "hash": hash_key,
                    "type": stmt.get("type", ""),
                }
                if stmt.get("subj"):
                    entry["subject"] = stmt["subj"].get("name", "")
                if stmt.get("obj"):
                    entry["object"] = stmt["obj"].get("name", "")
                if stmt.get("members"):
                    entry["members"] = [m.get("name", "") for m in stmt["members"] if m]
                evidence_list = stmt.get("evidence", [])
                entry["evidence_shown"] = len(evidence_list)
                entry["evidence"] = []
                for ev in evidence_list:
                    entry["evidence"].append(
                        {
                            "pmid": ev.get("pmid"),
                            "source": ev.get("source_api", ""),
                            "text": (ev.get("text", "") or "")[:300],
                        }
                    )
                results.append(entry)
            return {
                "status": "success",
                "data": {
                    "agent": agent,
                    "type_filter": stmt_type,
                    "statements": results,
                    "statements_returned": data.get("statements_returned", 0),
                    "total_evidence": data.get("total_evidence", 0),
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_evidence_count(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get total evidence count for an agent without fetching full statements."""
        agent = arguments.get("agent", "")
        if not agent:
            return {
                "status": "error",
                "error": "Parameter 'agent' is required",
            }
        try:
            params: Dict[str, Any] = {
                "agent": agent,
                "format": "json",
                "ev_limit": 0,
                "limit": 1,
            }
            stmt_type = arguments.get("type")
            if stmt_type:
                params["type"] = stmt_type
            url = f"{INDRA_DB_URL}/statements/from_agents"
            resp = requests.get(url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HTTP {resp.status_code} from INDRA DB",
                }
            data = resp.json()
            return {
                "status": "success",
                "data": {
                    "agent": agent,
                    "type_filter": stmt_type,
                    "total_evidence": data.get("total_evidence", 0),
                    "statements_returned": data.get("statements_returned", 0),
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_statement_by_hash(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific statement by its hash with full evidence."""
        stmt_hash = arguments.get("hash", "")
        if not stmt_hash:
            return {
                "status": "error",
                "error": "Parameter 'hash' is required (statement hash from get_statements results)",
            }
        try:
            ev_limit = arguments.get("ev_limit", 10)
            url = f"{INDRA_DB_URL}/statements/from_hash/{stmt_hash}"
            resp = requests.get(
                url,
                params={"format": "json", "ev_limit": ev_limit},
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HTTP {resp.status_code}: Statement hash {stmt_hash} not found",
                }
            data = resp.json()
            statements = data.get("statements", {})
            if not statements:
                return {
                    "status": "error",
                    "error": f"No statement found for hash {stmt_hash}",
                }
            stmt = list(statements.values())[0]
            result: Dict[str, Any] = {
                "hash": stmt_hash,
                "type": stmt.get("type", ""),
                "total_evidence": data.get("total_evidence", 0),
            }
            if stmt.get("subj"):
                result["subject"] = stmt["subj"]
            if stmt.get("obj"):
                result["object"] = stmt["obj"]
            if stmt.get("members"):
                result["members"] = stmt["members"]
            evidence_list = stmt.get("evidence", [])
            result["evidence"] = []
            for ev in evidence_list:
                result["evidence"].append(
                    {
                        "pmid": ev.get("pmid"),
                        "source": ev.get("source_api", ""),
                        "text": ev.get("text", ""),
                        "annotations": ev.get("annotations", {}),
                    }
                )
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}
