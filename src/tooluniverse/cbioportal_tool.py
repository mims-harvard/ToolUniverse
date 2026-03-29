import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("CBioPortalRESTTool")
class CBioPortalRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.cbioportal.org/api"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "ToolUniverse/1.0",
            }
        )
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        url = self.tool_config["fields"]["endpoint"]
        for k, v in args.items():
            url = url.replace(f"{{{k}}}", str(v))
        return url

    def _get_gene_entrez_ids(self, gene_symbols: str) -> list[int]:
        """Convert gene symbols to Entrez IDs"""
        genes = [g.strip() for g in gene_symbols.split(",")]
        entrez_ids = []

        for gene in genes:
            response = self.session.get(
                f"{self.base_url}/genes?keyword={gene}", timeout=self.timeout
            )
            if response.status_code == 200:
                gene_data = response.json()
                if gene_data:
                    entrez_ids.append(gene_data[0].get("entrezGeneId"))

        return entrez_ids

    def _get_mutation_profile_id(self, study_id: str) -> str:
        """Get the mutation molecular profile ID for a study"""
        response = self.session.get(
            f"{self.base_url}/studies/{study_id}/molecular-profiles",
            timeout=self.timeout,
        )
        if response.status_code == 200:
            profiles = response.json()
            for profile in profiles:
                alt_type = profile.get("molecularAlterationType")
                if alt_type == "MUTATION_EXTENDED":
                    return profile.get("molecularProfileId")

        # Fallback to common naming pattern
        return f"{study_id}_mutations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if "query" in arguments and "keyword" not in arguments:
                arguments = {**arguments, "keyword": arguments["query"]}
            if (
                "get_genes" in self.tool_config.get("name", "")
                and "keyword" not in arguments
            ):
                return {
                    "status": "error",
                    "error": "keyword or query parameter is required",
                }
            method = self.tool_config["fields"].get("method", "GET")
            url = self._build_url(arguments)

            # Special handling for mutation queries with new API
            if "cBioPortal_get_mutations" in self.tool_config.get("name", ""):
                study_id = arguments.get("study_id")
                gene_list = arguments.get("gene_list")
                sample_list_id = arguments.get("sample_list_id")

                # Get molecular profile ID
                profile_id = self._get_mutation_profile_id(study_id)

                # Get gene Entrez IDs
                entrez_ids = self._get_gene_entrez_ids(gene_list)

                if not entrez_ids:
                    error_msg = f"Could not find Entrez IDs for genes: {gene_list}"
                    return {"status": "error", "error": error_msg}

                # Use the new API endpoint
                url = f"{self.base_url}/molecular-profiles/{profile_id}/mutations/fetch"

                # Build payload
                payload = {"entrezGeneIds": entrez_ids}

                # Add sample filter if provided, otherwise use all samples
                if sample_list_id:
                    payload["sampleListId"] = sample_list_id
                else:
                    payload["sampleListId"] = f"{study_id}_all"

                response = self.session.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                return {
                    "status": "success",
                    "data": data,
                    "url": url,
                    "count": len(data) if isinstance(data, list) else 1,
                    "molecular_profile_id": profile_id,
                    "entrez_gene_ids": entrez_ids,
                }

            # Handle regular GET or POST requests
            if method == "POST":
                payload = self.tool_config["fields"].get("payload", {})
                # Replace placeholders in payload
                for k, v in arguments.items():
                    if isinstance(payload, dict):
                        for pk, pv in payload.items():
                            if isinstance(pv, str):
                                payload[pk] = pv.replace(f"{{{k}}}", str(v))

                response = self.session.post(url, json=payload, timeout=self.timeout)
            else:
                response = self.session.get(url, timeout=self.timeout)

            response.raise_for_status()
            data = response.json()

            return {
                "status": "success",
                "data": data,
                "url": url,
                "count": len(data) if isinstance(data, list) else 1,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"cBioPortal API error: {str(e)}",
                "url": url if "url" in locals() else "unknown",
            }
