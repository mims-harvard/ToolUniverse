import re
import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

_EFO_ID_RE = re.compile(r"^[A-Z]+[_:]\d+")


class GWASRESTTool(BaseTool):
    """Base class for GWAS Catalog REST API tools."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/gwas/rest/api"
        self.endpoint = ""  # Will be set by subclasses

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make a request to the GWAS Catalog API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}

    def _coerce_str(self, value: Any) -> Optional[str]:
        """Return a stripped string, or None."""
        if not isinstance(value, str):
            return None
        s = value.strip()
        return s or None

    def _coerce_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _efo_id_from_uri_or_id(self, value: Any) -> Optional[str]:
        """
        Best-effort normalize an EFO/OBA/etc identifier.

        Accepts either a full URI (e.g., 'http://www.ebi.ac.uk/efo/OBA_2050062')
        or a bare ID (e.g., 'OBA_2050062' or 'OBA:2050062').

        Note: The GWAS Catalog v2 REST API supports filtering by `efo_id` (and
        sometimes `efo_trait`) on associations/studies endpoints. Passing a full
        URI via `efo_uri` is not consistently supported; we normalize to `efo_id`.
        """
        s = self._coerce_str(value)
        if not s:
            return None
        if s.startswith(("http://", "https://")):
            s = s.rstrip("/").rsplit("/", 1)[-1]
        # Support CURIE-style IDs like "EFO:0001645" or "OBA:2050062" by converting
        # ":" to "_" (GWAS Catalog expects underscore form, e.g., "EFO_0001645").
        if ":" in s and "/" not in s and " " not in s:
            left, right = s.split(":", 1)
            if left and right:
                s = f"{left}_{right}"
        s = s.strip()
        return s or None

    def _resolve_trait_to_efo_id(self, disease_trait: str) -> Optional[str]:
        """Resolve a disease trait name to an EFO ID.

        Tries the GWAS Catalog efoTraits endpoint first, then falls back to
        a study-based resolution. The /v2/associations endpoint ignores the
        disease_trait query parameter, so we must resolve to an EFO ID.
        """
        # Primary: GWAS Catalog efoTraits endpoint (v1)
        try:
            resp = requests.get(
                f"{self.base_url}/efoTraits/search/findByEfoTrait",
                params={"trait": disease_trait},
                timeout=15,
            )
            if resp.status_code == 200:
                traits = resp.json().get("_embedded", {}).get("efoTraits", [])
                if traits:
                    short_name = traits[0].get("shortForm")
                    if short_name:
                        return short_name
        except Exception:
            pass

        # Fallback: search studies by disease_trait, extract efo_id from first result
        try:
            resp = requests.get(
                f"{self.base_url}/v2/studies",
                params={"disease_trait": disease_trait, "size": 1},
                timeout=15,
            )
            if resp.status_code == 200:
                studies = resp.json().get("_embedded", {}).get("studies", [])
                if studies:
                    efo_traits = studies[0].get("efo_traits", [])
                    if efo_traits:
                        efo_id = efo_traits[0].get("efo_id")
                        if efo_id:
                            return efo_id
        except Exception:
            pass

        return None

    def _resolve_trait_or_error(
        self, disease_trait: Optional[str], efo_id: Optional[str]
    ) -> Dict[str, Any]:
        """Resolve disease_trait to efo_id if needed.

        Returns {"efo_id": <str>} on success, or {"error": <dict>} when
        resolution fails and would produce an unfiltered query.
        Callers check ``"error" in result`` and return ``result["error"]``.
        """
        if disease_trait and not efo_id:
            resolved = self._resolve_trait_to_efo_id(disease_trait)
            if resolved:
                return {"efo_id": resolved}
            return {
                "error": {
                    "status": "error",
                    "error": (
                        f"Could not resolve trait '{disease_trait}' to an EFO ID. "
                        "GWAS Catalog uses specific EFO/MONDO terms. "
                        "For drug response traits, use the underlying disease instead "
                        "(e.g., 'depression' or 'major depressive disorder' instead of "
                        "'antidepressant response'). Or provide efo_id directly "
                        "(e.g., 'MONDO_0002009' for major depressive disorder, "
                        "'EFO_0000305' for breast carcinoma)."
                    ),
                },
            }
        return {"efo_id": efo_id}

    @staticmethod
    def _empty_result_note(efo_id: str) -> str:
        """Return a suggestion note when no associations are found for an EFO ID."""
        return (
            f"No associations found for EFO ID '{efo_id}'. "
            "GWAS Catalog may use a broader parent term — try disease_trait "
            "with a text query (e.g., 'colorectal cancer') to find related associations."
        )

    def _add_empty_result_note(
        self, result: Dict[str, Any], efo_id: Optional[str]
    ) -> None:
        """Add a suggestion note to result if the data list is empty."""
        if efo_id and isinstance(result.get("data"), list) and not result["data"]:
            result["note"] = self._empty_result_note(efo_id)

    def _extract_embedded_data(
        self, data: Dict[str, Any], data_type: str
    ) -> Dict[str, Any]:
        """Extract data from the _embedded structure and add metadata."""
        if "error" in data:
            if "status" not in data:
                return {"status": "error", **data}
            return data

        result: Dict[str, Any] = {"status": "success", "data": [], "metadata": {}}
        metadata: Dict[str, Any] = {}

        # Extract the main data from _embedded
        if "_embedded" in data and data_type in data["_embedded"]:
            result["data"] = data["_embedded"][data_type]

        # Extract pagination metadata
        if "page" in data:
            metadata["pagination"] = data["page"]

        # Extract links metadata
        if "_links" in data:
            metadata["links"] = data["_links"]

        if metadata:
            result["metadata"] = metadata

        # If no _embedded structure and no array was extracted, keep data as empty array
        # This handles the case where API returns pagination metadata but no results

        return result

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        return self._make_request(self.endpoint, arguments)


@register_tool("GWASAssociationSearch")
class GWASAssociationSearch(GWASRESTTool):
    """Search for GWAS associations by various criteria."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/associations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for associations with optional filters."""
        params = {}

        # Handle various search parameters
        # accept 'query' and 'trait' as aliases for 'disease_trait'
        disease_trait = self._coerce_str(
            arguments.get("disease_trait")
            or arguments.get("query")
            or arguments.get("trait")
        )

        # Prefer efo_id filtering. If user provided efo_uri, normalize to efo_id.
        efo_id = self._efo_id_from_uri_or_id(arguments.get("efo_id"))
        if not efo_id:
            efo_id = self._efo_id_from_uri_or_id(arguments.get("efo_uri"))

        # Feature-111A-004: if disease_trait looks like an EFO/OBA/HP ID, treat as efo_id
        if disease_trait and not efo_id and _EFO_ID_RE.match(disease_trait):
            efo_id = self._efo_id_from_uri_or_id(disease_trait)
            disease_trait = None

        # Feature-79C: /v2/associations ignores disease_trait param server-side.
        # Auto-resolve trait name to efo_id for reliable filtering.
        # Feature-81B-008: if resolution fails, return error instead of silently
        # running an unfiltered search that returns 1M+ unrelated associations.
        if disease_trait and not efo_id:
            resolved = self._resolve_trait_to_efo_id(disease_trait)
            if resolved:
                efo_id = resolved
            else:
                return {
                    "status": "error",
                    "error": (
                        f"Could not resolve trait '{disease_trait}' to an EFO ID. "
                        "GWAS Catalog uses specific EFO/MONDO disease terms. "
                        "For drug response traits, use the underlying disease "
                        "(e.g., 'depression' instead of 'antidepressant response', "
                        "'coronary artery disease' instead of 'statin response'). "
                        "Or provide efo_id directly (e.g., 'MONDO_0002009' for "
                        "major depressive disorder, 'EFO_0001645' for myocardial infarction)."
                    ),
                }

        if efo_id:
            params["efo_id"] = efo_id

        efo_trait = self._coerce_str(arguments.get("efo_trait"))
        if efo_trait:
            params["efo_trait"] = efo_trait

        rs_id = self._coerce_str(arguments.get("rs_id"))
        if rs_id:
            params["rs_id"] = rs_id

        accession_id = self._coerce_str(arguments.get("accession_id"))
        if accession_id:
            params["accession_id"] = accession_id

        sort = self._coerce_str(arguments.get("sort"))
        if sort:
            params["sort"] = sort

        direction = self._coerce_str(arguments.get("direction"))
        if direction:
            params["direction"] = direction

        size = self._coerce_int(arguments.get("size") or arguments.get("limit"))
        if size is not None:
            params["size"] = size

        page = self._coerce_int(arguments.get("page"))
        if page is not None:
            params["page"] = page

        # Feature-81B-008: require at least one filter to prevent returning 1M+ results
        filter_keys = {"efo_id", "efo_trait", "rs_id", "accession_id"}
        if not filter_keys.intersection(params):
            return {
                "status": "error",
                "error": (
                    "At least one filter is required: disease_trait, efo_id, "
                    "efo_trait, rs_id, or accession_id."
                ),
            }

        data = self._make_request(self.endpoint, params)
        result = self._extract_embedded_data(data, "associations")

        # Client-side p_value filter (GWAS Catalog API does not support server-side p-value filtering)
        p_threshold = arguments.get("p_value") or arguments.get("p_value_threshold")
        if p_threshold is not None and result.get("status") == "success":
            try:
                p_threshold = float(p_threshold)
                assocs = result.get("data", [])
                if isinstance(assocs, list):
                    filtered = [
                        a
                        for a in assocs
                        if a.get("p_value") is not None
                        and float(a["p_value"]) <= p_threshold
                    ]
                    result["data"] = filtered
                    result.setdefault("metadata", {})["p_value_filter"] = p_threshold
                    result["metadata"]["filtered_count"] = len(filtered)
                    result["metadata"]["total_before_filter"] = len(assocs)
            except (ValueError, TypeError):
                pass

        self._add_empty_result_note(result, efo_id)
        return result


