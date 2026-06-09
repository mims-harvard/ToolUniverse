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

    _ALTERATION_LABELS = {
        -2: "deep_deletion",
        -1: "shallow_loss",
        0: "neutral",
        1: "gain",
        2: "amplification",
    }

    def _get_cna_profile_id(self, study_id: str) -> str:
        """Get the discrete (GISTIC) copy-number molecular profile ID for a study."""
        response = self.session.get(
            f"{self.base_url}/studies/{study_id}/molecular-profiles",
            timeout=self.timeout,
        )
        if response.status_code == 200:
            for profile in response.json():
                if (
                    profile.get("molecularAlterationType") == "COPY_NUMBER_ALTERATION"
                    and profile.get("datatype") == "DISCRETE"
                ):
                    return profile.get("molecularProfileId")
        # Fallback to the common GISTIC naming pattern.
        return f"{study_id}_gistic"

    def _fetch_discrete_cna(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch discrete copy-number alteration (CNA) calls for a gene in a study.

        Returns per-sample alteration values (-2,-1,0,1,2 = deep-deletion,
        shallow-loss, neutral, gain, amplification) from GISTIC profiles, plus a
        count breakdown by alteration type.
        """
        study_id = arguments.get("study_id")
        if not study_id:
            return {"status": "error", "error": "study_id parameter is required"}

        gene_list = arguments.get("gene_list") or arguments.get("gene")
        if not gene_list:
            return {"status": "error", "error": "gene_list parameter is required"}

        event_type = (arguments.get("alteration_type") or "ALL").upper()
        valid_events = {"AMP", "GAIN", "DIPLOID", "HETLOSS", "HOMDEL", "ALL"}
        if event_type not in valid_events:
            event_type = "ALL"

        # Resolve molecular profile (allow explicit override).
        profile_id = arguments.get("molecular_profile_id") or self._get_cna_profile_id(
            study_id
        )

        # Resolve gene symbols -> Entrez IDs.
        entrez_ids = self._get_gene_entrez_ids(gene_list)
        entrez_ids = [e for e in entrez_ids if e is not None]
        if not entrez_ids:
            return {
                "status": "error",
                "error": f"Could not find Entrez IDs for genes: {gene_list}",
            }

        sample_list_id = arguments.get("sample_list_id") or f"{study_id}_all"

        url = (
            f"{self.base_url}/molecular-profiles/{profile_id}"
            f"/discrete-copy-number/fetch?projection=SUMMARY"
        )
        if event_type != "ALL":
            url += f"&discreteCopyNumberEventType={event_type}"

        payload = {"entrezGeneIds": entrez_ids, "sampleListId": sample_list_id}
        response = self.session.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            data = []

        # Tally alteration values into human-readable categories.
        counts: Dict[str, int] = {}
        for rec in data:
            label = self._ALTERATION_LABELS.get(rec.get("alteration"), "unknown")
            counts[label] = counts.get(label, 0) + 1

        return {
            "status": "success",
            "data": data,
            "url": url,
            "count": len(data),
            "molecular_profile_id": profile_id,
            "entrez_gene_ids": entrez_ids,
            "alteration_type": event_type,
            "alteration_counts": counts,
        }

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

            # Special handling for discrete copy-number alteration (CNA) queries.
            if "cBioPortal_get_copy_number_alterations" in self.tool_config.get(
                "name", ""
            ):
                return self._fetch_discrete_cna(arguments)

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
