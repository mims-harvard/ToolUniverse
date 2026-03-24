"""
RCSB PDB Structure Search Tool

Tool for searching similar protein structures using RCSB PDB Search API v2.
Supports both sequence-based and structure-based similarity search.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("RCSBSearchTool")
class RCSBSearchTool(BaseTool):
    """
    Tool for searching similar protein structures using RCSB PDB Search API v2.

    Supports:
    - Sequence-based similarity search
    - Structure-based similarity search (using PDB ID)
    - Text-based search (by name, keyword, etc.)
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.api_url = "https://search.rcsb.org/rcsbsearch/v2/query"
        self.timeout = 60  # API request timeout in seconds

    def _validate_pdb_id(self, pdb_id: str) -> bool:
        """Validate PDB ID format (4 characters, alphanumeric)"""
        if not isinstance(pdb_id, str):
            return False
        pdb_id = pdb_id.strip().upper()
        return len(pdb_id) == 4 and pdb_id.isalnum()

    def _validate_sequence(self, sequence: str) -> bool:
        """Validate protein sequence (amino acids only)"""
        if not isinstance(sequence, str):
            return False
        sequence = sequence.strip().upper()
        if len(sequence) < 10:
            return False
        # Valid amino acid codes
        valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
        return all(c in valid_aa for c in sequence)

    def _build_sequence_query(
        self, sequence: str, identity_cutoff: float, max_results: int
    ) -> Dict[str, Any]:
        """
        Build sequence similarity search query.

        Uses the correct RCSB Search API v2 format:
        - Uses "value" parameter (not "target")
        - Includes evalue_cutoff (required, default 0.1)
        - Includes identity_cutoff (optional, 0-1)
        - Includes sequence_type ("protein")
        """
        # Map identity_cutoff to evalue_cutoff: higher identity requires stricter evalue
        if identity_cutoff > 0.9:
            evalue_cutoff = 0.001
        elif identity_cutoff > 0.7:
            evalue_cutoff = 0.01
        else:
            evalue_cutoff = 0.1

        return {
            "query": {
                "type": "terminal",
                "service": "sequence",
                "parameters": {
                    "value": sequence.upper(),
                    "evalue_cutoff": evalue_cutoff,
                    "identity_cutoff": identity_cutoff,
                    "sequence_type": "protein",
                },
            },
            "return_type": "entry",
            "request_options": {
                "paginate": {
                    "start": 0,
                    "rows": max_results,
                },
                "sort": [{"sort_by": "score", "direction": "desc"}],
            },
        }

    def _build_structure_query(
        self, pdb_id: str, similarity_threshold: float, max_results: int
    ) -> Dict[str, Any]:
        """
        Build structure similarity search query.

        Uses the correct RCSB Search API v2 format:
        - Uses "value" as an object with "entry_id" and "assembly_id"
        - Includes "operator" (default: "strict_shape_match")
        - Includes "target_search_space" (default: "assembly")
        """
        return {
            "query": {
                "type": "terminal",
                "service": "structure",
                "parameters": {
                    "value": {
                        "entry_id": pdb_id.upper(),
                        "assembly_id": "1",  # Default to first assembly
                    },
                    "operator": "strict_shape_match",
                    "target_search_space": "assembly",
                },
            },
            "return_type": "entry",
            "request_options": {
                "paginate": {
                    "start": 0,
                    "rows": max_results,
                },
                "sort": [{"sort_by": "score", "direction": "desc"}],
            },
        }

    def _enrich_text_results(self, results: list) -> list:
        """Fetch title, resolution, and method for text search PDB IDs."""
        if not results:
            return results
        pdb_ids = [r["pdb_id"] for r in results if r.get("pdb_id")]
        if not pdb_ids:
            return results
        try:
            # Use RCSB GraphQL API to batch-fetch metadata
            graphql_url = "https://data.rcsb.org/graphql"
            query_str = """
            query($ids: [String!]!) {
              entries(entry_ids: $ids) {
                rcsb_id
                struct { title }
                rcsb_entry_info {
                  resolution_combined
                  experimental_method
                }
              }
            }
            """
            resp = requests.post(
                graphql_url,
                json={"query": query_str, "variables": {"ids": pdb_ids}},
                timeout=10,
            )
            if resp.status_code != 200:
                return results
            entries = resp.json().get("data", {}).get("entries", [])
            metadata = {}
            for entry in entries:
                if not entry:
                    continue
                pdb_id = entry.get("rcsb_id", "")
                info = entry.get("rcsb_entry_info") or {}
                resolution = info.get("resolution_combined")
                metadata[pdb_id] = {
                    "title": (entry.get("struct") or {}).get("title"),
                    "resolution": resolution[0] if resolution else None,
                    "method": info.get("experimental_method"),
                }
            for r in results:
                meta = metadata.get(r.get("pdb_id"), {})
                r.update({k: v for k, v in meta.items() if v is not None})
        except Exception:
            pass  # Return results without metadata on failure
        return results

    def _build_text_query(self, search_text: str, max_results: int) -> Dict[str, Any]:
        """
        Build text search query.

        Uses the correct RCSB Search API v2 format:
        - Searches in multiple attributes
          (struct.title, struct_keywords.pdbx_keywords)
        - Uses OR logic to combine search conditions
        - Supports pagination and sorting
        """
        # Search in multiple attributes using OR logic
        search_nodes = [
            {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "struct.title",
                    "operator": "contains_words",
                    "value": search_text,
                },
            },
            {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "struct_keywords.pdbx_keywords",
                    "operator": "contains_words",
                    "value": search_text,
                },
            },
        ]

        return {
            "query": {
                "type": "group",
                "logical_operator": "or",
                "nodes": search_nodes,
            },
            "return_type": "entry",
            "request_options": {
                "paginate": {
                    "start": 0,
                    "rows": max_results,
                },
                "sort": [{"sort_by": "score", "direction": "desc"}],
            },
        }

    def _parse_search_results(self, response_data: Dict[str, Any]) -> list:
        """
        Parse RCSB Search API response.

        Expected response format:
        {
            "query_id": "...",
            "result_type": "entry",
            "total_count": 123,
            "result_set": [
                {"identifier": "6B3Q", "score": 1.0},
                ...
            ]
        }
        """
        results = []

        if not isinstance(response_data, dict):
            return results

        # Extract result identifiers from result_set
        result_set = response_data.get("result_set", [])

        if not result_set:
            return results

        for idx, entry in enumerate(result_set):
            # Entry is a dict with "identifier" and optionally "score"
            if isinstance(entry, dict):
                pdb_id = entry.get("identifier", entry.get("pdb_id", ""))
                score = entry.get("score")
            elif isinstance(entry, str):
                # Fallback: if entry is just a string, use it as PDB ID
                pdb_id = entry
                score = None
            else:
                continue

            if pdb_id:
                result = {
                    "pdb_id": pdb_id,
                    "rank": idx + 1,
                }

                if score is not None:
                    result["score"] = score

                results.append(result)

        return results

    def run(
        self,
        arguments: Optional[Dict[str, Any]] = None,
        stream_callback: Optional[Any] = None,
        use_cache: bool = False,
        validate: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute structure similarity search.

        Args:
            arguments: Dictionary containing:
                - query: PDB ID, protein sequence, or search text
                - search_type: "sequence", "structure", or "text"
                  (default: "sequence")
                - similarity_threshold: Similarity threshold 0-1 (default: 0.7)
                  (not used for text search)
                - max_results: Maximum number of results (default: 20)
            stream_callback: Optional callback for streaming
            use_cache: Whether to use caching
            validate: Whether to validate parameters

        Returns:
            Dictionary with search results or error information
        """
        if arguments is None:
            arguments = {}

        query = arguments.get("query", "")
        if query:
            query = str(query).strip()
        search_type = arguments.get("search_type", "sequence")
        if search_type:
            search_type = str(search_type).lower()
        else:
            search_type = "sequence"

        # Get and validate similarity_threshold with clamping
        similarity_threshold_raw = arguments.get("similarity_threshold", 0.7)
        try:
            similarity_threshold = float(similarity_threshold_raw)
            similarity_threshold = max(0.0, min(1.0, similarity_threshold))
        except (ValueError, TypeError):
            similarity_threshold = 0.7

        # Get and validate max_results with clamping
        max_results_raw = arguments.get("max_results", 20)
        try:
            max_results = int(max_results_raw)
            max_results = max(1, min(100, max_results))
        except (ValueError, TypeError):
            max_results = 20

        # Validate parameters
        if not query:
            return {
                "status": "error",
                "error": (
                    "Missing required parameter: query. "
                    "Provide either a PDB ID (e.g., '1ABC'), "
                    "a protein sequence (amino acids), "
                    "or search text (e.g., drug name, keyword)."
                ),
            }

        # Build query based on search type
        if search_type == "structure":
            # Structure-based search using PDB ID
            if not self._validate_pdb_id(query):
                return {
                    "status": "error",
                    "error": (
                        f"Invalid PDB ID format: '{query}'. "
                        "PDB ID must be 4 alphanumeric characters "
                        "(e.g., '1ABC')."
                    ),
                }

            api_query = self._build_structure_query(
                query, similarity_threshold, max_results
            )
            query_type = "structure"

        elif search_type == "sequence":
            # Sequence-based search
            if not self._validate_sequence(query):
                return {
                    "status": "error",
                    "error": (
                        f"Invalid protein sequence: '{query[:50]}...'. "
                        "Sequence must be at least 10 amino acids long "
                        "and contain only valid amino acid codes "
                        "(A, C, D, E, F, G, H, I, K, L, M, N, P, Q, "
                        "R, S, T, V, W, Y)."
                    ),
                }

            api_query = self._build_sequence_query(
                query, similarity_threshold, max_results
            )
            query_type = "sequence"

        elif search_type == "text":
            # Text-based search (by name, keyword, etc.)
            # Note: empty query is already rejected above
            api_query = self._build_text_query(query, max_results)
            query_type = "text"

        else:
            return {
                "status": "error",
                "error": (
                    f"Invalid search_type: '{search_type}'. "
                    "Must be 'sequence', 'structure', or 'text'."
                ),
            }

        # Make API request
        try:
            response = requests.post(
                self.api_url,
                json=api_query,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()

            # Handle HTTP 204 No Content (empty result set)
            # RCSB API returns 204 when no results are found
            if response.status_code == 204 or len(response.content) == 0:
                response_data = {
                    "result_set": [],
                    "total_count": 0,
                }
            else:
                response_data = response.json()

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": (
                    "Request timeout. The RCSB PDB Search API "
                    "did not respond in time. Please try again later."
                ),
            }
        except requests.exceptions.HTTPError as e:
            # Try to extract detailed error message from API response
            error_detail = str(e)
            try:
                if hasattr(e, "response") and e.response is not None:
                    error_response = e.response.json()
                    if isinstance(error_response, dict):
                        api_message = error_response.get("message", "")
                        if api_message:
                            error_detail = f"{str(e)}. API message: {api_message}"
            except Exception:
                pass  # Use default error message if parsing fails

            if e.response.status_code == 400:
                return {
                    "status": "error",
                    "error": (
                        f"Invalid request to RCSB PDB Search API: "
                        f"{error_detail}. "
                        "Please check your query parameters. "
                        "Note: The API query format may need adjustment. "
                        "See documentation at "
                        "https://search.rcsb.org/redoc/index.html"
                    ),
                }
            elif e.response.status_code == 404:
                # 404 can mean the PDB ID doesn't exist or
                # doesn't support this search type
                pdb_id_msg = query if search_type == "structure" else "provided"
                error_msg = (
                    "Structure not found or does not support "
                    "similarity search. "
                    f"The PDB ID '{pdb_id_msg}' "
                    "may not exist in the database or may not support "
                    "structure similarity search. "
                    "Please verify the PDB ID is correct."
                )
                return {"status": "error", "error": error_msg}
            else:
                return {
                    "status": "error",
                    "error": (
                        f"RCSB PDB Search API error "
                        f"(HTTP {e.response.status_code}): {error_detail}"
                    ),
                }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": (
                    f"Network error while connecting to RCSB PDB Search API: {str(e)}"
                ),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error during search: {str(e)}",
            }

        # Parse results
        try:
            results = self._parse_search_results(response_data)

            # Get total_count from API response if available
            # This represents the total number of matches in the database,
            # not just the number of results returned
            # (which may be limited by max_results)
            total_found = response_data.get("total_count", len(results))

            if not results:
                if query_type == "text":
                    message = f"No structures found matching '{query}'."
                else:
                    message = (
                        f"No similar structures found with "
                        f"similarity threshold >= {similarity_threshold}."
                    )
                return {
                    "status": "success",
                    "data": {
                        "query": query,
                        "search_type": query_type,
                        "similarity_threshold": (
                            similarity_threshold if query_type != "text" else None
                        ),
                        "total_found": total_found,
                        "results": [],
                        "message": message,
                    },
                }

            # Feature-79B-003: Enrich text search results with metadata
            # (title, resolution, method) from RCSB data API
            if query_type == "text":
                results = self._enrich_text_results(results)

            result_dict = {
                "query": query,
                "search_type": query_type,
                "total_found": total_found,
                "results": results,
            }

            # Only include similarity_threshold for sequence/structure searches
            if query_type != "text":
                result_dict["similarity_threshold"] = similarity_threshold

            return {"status": "success", "data": result_dict}

        except Exception as e:
            return {
                "status": "error",
                "error": f"Error parsing search results: {str(e)}",
                "raw_response": str(response_data)[:500],
            }
