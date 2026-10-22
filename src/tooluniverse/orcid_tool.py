"""
ORCID Researcher Identity Tool

Provides access to the ORCID Public API v3.0 for querying researcher profiles,
publications, affiliations, and employment information.

API: https://pub.orcid.org/v3.0/
No authentication required for public data. Respects 24 req/s rate limit.
"""

import re
from typing import Dict, Any, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

ORCID_BASE_URL = "https://pub.orcid.org/v3.0"
ORCID_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "ToolUniverse/1.0 (research tool)",
}


@register_tool("ORCIDTool")
class ORCIDTool(BaseTool):
    """
    Tool for querying the ORCID Public API.

    Provides access to:
    - Researcher profiles and biographical data
    - Publication works
    - Search across all ORCID records
    - Employment and affiliation history
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "get_profile": self._get_profile,
            "get_works": self._get_works,
            "search_researchers": self._search_researchers,
            "get_employments": self._get_employments,
            "get_fundings": self._get_fundings,
            "get_peer_reviews": self._get_peer_reviews,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "ORCID API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to ORCID API"}
        except Exception as e:
            return {"status": "error", "error": f"Operation failed: {str(e)}"}

    def _make_request(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{ORCID_BASE_URL}/{path}"
        response = requests.get(
            url, headers=ORCID_HEADERS, params=params or {}, timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if not isinstance(data, dict):
                return {"ok": False, "error": "ORCID returned malformed JSON"}
            return {"ok": True, "data": data}
        elif response.status_code == 404:
            return {"ok": False, "error": "ORCID record not found", "detail": path}
        else:
            return {
                "ok": False,
                "error": f"API request failed with status {response.status_code}",
                "detail": response.text[:500],
            }

    @staticmethod
    def _valid_orcid(value: Any) -> tuple[str | None, str | None]:
        if not isinstance(value, str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9Xx]", value.strip()
        ):
            return None, "orcid must have format XXXX-XXXX-XXXX-XXXX"
        canonical = value.strip().upper()
        digits = canonical.replace("-", "")
        total = 0
        for char in digits[:15]:
            total = (total + int(char)) * 2
        checksum = (12 - (total % 11)) % 11
        expected = "X" if checksum == 10 else str(checksum)
        if digits[-1] != expected:
            return None, "orcid checksum is invalid"
        return canonical, None

    @staticmethod
    def _list(value: Any, field: str) -> list:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"ORCID returned malformed {field}")
        return value

    def _orcid_argument(
        self, arguments: Dict[str, Any]
    ) -> tuple[str | None, Dict | None]:
        orcid, error = self._valid_orcid(arguments.get("orcid"))
        if error:
            return None, {"status": "error", "error": error}
        return orcid, None

    def _get_profile(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        orcid, error = self._orcid_argument(arguments)
        if error:
            return error
        assert orcid is not None

        result = self._make_request(f"{orcid}/record")
        if not result["ok"]:
            return {
                "status": "error",
                "error": result["error"],
                "detail": result.get("detail", ""),
            }

        data = result["data"]
        person = data.get("person", {})
        activities = data.get("activities-summary", {})
        if not isinstance(person, dict) or not isinstance(activities, dict):
            return {"status": "error", "error": "ORCID returned a malformed record"}
        work_groups = self._list(
            (activities.get("works") or {}).get("group"), "works.group"
        )
        employment_groups = self._list(
            (activities.get("employments") or {}).get("affiliation-group"),
            "employments.affiliation-group",
        )
        works_summary_count = sum(
            len(self._list(group.get("work-summary"), "work-summary"))
            for group in work_groups
            if isinstance(group, dict)
        )
        employment_summary_count = sum(
            len(self._list(group.get("summaries"), "employment summaries"))
            for group in employment_groups
            if isinstance(group, dict)
        )

        return {
            "status": "success",
            "data": {
                "orcid": orcid,
                "name": person.get("name", {}),
                "biography": person.get("biography", {}),
                "emails": person.get("emails", {}),
                "keywords": person.get("keywords", {}),
                "urls": person.get("researcher-urls", {}),
                "external_identifiers": person.get("external-identifiers", {}),
                "other_names": person.get("other-names", {}),
                "addresses": person.get("addresses", {}),
                "person": person,
                "activities_summary": activities,
                "works_count": len(work_groups),
                "works_group_count": len(work_groups),
                "works_summary_count": works_summary_count,
                "employments_count": len(employment_groups),
                "employment_group_count": len(employment_groups),
                "employment_summary_count": employment_summary_count,
            },
            "metadata": {
                "requested_orcid": orcid,
                "source_record_complete": True,
                "legacy_count_semantics": "works_count and employments_count are group counts",
            },
        }

    def _get_works(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        orcid, error = self._orcid_argument(arguments)
        if error:
            return error
        assert orcid is not None

        result = self._make_request(f"{orcid}/works")
        if not result["ok"]:
            return {
                "status": "error",
                "error": result["error"],
                "detail": result.get("detail", ""),
            }

        data = result["data"]
        groups = self._list(data.get("group"), "works.group")

        works = []
        for group_index, group in enumerate(groups):
            if not isinstance(group, dict):
                raise ValueError("ORCID returned a malformed work group")
            summaries = self._list(group.get("work-summary"), "work-summary")
            for summary_index, s in enumerate(summaries):
                if not isinstance(s, dict):
                    raise ValueError("ORCID returned a malformed work summary")
                works.append(
                    {
                        "group_index": group_index,
                        "summary_index": summary_index,
                        "group_external_ids": group.get("external-ids", {}),
                        "put_code": s.get("put-code"),
                        "title": s.get("title", {}).get("title", {}).get("value"),
                        "type": s.get("type"),
                        "publication_date": s.get("publication-date"),
                        "journal_title": s.get("journal-title", {}).get("value")
                        if s.get("journal-title")
                        else None,
                        "external_ids": s.get("external-ids", {}).get(
                            "external-id", []
                        ),
                    }
                )

        return {
            "status": "success",
            "data": works,
            "num_works": len(works),
            "metadata": {
                "work_group_count": len(groups),
                "work_summary_count": len(works),
                "all_group_summaries_returned": True,
                "requested_orcid": orcid,
            },
        }

    def _search_researchers(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return {"status": "error", "error": "query must be a non-empty string"}
        query = query.strip()

        start = arguments.get("start", 0)
        rows = arguments.get("rows", 10)
        if isinstance(start, bool) or not isinstance(start, int) or start < 0:
            return {"status": "error", "error": "start must be a non-negative integer"}
        if isinstance(rows, bool) or not isinstance(rows, int) or not 1 <= rows <= 200:
            return {"status": "error", "error": "rows must be an integer from 1 to 200"}

        params = {"q": query, "start": start, "rows": rows}
        # expanded-search (vs. plain search) returns names/institutions inline,
        # so callers can disambiguate same-named candidates without a
        # separate get_profile call per result.
        result = self._make_request("expanded-search", params)
        if not result["ok"]:
            return {
                "status": "error",
                "error": result["error"],
                "detail": result.get("detail", ""),
            }

        data = result["data"]
        results = self._list(data.get("expanded-result"), "expanded-result")
        total_found = data.get("num-found")
        if (
            isinstance(total_found, bool)
            or not isinstance(total_found, int)
            or total_found < 0
        ):
            return {"status": "error", "error": "ORCID returned invalid search totals"}
        if len(results) > rows:
            return {
                "status": "error",
                "error": "ORCID returned more rows than requested",
            }

        researchers = []
        for r in results:
            if not isinstance(r, dict):
                return {
                    "status": "error",
                    "error": "ORCID returned a malformed search result",
                }
            returned_orcid, orcid_error = self._valid_orcid(r.get("orcid-id"))
            if orcid_error:
                return {
                    "status": "error",
                    "error": "ORCID search returned an invalid ORCID iD",
                }
            researchers.append(
                {
                    "orcid": returned_orcid,
                    "given_names": r.get("given-names"),
                    "family_names": r.get("family-names"),
                    "credit_name": r.get("credit-name"),
                    "other_names": r.get("other-name") or [],
                    "institutions": r.get("institution-name") or [],
                }
            )

        return {
            "status": "success",
            "data": researchers,
            "num_results": len(researchers),
            "total_found": total_found,
            "metadata": {
                "start": start,
                "rows": rows,
                "returned": len(researchers),
                "total_found": total_found,
                "has_more": start + len(researchers) < total_found,
                "next_start": start + len(researchers)
                if start + len(researchers) < total_found and researchers
                else None,
                "page_complete": len(researchers)
                == min(rows, max(total_found - start, 0)),
            },
        }

    def _get_employments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        orcid, error = self._orcid_argument(arguments)
        if error:
            return error
        assert orcid is not None

        result = self._make_request(f"{orcid}/employments")
        if not result["ok"]:
            return {
                "status": "error",
                "error": result["error"],
                "detail": result.get("detail", ""),
            }

        data = result["data"]
        groups = self._list(data.get("affiliation-group"), "affiliation-group")

        employments = []
        for group_index, group in enumerate(groups):
            if not isinstance(group, dict):
                raise ValueError("ORCID returned a malformed employment group")
            summaries = self._list(group.get("summaries"), "employment summaries")
            for s in summaries:
                if not isinstance(s, dict):
                    raise ValueError("ORCID returned a malformed employment summary")
                emp = s.get("employment-summary", {})
                employments.append(
                    {
                        "group_index": group_index,
                        "organization": emp.get("organization", {}).get("name"),
                        "department": emp.get("department-name"),
                        "role": emp.get("role-title"),
                        "start_date": emp.get("start-date"),
                        "end_date": emp.get("end-date"),
                        "country": emp.get("organization", {})
                        .get("address", {})
                        .get("country"),
                    }
                )

        return {
            "status": "success",
            "data": employments,
            "num_employments": len(employments),
            "metadata": {
                "employment_group_count": len(groups),
                "employment_summary_count": len(employments),
                "all_group_summaries_returned": True,
                "requested_orcid": orcid,
            },
        }

    def _get_fundings(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        orcid, error = self._orcid_argument(arguments)
        if error:
            return error
        assert orcid is not None

        result = self._make_request(f"{orcid}/fundings")
        if not result["ok"]:
            return {
                "status": "error",
                "error": result["error"],
                "detail": result.get("detail", ""),
            }

        data = result["data"]
        groups = self._list(data.get("group"), "funding groups")

        fundings = []
        for group_index, group in enumerate(groups):
            if not isinstance(group, dict):
                raise ValueError("ORCID returned a malformed funding group")
            summaries = self._list(group.get("funding-summary"), "funding-summary")
            for summary_index, s in enumerate(summaries):
                if not isinstance(s, dict):
                    raise ValueError("ORCID returned a malformed funding summary")
                org = s.get("organization", {}) or {}
                fundings.append(
                    {
                        "group_index": group_index,
                        "summary_index": summary_index,
                        "group_external_ids": group.get("external-ids", {}),
                        "put_code": s.get("put-code"),
                        "title": (s.get("title", {}) or {})
                        .get("title", {})
                        .get("value"),
                        "type": s.get("type"),
                        "organization": org.get("name"),
                        "organization_country": (org.get("address", {}) or {}).get(
                            "country"
                        ),
                        "start_date": s.get("start-date"),
                        "end_date": s.get("end-date"),
                        "url": (s.get("url", {}) or {}).get("value")
                        if s.get("url")
                        else None,
                        "external_ids": (s.get("external-ids", {}) or {}).get(
                            "external-id", []
                        ),
                    }
                )

        return {
            "status": "success",
            "data": fundings,
            "num_fundings": len(fundings),
            "metadata": {
                "funding_group_count": len(groups),
                "funding_summary_count": len(fundings),
                "all_group_summaries_returned": True,
                "requested_orcid": orcid,
            },
        }

    def _get_peer_reviews(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        orcid, error = self._orcid_argument(arguments)
        if error:
            return error
        assert orcid is not None

        result = self._make_request(f"{orcid}/peer-reviews")
        if not result["ok"]:
            return {
                "status": "error",
                "error": result["error"],
                "detail": result.get("detail", ""),
            }

        data = result["data"]
        groups = self._list(data.get("group"), "peer-review groups")

        reviews = []
        subgroup_count = 0
        for group_index, group in enumerate(groups):
            if not isinstance(group, dict):
                raise ValueError("ORCID returned a malformed peer-review group")
            subgroups = self._list(group.get("peer-review-group"), "peer-review-group")
            subgroup_count += len(subgroups)
            for subgroup_index, sub in enumerate(subgroups):
                if not isinstance(sub, dict):
                    raise ValueError("ORCID returned a malformed peer-review subgroup")
                summaries = self._list(
                    sub.get("peer-review-summary"), "peer-review-summary"
                )
                for summary_index, s in enumerate(summaries):
                    if not isinstance(s, dict):
                        raise ValueError(
                            "ORCID returned a malformed peer-review summary"
                        )
                    conv = s.get("convening-organization", {}) or {}
                    reviews.append(
                        {
                            "group_index": group_index,
                            "subgroup_index": subgroup_index,
                            "summary_index": summary_index,
                            "group_external_ids": group.get("external-ids", {}),
                            "put_code": s.get("put-code"),
                            "reviewer_role": s.get("reviewer-role"),
                            "review_type": s.get("review-type"),
                            "review_group_id": s.get("review-group-id"),
                            "convening_organization": conv.get("name"),
                            "convening_organization_country": (
                                conv.get("address", {}) or {}
                            ).get("country"),
                            "completion_date": s.get("completion-date"),
                            "review_url": (s.get("review-url", {}) or {}).get("value")
                            if s.get("review-url")
                            else None,
                        }
                    )

        return {
            "status": "success",
            "data": reviews,
            "num_peer_reviews": len(reviews),
            "metadata": {
                "peer_review_group_count": len(groups),
                "peer_review_subgroup_count": subgroup_count,
                "peer_review_summary_count": len(reviews),
                "all_group_summaries_returned": True,
                "requested_orcid": orcid,
            },
        }
