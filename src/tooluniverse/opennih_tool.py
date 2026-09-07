"""ToolUniverse adapter for the public OpenNIH MCP server."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("OpenNIHTool")
class OpenNIHTool(BaseTool):
    """Call one configured OpenNIH tool and normalize the MCP envelope."""

    SERVER_URL = "https://mcp.opennih.org/mcp"
    SUPPORTED_OPERATIONS = {
        "source_status",
        "search_grants",
        "rank_institutions",
        "get_pi_profile",
        "get_institution_profile",
        "funding_trend",
        "topic_trend",
        "activity_code_distribution",
        "institution_concentration",
        "mechanism_mix",
        "ic_topic_cross",
        "funding_growth",
        "search",
        "fetch",
    }

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.server_url = tool_config.get("server_url", self.SERVER_URL)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("operation")

    def _make_mcp_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send one stateless JSON-RPC request and decode an SSE MCP response."""
        request_id = str(uuid.uuid4())
        response = requests.post(
            self.server_url,
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            },
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            timeout=(10, self.timeout),
        )
        response.raise_for_status()
        # JSON and MCP SSE payloads are UTF-8 even when the server omits a
        # charset from the text/event-stream Content-Type header.
        response.encoding = "utf-8"

        messages = []
        content_type = next(
            (
                str(value).lower()
                for key, value in response.headers.items()
                if key.lower() == "content-type"
            ),
            "",
        )
        if "text/event-stream" in content_type:
            event_data = []
            for line in response.text.splitlines():
                if not line:
                    if event_data:
                        messages.append(json.loads("\n".join(event_data)))
                        event_data = []
                    continue
                if line.startswith("data:"):
                    event_data.append(line[5:].lstrip())
            if event_data:
                messages.append(json.loads("\n".join(event_data)))
        else:
            messages.append(response.json())

        for message in messages:
            if str(message.get("id")) != request_id:
                continue
            if "error" in message:
                error = message["error"]
                if isinstance(error, dict):
                    error = error.get("message", json.dumps(error))
                raise RuntimeError(str(error))
            result = message.get("result")
            if isinstance(result, dict):
                return result

        raise RuntimeError("OpenNIH returned no matching JSON-RPC response")

    @staticmethod
    def _text_from_content(content: Any) -> str:
        if not isinstance(content, list):
            return str(content or "")
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(part for part in parts if part)

    @classmethod
    def _normalize_result(cls, result: Any) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {
                "status": "error",
                "error": "OpenNIH returned an invalid MCP response",
            }

        text = cls._text_from_content(result.get("content"))
        if result.get("isError") or result.get("is_error"):
            return {
                "status": "error",
                "error": text or "OpenNIH reported an MCP tool error",
            }

        structured = result.get("structuredContent")
        if structured is None:
            structured = result.get("structured_content")
        if structured is not None:
            return {"status": "success", "data": structured}

        if text:
            try:
                return {"status": "success", "data": json.loads(text)}
            except json.JSONDecodeError:
                return {"status": "success", "data": {"text": text}}

        return {
            "status": "error",
            "error": "OpenNIH returned no structured or textual content",
        }

    @staticmethod
    def _duplicate_project_nums(rows: Any) -> list[str]:
        """Return repeated full project numbers visible in a response page."""
        if not isinstance(rows, list):
            return []
        counts = Counter(
            str(row["project_num"])
            for row in rows
            if isinstance(row, dict) and row.get("project_num")
        )
        return sorted(project_num for project_num, count in counts.items() if count > 1)

    def _annotate_contract_warnings(self, normalized: Dict[str, Any]) -> Dict[str, Any]:
        """Add stable interpretation warnings without changing server values."""
        if normalized.get("status") != "success":
            return normalized

        data = normalized.get("data")
        if not isinstance(data, dict):
            return normalized

        warnings = []
        if self.operation == "search_grants":
            duplicate_project_nums = self._duplicate_project_nums(data.get("results"))
            meta = data.get("meta")
            total_rows = meta.get("total") if isinstance(meta, dict) else None
            unique_project_nums = (
                meta.get("unique_project_nums") if isinstance(meta, dict) else None
            )
            slice_has_duplicates = (
                isinstance(total_rows, int)
                and isinstance(unique_project_nums, int)
                and total_rows > unique_project_nums
            )
            if duplicate_project_nums or slice_has_duplicates:
                warning = {
                    "code": "duplicate_full_project_rows",
                    "message": (
                        "The matching slice contains repeated full project numbers, "
                        "which can represent parent and component rows. "
                        "meta.total_funding is a row sum and may double-count "
                        "unique-award dollars."
                    ),
                }
                if duplicate_project_nums:
                    warning["project_nums_on_page"] = duplicate_project_nums
                if slice_has_duplicates:
                    warning["slice_total_rows"] = total_rows
                    warning["slice_unique_project_nums"] = unique_project_nums
                warnings.append(warning)

        elif self.operation == "get_pi_profile":
            if "publications" not in data:
                warnings.append(
                    {
                        "code": "publications_not_exposed",
                        "message": (
                            "This endpoint does not expose linked publications. A missing "
                            "publications field is not evidence that the PI has no papers; "
                            "use a publication source with grant or author disambiguation."
                        ),
                    }
                )

            duplicate_project_nums = self._duplicate_project_nums(data.get("grants"))
            profile_warning = {
                "code": "profile_row_counts_not_awards",
                "message": (
                    "Profile grant_count, active_grants, and total_funding aggregate "
                    "grant rows, not deduplicated core awards. Reconcile distinct core "
                    "project numbers before reporting award-level counts or dollars."
                ),
            }
            if duplicate_project_nums:
                profile_warning["project_nums_on_page"] = duplicate_project_nums
            warnings.append(profile_warning)

            collaborators = data.get("collaborators")
            if isinstance(collaborators, list) and collaborators:
                warnings.append(
                    {
                        "code": "shared_award_not_direct_collaboration",
                        "message": (
                            "Collaborators are people associated with shared awards. This is "
                            "not proof of coauthorship, mentorship, equal roles, or a direct "
                            "working relationship."
                        ),
                    }
                )

                meta = data.get("meta")
                requested_start = (
                    meta.get("fiscal_year_start") if isinstance(meta, dict) else None
                )
                requested_end = (
                    meta.get("fiscal_year_end") if isinstance(meta, dict) else None
                )
                if requested_start is not None or requested_end is not None:
                    warnings.append(
                        {
                            "code": "collaborators_not_year_filtered",
                            "message": (
                                "The fiscal-year window filters grants and profile totals, "
                                "but not collaborators. Collaborator rows can come from "
                                "shared awards outside the requested window."
                            ),
                            "requested_fiscal_year_start": requested_start,
                            "requested_fiscal_year_end": requested_end,
                        }
                    )

        elif self.operation == "fetch":
            metadata = data.get("metadata")
            matching_rows = (
                metadata.get("matching_rows") if isinstance(metadata, dict) else None
            )
            if isinstance(matching_rows, int) and matching_rows > 1:
                warnings.append(
                    {
                        "code": "canonical_fetch_has_components",
                        "message": (
                            "fetch returned one canonical row from multiple matching rows. "
                            "Its amount is not a sum or deduplicated total for all components."
                        ),
                        "matching_rows": matching_rows,
                    }
                )

        if warnings:
            existing = data.get("tooluniverse_contract_warnings")
            if isinstance(existing, list):
                existing_codes = {
                    warning.get("code")
                    for warning in existing
                    if isinstance(warning, dict)
                }
                warnings = [
                    *existing,
                    *[
                        warning
                        for warning in warnings
                        if warning.get("code") not in existing_codes
                    ],
                ]
            data["tooluniverse_contract_warnings"] = warnings
        return normalized

    def validate_parameters(self, arguments: Dict[str, Any]) -> Any:
        """Apply JSON Schema validation plus OpenNIH cross-field constraints."""
        validation_error = super().validate_parameters(arguments)
        if validation_error:
            return validation_error

        fiscal_year_start = arguments.get("fiscal_year_start")
        fiscal_year_end = arguments.get("fiscal_year_end")
        if (
            isinstance(fiscal_year_start, int)
            and isinstance(fiscal_year_end, int)
            and fiscal_year_start > fiscal_year_end
        ):
            from .exceptions import ToolValidationError

            return ToolValidationError(
                "Parameter validation failed: fiscal_year_start must be less than "
                "or equal to fiscal_year_end",
                details={
                    "fiscal_year_start": fiscal_year_start,
                    "fiscal_year_end": fiscal_year_end,
                },
            )
        return None

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.operation not in self.SUPPORTED_OPERATIONS:
            return {
                "status": "error",
                "error": f"Unsupported OpenNIH operation: {self.operation}",
            }

        arguments = arguments or {}
        validation_error = self.validate_parameters(arguments)
        if validation_error:
            return {"status": "error", "error": str(validation_error)}

        try:
            result = self._make_mcp_request(
                "tools/call",
                {"name": self.operation, "arguments": arguments or {}},
            )
            return self._annotate_contract_warnings(self._normalize_result(result))
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"OpenNIH request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", "unknown")
            return {
                "status": "error",
                "error": f"OpenNIH HTTP error: {status_code}",
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