@register_tool("GWASStudySearch")
class GWASStudySearch(GWASRESTTool):
    """Search for GWAS studies by various criteria."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/studies"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for studies with optional filters."""
        params = {}

        disease_trait = self._coerce_str(arguments.get("disease_trait"))
        if disease_trait:
            params["disease_trait"] = disease_trait

        efo_id = self._efo_id_from_uri_or_id(arguments.get("efo_id"))
        if not efo_id:
            efo_id = self._efo_id_from_uri_or_id(arguments.get("efo_uri"))
        if efo_id:
            params["efo_id"] = efo_id

        efo_trait = self._coerce_str(arguments.get("efo_trait"))
        if efo_trait:
            params["efo_trait"] = efo_trait

        cohort = self._coerce_str(arguments.get("cohort"))
        if cohort:
            params["cohort"] = cohort

        if arguments.get("gxe") is not None:
            params["gxe"] = bool(arguments.get("gxe"))
        if arguments.get("full_pvalue_set") is not None:
            params["full_pvalue_set"] = bool(arguments.get("full_pvalue_set"))

        size = self._coerce_int(arguments.get("size"))
        if size is not None:
            params["size"] = size
        page = self._coerce_int(arguments.get("page"))
        if page is not None:
            params["page"] = page

        data = self._make_request(self.endpoint, params)
        return self._extract_embedded_data(data, "studies")


