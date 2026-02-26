"""
Orphanet API tool for ToolUniverse.

Orphanet is the reference portal for rare diseases and orphan drugs.
This tool uses the Orphadata API and RDcode API for programmatic access.

API Documentation:
- Orphadata: https://api.orphadata.com/
- RDcode: https://api.orphacode.org/
"""

import requests
import urllib.parse
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URLs for Orphanet APIs
ORPHADATA_API_URL = "https://api.orphadata.com"
RDCODE_API_URL = "https://api.orphacode.org"

# RDcode API requires apiKey header (any value accepted)
RDCODE_API_KEY = "ToolUniverse"


def get_rdcode_headers():
    """Get headers for RDcode API requests."""
    return {
        "Accept": "application/json",
        "User-Agent": "ToolUniverse/Orphanet",
        "apiKey": RDCODE_API_KEY,
    }


def normalize_lang(lang: str) -> str:
    """Convert language code to uppercase as required by RDcode API."""
    return lang.upper() if lang else "EN"


@register_tool("OrphanetTool")
class OrphanetTool(BaseTool):
    """
    Tool for querying Orphanet rare disease database.

    Orphanet provides:
    - Rare disease nomenclature and classification
    - Disease-gene associations
    - Epidemiology data (prevalence, inheritance)
    - Expert centers and patient organizations

    RDcode API requires apiKey header (any value accepted).
    Orphadata API is free public access.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Orphanet API call based on operation type."""
        operation = arguments.get("operation", "")

        if operation == "search_diseases":
            return self._search_diseases(arguments)
        elif operation == "get_disease":
            return self._get_disease(arguments)
        elif operation == "get_genes":
            return self._get_genes(arguments)
        elif operation == "get_classification":
            return self._get_classification(arguments)
        elif operation == "search_by_name":
            return self._search_by_name(arguments)
        elif operation == "get_phenotypes":
            return self._get_phenotypes(arguments)
        elif operation == "get_epidemiology":
            return self._get_epidemiology(arguments)
        elif operation == "get_natural_history":
            return self._get_natural_history(arguments)
        elif operation == "get_gene_diseases":
            return self._get_gene_diseases(arguments)
        elif operation == "get_icd_mapping":
            return self._get_icd_mapping(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search_diseases, get_disease, get_genes, get_classification, search_by_name, get_phenotypes, get_epidemiology, get_natural_history, get_gene_diseases, get_icd_mapping",
            }

    def _search_diseases(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search Orphanet for rare diseases by query term.

        Args:
            arguments: Dict containing:
                - query: Search query (disease name, keyword)
                - lang: Language code (en, fr, de, etc.). Default: en
        """
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "Missing required parameter: query"}

        lang = normalize_lang(arguments.get("lang", "en"))

        try:
            # Use RDcode API for approximate name search
            # URL pattern: /{lang}/ClinicalEntity/ApproximateName/{label}
            encoded_query = urllib.parse.quote(query, safe="")
            response = requests.get(
                f"{RDCODE_API_URL}/{lang}/ClinicalEntity/ApproximateName/{encoded_query}",
                timeout=self.timeout,
                headers=get_rdcode_headers(),
            )
            response.raise_for_status()
            data = response.json()

            # Parse results from API response
            results = []
            if isinstance(data, list):
                results = data
            elif isinstance(data, dict):
                # API returns a dict with entities
                results = data.get("entities", data.get("results", [data]))

            return {
                "status": "success",
                "data": {
                    "results": results,
                    "query": query,
                    "language": lang,
                },
                "metadata": {
                    "source": "Orphanet RDcode API",
                    "query": query,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {"results": [], "query": query, "language": lang},
                    "metadata": {"note": "No diseases found matching the query"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get disease details by ORPHA code.

        Args:
            arguments: Dict containing:
                - orpha_code: Orphanet disease code (e.g., 558, 166024)
                - lang: Language code (default: en)
        """
        orpha_code = arguments.get("orpha_code", "")
        if not orpha_code:
            return {
                "status": "error",
                "error": "Missing required parameter: orpha_code",
            }

        # Clean ORPHA code
        orpha_code = (
            str(orpha_code).replace("ORPHA:", "").replace("Orphanet:", "").strip()
        )
        lang = normalize_lang(arguments.get("lang", "en"))
        headers = get_rdcode_headers()

        result_data = {"ORPHAcode": orpha_code}

        try:
            # Get preferred name: /{lang}/ClinicalEntity/orphacode/{orphacode}/Name
            name_response = requests.get(
                f"{RDCODE_API_URL}/{lang}/ClinicalEntity/orphacode/{orpha_code}/Name",
                timeout=self.timeout,
                headers=headers,
            )
            name_response.raise_for_status()
            name_data = name_response.json()
            if isinstance(name_data, dict):
                result_data["Preferred term"] = name_data.get(
                    "Preferred term", name_data.get("Name", "")
                )
            else:
                result_data["Preferred term"] = str(name_data) if name_data else ""

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Disease not found: ORPHA:{orpha_code}",
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}

        try:
            # Get definition: /{lang}/ClinicalEntity/orphacode/{orphacode}/Definition
            def_response = requests.get(
                f"{RDCODE_API_URL}/{lang}/ClinicalEntity/orphacode/{orpha_code}/Definition",
                timeout=self.timeout,
                headers=headers,
            )
            if def_response.status_code == 200:
                def_data = def_response.json()
                if isinstance(def_data, dict):
                    result_data["Definition"] = def_data.get("Definition", "")
                else:
                    result_data["Definition"] = str(def_data) if def_data else ""
        except Exception:
            result_data["Definition"] = ""

        try:
            # Get synonyms: /{lang}/ClinicalEntity/orphacode/{orphacode}/Synonym
            syn_response = requests.get(
                f"{RDCODE_API_URL}/{lang}/ClinicalEntity/orphacode/{orpha_code}/Synonym",
                timeout=self.timeout,
                headers=headers,
            )
            if syn_response.status_code == 200:
                syn_data = syn_response.json()
                if isinstance(syn_data, list):
                    result_data["Synonyms"] = syn_data
                elif isinstance(syn_data, dict):
                    result_data["Synonyms"] = syn_data.get(
                        "Synonyms", syn_data.get("Synonym", [])
                    )
                else:
                    result_data["Synonyms"] = []
        except Exception:
            result_data["Synonyms"] = []

        return {
            "status": "success",
            "data": result_data,
            "metadata": {
                "source": "Orphanet RDcode API",
                "orpha_code": orpha_code,
            },
        }

    def _get_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get genes associated with a rare disease.

        Uses Orphadata rd-associated-genes gene name search, since the
        per-orphacode gene endpoint is not reliably available.
        Falls back to RDcode OMIM cross-references to identify associated genes.

        Args:
            arguments: Dict containing:
                - orpha_code: Orphanet disease code
        """
        orpha_code = arguments.get("orpha_code", "")
        if not orpha_code:
            return {
                "status": "error",
                "error": "Missing required parameter: orpha_code",
            }

        orpha_code = (
            str(orpha_code).replace("ORPHA:", "").replace("Orphanet:", "").strip()
        )

        try:
            # First get the disease name from RDcode API
            name_response = requests.get(
                f"{RDCODE_API_URL}/EN/ClinicalEntity/orphacode/{orpha_code}/Name",
                timeout=self.timeout,
                headers=get_rdcode_headers(),
            )
            name_response.raise_for_status()
            name_data = name_response.json()
            disease_name = ""
            if isinstance(name_data, dict):
                disease_name = name_data.get(
                    "Preferred term", name_data.get("Name", "")
                )

            # Search Orphadata gene associations using disease name keywords
            genes = []
            if disease_name:
                # Use first significant word of the disease name to search
                search_term = disease_name.split()[0].lower() if disease_name else ""
                if len(search_term) < 4:
                    # Use longer terms if first word is too short
                    words = [
                        w
                        for w in disease_name.split()
                        if len(w) >= 4
                        and w.lower() not in ("syndrome", "disease", "disorder", "type")
                    ]
                    search_term = (
                        words[0].lower() if words else disease_name.split()[0].lower()
                    )

                try:
                    gene_response = requests.get(
                        f"{ORPHADATA_API_URL}/rd-associated-genes/genes/names/{urllib.parse.quote(search_term, safe='')}",
                        timeout=self.timeout,
                        headers={
                            "Accept": "application/json",
                            "User-Agent": "ToolUniverse/Orphanet",
                        },
                    )
                    if gene_response.status_code == 200:
                        gene_data = gene_response.json()
                        results = gene_data.get("data", {}).get("results", [])
                        # Filter results for our specific ORPHA code
                        for result in results:
                            if str(result.get("ORPHAcode", "")) == str(orpha_code):
                                for assoc in result.get("DisorderGeneAssociation", []):
                                    gene_info = assoc.get("Gene", {})
                                    genes.append(
                                        {
                                            "Symbol": gene_info.get("Symbol", ""),
                                            "Name": gene_info.get("name", ""),
                                            "GeneType": gene_info.get("GeneType", ""),
                                            "Locus": gene_info.get("Locus", []),
                                            "AssociationType": assoc.get(
                                                "DisorderGeneAssociationType", ""
                                            ),
                                            "AssociationStatus": assoc.get(
                                                "DisorderGeneAssociationStatus", ""
                                            ),
                                            "SourceOfValidation": assoc.get(
                                                "SourceOfValidation", ""
                                            ),
                                        }
                                    )
                except Exception:
                    pass

            return {
                "status": "success",
                "data": {
                    "orpha_code": orpha_code,
                    "disease_name": disease_name,
                    "genes": genes,
                },
                "metadata": {
                    "source": "Orphanet Orphadata API",
                    "orpha_code": orpha_code,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {"orpha_code": orpha_code, "disease_name": "", "genes": []},
                    "metadata": {"note": "No gene associations found"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_classification(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get disease classification hierarchy.

        Args:
            arguments: Dict containing:
                - orpha_code: Orphanet disease code
                - lang: Language code (default: en)
        """
        orpha_code = arguments.get("orpha_code", "")
        if not orpha_code:
            return {
                "status": "error",
                "error": "Missing required parameter: orpha_code",
            }

        orpha_code = (
            str(orpha_code).replace("ORPHA:", "").replace("Orphanet:", "").strip()
        )
        lang = normalize_lang(arguments.get("lang", "en"))

        try:
            # Use RDcode API: /{lang}/ClinicalEntity/orphacode/{orphacode}/Classification
            response = requests.get(
                f"{RDCODE_API_URL}/{lang}/ClinicalEntity/orphacode/{orpha_code}/Classification",
                timeout=self.timeout,
                headers=get_rdcode_headers(),
            )
            response.raise_for_status()
            data = response.json()

            return {
                "status": "success",
                "data": {
                    "orpha_code": orpha_code,
                    "classification": data,
                },
                "metadata": {
                    "source": "Orphanet RDcode API",
                    "orpha_code": orpha_code,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {"orpha_code": orpha_code, "classification": []},
                    "metadata": {"note": "No classification found"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _search_by_name(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for diseases by exact or partial name match.

        Args:
            arguments: Dict containing:
                - name: Disease name to search
                - exact: Whether to match exactly (default: False)
                - lang: Language code (default: en)
        """
        name = arguments.get("name", "")
        if not name:
            return {"status": "error", "error": "Missing required parameter: name"}

        exact = arguments.get("exact", False)
        lang = normalize_lang(arguments.get("lang", "en"))

        try:
            # URL encode the search name
            encoded_name = urllib.parse.quote(name, safe="")

            if exact:
                # For exact match, use FindbyName endpoint
                endpoint = (
                    f"{RDCODE_API_URL}/{lang}/ClinicalEntity/FindbyName/{encoded_name}"
                )
            else:
                # For partial match, use ApproximateName endpoint
                endpoint = f"{RDCODE_API_URL}/{lang}/ClinicalEntity/ApproximateName/{encoded_name}"

            response = requests.get(
                endpoint,
                timeout=self.timeout,
                headers=get_rdcode_headers(),
            )
            response.raise_for_status()
            data = response.json()

            # Parse results from response
            if isinstance(data, list):
                results = data
            elif isinstance(data, dict):
                # Single result or wrapped in dict
                results = data.get("entities", data.get("results", [data]))
            else:
                results = [data] if data else []

            return {
                "status": "success",
                "data": {
                    "results": results,
                    "count": len(results),
                    "search_name": name,
                    "exact_match": exact,
                },
                "metadata": {
                    "source": "Orphanet RDcode API",
                    "name": name,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {
                        "results": [],
                        "count": 0,
                        "search_name": name,
                        "exact_match": exact,
                    },
                    "metadata": {"note": "No diseases found matching the name"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get HPO phenotypes associated with a rare disease.

        Args:
            arguments: Dict containing:
                - orpha_code: Orphanet disease code (e.g., 558 for Marfan)
        """
        orpha_code = arguments.get("orpha_code", "")
        if not orpha_code:
            return {
                "status": "error",
                "error": "Missing required parameter: orpha_code",
            }

        orpha_code = (
            str(orpha_code).replace("ORPHA:", "").replace("Orphanet:", "").strip()
        )

        try:
            response = requests.get(
                f"{ORPHADATA_API_URL}/rd-phenotypes/orphacodes/{orpha_code}",
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/Orphanet",
                },
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("data", {}).get("results", {})
            disorder = results.get("Disorder", results)
            hpo_associations = disorder.get("HPODisorderAssociation", [])

            phenotypes = []
            for assoc in hpo_associations:
                hpo = assoc.get("HPO", {})
                phenotypes.append(
                    {
                        "hpo_id": hpo.get("HPOId", ""),
                        "hpo_term": hpo.get("HPOTerm", ""),
                        "frequency": assoc.get("HPOFrequency", ""),
                        "diagnostic_criteria": assoc.get("DiagnosticCriteria"),
                    }
                )

            return {
                "status": "success",
                "data": {
                    "orpha_code": orpha_code,
                    "preferred_term": results.get("Preferred term", ""),
                    "phenotypes": phenotypes,
                    "phenotype_count": len(phenotypes),
                },
                "metadata": {
                    "source": "Orphanet Orphadata API",
                    "orpha_code": orpha_code,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {
                        "orpha_code": orpha_code,
                        "preferred_term": "",
                        "phenotypes": [],
                        "phenotype_count": 0,
                    },
                    "metadata": {"note": "No phenotype data found"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_epidemiology(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get epidemiology data (prevalence) for a rare disease.

        Args:
            arguments: Dict containing:
                - orpha_code: Orphanet disease code
        """
        orpha_code = arguments.get("orpha_code", "")
        if not orpha_code:
            return {
                "status": "error",
                "error": "Missing required parameter: orpha_code",
            }

        orpha_code = (
            str(orpha_code).replace("ORPHA:", "").replace("Orphanet:", "").strip()
        )

        try:
            response = requests.get(
                f"{ORPHADATA_API_URL}/rd-epidemiology/orphacodes/{orpha_code}",
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/Orphanet",
                },
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("data", {}).get("results", {})
            prevalence_data = results.get("Prevalence", [])

            prevalences = []
            for p in prevalence_data:
                prevalences.append(
                    {
                        "type": p.get("PrevalenceType", ""),
                        "class": p.get("PrevalenceClass", ""),
                        "geographic": p.get("PrevalenceGeographic", ""),
                        "qualification": p.get("PrevalenceQualification", ""),
                        "mean_value": p.get("ValMoy", ""),
                        "source": p.get("Source", ""),
                        "validation_status": p.get("PrevalenceValidationStatus", ""),
                    }
                )

            return {
                "status": "success",
                "data": {
                    "orpha_code": orpha_code,
                    "preferred_term": results.get("Preferred term", ""),
                    "prevalences": prevalences,
                    "prevalence_count": len(prevalences),
                },
                "metadata": {
                    "source": "Orphanet Orphadata API",
                    "orpha_code": orpha_code,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {
                        "orpha_code": orpha_code,
                        "preferred_term": "",
                        "prevalences": [],
                        "prevalence_count": 0,
                    },
                    "metadata": {"note": "No epidemiology data found"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_natural_history(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get natural history data for a rare disease (age of onset, inheritance).

        Args:
            arguments: Dict containing:
                - orpha_code: Orphanet disease code
        """
        orpha_code = arguments.get("orpha_code", "")
        if not orpha_code:
            return {
                "status": "error",
                "error": "Missing required parameter: orpha_code",
            }

        orpha_code = (
            str(orpha_code).replace("ORPHA:", "").replace("Orphanet:", "").strip()
        )

        try:
            response = requests.get(
                f"{ORPHADATA_API_URL}/rd-natural_history/orphacodes/{orpha_code}",
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/Orphanet",
                },
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("data", {}).get("results", {})

            return {
                "status": "success",
                "data": {
                    "orpha_code": orpha_code,
                    "preferred_term": results.get("Preferred term", ""),
                    "average_age_of_onset": results.get("AverageAgeOfOnset", []),
                    "type_of_inheritance": results.get("TypeOfInheritance", []),
                    "disorder_group": results.get("DisorderGroup", ""),
                    "typology": results.get("Typology", ""),
                },
                "metadata": {
                    "source": "Orphanet Orphadata API",
                    "orpha_code": orpha_code,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {
                        "orpha_code": orpha_code,
                        "preferred_term": "",
                        "average_age_of_onset": [],
                        "type_of_inheritance": [],
                        "disorder_group": "",
                        "typology": "",
                    },
                    "metadata": {"note": "No natural history data found"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_gene_diseases(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get rare diseases associated with a gene name.

        Uses Orphadata gene name search to find diseases associated with genes
        matching the given search term. Search by gene name keywords
        (e.g., 'fibrillin', 'huntingtin', 'dystrophin').

        Args:
            arguments: Dict containing:
                - gene_name: Gene name keyword to search (e.g., 'fibrillin', 'collagen')
        """
        gene_name = arguments.get("gene_name", "")
        if not gene_name:
            return {"status": "error", "error": "Missing required parameter: gene_name"}

        try:
            encoded_name = urllib.parse.quote(gene_name, safe="")
            response = requests.get(
                f"{ORPHADATA_API_URL}/rd-associated-genes/genes/names/{encoded_name}",
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/Orphanet",
                },
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("data", {}).get("results", [])

            diseases = []
            for result in results:
                disease_entry = {
                    "orpha_code": result.get("ORPHAcode", ""),
                    "preferred_term": result.get("Preferred term", ""),
                    "disorder_group": result.get("DisorderGroup", ""),
                    "typology": result.get("Typology", ""),
                    "genes": [],
                }
                for assoc in result.get("DisorderGeneAssociation", []):
                    gene_info = assoc.get("Gene", {})
                    disease_entry["genes"].append(
                        {
                            "symbol": gene_info.get("Symbol", ""),
                            "name": gene_info.get("name", ""),
                            "gene_type": gene_info.get("GeneType", ""),
                            "locus": [
                                loc.get("GeneLocus", "")
                                for loc in gene_info.get("Locus", [])
                            ],
                            "association_type": assoc.get(
                                "DisorderGeneAssociationType", ""
                            ),
                            "association_status": assoc.get(
                                "DisorderGeneAssociationStatus", ""
                            ),
                        }
                    )
                diseases.append(disease_entry)

            return {
                "status": "success",
                "data": {
                    "gene_name": gene_name,
                    "diseases": diseases,
                    "disease_count": len(diseases),
                },
                "metadata": {
                    "source": "Orphanet Orphadata API",
                    "gene_name": gene_name,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {
                        "gene_name": gene_name,
                        "diseases": [],
                        "disease_count": 0,
                    },
                    "metadata": {"note": "No diseases found for this gene name"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_icd_mapping(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get ICD-10, ICD-11, OMIM, and SNOMED-CT cross-references for a rare disease.

        Args:
            arguments: Dict containing:
                - orpha_code: Orphanet disease code
                - coding_system: Which coding system to retrieve (icd10, icd11, omim, snomed). Default: all
                - lang: Language code (default: en)
        """
        orpha_code = arguments.get("orpha_code", "")
        if not orpha_code:
            return {
                "status": "error",
                "error": "Missing required parameter: orpha_code",
            }

        orpha_code = (
            str(orpha_code).replace("ORPHA:", "").replace("Orphanet:", "").strip()
        )
        coding_system = arguments.get("coding_system", "all").lower()
        lang = normalize_lang(arguments.get("lang", "en"))
        headers = get_rdcode_headers()

        mappings = {}

        systems_to_query = []
        if coding_system == "all":
            systems_to_query = ["ICD10", "ICD11", "OMIM", "SNOMED-CT"]
        elif coding_system == "icd10":
            systems_to_query = ["ICD10"]
        elif coding_system == "icd11":
            systems_to_query = ["ICD11"]
        elif coding_system == "omim":
            systems_to_query = ["OMIM"]
        elif coding_system == "snomed":
            systems_to_query = ["SNOMED-CT"]
        else:
            return {
                "status": "error",
                "error": f"Unknown coding_system: {coding_system}. Supported: all, icd10, icd11, omim, snomed",
            }

        for system in systems_to_query:
            try:
                response = requests.get(
                    f"{RDCODE_API_URL}/{lang}/ClinicalEntity/orphacode/{orpha_code}/{system}",
                    timeout=self.timeout,
                    headers=headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict):
                        refs = data.get("References", data.get(f"Code {system}", []))
                        if isinstance(refs, list):
                            mappings[system] = refs
                        elif isinstance(refs, str):
                            mappings[system] = [{"code": refs}]
                        else:
                            mappings[system] = [refs] if refs else []
                    elif isinstance(data, list):
                        mappings[system] = data
                    else:
                        mappings[system] = []
                else:
                    mappings[system] = []
            except Exception:
                mappings[system] = []

        return {
            "status": "success",
            "data": {
                "orpha_code": orpha_code,
                "mappings": mappings,
            },
            "metadata": {
                "source": "Orphanet RDcode API",
                "orpha_code": orpha_code,
                "coding_systems": systems_to_query,
            },
        }
