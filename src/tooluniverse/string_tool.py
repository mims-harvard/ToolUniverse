"""STRING Database REST API Tool for protein-protein interaction data."""

import requests
from typing import Any, Dict, List
from .base_tool import BaseTool
from .tool_registry import register_tool

STRING_BASE_URL = "https://string-db.org/api"

# Identifier-mapping endpoint. Only its responses carry the queryIndex ->
# submitted-identifier correspondence used by _annotate_mapping_coverage.
_STRING_IDS_ENDPOINT = "/json/get_string_ids"

# Upper bound on the follow-up requests _classify_missing may issue.
_MAX_MAPPING_PROBE_ROUNDS = 5

# Categories whose STRING label differs from the value our schema advertises.
# Every other enum value ('Process', 'Component', 'Function', 'KEGG',
# 'WikiPathways', 'COMPARTMENTS', 'TISSUES', 'DISEASES') matches STRING exactly.
_STRING_CATEGORY_LABELS = {"Reactome": "RCTM"}


@register_tool("STRINGRESTTool")
class STRINGRESTTool(BaseTool):
    """STRING Database REST API tool.
    Generic wrapper for STRING API endpoints defined in ppi_tools.json.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        parameter = tool_config.get("parameter", {})

        self.endpoint_template: str = fields.get("endpoint", "/tsv/network")
        self.required: List[str] = parameter.get("required", [])
        self.output_format: str = fields.get("return_format", "TSV")

    def _build_url(self) -> str:
        """Build URL for STRING API request."""
        return STRING_BASE_URL + self.endpoint_template

    def _build_params(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for STRING API request."""
        params = {}

        # Map protein IDs to STRING format
        if "protein_ids" in arguments:
            protein_ids = arguments["protein_ids"]
            if isinstance(protein_ids, list):
                params["identifiers"] = "\r".join(protein_ids)
            else:
                params["identifiers"] = str(protein_ids)

        # Add other parameters
        if "species" in arguments:
            params["species"] = arguments["species"]
        if "confidence_score" in arguments:
            params["required_score"] = int(arguments["confidence_score"] * 1000)
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        if "network_type" in arguments:
            params["network_type"] = arguments["network_type"]

        # Additional parameters for other endpoints
        if "caller_identity" in arguments:
            params["caller_identity"] = arguments["caller_identity"]
        if "echo_query" in arguments:
            params["echo_query"] = arguments["echo_query"]
        if "add_nodes" in arguments:
            params["add_nodes"] = arguments["add_nodes"]
        if "category" in arguments:
            params["category"] = arguments["category"]

        return params

    def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a GET request and handle common errors."""
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            if self.output_format == "TSV":
                return self._parse_tsv_response(response.text)
            if self.output_format == "JSON":
                return response.json()

            try:
                return response.json()
            except (ValueError, KeyError):
                return self._parse_tsv_response(response.text)

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _parse_tsv_response(self, text: str) -> Dict[str, Any]:
        """Parse TSV response from STRING API."""
        lines = text.strip().split("\n")
        if len(lines) < 2:
            return {"data": [], "error": "No data returned"}

        header = lines[0].split("\t")
        data = [
            dict(zip(header, line.split("\t"))) for line in lines[1:] if line.strip()
        ]

        return {"data": data, "header": header}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        for param in self.required:
            if param not in arguments:
                error_msg = f"Missing required parameter: {param}"
                return {
                    "status": "error",
                    "data": {"error": error_msg},
                    "error": error_msg,
                }

        url = self._build_url()
        params = self._build_params(arguments)
        api_response = self._make_request(url, params)

        if "error" in api_response:
            return {
                "status": "error",
                "data": api_response,
                "error": api_response.get("error"),
            }

        # Feature-79B: STRING /json/enrichment ignores `category` param server-side.
        # Apply client-side filter when category is specified.
        category_filter = arguments.get("category")
        if category_filter:
            # STRING labels its own categories differently from our enum for
            # Reactome ('RCTM'). Comparing the enum value verbatim matched no
            # row, so a declared and schema-validated category returned zero
            # enriched terms as a success -- indistinguishable from "this gene
            # set has no Reactome enrichment".
            category_filter = _STRING_CATEGORY_LABELS.get(
                category_filter, category_filter
            )
            if isinstance(api_response, list):
                api_response = [
                    r for r in api_response if r.get("category") == category_filter
                ]
            elif isinstance(api_response, dict):
                data_list = api_response.get("data", [])
                if isinstance(data_list, list):
                    api_response["data"] = [
                        r for r in data_list if r.get("category") == category_filter
                    ]

        # Unwrap TSV parsed responses to avoid double-nesting
        # _parse_tsv_response returns {"data": [...], "header": [...]}
        # Without unwrapping, result would be {"data": {"data": [...], "header": [...]}}
        if (
            isinstance(api_response, dict)
            and "data" in api_response
            and "header" in api_response
        ):
            rows = api_response["data"]
            metadata = {"columns": api_response["header"]}
            # `limit` is documented as "Maximum number of interactions to return",
            # but STRING interprets it as a network node-expansion count and then
            # returns EVERY pairwise edge -- so limit=50 could yield 300+ rows,
            # far more than asked. Honor the documented meaning by returning at
            # most `limit` interactions, keeping the highest-confidence ones.
            limit = arguments.get("limit")
            if isinstance(rows, list) and isinstance(limit, int) and len(rows) > limit:

                def _score(row):
                    try:
                        return float(row.get("score"))
                    except (TypeError, ValueError):
                        return -1.0

                rows = sorted(rows, key=_score, reverse=True)[:limit]
                metadata["truncated_to_limit"] = limit
            if isinstance(rows, list):
                rows = self._label_partners(rows, arguments)
                metadata["partner_note"] = (
                    "STRING returns each edge as an A/B pair and the queried "
                    "protein appears on either side, so `partner` names the "
                    "other end of each edge. Collect partners from `partner`, "
                    "not from preferredName_B alone."
                )
            return {
                "status": "success",
                "data": rows,
                "metadata": metadata,
            }

        if self.endpoint_template == _STRING_IDS_ENDPOINT and isinstance(
            api_response, list
        ):
            return self._annotate_mapping_coverage(api_response, arguments)

        return {"status": "success", "data": api_response}

    @staticmethod
    def _submitted_identifiers(arguments) -> List[str]:
        """Recover the submitted identifier list in the order STRING indexed it.

        `queryIndex` is a 0-based offset into the identifiers we posted, so the
        list has to be rebuilt exactly as _build_params serialized it.
        """
        protein_ids = arguments.get("protein_ids")
        if protein_ids is None:
            protein_ids = arguments.get("identifiers", [])
        if isinstance(protein_ids, list):
            return [str(p) for p in protein_ids]
        joined = str(protein_ids).replace("%0d", "\r").replace("\n", "\r")
        return [part for part in joined.split("\r") if part.strip()]

    def _annotate_mapping_coverage(self, records, arguments) -> Dict[str, Any]:
        """Report which submitted identifiers STRING did not return.

        STRING's /json/get_string_ids simply omits identifiers it does not
        return -- no placeholder row, no warning -- so a batch of 500 gene
        symbols could come back as 480 records with a plain "success" and the
        caller would only notice by diffing the returned `queryIndex` values
        against their own input. Silently shrinking the gene set skews every
        downstream enrichment, and this tool's whole job is validating that
        identifiers exist in STRING, so name the omissions explicitly.
        """
        submitted = self._submitted_identifiers(arguments)
        # `limit` is matches-per-identifier here (up to 10), so several records
        # can share one queryIndex -- correlate on distinct indices, not rows.
        returned_indices = {
            record["queryIndex"]
            for record in records
            if isinstance(record, dict) and isinstance(record.get("queryIndex"), int)
        }

        metadata: Dict[str, Any] = {
            "submitted_count": len(submitted),
            "mapped_count": len(returned_indices),
        }

        if not submitted or (records and not returned_indices):
            # Nothing to correlate against (no queryIndex in the response);
            # report the records as-is rather than inventing an omission list.
            metadata["unmapped_count"] = 0
            metadata["unmapped_identifiers"] = []
            return {"status": "success", "data": records, "metadata": metadata}

        missing = [
            identifier
            for index, identifier in enumerate(submitted)
            if index not in returned_indices
        ]

        if not returned_indices:
            metadata["unmapped_count"] = len(missing)
            metadata["unmapped_identifiers"] = missing
            error_msg = (
                f"STRING could not map any of the {len(submitted)} submitted "
                f"identifier(s): {', '.join(missing)}. Check the identifier "
                "spelling and that `species` matches the organism."
            )
            metadata["unmapped_note"] = error_msg
            return {
                "status": "error",
                "data": records,
                "metadata": metadata,
                "error": error_msg,
            }

        unmapped, duplicates = self._classify_missing(missing, arguments)
        metadata["mapped_count"] = len(returned_indices) + len(duplicates)
        metadata["unmapped_count"] = len(unmapped)
        metadata["unmapped_identifiers"] = unmapped

        if duplicates:
            metadata["duplicate_identifiers"] = duplicates
            metadata["duplicate_note"] = (
                f"{len(duplicates)} submitted identifier(s) resolve to a STRING "
                "protein that another submitted identifier already covers, and "
                "STRING keeps only the last of each such group: "
                f"{', '.join(duplicates)}. These are mapped, not missing."
            )
        if unmapped:
            metadata["unmapped_note"] = (
                f"{len(unmapped)} of {len(submitted)} submitted identifier(s) "
                "could not be mapped by STRING and are absent from `data`: "
                f"{', '.join(unmapped)}. Exclude them from downstream analyses "
                "or supply an alternative identifier type."
            )

        return {"status": "success", "data": records, "metadata": metadata}

    def _classify_missing(self, missing, arguments):
        """Split absent identifiers into truly unmapped vs. collapsed duplicates.

        An index absent from the response does not always mean STRING failed to
        map it: STRING also de-duplicates by resolved protein, keeping only the
        LAST identifier of every group that resolves to the same entry. Querying
        ['TP53', 'P04637'] returns one record at queryIndex 1, so calling TP53
        "not found in STRING" would be flatly wrong. Re-query the absent ones on
        their own -- whatever STRING returns then was a collapsed duplicate,
        whatever it still omits is genuinely unmapped. A round that resolves
        nothing proves the remainder is unmappable, so this terminates quickly
        (usually after one extra request, and none at all when nothing is
        missing).
        """
        duplicates = []
        remaining = list(missing)
        # One round per alias-group member is needed in theory; cap the extra
        # requests so a pathological input cannot fan out into a request storm.
        for _ in range(min(len(missing), _MAX_MAPPING_PROBE_ROUNDS)):
            if not remaining:
                break
            probe = self._make_request(
                self._build_url(),
                self._build_params({**arguments, "protein_ids": remaining}),
            )
            if not isinstance(probe, list):
                # Probe failed (network/API error); stay conservative and treat
                # the remainder as unmapped rather than claiming it mapped.
                break
            resolved = {
                record["queryIndex"]
                for record in probe
                if isinstance(record, dict)
                and isinstance(record.get("queryIndex"), int)
            }
            if not resolved:
                break
            duplicates.extend(
                identifier
                for index, identifier in enumerate(remaining)
                if index in resolved
            )
            remaining = [
                identifier
                for index, identifier in enumerate(remaining)
                if index not in resolved
            ]
        return remaining, duplicates

    @staticmethod
    def _label_partners(rows, arguments):
        """Name the non-queried end of each edge.

        STRING orders every edge as A/B by internal ID, not by what was asked
        for, so the queried protein turns up as `preferredName_A` on some rows
        and `preferredName_B` on others. Reading `preferredName_B` alone -- the
        obvious thing to do -- silently drops every edge where the query landed
        in the A column, which is roughly half of them.
        """
        queried = arguments.get("protein_ids") or arguments.get("identifiers") or []
        if isinstance(queried, str):
            queried = [
                q.strip() for q in queried.replace("%0d", "\n").split() if q.strip()
            ]
        wanted = {str(q).strip().upper() for q in queried if str(q).strip()}
        for row in rows:
            if not isinstance(row, dict):
                continue
            a = str(row.get("preferredName_A") or "")
            b = str(row.get("preferredName_B") or "")
            if wanted and a.upper() in wanted and b.upper() not in wanted:
                row["partner"] = b
            elif wanted and b.upper() in wanted and a.upper() not in wanted:
                row["partner"] = a
            else:
                # Self-edge, or neither side matched (alias/ID mismatch): leave
                # the caller both names rather than guessing one.
                row["partner"] = None
        return rows