@register_tool("GWASSNPSearch")
class GWASSNPSearch(GWASRESTTool):
    """Search for GWAS single nucleotide polymorphisms (SNPs)."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/single-nucleotide-polymorphisms"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for SNPs with optional filters."""
        params = {}

        rs_id = arguments.get("rs_id") or arguments.get("rsid")
        if rs_id:
            params["rs_id"] = rs_id
        if "mapped_gene" in arguments:
            params["mapped_gene"] = arguments["mapped_gene"]
        if "size" in arguments:
            params["size"] = arguments["size"]
        if "page" in arguments:
            params["page"] = arguments["page"]

        data = self._make_request(self.endpoint, params)
        return self._extract_embedded_data(data, "snps")


# Get by ID tools
@register_tool("GWASAssociationByID")
class GWASAssociationByID(GWASRESTTool):
    """Get a specific GWAS association by its ID."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/associations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get association by ID."""
        if "association_id" not in arguments:
            return {"status": "error", "error": "association_id is required"}

        association_id = arguments["association_id"]
        return self._make_request(f"{self.endpoint}/{association_id}")


@register_tool("GWASStudyByID")
class GWASStudyByID(GWASRESTTool):
    """Get a specific GWAS study by its ID."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/studies"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get study by ID."""
        if "study_id" not in arguments:
            return {"status": "error", "error": "study_id is required"}

        study_id = arguments["study_id"]
        return self._make_request(f"{self.endpoint}/{study_id}")


