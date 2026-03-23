import time
import requests
from typing import Any, Dict, Optional
from .base_tool import BaseTool, ToolError
from .tool_registry import register_tool


@register_tool("UniProtRESTTool")
class UniProtRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.endpoint = tool_config["fields"]["endpoint"]
        self.extract_path = tool_config["fields"].get("extract_path")
        self.timeout = 15  # Increase timeout for large entries

    def validate_parameters(self, arguments: Dict[str, Any]) -> Optional[ToolError]:
        """
        Validate parameters with automatic type coercion for limit.
        """
        # Coerce limit to integer if passed as string
        if "limit" in arguments and isinstance(arguments["limit"], str):
            try:
                arguments["limit"] = int(arguments["limit"])
            except (ValueError, TypeError):
                # Let schema validation handle the error
                pass

        # Call parent validation
        return super().validate_parameters(arguments)

    def _build_url(self, args: Dict[str, Any]) -> str:
        url = self.endpoint
        for k, v in args.items():
            url = url.replace(f"{{{k}}}", str(v))
        return url

    def _extract_data(self, data: Dict, extract_path: str) -> Any:
        """Custom data extraction with support for filtering"""

        # Handle specific UniProt extraction patterns
        if extract_path == ("comments[?(@.commentType=='FUNCTION')].texts[*].value"):
            # Extract function comments
            result = []
            for comment in data.get("comments", []):
                if comment.get("commentType") == "FUNCTION":
                    for text in comment.get("texts", []):
                        if "value" in text:
                            result.append(text["value"])
            return result

        elif extract_path == (
            "comments[?(@.commentType=="
            "'SUBCELLULAR LOCATION')].subcellularLocations[*].location.value"
        ):
            # Extract subcellular locations
            result = []
            for comment in data.get("comments", []):
                if comment.get("commentType") == "SUBCELLULAR LOCATION":
                    for location in comment.get("subcellularLocations", []):
                        if "location" in location and ("value" in location["location"]):
                            result.append(location["location"]["value"])
            return result

        elif extract_path == "features[?(@.type=='VARIANT')]":
            # Extract variant features
            result = []
            for feature in data.get("features", []):
                if feature.get("type") == "Natural variant":
                    result.append(feature)
            return result

        elif extract_path == (
            "features[?(@.type=='MODIFIED RESIDUE' || @.type=='SIGNAL')]"
        ):
            # Extract PTM and signal features
            result = []
            for feature in data.get("features", []):
                if feature.get("type") in ["Modified residue", "Signal"]:
                    result.append(feature)
            return result

        elif extract_path == (
            "comments[?(@.commentType=="
            "'ALTERNATIVE PRODUCTS')].isoforms[*].isoformIds[*]"
        ):
            # Extract isoform IDs
            result = []
            for comment in data.get("comments", []):
                if comment.get("commentType") == "ALTERNATIVE PRODUCTS":
                    for isoform in comment.get("isoforms", []):
                        for isoform_id in isoform.get("isoformIds", []):
                            result.append(isoform_id)
            return result

        # For simple paths, use jsonpath_ng
        try:
            from jsonpath_ng import parse

            expr = parse(extract_path)
            matches = expr.find(data)
            extracted_data = [m.value for m in matches]

            # Return single item if only one match, otherwise return list
            if len(extracted_data) == 0:
                return {"error": f"No data found for JSONPath: {extract_path}"}
            elif len(extracted_data) == 1:
                return extracted_data[0]
            else:
                return extracted_data

        except ImportError:
            return {"error": "jsonpath_ng library is required for data extraction"}
        except Exception as e:
            return {
                "error": (
                    f"Failed to extract UniProt fields using "
                    f"JSONPath '{extract_path}': {e}"
                )
            }

    def _handle_search(self, arguments: Dict[str, Any]) -> Any:
        """Handle search queries with flexible parameters"""
        query = arguments.get("query", "")
        organism = arguments.get("organism", "")
        fields = arguments.get("fields")
        min_length = arguments.get("min_length")
        max_length = arguments.get("max_length")

        # Coerce limit to integer if passed as string
        limit_value = arguments.get("limit", 25)
        if isinstance(limit_value, str):
            limit_value = int(limit_value)
        limit = min(limit_value, 500)

        # Normalize query: replace 'organism:' with 'organism_id:'
        # for UniProt API compatibility
        query = query.replace("organism:", "organism_id:")

        # Build query string
        query_parts = [query]
        if organism:
            # Support common organism names (both common names and scientific names)
            organism_map = {
                "human": "9606",
                "homo sapiens": "9606",
                "mouse": "10090",
                "mus musculus": "10090",
                "rat": "10116",
                "rattus norvegicus": "10116",
                "yeast": "559292",
                "saccharomyces cerevisiae": "559292",
                "zebrafish": "7955",
                "danio rerio": "7955",
                "fruitfly": "7227",
                "drosophila melanogaster": "7227",
                "c. elegans": "6239",
                "caenorhabditis elegans": "6239",
                "arabidopsis": "3702",
                "arabidopsis thaliana": "3702",
                "pig": "9823",
                "sus scrofa": "9823",
                "cow": "9913",
                "bos taurus": "9913",
                "rabbit": "9986",
                "oryctolagus cuniculus": "9986",
            }
            taxon_id = organism_map.get(organism.lower(), organism)

            # Check if query already includes organism_id filter
            # to avoid duplication
            if "organism_id:" not in query.lower():
                query_parts.append(f"organism_id:{taxon_id}")
            # If it does, skip adding the organism filter

        # Auto-convert length parameters to range syntax
        if min_length or max_length:
            min_val = min_length if min_length else "*"
            max_val = max_length if max_length else "*"
            query_parts.append(f"length:[{min_val} TO {max_val}]")

        full_query = " AND ".join(query_parts)

        # Build parameters
        params = {"query": full_query, "size": str(limit), "format": "json"}

        # Add fields parameter if specified
        if fields and isinstance(fields, list):
            params["fields"] = ",".join(fields)

        url = "https://rest.uniprot.org/uniprotkb/search"

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            # Extract results
            results = data.get("results", [])

            # If custom fields requested, return raw API response for flexibility
            if fields and isinstance(fields, list):
                return {
                    "total_results": data.get("resultsFound", 0),
                    "returned": len(results),
                    "results": results,  # Return raw results when custom fields used
                }

            # Otherwise, use formatted extraction logic
            formatted_results = []

            for entry in results:
                formatted_entry = {
                    "accession": entry.get("primaryAccession", ""),
                    "id": entry.get("uniProtkbId", ""),
                    "protein_name": "",
                    "gene_names": [],
                    "organism": "",
                    "length": 0,
                }

                # Extract protein name
                protein_desc = entry.get("proteinDescription", {})
                rec_name = protein_desc.get("recommendedName", {})
                if rec_name:
                    full_name = rec_name.get("fullName", {})
                    if full_name:
                        formatted_entry["protein_name"] = full_name.get("value", "")

                # Extract gene names
                genes = entry.get("genes", [])
                for gene in genes:
                    gene_name = gene.get("geneName", {})
                    if gene_name:
                        formatted_entry["gene_names"].append(gene_name.get("value", ""))

                # Extract organism
                organism_info = entry.get("organism", {})
                formatted_entry["organism"] = organism_info.get("scientificName", "")

                # Extract sequence length
                sequence = entry.get("sequence", {})
                formatted_entry["length"] = sequence.get("length", 0)

                formatted_results.append(formatted_entry)

            return {
                "total_results": data.get("resultsFound", len(results)),
                "returned": len(results),
                "results": formatted_results,
            }

        except requests.exceptions.Timeout:
            return {"error": "Request to UniProt API timed out"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request to UniProt API failed: {e}"}
        except ValueError as e:
            return {"error": f"Failed to parse JSON response: {e}", "retryable": True}

    def _handle_id_mapping(self, arguments: Dict[str, Any]) -> Any:
        """Handle ID mapping requests"""

        ids = arguments.get("ids", [])
        from_db = arguments.get("from_db", "")
        to_db = arguments.get("to_db", "UniProtKB")
        # UniProt mapping jobs can take >30s even for small inputs.
        max_wait_time = arguments.get("max_wait_time", 120)

        # Normalize IDs to list
        if isinstance(ids, str):
            ids = [ids]

        # Normalize database names
        # Map user-friendly names to UniProt ID mapping database names.
        # Important: do NOT map target UniProtKB to UniProtKB_AC-ID.
        db_mapping = {
            "Ensembl": "Ensembl",
            "Gene_Name": "Gene_Name",
            "RefSeq_Protein": "RefSeq_Protein_ID",
            "EMBL": "EMBL_ID",
            "UniProtKB": "UniProtKB",
            "UniProtKB_AC-ID": "UniProtKB_AC-ID",
        }
        from_db_normalized = db_mapping.get(from_db, from_db)
        to_db_normalized = db_mapping.get(to_db, to_db)

        # Step 1: Submit mapping job
        submit_url = "https://rest.uniprot.org/idmapping/run"
        # UniProt ID mapping API expects application/x-www-form-urlencoded,
        # not JSON.
        payload = {
            "ids": ",".join(ids),
            "from": from_db_normalized,
            "to": to_db_normalized,
        }

        try:
            resp = requests.post(submit_url, data=payload, timeout=self.timeout)
            resp.raise_for_status()
            job_data = resp.json()
            job_id = job_data.get("jobId")

            if not job_id:
                return {
                    "status": "error",
                    "data": {"error": "Failed to get job ID from UniProt ID mapping"},
                }

            # Step 2: Poll for job completion
            status_url = f"https://rest.uniprot.org/idmapping/status/{job_id}"
            results_url = f"https://rest.uniprot.org/idmapping/results/{job_id}"

            raw_results = None
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                status_resp = requests.get(status_url, timeout=self.timeout)
                status_data = status_resp.json()

                job_status = status_data.get("jobStatus") or status_data.get("status")

                if job_status == "FINISHED":
                    # Explicit FINISHED status — fetch results separately
                    results_resp = requests.get(results_url, timeout=self.timeout)
                    raw_results = results_resp.json().get("results", [])
                    break
                elif "results" in status_data:
                    # Feature-26A-13: UniProt status endpoint redirected (303) to
                    # results page; results are embedded directly in status_data.
                    raw_results = status_data["results"]
                    break
                elif job_status in ("FAILED", "ERROR"):
                    return {
                        "status": "error",
                        "error": "ID mapping job failed",
                    }

                time.sleep(1)  # Wait 1 second before next poll

            if raw_results is None:
                return {
                    "status": "error",
                    "error": (
                        f"UniProt ID mapping job did not complete within "
                        f"{max_wait_time}s. Try again or reduce the number of IDs."
                    ),
                }

            # Step 3: Parse results
            # UniProt returns `to` as a plain string (for simple DB mappings like
            # PDB) or as a full UniProtKB entry dict. Flatten both into a simple
            # from/to pair.
            formatted_results = []
            for result in raw_results:
                from_value = result.get("from", "")
                to_value = result.get("to")
                if isinstance(to_value, dict):
                    # UniProtKB entry: extract accession and gene name
                    gene_names = to_value.get("geneNames", [])
                    gene_name = gene_names[0].get("value", "") if gene_names else ""
                    formatted_results.append(
                        {
                            "from": from_value,
                            "to": {
                                "accession": to_value.get("primaryAccession", ""),
                                "id": to_value.get("uniProtkbId", ""),
                                "gene_name": gene_name,
                            },
                        }
                    )
                elif to_value is not None:
                    # Simple string mapping (PDB, Ensembl, etc.)
                    formatted_results.append({"from": from_value, "to": str(to_value)})

            result_data = {
                "mapped_count": len(formatted_results),
                "results": formatted_results,
                "failed_ids": [],
            }
            return {"status": "success", "data": result_data}

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "data": {"error": "Request to UniProt API timed out"},
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "data": {"error": f"Request to UniProt API failed: {e}"},
            }
        except ValueError as e:
            return {
                "status": "error",
                "data": {"error": f"Failed to parse JSON response: {e}"},
            }

    def _handle_uniref_search(self, arguments: Dict[str, Any]) -> Any:
        """Handle UniRef search queries"""
        query = arguments.get("query", "")
        cluster_type = arguments.get("cluster_type", "")
        limit_value = arguments.get("limit", 25)
        if isinstance(limit_value, str):
            limit_value = int(limit_value)
        limit = min(limit_value, 500)

        # Build query - if cluster_type specified and not in query, add it
        # Note: UniRef search accepts queries like "P04637" or "id:UniRef50_P04637"
        full_query = query
        if cluster_type and "uniref" not in query.lower():
            # User can filter by cluster type in their query if needed
            # For now, just use the query as-is - API will return matching clusters
            pass

        params = {"query": full_query, "size": str(limit), "format": "json"}
        url = "https://rest.uniprot.org/uniref/search"

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            return {
                "total_results": data.get("resultsFound", len(results)),
                "returned": len(results),
                "results": results,
            }
        except requests.exceptions.Timeout:
            return {"error": "Request to UniProt API timed out"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request to UniProt API failed: {e}"}
        except ValueError as e:
            return {"error": f"Failed to parse JSON response: {e}", "retryable": True}

    def _handle_uniparc_search(self, arguments: Dict[str, Any]) -> Any:
        """Handle UniParc search queries"""
        query = arguments.get("query", "")
        limit_value = arguments.get("limit", 25)
        if isinstance(limit_value, str):
            limit_value = int(limit_value)
        limit = min(limit_value, 500)

        params = {"query": query, "size": str(limit), "format": "json"}
        url = "https://rest.uniprot.org/uniparc/search"

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            return {
                "total_results": data.get("resultsFound", len(results)),
                "returned": len(results),
                "results": results,
            }
        except requests.exceptions.Timeout:
            return {"error": "Request to UniProt API timed out"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request to UniProt API failed: {e}"}
        except ValueError as e:
            return {"error": f"Failed to parse JSON response: {e}", "retryable": True}

    def run(self, arguments: Dict[str, Any]) -> Any:
        # Check if this is a search request
        search_type = self.tool_config.get("fields", {}).get("search_type")
        mapping_type = self.tool_config.get("fields", {}).get("mapping_type")

        if search_type == "search":
            return self._handle_search(arguments)
        elif search_type == "uniref_search":
            return self._handle_uniref_search(arguments)
        elif search_type == "uniparc_search":
            return self._handle_uniparc_search(arguments)
        elif mapping_type == "async":
            return self._handle_id_mapping(arguments)

        # Build URL for standard accession-based queries
        url = self._build_url(arguments)
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return {
                    "error": (f"UniProt API returned status code: {resp.status_code}"),
                    "detail": resp.text,
                }
            data = resp.json()
        except requests.exceptions.Timeout:
            return {"error": "Request to UniProt API timed out"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request to UniProt API failed: {e}"}
        except ValueError as e:
            return {"error": f"Failed to parse JSON response: {e}", "retryable": True}

        # If extract_path is configured, extract the corresponding subset
        if self.extract_path:
            result = self._extract_data(data, self.extract_path)

            # Handle empty results
            if isinstance(result, list) and len(result) == 0:
                return {"error": f"No data found for path: {self.extract_path}"}
            elif isinstance(result, dict) and "error" in result:
                return result

            return result

        return data

    # Method bindings for backward compatibility
    def get_entry_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})

    def get_function_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})

    def get_names_taxonomy_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})

    def get_subcellular_location_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})

    def get_disease_variants_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})

    def get_ptm_processing_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})

    def get_sequence_isoforms_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})
