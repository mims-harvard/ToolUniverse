"""
RxClass Tool

Drug classification tools using the NLM RxClass API (part of RxNav):
  - get_drug_classes:    Look up ATC/EPC/MoA/VA drug classes for a drug name or RXCUI
  - get_class_members:   List drugs that belong to a given class ID
  - find_classes:        Search for drug classes by name keyword
  - get_class_hierarchy: Traverse the ATC ancestor chain / class tree for a class
  - get_disease_relations: MED-RT drug<->disease relations (may_treat, may_prevent,
                         CI_with, induces, has_PE), forward (by drug) and reverse
                         (all drugs for a disease class)

API base: https://rxnav.nlm.nih.gov/REST/rxclass
No authentication required. Free public NLM API.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

RXCLASS_BASE = "https://rxnav.nlm.nih.gov/REST/rxclass"
RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"

# Supported relaSource values for byDrugName endpoint
RELA_SOURCES = {
    "ATC": "WHO Anatomical Therapeutic Chemical classification",
    "FDASPL": "FDA Pharmacologic Class (EPC, MoA, PE)",
    "MESH": "MeSH pharmacological actions",
    "VA": "VA Drug Classification",
    "DAILYMED": "DailyMed drug classification",
}


@register_tool("RxClassTool")
class RxClassTool(BaseTool):
    """
    Drug classification via NLM RxClass API.

    Operations:
      - get_drug_classes:    Get ATC, EPC, MoA, VA drug classes for a drug
      - get_class_members:   List drugs in a specified drug class
      - find_classes:        Search drug classes by keyword
      - get_class_hierarchy: Traverse the ATC ancestor chain for a class
      - get_disease_relations: MED-RT drug<->disease relations (forward + reverse)
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_drug_classes"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        op = self.operation
        if op == "get_drug_classes":
            return self._get_drug_classes(arguments)
        if op == "get_class_members":
            return self._get_class_members(arguments)
        if op == "find_classes":
            return self._find_classes(arguments)
        if op == "get_class_hierarchy":
            return self._get_class_hierarchy(arguments)
        if op == "get_disease_relations":
            return self._get_disease_relations(arguments)
        return {"status": "error", "error": f"Unknown operation: {op}"}

    # ------------------------------------------------------------------
    # shared HTTP helper
    # ------------------------------------------------------------------

    def _api_get(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Shared HTTP GET with consistent RxClass error handling."""
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return {"ok": True, "data": resp.json()}
        except requests.exceptions.Timeout:
            return {"ok": False, "error": "RxClass API timeout", "retryable": True}
        except requests.exceptions.HTTPError as e:
            sc = e.response.status_code
            return {
                "ok": False,
                "error": f"RxClass HTTP {sc}",
                "retryable": sc in (408, 429, 500, 502, 503, 504),
            }
        except ValueError:
            ct = resp.headers.get("content-type", "")
            return {
                "ok": False,
                "error": "RxClass returned non-JSON response",
                "content_type": ct,
                "response_snippet": resp.text[:200],
                "retryable": "text/html" in ct or resp.text.lstrip().startswith("<"),
                "suggestion": "RxClass may be under maintenance. Retry in a few minutes.",
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "retryable": False}

    # ------------------------------------------------------------------
    # operation: get_drug_classes
    # ------------------------------------------------------------------

    def _get_drug_classes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        drug_name = arguments.get("drug_name") or arguments.get("name")
        rxcui = arguments.get("rxcui")
        rela_source = arguments.get("rela_source", "ATC")
        limit = arguments.get("limit", 20)

        if not drug_name and not rxcui:
            return {"status": "error", "error": "Provide 'drug_name' or 'rxcui'."}

        if rela_source not in RELA_SOURCES and rela_source != "ALL":
            rela_source = "ATC"

        try:
            if rxcui:
                url = f"{RXCLASS_BASE}/class/byRxcui.json"
                params: Dict[str, Any] = {"rxcui": str(rxcui).strip()}
                if rela_source != "ALL":
                    params["relaSource"] = rela_source
            else:
                url = f"{RXCLASS_BASE}/class/byDrugName.json"
                params = {"drugName": drug_name.strip()}
                if rela_source != "ALL":
                    params["relaSource"] = rela_source

            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "RxClass API timeout",
                "retryable": True,
            }
        except requests.exceptions.HTTPError as e:
            sc = e.response.status_code
            return {
                "status": "error",
                "error": f"RxClass HTTP {sc}",
                "retryable": sc in (408, 429, 500, 502, 503, 504),
            }
        except ValueError:
            ct = resp.headers.get("content-type", "")
            return {
                "status": "error",
                "error": "RxClass returned non-JSON response",
                "content_type": ct,
                "response_snippet": resp.text[:200],
                "retryable": "text/html" in ct or resp.text.lstrip().startswith("<"),
                "suggestion": "RxClass may be under maintenance. Retry in a few minutes.",
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "retryable": False}

        items = data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
        if not items:
            query_str = rxcui if rxcui else drug_name
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "query": query_str,
                    "rela_source": rela_source,
                    "count": 0,
                    "note": f"No drug classes found for '{query_str}' in source '{rela_source}'. Try rela_source='ALL' or a different source.",
                },
            }

        classes = []
        seen = set()
        for item in items:
            mc = item.get("rxclassMinConceptItem", {})
            drug_mc = item.get("minConcept", {})
            class_id = mc.get("classId", "")
            class_key = (class_id, drug_mc.get("rxcui", ""))
            if class_key in seen:
                continue
            seen.add(class_key)
            classes.append(
                {
                    "classId": class_id,
                    "className": mc.get("className", ""),
                    "classType": mc.get("classType", ""),
                    "rxcui": drug_mc.get("rxcui", ""),
                    "drugName": drug_mc.get("name", ""),
                    "tty": drug_mc.get("tty", ""),
                    "rela": item.get("rela", ""),
                    "relaSource": item.get("relaSource", rela_source),
                }
            )

        classes = classes[:limit]

        return {
            "status": "success",
            "data": classes,
            "metadata": {
                "query": rxcui if rxcui else drug_name,
                "rela_source": rela_source,
                "count": len(classes),
                "available_sources": list(RELA_SOURCES.keys()),
            },
        }

    # ------------------------------------------------------------------
    # operation: get_class_members
    # ------------------------------------------------------------------

    def _get_class_members(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        class_id = arguments.get("class_id") or arguments.get("classId")
        rela_source = arguments.get("rela_source", "ATC")
        ttys = arguments.get("ttys", "IN")
        limit = arguments.get("limit", 50)

        if not class_id:
            return {
                "status": "error",
                "error": "Provide 'class_id' (e.g., 'M01AE', 'N02BA').",
            }

        try:
            url = f"{RXCLASS_BASE}/classMembers.json"
            params: Dict[str, Any] = {
                "classId": str(class_id).strip(),
                "relaSource": rela_source,
                "ttys": ttys,
            }
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "RxClass API timeout",
                "retryable": True,
            }
        except requests.exceptions.HTTPError as e:
            sc = e.response.status_code
            return {
                "status": "error",
                "error": f"RxClass HTTP {sc}",
                "retryable": sc in (408, 429, 500, 502, 503, 504),
            }
        except ValueError:
            ct = resp.headers.get("content-type", "")
            return {
                "status": "error",
                "error": "RxClass returned non-JSON response",
                "content_type": ct,
                "response_snippet": resp.text[:200],
                "retryable": "text/html" in ct or resp.text.lstrip().startswith("<"),
                "suggestion": "RxClass may be under maintenance. Retry in a few minutes.",
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "retryable": False}

        members = data.get("drugMemberGroup", {}).get("drugMember", [])
        if not members:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "class_id": class_id,
                    "rela_source": rela_source,
                    "count": 0,
                    "note": f"No drug members found for class '{class_id}'. Verify class ID and rela_source.",
                },
            }

        drugs = []
        for m in members[:limit]:
            mc = m.get("minConcept", {})
            drugs.append(
                {
                    "rxcui": mc.get("rxcui", ""),
                    "name": mc.get("name", ""),
                    "tty": mc.get("tty", ""),
                }
            )

        return {
            "status": "success",
            "data": drugs,
            "metadata": {
                "class_id": class_id,
                "rela_source": rela_source,
                "ttys": ttys,
                "count": len(drugs),
            },
        }

    # ------------------------------------------------------------------
    # operation: find_classes
    # ------------------------------------------------------------------

    def _find_classes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query") or arguments.get("keyword")
        class_type = arguments.get("class_type", "")
        limit = arguments.get("limit", 20)

        if not query:
            return {
                "status": "error",
                "error": "Provide 'query' keyword to search drug classes.",
            }

        # classSearch.json is not available in current RxClass API version.
        # Use allClasses.json and filter client-side by class name keyword.
        params: Dict[str, Any] = {}
        if class_type:
            params["classTypes"] = class_type
        try:
            resp = requests.get(
                f"{RXCLASS_BASE}/allClasses.json", params=params, timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "RxClass API timeout",
                "retryable": True,
            }
        except requests.exceptions.HTTPError as e:
            sc = e.response.status_code
            return {
                "status": "error",
                "error": f"RxClass HTTP {sc}",
                "retryable": sc in (408, 429, 500, 502, 503, 504),
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "retryable": False}

        all_classes = data.get("rxclassMinConceptList", {}).get("rxclassMinConcept", [])
        kw = query.strip().lower()
        matches = [
            {
                "classId": c.get("classId", ""),
                "className": c.get("className", ""),
                "classType": c.get("classType", ""),
            }
            for c in all_classes
            if kw in c.get("className", "").lower()
        ][:limit]

        return {
            "status": "success",
            "data": matches,
            "metadata": {
                "query": query,
                "class_type": class_type or "all",
                "count": len(matches),
            },
        }

    # ------------------------------------------------------------------
    # operation: get_class_hierarchy
    # ------------------------------------------------------------------

    def _get_class_hierarchy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Return the ancestor chain / class tree for a class via classGraph."""
        class_id = arguments.get("class_id") or arguments.get("classId")
        source = arguments.get("source", "")
        if not class_id:
            return {
                "status": "error",
                "error": "Provide 'class_id' (e.g., 'N02BA' for salicylic acid derivatives).",
            }

        params: Dict[str, Any] = {"classId": str(class_id).strip()}
        if source:
            params["source"] = str(source).strip()

        result = self._api_get(f"{RXCLASS_BASE}/classGraph.json", params)
        if not result["ok"]:
            result.pop("ok", None)
            return {"status": "error", **result}

        graph = result["data"].get("rxclassGraph", {}) or {}
        raw_nodes = graph.get("rxclassMinConceptItem", []) or []
        raw_edges = graph.get("rxclassEdge", []) or []

        if not raw_nodes:
            return {
                "status": "success",
                "data": {"nodes": [], "edges": [], "ancestor_path": []},
                "metadata": {
                    "class_id": class_id,
                    "node_count": 0,
                    "edge_count": 0,
                    "note": f"No class hierarchy found for class '{class_id}'. Verify the class ID.",
                },
            }

        nodes = [
            {
                "classId": n.get("classId", ""),
                "className": n.get("className", ""),
                "classType": n.get("classType", ""),
            }
            for n in raw_nodes
        ]
        edges = [
            {
                "child": e.get("classId1", ""),
                "rela": e.get("rela", ""),
                "parent": e.get("classId2", ""),
            }
            for e in raw_edges
        ]

        # Build an ordered ancestor path from the requested leaf up to the root
        # by following parent links from each child.
        parent_of = {e["child"]: e["parent"] for e in edges}
        name_of = {n["classId"]: n["className"] for n in nodes}
        type_of = {n["classId"]: n["classType"] for n in nodes}
        ancestor_path = []
        current = str(class_id).strip()
        visited = set()
        while current and current not in visited:
            visited.add(current)
            ancestor_path.append(
                {
                    "classId": current,
                    "className": name_of.get(current, ""),
                    "classType": type_of.get(current, ""),
                }
            )
            current = parent_of.get(current)

        return {
            "status": "success",
            "data": {
                "nodes": nodes,
                "edges": edges,
                "ancestor_path": ancestor_path,
            },
            "metadata": {
                "class_id": class_id,
                "source": source or None,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "depth": len(ancestor_path),
            },
        }

    # ------------------------------------------------------------------
    # operation: get_disease_relations
    # ------------------------------------------------------------------

    def _get_disease_relations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """MED-RT drug<->disease relations (may_treat, may_prevent, CI_with, ...).

        Two directions:
          * forward (drug_name or rxcui given): which disease classes a drug relates
            to under MED-RT (via class/byDrugName or class/byRxcui).
          * reverse (class_id given): which ingredient drugs relate to a disease
            class (via classMembers with relaSource=MEDRT).
        """
        drug_name = arguments.get("drug_name") or arguments.get("name")
        rxcui = arguments.get("rxcui")
        class_id = arguments.get("class_id") or arguments.get("classId")
        rela = arguments.get("rela") or arguments.get("relas")
        ttys = arguments.get("ttys", "IN")

        if not (drug_name or rxcui or class_id):
            return {
                "status": "error",
                "error": "Provide 'drug_name'/'rxcui' (forward) or 'class_id' (reverse disease-class lookup).",
            }

        # Reverse: all drugs for a disease class
        if class_id and not (drug_name or rxcui):
            params: Dict[str, Any] = {
                "classId": str(class_id).strip(),
                "relaSource": "MEDRT",
                "ttys": ttys,
            }
            if rela:
                params["rela"] = str(rela).strip()
            result = self._api_get(f"{RXCLASS_BASE}/classMembers.json", params)
            if not result["ok"]:
                result.pop("ok", None)
                return {"status": "error", **result}

            members = (
                result["data"].get("drugMemberGroup", {}).get("drugMember", []) or []
            )
            drugs = []
            for m in members:
                mc = m.get("minConcept", {}) or {}
                drugs.append(
                    {
                        "rxcui": mc.get("rxcui", ""),
                        "name": mc.get("name", ""),
                        "tty": mc.get("tty", ""),
                        "rela": m.get("rela", "") or (rela or ""),
                    }
                )
            return {
                "status": "success",
                "data": drugs,
                "metadata": {
                    "direction": "reverse",
                    "class_id": class_id,
                    "rela_source": "MEDRT",
                    "rela": rela or None,
                    "ttys": ttys,
                    "count": len(drugs),
                },
            }

        # Forward: which disease classes a drug relates to
        if rxcui:
            url = f"{RXCLASS_BASE}/class/byRxcui.json"
            params = {"rxcui": str(rxcui).strip(), "relaSource": "MEDRT"}
            query_label = str(rxcui).strip()
        else:
            url = f"{RXCLASS_BASE}/class/byDrugName.json"
            params = {"drugName": drug_name.strip(), "relaSource": "MEDRT"}
            query_label = drug_name.strip()
        if rela:
            params["relas"] = str(rela).strip()

        result = self._api_get(url, params)
        if not result["ok"]:
            result.pop("ok", None)
            return {"status": "error", **result}

        items = (
            result["data"].get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
            or []
        )
        relations = []
        seen = set()
        for it in items:
            mc = it.get("rxclassMinConceptItem", {}) or {}
            dmc = it.get("minConcept", {}) or {}
            key = (mc.get("classId", ""), it.get("rela", ""), dmc.get("rxcui", ""))
            if key in seen:
                continue
            seen.add(key)
            relations.append(
                {
                    "classId": mc.get("classId", ""),
                    "className": mc.get("className", ""),
                    "classType": mc.get("classType", ""),
                    "rela": it.get("rela", ""),
                    "rxcui": dmc.get("rxcui", ""),
                    "drugName": dmc.get("name", ""),
                }
            )

        return {
            "status": "success",
            "data": relations,
            "metadata": {
                "direction": "forward",
                "query": query_label,
                "rela_source": "MEDRT",
                "rela": rela or None,
                "count": len(relations),
            },
        }
