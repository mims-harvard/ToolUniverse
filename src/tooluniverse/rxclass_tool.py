"""
RxClass Tool

Drug classification tools using the NLM RxClass API (part of RxNav):
  - get_drug_classes:   Look up ATC/EPC/MoA/VA drug classes for a drug name or RXCUI
  - get_class_members:  List drugs that belong to a given class ID
  - find_classes:       Search for drug classes by name keyword

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
      - get_drug_classes:  Get ATC, EPC, MoA, VA drug classes for a drug
      - get_class_members: List drugs in a specified drug class
      - find_classes:      Search drug classes by keyword
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
        return {"status": "error", "error": f"Unknown operation: {op}"}

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