@register_tool("GWASSNPByID")
class GWASSNPByID(GWASRESTTool):
    """Get a specific GWAS SNP by its rs ID."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/single-nucleotide-polymorphisms"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get SNP by rs ID."""
        if "rs_id" not in arguments:
            return {"status": "error", "error": "rs_id is required"}

        rs_id = arguments["rs_id"]
        return self._make_request(f"{self.endpoint}/{rs_id}")


# Specialized search tools based on common use cases from examples
@register_tool("GWASVariantsForTrait")
class GWASVariantsForTrait(GWASRESTTool):
    """Get all variants associated with a specific trait."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/associations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get variants for a trait with pagination support."""
        disease_trait = self._coerce_str(
            arguments.get("disease_trait") or arguments.get("trait")
        )
        efo_id = self._efo_id_from_uri_or_id(
            arguments.get("efo_id")
        ) or self._efo_id_from_uri_or_id(arguments.get("efo_uri"))
        efo_trait = self._coerce_str(arguments.get("efo_trait"))

        if disease_trait and not efo_id and _EFO_ID_RE.match(disease_trait):
            efo_id = self._efo_id_from_uri_or_id(disease_trait)
            disease_trait = None

        # /v2/associations ignores disease_trait — resolve to efo_id
        resolution = self._resolve_trait_or_error(disease_trait, efo_id)
        if "error" in resolution:
            return resolution["error"]
        efo_id = resolution["efo_id"]

        if not disease_trait and not efo_id and not efo_trait:
            return {
                "status": "error",
                "error": "Provide at least one of: disease_trait, efo_id (or efo_uri), efo_trait.",
            }

        page_size = (
            self._coerce_int(arguments.get("size") or arguments.get("limit")) or 200
        )
        params: Dict[str, Any] = {
            "size": page_size,
            "page": self._coerce_int(arguments.get("page")) or 0,
        }
        if efo_id:
            params["efo_id"] = efo_id
        elif efo_trait:
            params["efo_trait"] = efo_trait

        data = self._make_request(self.endpoint, params)
        result = self._extract_embedded_data(data, "associations")
        if efo_id and disease_trait:
            result["resolved_efo_id"] = efo_id
        self._add_empty_result_note(result, efo_id)
        return result


@register_tool("GWASAssociationsForTrait")
class GWASAssociationsForTrait(GWASRESTTool):
    """Get all associations for a specific trait, sorted by p-value."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/associations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get associations for a trait, sorted by significance."""
        disease_trait = self._coerce_str(
            arguments.get("disease_trait") or arguments.get("trait")
        )
        efo_id = self._efo_id_from_uri_or_id(
            arguments.get("efo_id")
        ) or self._efo_id_from_uri_or_id(arguments.get("efo_uri"))
        efo_trait = self._coerce_str(arguments.get("efo_trait"))

        if disease_trait and not efo_id and _EFO_ID_RE.match(disease_trait):
            efo_id = self._efo_id_from_uri_or_id(disease_trait)
            disease_trait = None

        # /v2/associations ignores disease_trait — resolve to efo_id
        resolution = self._resolve_trait_or_error(disease_trait, efo_id)
        if "error" in resolution:
            return resolution["error"]
        efo_id = resolution["efo_id"]

        if not disease_trait and not efo_id and not efo_trait:
            return {
                "status": "error",
                "error": "Provide at least one of: disease_trait, efo_id (or efo_uri), efo_trait.",
            }

        params: Dict[str, Any] = {
            "sort": "p_value",
            "direction": "asc",
            "size": arguments.get("size", 40),
            "page": arguments.get("page", 0),
        }
        if efo_id:
            params["efo_id"] = efo_id
        elif efo_trait:
            params["efo_trait"] = efo_trait

        data = self._make_request(self.endpoint, params)
        result = self._extract_embedded_data(data, "associations")
        if efo_id and disease_trait:
            result["resolved_efo_id"] = efo_id
        self._add_empty_result_note(result, efo_id)
        return result


