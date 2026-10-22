# orthodb_tool.py
"""
OrthoDB v12 tool for ToolUniverse.

OrthoDB provides orthologous groups of proteins at different taxonomic levels,
enabling evolutionary analysis of gene conservation, functional annotation
transfer between species, and phylogenetic profiling.

API: https://data.orthodb.org/v12/
No authentication required. Free public access.
"""

import json
import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ORTHODB_BASE_URL = "https://data.orthodb.org/v12"


@register_tool("OrthoDBTool")
class OrthoDBTool(BaseTool):
    """
    OrthoDB v12 tool for orthologous group analysis.

    Provides search for orthologous groups, group details with functional
    annotations (KEGG, GO), and member gene lists across species.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the OrthoDB API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"OrthoDB API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to OrthoDB API"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"OrthoDB API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying OrthoDB API: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "search":
            return self._search(arguments)
        elif self.endpoint == "group":
            return self._get_group(arguments)
        elif self.endpoint == "orthologs":
            return self._get_orthologs(arguments)
        elif self.endpoint == "fasta":
            return self._get_group_fasta(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for orthologous groups by gene/protein name."""
        query = arguments.get("query", "")
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (gene name, e.g., 'BRCA1')",
            }
        species = arguments.get("species")
        level = arguments.get("level")
        limit = arguments.get("limit", 10)
        offset = arguments.get("offset", 0)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            return {"status": "error", "error": "limit must be an integer from 1 to 50"}
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {"status": "error", "error": "offset must be a non-negative integer"}

        # OrthoDB v12 ignores `limit` and always returns a 100-record search
        # window, but its `skip` parameter works. Start that window at the
        # requested offset, then take the caller's page size locally.
        params = {"query": query, "limit": 100, "skip": offset}
        if species:
            params["species"] = species
        if level:
            params["level"] = level

        url = f"{ORTHODB_BASE_URL}/search"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        group_ids = (data.get("data") or [])[:limit]
        try:
            total_groups = int(data.get("count", len(group_ids)))
        except (TypeError, ValueError):
            total_groups = len(group_ids)

        # /search only returns bare group ids -- name/level_taxid require a
        # separate per-group /tab lookup (confirmed live: OrthoDB has no
        # batch/comma-separated id support for /tab). Enrich every returned
        # group, not just the first -- confirmed live this previously left
        # 9 of 10 results as bare {"group_id": ...} with no way to tell
        # them apart without a follow-up call per group.
        groups = []
        enrichment_failures = []
        for gid in group_ids:
            group = {"group_id": gid, "enrichment_status": "unavailable"}
            try:
                tab_resp = requests.get(
                    f"{ORTHODB_BASE_URL}/tab",
                    params={"id": gid, "limit": 1},
                    timeout=self.timeout,
                )
                if tab_resp.status_code == 200:
                    lines = tab_resp.text.strip().split("\n")
                    if len(lines) > 1:
                        cols = lines[1].split("\t")
                        if len(cols) >= 2:
                            group["name"] = cols[1]
                            group["level_taxid"] = cols[2] if len(cols) > 2 else None
                            group["enrichment_status"] = "complete"
                        else:
                            group["enrichment_error"] = "OrthoDB /tab row had fewer than two columns"
                    else:
                        group["enrichment_error"] = "OrthoDB /tab returned no member row"
                else:
                    group["enrichment_error"] = (
                        f"OrthoDB /tab returned HTTP {tab_resp.status_code}"
                    )
            except Exception as exc:
                group["enrichment_error"] = f"OrthoDB /tab request failed: {exc}"
            if group["enrichment_status"] != "complete":
                enrichment_failures.append(
                    {
                        "group_id": gid,
                        "error": group.get("enrichment_error", "Unknown enrichment failure"),
                    }
                )
            groups.append(group)

        return {
            "status": "success",
            "data": {
                "query": query,
                "groups": groups,
                "total_groups": total_groups,
                "returned": len(groups),
                "offset": offset,
                "limit": limit,
                "has_more": offset + len(groups) < total_groups,
                "next_offset": (
                    offset + len(groups)
                    if offset + len(groups) < total_groups
                    else None
                ),
                "result_set_complete": offset == 0 and len(groups) == total_groups,
            },
            "metadata": {
                "source": "OrthoDB v12 - Search",
                "query": query,
                "total_results": total_groups,
                "total_results_is_exact": True,
                "group_enrichment": {
                    "attempted": len(groups),
                    "complete": len(groups) - len(enrichment_failures),
                    "failed": len(enrichment_failures),
                    "all_complete": not enrichment_failures,
                    "failures": enrichment_failures,
                },
            },
        }

    def _get_group(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about an orthologous group."""
        group_id = arguments.get("group_id", "")
        if not group_id:
            return {
                "status": "error",
                "error": "group_id parameter is required (e.g., '727649at7742')",
            }

        url = f"{ORTHODB_BASE_URL}/group"
        params = {"id": group_id}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        group_data = data.get("data", {})
        if not group_data:
            return {"status": "error", "error": f"No data found for group {group_id}"}

        # OrthoDB v12 split the old `GO` array into ontology-aspect keys.
        # Read both schemas, preserve the aspect, and de-duplicate terms that
        # also appear in the upstream "unclassified GO terms" bucket.
        go_terms = []
        seen_go_ids = set()
        go_sources = [
            ("biological_process", group_data.get("biological_process") or []),
            ("cellular_component", group_data.get("cellular_component") or []),
            ("molecular_function", group_data.get("molecular_function") or []),
            ("unclassified", group_data.get("unclassified GO terms") or []),
            (None, group_data.get("GO") or []),
        ]
        for category, annotations in go_sources:
            for go in annotations:
                go_id = go.get("id")
                if go_id in seen_go_ids:
                    continue
                seen_go_ids.add(go_id)
                go_terms.append(
                    {
                        "id": go_id,
                        "description": go.get("description"),
                        "category": category or go.get("type"),
                        "count": go.get("count"),
                    }
                )

        # Extract KEGG pathways
        kegg_pathways = []
        for k in group_data.get("KEGGpathway") or []:
            kegg_pathways.append(
                {
                    "id": k.get("id"),
                    "description": k.get("description"),
                    "count": k.get("count"),
                }
            )

        # Extract InterPro domains
        interpro = []
        interpro_source = (
            group_data.get("interpro_domains") or group_data.get("InterPro") or []
        )
        for ip in interpro_source:
            interpro.append(
                {
                    "id": ip.get("id"),
                    "description": ip.get("description"),
                    "count": ip.get("count"),
                }
            )

        return {
            "status": "success",
            "data": {
                "group_id": group_data.get("id"),
                "name": group_data.get("name"),
                "level_name": group_data.get("level_name"),
                "tax_id": group_data.get("tax_id"),
                "go_terms": go_terms if go_terms else None,
                "kegg_pathways": kegg_pathways if kegg_pathways else None,
                "interpro_domains": interpro if interpro else None,
                "ec_numbers": group_data.get("ECnumber") or None,
                "functional_categories": group_data.get("functional_category") or None,
                "phyletic_profile": group_data.get("phyletic_profile"),
                "evolutionary_rate": group_data.get("evolutionary_rate"),
                "gene_architecture": group_data.get("gene_architecture"),
            },
            "metadata": {
                "source": "OrthoDB v12 - Group Details",
                "group_id": group_id,
                "annotation_counts": {
                    "go_terms": len(go_terms),
                    "kegg_pathways": len(kegg_pathways),
                    "interpro_domains": len(interpro),
                    "ec_numbers": len(group_data.get("ECnumber") or []),
                    "functional_categories": len(
                        group_data.get("functional_category") or []
                    ),
                },
            },
        }

    def _get_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get orthologous genes in specific species from a group."""
        group_id = arguments.get("group_id", "")
        if not group_id:
            return {
                "status": "error",
                "error": "group_id parameter is required (e.g., '727649at7742')",
            }
        species = arguments.get("species")
        limit = arguments.get("limit", 100)
        offset = arguments.get("offset", 0)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            return {
                "status": "error",
                "error": "limit must be an integer from 1 to 1000",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
            }

        # OrthoDB v12's /tab endpoint does not expose working pagination:
        # `skip` is rejected by its schema and `offset` silently returns an
        # empty HTTP-200 response. Fetch a bounded complete window once, then
        # page it locally so records after the former hard limit remain
        # reachable.
        url = f"{ORTHODB_BASE_URL}/tab"
        upstream_limit = 5000
        params = {"id": group_id, "limit": upstream_limit}
        if species:
            params["species"] = species

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        lines = response.text.strip().split("\n")
        if len(lines) < 2:
            return {
                "status": "error",
                "error": f"No ortholog data found for group {group_id}",
            }

        # Parse header
        lines[0].split("\t")

        all_orthologs = []
        for line in lines[1:]:
            cols = line.split("\t")
            if len(cols) >= 6:
                all_orthologs.append(
                    {
                        "group_id": cols[0] if len(cols) > 0 else None,
                        "group_name": cols[1] if len(cols) > 1 else None,
                        "level_taxid": cols[2] if len(cols) > 2 else None,
                        "organism_taxid": cols[3] if len(cols) > 3 else None,
                        "organism_name": cols[4] if len(cols) > 4 else None,
                        "gene_id": cols[5] if len(cols) > 5 else None,
                        "description": cols[6] if len(cols) > 6 else None,
                    }
                )

        orthologs = all_orthologs[offset : offset + limit]
        total_orthologs = len(all_orthologs)
        total_is_lower_bound = total_orthologs >= upstream_limit
        has_more = offset + len(orthologs) < total_orthologs
        accessible_window_complete = not total_is_lower_bound

        # Summarize by organism
        organisms = {}
        for o in orthologs:
            org = o.get("organism_name", "unknown")
            organisms[org] = organisms.get(org, 0) + 1

        return {
            "status": "success",
            "data": {
                "group_id": group_id,
                "orthologs": orthologs,
                "total_orthologs": total_orthologs,
                "returned": len(orthologs),
                "offset": offset,
                "limit": limit,
                "has_more": has_more,
                "next_offset": offset + len(orthologs) if has_more else None,
                "truncated": offset > 0 or has_more or total_is_lower_bound,
                "result_set_complete": bool(
                    offset == 0
                    and len(orthologs) == total_orthologs
                    and accessible_window_complete
                ),
                "organisms_summary": organisms,
            },
            "metadata": {
                "source": "OrthoDB v12 - Orthologs",
                "group_id": group_id,
                "api_result_window_limit": upstream_limit,
                "total_is_lower_bound": total_is_lower_bound,
                "accessible_window_complete": accessible_window_complete,
                "upstream_truncated": total_is_lower_bound,
                "warning": (
                    "OrthoDB returned the 5,000-record API window; additional orthologs may exist upstream."
                    if total_is_lower_bound
                    else None
                ),
            },
        }

    def _get_group_fasta(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get member protein sequences (FASTA) for an orthologous group."""
        group_id = arguments.get("group_id", "")
        if not group_id:
            return {
                "status": "error",
                "error": "group_id parameter is required (e.g., '794361at2759')",
            }

        species = arguments.get("species")
        limit = arguments.get("limit", 50)
        offset = arguments.get("offset", 0)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            return {"status": "error", "error": "limit must be an integer from 1 to 500"}
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {"status": "error", "error": "offset must be a non-negative integer"}

        url = f"{ORTHODB_BASE_URL}/fasta"
        params = {"id": group_id}
        if species:
            params["species"] = species

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        text = response.text.strip()

        if not text or not text.startswith(">"):
            return {
                "status": "error",
                "error": (
                    f"No FASTA sequences found for group '{group_id}'"
                    + (f" (species {species})" if species else "")
                ),
            }

        all_sequences = self._parse_fasta(text)
        sequences = all_sequences[offset : offset + limit]

        if not sequences:
            return {
                "status": "error",
                "error": f"No FASTA sequences found for group '{group_id}'",
            }

        return {
            "status": "success",
            "data": {
                "group_id": group_id,
                "sequences": sequences,
                "total_sequences": len(all_sequences),
                "returned": len(sequences),
                "offset": offset,
                "limit": limit,
                "has_more": offset + len(sequences) < len(all_sequences),
                "next_offset": (
                    offset + len(sequences)
                    if offset + len(sequences) < len(all_sequences)
                    else None
                ),
                "fasta": text,
            },
            "metadata": {
                "source": "OrthoDB v12 - FASTA",
                "group_id": group_id,
                "species": species,
                "fasta_contains_all_sequences": True,
            },
        }

    @staticmethod
    def _parse_fasta(text: str, limit: int | None = None) -> list:
        """Parse OrthoDB FASTA: each header carries JSON-encoded metadata."""
        sequences = []
        record_id = None
        header_meta = None
        seq_lines: list = []

        def _flush():
            if record_id is None:
                return
            sequence = "".join(seq_lines)
            record = {
                "id": record_id,
                "sequence": sequence,
                "length": len(sequence),
            }
            if isinstance(header_meta, dict):
                record["pub_gene_id"] = header_meta.get("pub_gene_id")
                record["og_name"] = header_meta.get("og_name")
                record["organism_name"] = header_meta.get("organism_name")
                record["organism_taxid"] = header_meta.get("organism_taxid")
                record["description"] = header_meta.get("description")
                record["pub_og_id"] = header_meta.get("pub_og_id")
            sequences.append(record)

        for line in text.splitlines():
            if line.startswith(">"):
                if limit is not None and len(sequences) >= limit:
                    break
                _flush()
                seq_lines = []
                content = line[1:].strip()
                # Header format: ">9606_0:003066 {json metadata}"
                brace = content.find("{")
                if brace != -1:
                    record_id = content[:brace].strip()
                    try:
                        header_meta = json.loads(content[brace:])
                    except (ValueError, json.JSONDecodeError):
                        header_meta = None
                else:
                    record_id = content
                    header_meta = None
            else:
                seq_lines.append(line.strip())

        if limit is None or len(sequences) < limit:
            _flush()

        return sequences
