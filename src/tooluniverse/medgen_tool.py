"""
MedGen API tool for ToolUniverse.

MedGen is an NCBI portal for medical genetics. It aggregates information from
multiple sources (OMIM, Orphanet, HPO, ClinVar, GTR, GeneReviews) to provide
a unified view of genetic conditions, associated genes, clinical features,
and modes of inheritance.

API: NCBI E-utilities (eutils.ncbi.nlm.nih.gov)
No authentication required (NCBI public access).

Documentation: https://www.ncbi.nlm.nih.gov/medgen/docs/
"""

import os
import re
import time
import requests
from typing import Any
from xml.etree import ElementTree

from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")
_LAST_REQUEST_TIME = 0.0


@register_tool("MedGenTool")
class MedGenTool(BaseRESTTool):
    """
    Tool for querying the NCBI MedGen database.

    Provides access to:
    - Search for genetic conditions/diseases
    - Get detailed condition summaries (definition, synonyms, genes, HPO features)
    - Map conditions to OMIM, Orphanet, SNOMED CT identifiers

    Uses NCBI E-utilities. No authentication required.
    """

    def __init__(self, tool_config: dict):
        super().__init__(tool_config)
        self.timeout = 30
        self.operation = tool_config.get("fields", {}).get("operation", "search")
        self.api_key = _NCBI_API_KEY

    def _ncbi_get(self, url: str, params: dict) -> requests.Response:
        """Rate-limited GET request to NCBI E-utilities."""
        global _LAST_REQUEST_TIME
        # NCBI allows 3 req/s without key, 10 req/s with key
        min_interval = 0.15 if self.api_key else 0.4
        elapsed = time.time() - _LAST_REQUEST_TIME
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        if self.api_key:
            params["api_key"] = self.api_key
        _LAST_REQUEST_TIME = time.time()
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp

    def run(self, arguments: dict) -> dict:
        """Execute the MedGen API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"MedGen request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to NCBI. Check network connectivity.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"MedGen error: {str(e)}",
            }

    def _query(self, arguments: dict) -> dict:
        """Route to the appropriate operation."""
        op = self.operation
        if op == "search":
            return self._search(arguments)
        elif op == "get_condition":
            return self._get_condition(arguments)
        elif op == "get_clinical_features":
            return self._get_clinical_features(arguments)
        return {"status": "error", "error": f"Unknown operation: {op}"}

    def _search(self, arguments: dict) -> dict:
        """Search MedGen for genetic conditions by name or keyword."""
        query = arguments.get("query", "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'cystic fibrosis', 'BRCA1').",
            }

        max_results = min(int(arguments.get("max_results", 10)), 50)

        params = {
            "db": "medgen",
            "term": query,
            "retmode": "json",
            "retmax": max_results,
        }
        resp = self._ncbi_get(f"{EUTILS_BASE}/esearch.fcgi", params)
        search_data = resp.json()

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        total_count = int(search_data.get("esearchresult", {}).get("count", 0))

        if not id_list:
            return {
                "status": "success",
                "data": {
                    "conditions": [],
                    "total_count": 0,
                },
                "metadata": {
                    "query": query,
                    "source": "NCBI MedGen",
                },
            }

        # Fetch summaries for found IDs
        summary_params = {
            "db": "medgen",
            "id": ",".join(id_list),
            "retmode": "json",
        }
        sum_resp = self._ncbi_get(f"{EUTILS_BASE}/esummary.fcgi", summary_params)
        sum_data = sum_resp.json()

        results = sum_data.get("result", {})
        conditions = []
        for uid in id_list:
            entry = results.get(str(uid), {})
            if not isinstance(entry, dict):
                continue

            concept_meta = entry.get("conceptmeta", "")
            omim_ids = self._extract_omim(concept_meta)
            genes = self._extract_genes(concept_meta)

            definition_val = entry.get("definition", {})
            definition = (
                definition_val.get("value", "")
                if isinstance(definition_val, dict)
                else str(definition_val)
            )

            conditions.append(
                {
                    "uid": uid,
                    "concept_id": entry.get("conceptid"),
                    "title": entry.get("title"),
                    "definition": definition[:500] if definition else None,
                    "semantic_type": (
                        entry.get("semantictype", {}).get("value")
                        if isinstance(entry.get("semantictype"), dict)
                        else entry.get("semantictype")
                    ),
                    "omim_ids": omim_ids,
                    "associated_genes": genes,
                }
            )

        return {
            "status": "success",
            "data": {
                "conditions": conditions,
                "total_count": total_count,
            },
            "metadata": {
                "query": query,
                "source": "NCBI MedGen",
                "description": (
                    "MedGen aggregates genetic condition data from OMIM, Orphanet, "
                    "ClinVar, HPO, GTR, and GeneReviews."
                ),
            },
        }

    def _get_condition(self, arguments: dict) -> dict:
        # Accept concept_id as alias for cui (UMLS CUI format like C0010674)
        if (
            not arguments.get("uid")
            and not arguments.get("cui")
            and arguments.get("concept_id")
        ):
            arguments = dict(arguments, cui=arguments["concept_id"])
        uid = arguments.get("uid", "").strip()
        cui = arguments.get("cui", "").strip()

        if not uid and not cui:
            return {
                "status": "error",
                "error": "Either uid (MedGen UID) or cui (UMLS CUI like C0010674) is required.",
            }

        # If CUI provided, search for it first
        if cui and not uid:
            search_params = {
                "db": "medgen",
                "term": f"{cui}[CUI]",
                "retmode": "json",
                "retmax": 1,
            }
            search_resp = self._ncbi_get(f"{EUTILS_BASE}/esearch.fcgi", search_params)
            id_list = search_resp.json().get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return {
                    "status": "error",
                    "error": f"No MedGen entry found for CUI: {cui}",
                }
            uid = id_list[0]

        # Fetch full summary
        summary_params = {
            "db": "medgen",
            "id": uid,
            "retmode": "json",
        }
        resp = self._ncbi_get(f"{EUTILS_BASE}/esummary.fcgi", summary_params)
        data = resp.json()

        entry = data.get("result", {}).get(str(uid), {})
        if not isinstance(entry, dict) or "title" not in entry:
            return {
                "status": "error",
                "error": f"No MedGen entry found for UID: {uid}",
            }

        concept_meta = entry.get("conceptmeta", "")

        definition_val = entry.get("definition", {})
        definition = (
            definition_val.get("value", "")
            if isinstance(definition_val, dict)
            else str(definition_val)
        )

        # Parse rich metadata from conceptmeta XML
        omim_ids = self._extract_omim(concept_meta)
        genes = self._extract_genes(concept_meta)
        synonyms = self._extract_synonyms(concept_meta)
        clinical_features = self._extract_clinical_features_from_meta(concept_meta)
        inheritance = self._extract_inheritance(concept_meta)

        condition_data: dict[str, Any] = {
            "uid": uid,
            "concept_id": entry.get("conceptid"),
            "title": entry.get("title"),
            "definition": definition,
            "semantic_type": (
                entry.get("semantictype", {}).get("value")
                if isinstance(entry.get("semantictype"), dict)
                else entry.get("semantictype")
            ),
            "omim_ids": omim_ids,
            "associated_genes": genes,
            "synonyms": synonyms[:20],
            "modes_of_inheritance": inheritance,
            "clinical_features": clinical_features[:30],
        }

        return {
            "status": "success",
            "data": condition_data,
            "metadata": {
                "uid": uid,
                "source": "NCBI MedGen",
                "description": (
                    "Detailed genetic condition information from MedGen including "
                    "genes, OMIM IDs, clinical features, and inheritance patterns."
                ),
            },
        }

    def _get_clinical_features(self, arguments: dict) -> dict:
        """Get HPO clinical features associated with a MedGen condition."""
        if (
            not arguments.get("uid")
            and not arguments.get("cui")
            and arguments.get("concept_id")
        ):
            arguments = dict(arguments, cui=arguments["concept_id"])
        uid = arguments.get("uid", "").strip()
        cui = arguments.get("cui", "").strip()

        if not uid and not cui:
            return {
                "status": "error",
                "error": "Either uid (MedGen UID) or cui (UMLS CUI) is required.",
            }

        # Resolve CUI to UID
        if cui and not uid:
            search_params = {
                "db": "medgen",
                "term": f"{cui}[CUI]",
                "retmode": "json",
                "retmax": 1,
            }
            search_resp = self._ncbi_get(f"{EUTILS_BASE}/esearch.fcgi", search_params)
            id_list = search_resp.json().get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return {
                    "status": "error",
                    "error": f"No MedGen entry found for CUI: {cui}",
                }
            uid = id_list[0]

        # Get summary which contains clinical features in conceptmeta
        summary_params = {
            "db": "medgen",
            "id": uid,
            "retmode": "json",
        }
        resp = self._ncbi_get(f"{EUTILS_BASE}/esummary.fcgi", summary_params)
        data = resp.json()

        entry = data.get("result", {}).get(str(uid), {})
        if not isinstance(entry, dict) or "title" not in entry:
            return {
                "status": "error",
                "error": f"No MedGen entry found for UID: {uid}",
            }

        concept_meta = entry.get("conceptmeta", "")
        features = self._extract_clinical_features_from_meta(concept_meta)

        return {
            "status": "success",
            "data": {
                "condition_title": entry.get("title"),
                "condition_uid": uid,
                "clinical_features": features,
                "total_features": len(features),
            },
            "metadata": {
                "uid": uid,
                "source": "NCBI MedGen (HPO)",
                "description": (
                    "Clinical features (phenotypes) associated with this condition, "
                    "sourced from HPO. Includes HPO IDs and definitions."
                ),
            },
        }

    # --- Parsing helpers ---

    def _extract_omim(self, concept_meta: str) -> list[str]:
        """Extract OMIM IDs from conceptmeta XML."""
        omim_ids = []
        try:
            matches = re.findall(r"<MIM>(\d+)</MIM>", concept_meta)
            omim_ids = list(dict.fromkeys(matches))
        except Exception:
            pass
        return omim_ids

    def _extract_genes(self, concept_meta: str) -> list[dict]:
        """Extract associated genes from conceptmeta XML."""
        genes = []
        try:
            matches = re.findall(
                r'<Gene gene_id="(\d+)"[^>]*>([^<]+)</Gene>', concept_meta
            )
            seen = set()
            for gene_id, gene_name in matches:
                if gene_name not in seen:
                    genes.append({"gene_id": gene_id, "symbol": gene_name})
                    seen.add(gene_name)
        except Exception:
            pass
        return genes

    def _extract_synonyms(self, concept_meta: str) -> list[str]:
        """Extract synonym names from conceptmeta XML."""
        synonyms = []
        try:
            matches = re.findall(
                r'<Name[^>]*type="(?:syn|preferred)"[^>]*>([^<]+)</Name>', concept_meta
            )
            synonyms = list(dict.fromkeys(matches))
        except Exception:
            pass
        return synonyms

    def _extract_clinical_features_from_meta(self, concept_meta: str) -> list[dict]:
        """Extract clinical features from conceptmeta XML."""
        features = []
        try:
            # Parse ClinicalFeature elements
            pattern = (
                r'<ClinicalFeature[^>]*CUI="([^"]*)"[^>]*>'
                r".*?<Name>([^<]+)</Name>"
                r".*?<Definition>([^<]*)</Definition>"
                r".*?</ClinicalFeature>"
            )
            matches = re.findall(pattern, concept_meta, re.DOTALL)
            seen = set()
            for cui, name, definition in matches:
                if name not in seen:
                    # Extract HPO ID if available
                    hpo_match = re.search(
                        rf'<ClinicalFeature[^>]*CUI="{re.escape(cui)}"[^>]*SDUI="(HP:\d+)"',
                        concept_meta,
                    )
                    hpo_id = hpo_match.group(1) if hpo_match else None
                    features.append(
                        {
                            "name": name,
                            "cui": cui,
                            "hpo_id": hpo_id,
                            "definition": definition[:300] if definition else None,
                        }
                    )
                    seen.add(name)
        except Exception:
            pass
        return features

    def _extract_inheritance(self, concept_meta: str) -> list[str]:
        """Extract modes of inheritance from conceptmeta XML."""
        modes = []
        try:
            pattern = r"<ModeOfInheritance[^>]*>.*?<Name>([^<]+)</Name>.*?</ModeOfInheritance>"
            matches = re.findall(pattern, concept_meta, re.DOTALL)
            modes = list(dict.fromkeys(matches))
        except Exception:
            pass
        return modes