@register_tool("GWASAssociationsForSNP")
class GWASAssociationsForSNP(GWASRESTTool):
    """Get all associations for a specific SNP."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/associations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get associations for a SNP."""
        rs_id = self._coerce_str(arguments.get("rs_id"))
        if not rs_id:
            return {"status": "error", "error": "rs_id is required"}

        params = {
            "rs_id": rs_id,
            "size": self._coerce_int(arguments.get("size")) or 200,
            "page": self._coerce_int(arguments.get("page")) or 0,
        }

        sort = self._coerce_str(arguments.get("sort"))
        if sort:
            params["sort"] = sort
        direction = self._coerce_str(arguments.get("direction"))
        if direction:
            params["direction"] = direction

        data = self._make_request(self.endpoint, params)
        return self._extract_embedded_data(data, "associations")


@register_tool("GWASStudiesForTrait")
class GWASStudiesForTrait(GWASRESTTool):
    """Get studies for a specific trait with optional filters."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/studies"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get studies for a trait with optional filters."""
        disease_trait = self._coerce_str(arguments.get("disease_trait"))
        efo_id = self._efo_id_from_uri_or_id(
            arguments.get("efo_id")
        ) or self._efo_id_from_uri_or_id(arguments.get("efo_uri"))
        efo_trait = self._coerce_str(arguments.get("efo_trait"))
        if not disease_trait and not efo_id and not efo_trait:
            return {
                "status": "error",
                "error": "Provide at least one of: disease_trait, efo_id (or efo_uri), efo_trait.",
            }

        params = {
            "size": self._coerce_int(arguments.get("size")) or 200,
            "page": self._coerce_int(arguments.get("page")) or 0,
        }

        if disease_trait:
            params["disease_trait"] = disease_trait
        if efo_id:
            params["efo_id"] = efo_id
        if efo_trait:
            params["efo_trait"] = efo_trait

        cohort = self._coerce_str(arguments.get("cohort"))
        if cohort:
            params["cohort"] = cohort
        if arguments.get("gxe") is not None:
            params["gxe"] = bool(arguments.get("gxe"))
        if arguments.get("full_pvalue_set") is not None:
            params["full_pvalue_set"] = bool(arguments.get("full_pvalue_set"))

        data = self._make_request(self.endpoint, params)
        return self._extract_embedded_data(data, "studies")


@register_tool("GWASSNPsForGene")
class GWASSNPsForGene(GWASRESTTool):
    """Get SNPs mapped to a specific gene."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Feature-83B-001: v2 /single-nucleotide-polymorphisms?mapped_gene= returns
        # HTTP 500 for all gene queries. The v1 endpoint
        # /singleNucleotidePolymorphisms/search/findByGene?geneName= works correctly.
        self.endpoint = "/singleNucleotidePolymorphisms/search/findByGene"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get SNPs for a gene."""
        gene = (
            arguments.get("gene_symbol")
            or arguments.get("mapped_gene")
            or arguments.get("gene")
        )
        if not gene:
            return {"status": "error", "error": "gene_symbol is required"}

        params = {
            "geneName": gene,
            "size": arguments.get("size", 50),
            "page": arguments.get("page", 0),
        }

        data = self._make_request(self.endpoint, params)
        # v1 endpoint returns key "singleNucleotidePolymorphisms", not "snps"
        return self._extract_embedded_data(data, "singleNucleotidePolymorphisms")


@register_tool("GWASAssociationsForStudy")
class GWASAssociationsForStudy(GWASRESTTool):
    """Get all associations for a specific study."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/associations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get associations for a study."""
        if "accession_id" not in arguments:
            return {"status": "error", "error": "accession_id is required"}

        params = {
            "accession_id": arguments["accession_id"],
            "sort": "p_value",
            "direction": "asc",
            "size": arguments.get("size", 200),
            "page": arguments.get("page", 0),
        }

        data = self._make_request(self.endpoint, params)
        return self._extract_embedded_data(data, "associations")
