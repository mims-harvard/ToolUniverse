"""
RxNorm API Tool

This tool provides access to the RxNorm API from the U.S. National Library of Medicine (NLM)
for drug name standardization. It can look up RXCUI (RxNorm Concept Unique Identifier) by
drug name and retrieve all associated names (generic names, brand names, synonyms, etc.).
"""

import requests
import re
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

RXNORM_BASE_URL = "https://rxnav.nlm.nih.gov/REST"


@register_tool("RxNormTool")
class RxNormTool(BaseTool):
    """
    Tool for querying RxNorm API to get drug standardization information.

    This tool performs a two-step process:
    1. Look up RXCUI (RxNorm Concept Unique Identifier) by drug name
    2. Retrieve all associated names (generic names, brand names, synonyms, etc.) using RXCUI
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = RXNORM_BASE_URL
        self.timeout = 30

    def _preprocess_drug_name(self, drug_name: str) -> str:
        """
        Preprocess drug name to improve matching success rate.
        Removes common patterns that might prevent matching:
        - Dosage information (e.g., "200mg", "81mg")
        - Formulations (e.g., "tablet", "capsule", "oral")
        - Modifiers (e.g., "Extra Strength", "Extended Release")
        - Special characters that might interfere

        Args:
            drug_name: Original drug name

        Returns:
            Preprocessed drug name
        """
        if not drug_name:
            return drug_name

        # Strip whitespace
        processed = drug_name.strip()

        # Remove common dosage patterns (e.g., "200mg", "81 mg", "500 MG")
        processed = re.sub(
            r"\d+\s*(mg|mcg|g|ml|mL|%)\s*", "", processed, flags=re.IGNORECASE
        )

        # Remove numbers at the end (e.g., "ibuprofen-200" -> "ibuprofen")
        processed = re.sub(r"[-_]\d+$", "", processed)
        processed = re.sub(r"\s+\d+$", "", processed)

        # Remove common formulation terms
        formulation_patterns = [
            r"\b(tablet|tablets|tab|tabs)\b",
            r"\b(capsule|capsules|cap|caps)\b",
            r"\b(oral|injection|injectable|IV|topical|cream|gel|ointment)\b",
            r"\b(extended\s+release|ER|XR|SR|CR|LA)\b",
            r"\b(extra\s+strength|regular\s+strength|maximum\s+strength)\b",
            r"\b(hydrochloride|HCl|HCL|sulfate|sodium|potassium)\b",
        ]
        for pattern in formulation_patterns:
            processed = re.sub(pattern, "", processed, flags=re.IGNORECASE)

        # Remove trailing special characters (+, /, etc.)
        processed = re.sub(r"[+\-/]+$", "", processed)
        processed = re.sub(r"^[+\-/]+", "", processed)

        # Remove multiple spaces
        processed = re.sub(r"\s+", " ", processed)

        # Strip again
        processed = processed.strip()

        return processed

    def _get_rxcui_by_name(self, drug_name: str) -> Dict[str, Any]:
        """
        Get RXCUI (RxNorm Concept Unique Identifier) by drug name.

        Args:
            drug_name: The name of the drug to search for

        Returns:
            Dictionary containing RXCUI information or error
        """
        url = f"{self.base_url}/rxcui.json"
        params = {"name": drug_name}

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # RxNorm API returns data in idGroup structure
            id_group = data.get("idGroup", {})
            rxcuis = id_group.get("rxnormId", [])

            if not rxcuis:
                return {
                    "status": "error",
                    "error": f"No RXCUI found for drug name: {drug_name}",
                    "drug_name": drug_name,
                }

            # Return the first RXCUI (most common case)
            # If multiple RXCUIs exist, we'll use the first one
            return {
                "rxcui": rxcuis[0] if isinstance(rxcuis, list) else rxcuis,
                "all_rxcuis": rxcuis if isinstance(rxcuis, list) else [rxcuis],
                "drug_name": drug_name,
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Failed to query RxNorm API for RXCUI: {str(e)}",
                "drug_name": drug_name,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error while querying RXCUI: {str(e)}",
                "drug_name": drug_name,
            }

    def _get_all_names_by_rxcui(self, rxcui: str) -> Dict[str, Any]:
        """
        Get all names associated with an RXCUI, including generic names, brand names, and synonyms.

        Args:
            rxcui: The RxNorm Concept Unique Identifier

        Returns:
            Dictionary containing all names or error
        """
        names = []

        # Method 1: Get names from allProperties endpoint
        try:
            url = f"{self.base_url}/rxcui/{rxcui}/allProperties.json"
            params = {"prop": "names"}
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # RxNorm API returns data in propConceptGroup.propConcept structure
            prop_concept_group = data.get("propConceptGroup", {})
            prop_concepts = prop_concept_group.get("propConcept", [])

            if prop_concepts:
                # Ensure prop_concepts is a list
                if not isinstance(prop_concepts, list):
                    prop_concepts = [prop_concepts]

                # Extract all name values from propConcept array
                for prop_concept in prop_concepts:
                    if isinstance(prop_concept, dict):
                        prop_value = prop_concept.get("propValue")
                        if prop_value:
                            names.append(prop_value)
        except Exception:
            # Continue even if this endpoint fails
            pass

        # Method 2: Get brand names (tradenames) from related endpoint
        try:
            url = f"{self.base_url}/rxcui/{rxcui}/related.json"
            params = {"rela": "has_tradename"}
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            related_group = data.get("relatedGroup", {})
            concept_groups = related_group.get("conceptGroup", [])

            if concept_groups:
                # Ensure concept_groups is a list
                if not isinstance(concept_groups, list):
                    concept_groups = [concept_groups]

                # Extract brand names from concept groups
                for concept_group in concept_groups:
                    concept_properties = concept_group.get("conceptProperties", [])
                    if not isinstance(concept_properties, list):
                        concept_properties = [concept_properties]

                    for prop in concept_properties:
                        if isinstance(prop, dict):
                            brand_name = prop.get("name")
                            if brand_name:
                                names.append(brand_name)
        except Exception:
            # Continue even if this endpoint fails
            pass

        # Method 3: Get properties to get the main name
        try:
            url = f"{self.base_url}/rxcui/{rxcui}/properties.json"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            properties = data.get("properties", {})
            if properties:
                main_name = properties.get("name")
                if main_name:
                    names.append(main_name)
                synonym = properties.get("synonym")
                if synonym:
                    names.append(synonym)
        except Exception:
            # Continue even if this endpoint fails
            pass

        if not names:
            return {
                "status": "error",
                "error": f"No names found for RXCUI: {rxcui}",
                "rxcui": rxcui,
            }

        # Remove duplicates while preserving order
        unique_names = []
        seen = set()
        for name in names:
            # Normalize name (strip whitespace, convert to string)
            normalized = str(name).strip() if name else ""
            if normalized and normalized.lower() not in seen:
                unique_names.append(normalized)
                seen.add(normalized.lower())

        return {"rxcui": rxcui, "names": unique_names}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the RxNorm tool.

        Args:
            arguments: Dictionary containing:
                - drug_name (str, required): The name of the drug to search for

        Returns:
            Dictionary containing:
                - rxcui: The RxNorm Concept Unique Identifier
                - names: List of all associated names (generic names, brand names, synonyms, etc.)
                - drug_name: The original drug name queried
                - processed_name: The preprocessed drug name used for search (if different)
        """
        drug_name = arguments.get("drug_name")

        # Validate input
        if not drug_name:
            return {"status": "error", "error": "drug_name parameter is required"}

        # Check for whitespace-only input
        if not drug_name.strip():
            return {
                "status": "error",
                "error": "drug_name cannot be empty or whitespace only",
            }

        # Try original name first
        rxcui_result = self._get_rxcui_by_name(drug_name)

        # If original name fails, try preprocessed version
        processed_name = None
        if "error" in rxcui_result:
            processed_name = self._preprocess_drug_name(drug_name)
            if (
                processed_name
                and processed_name != drug_name
                and processed_name.strip()
            ):
                # Try with preprocessed name
                rxcui_result = self._get_rxcui_by_name(processed_name)

        if "error" in rxcui_result:
            # Return helpful error message
            error_msg = rxcui_result.get("error", "Unknown error")
            if processed_name and processed_name != drug_name:
                error_msg += f" (also tried preprocessed name: '{processed_name}')"
            return {
                "status": "error",
                "error": error_msg,
                "drug_name": drug_name,
                "processed_name": processed_name
                if processed_name != drug_name
                else None,
            }

        rxcui = rxcui_result["rxcui"]

        # Step 2: Get all names by RXCUI
        names_result = self._get_all_names_by_rxcui(rxcui)

        if "error" in names_result:
            # If we got RXCUI but failed to get names, return what we have
            return {
                "rxcui": rxcui,
                "drug_name": drug_name,
                "processed_name": processed_name
                if processed_name != drug_name
                else None,
                "error": names_result["error"],
                "all_rxcuis": rxcui_result.get("all_rxcuis", []),
            }

        # Combine results
        result = {
            "rxcui": rxcui,
            "drug_name": drug_name,
            "names": names_result["names"],
            "all_rxcuis": rxcui_result.get("all_rxcuis", []),
        }

        # Include processed_name if it was used
        if processed_name and processed_name != drug_name:
            result["processed_name"] = processed_name

        return result
