"""
Proteins API Tool

This tool provides access to the EBI Proteins API for comprehensive protein
annotations, variation data, proteomics, and reference genome mappings.
"""

import requests
from typing import Any, Dict, Optional, List, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("ProteinsAPIRESTTool")
class ProteinsAPIRESTTool(BaseTool):
    """
    Proteins API REST tool.
    Generic wrapper for Proteins API endpoints defined in proteins_api_tools.json.
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/proteins/api"
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build URL from endpoint template and arguments"""
        endpoint_template = self.tool_config["fields"].get("endpoint", "")
        tool_name = self.tool_config.get("name", "")

        if endpoint_template:
            url = endpoint_template
            for k, v in args.items():
                url = url.replace(f"{{{k}}}", str(v))
            return url

        # Build URL based on tool name
        if tool_name == "proteins_api_get_protein":
            accession = args.get("accession", "")
            if accession:
                return f"{self.base_url}/proteins/{accession}"

        elif tool_name == "proteins_api_get_variants":
            accession = args.get("accession", "")
            if accession:
                # Use the variation API endpoint (not the proteins endpoint)
                return f"{self.base_url}/variation"

        elif tool_name == "proteins_api_get_proteomics":
            accession = args.get("accession", "")
            if accession:
                # Try proteomics endpoint, fallback to main protein endpoint
                return f"{self.base_url}/proteins/{accession}/proteomics"

        elif tool_name == "proteins_api_get_epitopes":
            accession = args.get("accession", "")
            if accession:
                # Try epitopes endpoint, fallback to main protein endpoint
                return f"{self.base_url}/proteins/{accession}/epitopes"

        elif tool_name == "proteins_api_search":
            # Proteins API search uses query parameter, not path
            return f"{self.base_url}/proteins/search"

        return self.base_url

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for Proteins API"""
        params = {}
        tool_name = self.tool_config.get("name", "")

        if tool_name == "proteins_api_search":
            # Proteins API search requires specific parameters:
            # gene, protein, accession, organism, taxid, etc.
            if "query" in args:
                query = args["query"]
                # Feature-81B-007: always use gene param for short queries —
                # gene names like CYP2D6 are 6 chars and were incorrectly
                # classified as UniProt accessions. For accession lookup,
                # use proteins_api_get_protein with an explicit accession.
                if query and len(query) <= 10 and any(c.isalpha() for c in query):
                    params["gene"] = query
                else:
                    # For longer queries, try protein parameter
                    params["protein"] = query
            if "size" in args:
                params["size"] = args["size"]
            if "offset" in args:
                params["offset"] = args["offset"]
            # Feature-69A-007: Default to human (taxId 9606) to avoid non-human proteins
            # appearing before human proteins. User can override with organism param.
            if "reviewed" in args:
                params["reviewed"] = str(args["reviewed"]).lower()
            if "organism" in args:
                params["organism"] = args["organism"]
            elif "taxid" in args:
                params["taxid"] = args["taxid"]
            elif "accession" not in params:
                # Only apply human filter for gene/protein name searches
                params["taxid"] = "9606"

        elif tool_name == "proteins_api_get_variants":
            # Variation API uses accession query parameter
            if "accession" in args:
                params["accession"] = args["accession"]
            if "size" in args:
                params["size"] = args.get("size", 100)
            if "offset" in args:
                params["offset"] = args["offset"]

        # Format parameter
        if "format" in args:
            params["format"] = args["format"]
        else:
            params["format"] = "json"

        return params

    def _extract_from_protein_endpoint(
        self, accession: str, tool_name: str
    ) -> Optional[Dict[str, Any]]:
        """Extract data from main protein endpoint when specific endpoints don't exist"""
        try:
            protein_url = f"{self.base_url}/proteins/{accession}"
            response = self.session.get(protein_url, timeout=self.timeout)
            response.raise_for_status()
            protein_data = response.json()

            # Extract relevant data based on tool name
            if tool_name == "proteins_api_get_proteomics":
                # Look for proteomics-related data in response
                proteomics_data = []

                # Check comments for proteomics information
                if "comments" in protein_data:
                    for comment in protein_data["comments"]:
                        comment_type = str(comment.get("commentType", "")).upper()
                        if any(
                            x in comment_type
                            for x in [
                                "PTM",
                                "MODIFIED",
                                "MASS",
                                "SPECTROMETRY",
                                "PROTEOMICS",
                            ]
                        ):
                            proteomics_data.append(comment)

                # Check features for proteomics-related features
                if "features" in protein_data:
                    for feature in protein_data["features"]:
                        feature_type = str(feature.get("type", "")).lower()
                        if any(
                            x in feature_type
                            for x in ["modified", "mutagenesis", "site", "variant"]
                        ):
                            proteomics_data.append(feature)

                return {
                    "status": "success",
                    "data": proteomics_data,
                    "url": response.url,
                    "count": len(proteomics_data),
                    "note": "Proteomics data extracted from main protein endpoint (proteomics endpoint not available). Includes PTM comments, modified residues, and related features.",
                    "fallback_used": True,
                    "source": "main_protein_endpoint",
                }

            elif tool_name == "proteins_api_get_epitopes":
                # Look for epitope-related data
                epitopes_data = []

                # Check comments for epitope information
                if "comments" in protein_data:
                    for comment in protein_data["comments"]:
                        comment_str = str(comment).lower()
                        comment_type = str(comment.get("commentType", "")).upper()
                        if "epitope" in comment_str or comment_type == "IMMUNOLOGY":
                            epitopes_data.append(comment)

                # Check features for epitope sites
                if "features" in protein_data:
                    for feature in protein_data["features"]:
                        feature_str = str(feature).lower()
                        feature_type = str(feature.get("type", "")).lower()
                        if "epitope" in feature_str or "epitope" in feature_type:
                            epitopes_data.append(feature)

                return {
                    "status": "success",
                    "data": epitopes_data,
                    "url": response.url,
                    "count": len(epitopes_data),
                    "note": "Epitope data extracted from main protein endpoint (epitopes endpoint not available). Includes immunology comments and epitope features if present.",
                    "fallback_used": True,
                    "source": "main_protein_endpoint",
                }

            elif tool_name == "proteins_api_get_features":
                # Extract features directly from main protein endpoint
                features_data = protein_data.get("features", [])
                return {
                    "status": "success",
                    "data": features_data,
                    "url": response.url,
                    "count": len(features_data),
                    "note": "Features extracted from main protein endpoint (features endpoint not available as separate endpoint).",
                    "fallback_used": True,
                    "source": "main_protein_endpoint",
                }

            elif tool_name == "proteins_api_get_comments":
                # Extract comments directly from main protein endpoint
                comments_data = protein_data.get("comments", [])
                return {
                    "status": "success",
                    "data": comments_data,
                    "url": response.url,
                    "count": len(comments_data),
                    "note": "Comments extracted from main protein endpoint (comments endpoint not available as separate endpoint).",
                    "fallback_used": True,
                    "source": "main_protein_endpoint",
                }

            elif tool_name == "proteins_api_get_xrefs":
                # Extract cross-references (dbReferences) from main protein endpoint
                xrefs_data = protein_data.get("dbReferences", [])
                return {
                    "status": "success",
                    "data": xrefs_data,
                    "url": response.url,
                    "count": len(xrefs_data),
                    "note": "Cross-references extracted from main protein endpoint (xrefs endpoint not available as separate endpoint).",
                    "fallback_used": True,
                    "source": "main_protein_endpoint",
                }

            elif tool_name == "proteins_api_get_publications":
                # Extract references (publications) from main protein endpoint
                publications_data = protein_data.get("references", [])
                return {
                    "status": "success",
                    "data": publications_data,
                    "url": response.url,
                    "count": len(publications_data),
                    "note": "Publications extracted from main protein endpoint (publications endpoint not available as separate endpoint).",
                    "fallback_used": True,
                    "source": "main_protein_endpoint",
                }

            elif tool_name == "proteins_api_get_genome_mappings":
                # Extract genome-related cross-references (Ensembl, RefSeq, etc.)
                genome_mappings = []
                db_references = protein_data.get("dbReferences", [])

                # Look for Ensembl, RefSeq, and other genome-related cross-references
                genome_db_types = ["Ensembl", "RefSeq", "EMBL", "GenBank"]
                for ref in db_references:
                    ref_type = ref.get("type", "")
                    if ref_type in genome_db_types:
                        # Try to extract genome-related information
                        mapping_entry = {
                            "database": ref_type,
                            "id": ref.get("id", ""),
                            "properties": ref.get("properties", {}),
                        }
                        genome_mappings.append(mapping_entry)

                return {
                    "status": "success",
                    "data": genome_mappings,
                    "url": response.url,
                    "count": len(genome_mappings),
                    "note": "Genome mappings extracted from cross-references in main protein endpoint (genome endpoint not available as separate endpoint). Includes Ensembl, RefSeq, EMBL, and GenBank cross-references that may contain genomic location information.",
                    "fallback_used": True,
                    "source": "main_protein_endpoint",
                }

        except Exception:
            return None

    def _parse_accessions(self, accession: Union[str, List[str]]) -> List[str]:
        """Parse accession parameter - handle string, list, or comma-separated string"""
        if isinstance(accession, list):
            return [str(acc).strip() for acc in accession if acc]
        elif isinstance(accession, str):
            # Check if it's comma-separated
            if "," in accession:
                return [acc.strip() for acc in accession.split(",") if acc.strip()]
            else:
                return [accession.strip()]
        else:
            return [str(accession).strip()]

    def _handle_batch_request(
        self, accessions: List[str], tool_name: str, format: str = "json"
    ) -> Dict[str, Any]:
        """Handle batch requests by making multiple API calls and aggregating results"""
        results = []
        errors = []
        successful_count = 0

        # Use ThreadPoolExecutor for parallel requests (max 5 concurrent)
        max_workers = min(5, len(accessions))

        def fetch_single(
            acc: str,
        ) -> tuple[str, Optional[Dict[str, Any]], Optional[str]]:
            """Fetch data for a single accession"""
            try:
                # Build arguments for single accession
                single_args = {"accession": acc, "format": format}
                url = self._build_url(single_args)
                params = self._build_params(single_args)

                # For variants tool, params should contain accession
                if tool_name == "proteins_api_get_variants":
                    params["accession"] = acc

                response = self.session.get(url, params=params, timeout=self.timeout)

                # Handle fallback for endpoints that may not exist
                fallback_tools = [
                    "proteins_api_get_proteomics",
                    "proteins_api_get_epitopes",
                    "proteins_api_get_features",
                    "proteins_api_get_comments",
                    "proteins_api_get_xrefs",
                    "proteins_api_get_publications",
                    "proteins_api_get_genome_mappings",
                ]

                if tool_name in fallback_tools and response.status_code == 404:
                    fallback_result = self._extract_from_protein_endpoint(
                        acc, tool_name
                    )
                    if fallback_result:
                        return (acc, fallback_result, None)

                response.raise_for_status()
                data = response.json()

                return (
                    acc,
                    {"status": "success", "data": data, "url": response.url},
                    None,
                )
            except Exception as e:
                return (acc, None, str(e))

        # Execute requests in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_acc = {
                executor.submit(fetch_single, acc): acc for acc in accessions
            }

            for future in as_completed(future_to_acc):
                acc, result, error = future.result()
                if result:
                    results.append({"accession": acc, **result})
                    successful_count += 1
                else:
                    errors.append({"accession": acc, "error": error})

        # Aggregate results
        response_data = {
            "status": "success" if successful_count > 0 else "error",
            "data": results,
            "count": successful_count,
            "total_requested": len(accessions),
            "errors": errors if errors else None,
        }

        if errors:
            response_data["note"] = (
                f"Successfully retrieved {successful_count} of {len(accessions)} accessions. {len(errors)} accessions failed."
            )

        return response_data

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Proteins API call"""
        tool_name = self.tool_config.get("name", "")

        # Check if this is a batch operation (accession is list or comma-separated)
        # Only apply to tools that use accession parameter
        batch_tools = [
            "proteins_api_get_protein",
            "proteins_api_get_variants",
            "proteins_api_get_proteomics",
            "proteins_api_get_epitopes",
            "proteins_api_get_features",
            "proteins_api_get_comments",
            "proteins_api_get_xrefs",
            "proteins_api_get_publications",
            "proteins_api_get_genome_mappings",
        ]

        # Feature-111B-007: gene_symbol/gene as aliases for query in proteins_api_search
        if tool_name == "proteins_api_search" and not arguments.get("query"):
            gene_alias = arguments.get("gene_symbol") or arguments.get("gene")
            if gene_alias:
                arguments = dict(arguments, query=gene_alias)

        if tool_name in batch_tools and "accession" in arguments:
            accession = arguments.get("accession")
            accessions = self._parse_accessions(accession)

            # If multiple accessions, use batch handler
            if len(accessions) > 1:
                format_param = arguments.get("format", "json")
                return self._handle_batch_request(accessions, tool_name, format_param)
            # Single accession - continue with normal flow
            elif len(accessions) == 1:
                arguments["accession"] = accessions[0]

        try:
            url = self._build_url(arguments)
            params = self._build_params(arguments)

            response = self.session.get(url, params=params, timeout=self.timeout)

            # Handle endpoints that may not exist - fallback to main protein endpoint
            fallback_tools = [
                "proteins_api_get_proteomics",
                "proteins_api_get_epitopes",
                "proteins_api_get_features",
                "proteins_api_get_comments",
                "proteins_api_get_xrefs",
                "proteins_api_get_publications",
                "proteins_api_get_genome_mappings",
            ]
            if tool_name in fallback_tools:
                if response.status_code == 404:
                    fallback_result = self._extract_from_protein_endpoint(
                        arguments.get("accession", ""), tool_name
                    )
                    if fallback_result:
                        return fallback_result

            # Handle search endpoint which may not exist
            if tool_name == "proteins_api_search" and response.status_code == 400:
                return {
                    "status": "error",
                    "error": "Proteins API search endpoint may not be available. Use proteins_api_get_protein with a specific accession instead, or use EBI Search API with 'uniprot' domain.",
                    "url": response.url,
                    "suggestion": "Try using ebi_search_domain with domain='uniprot' and your query instead.",
                }

            response.raise_for_status()
            data = response.json()

            # Feature-81B-fallback: if gene-name search returns empty,
            # retry with protein= param (e.g. "insulin" is a protein name, not gene symbol)
            if (
                tool_name == "proteins_api_search"
                and isinstance(data, list)
                and len(data) == 0
                and "gene" in params
            ):
                retry_params = dict(params)
                retry_params.pop("gene")
                retry_params["protein"] = arguments.get("query", "")
                retry_resp = self.session.get(
                    url, params=retry_params, timeout=self.timeout
                )
                if retry_resp.status_code == 200:
                    retry_data = retry_resp.json()
                    if isinstance(retry_data, list) and len(retry_data) > 0:
                        data = retry_data
                        # Update response for URL tracking
                        response = retry_resp

            # Cap features per entry to avoid 25MB+ responses for heavily-annotated proteins
            if tool_name == "proteins_api_get_variants" and isinstance(data, list):
                max_variants = int(arguments.get("max_variants", 200))
                for entry in data:
                    if isinstance(entry, dict) and "features" in entry:
                        features = entry["features"]
                        if len(features) > max_variants:
                            entry["features"] = features[:max_variants]
                            entry["features_truncated"] = True
                            entry["total_features"] = len(features)

            # For gene-name searches, sort exact gene matches to the top
            if (
                tool_name == "proteins_api_search"
                and isinstance(data, list)
                and "query" in arguments
            ):
                query_upper = arguments["query"].strip().upper()

                def _gene_sort_key(entry):
                    primary = (
                        entry.get("gene", [{}])[0].get("name", {}).get("value", "")
                        if entry.get("gene")
                        else ""
                    )
                    return 0 if primary.upper() == query_upper else 1

                data = sorted(data, key=_gene_sort_key)

            response_data = {
                "status": "success",
                "data": data,
                "url": response.url,
            }

            if isinstance(data, list):
                response_data["count"] = len(data)
            elif isinstance(data, dict):
                if "results" in data and isinstance(data["results"], list):
                    response_data["count"] = len(data["results"])

            return response_data

        except requests.exceptions.RequestException as e:
            tool_name = self.tool_config.get("name", "")

            # For endpoints that may not exist, try fallback
            fallback_tools = [
                "proteins_api_get_proteomics",
                "proteins_api_get_epitopes",
                "proteins_api_get_features",
                "proteins_api_get_comments",
                "proteins_api_get_xrefs",
                "proteins_api_get_publications",
                "proteins_api_get_genome_mappings",
            ]
            if tool_name in fallback_tools:
                # Check if it's a 404 error (either in exception message or response status)
                is_404 = "404" in str(e) or (
                    hasattr(e, "response")
                    and e.response is not None
                    and e.response.status_code == 404
                )
                if is_404:
                    fallback_result = self._extract_from_protein_endpoint(
                        arguments.get("accession", ""), tool_name
                    )
                    if fallback_result:
                        return fallback_result

            # For variations endpoint, provide helpful error
            if tool_name == "proteins_api_get_variants":
                if "404" in str(e):
                    return {
                        "status": "error",
                        "error": "No variations found for this protein accession.",
                        "url": url if "url" in locals() else None,
                        "note": "The protein may not have annotated variants. Try using proteins_api_get_protein to get other protein information.",
                    }
                elif "400" in str(e):
                    return {
                        "status": "error",
                        "error": "Invalid accession format for variation query.",
                        "url": url if "url" in locals() else None,
                        "note": "Ensure you're using a valid UniProt accession (e.g., P05067).",
                    }
            return {
                "status": "error",
                "error": f"Proteins API error: {str(e)}",
                "url": url if "url" in locals() else None,
            }
        except Exception as e:
            tool_name = self.tool_config.get("name", "")
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "url": url if "url" in locals() else None,
            }
