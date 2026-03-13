# mydisease_tool.py
"""
MyDisease.info API tool for ToolUniverse.

Provides access to the MyDisease.info BioThings API, which aggregates
disease annotations from multiple sources: MONDO, Disease Ontology,
CTD (Comparative Toxicogenomics Database), HPO (Human Phenotype Ontology),
and DisGeNET (gene-disease associations).

API: https://mydisease.info/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool


MYDISEASE_BASE_URL = "https://mydisease.info/v1"


class MyDiseaseTool(BaseTool):
    """
    Tool for MyDisease.info BioThings API providing aggregated disease
    annotations from MONDO, Disease Ontology, CTD, HPO, and DisGeNET.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_disease")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MyDisease.info API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"MyDisease.info API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to MyDisease.info API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "error": f"Disease not found: {arguments.get('disease_id', arguments.get('query', ''))}"
                }
            return {"error": f"MyDisease.info API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying MyDisease.info: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_disease":
            return self._get_disease(arguments)
        elif self.endpoint == "search_diseases":
            return self._search_diseases(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive disease annotations by disease ID."""
        disease_id = arguments.get("disease_id", "")
        if not disease_id:
            return {"error": "disease_id parameter is required (e.g., 'MONDO:0005148')"}

        fields_param = arguments.get("fields", "mondo,disease_ontology,ctd,hpo")

        # Build API fields parameter
        if fields_param == "all":
            api_fields = "all"
        else:
            field_map = {
                "mondo": "mondo",
                "disease_ontology": "disease_ontology",
                "ctd": "ctd",
                "hpo": "hpo",
                "disgenet": "disgenet",
            }
            requested = [f.strip() for f in fields_param.split(",")]
            api_parts = []
            for f in requested:
                if f in field_map:
                    api_parts.append(field_map[f])
            api_fields = ",".join(api_parts) if api_parts else "mondo,disease_ontology"

        url = f"{MYDISEASE_BASE_URL}/disease/{disease_id}"
        params = {"fields": api_fields}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Build result
        result = {"disease_id": data.get("_id", disease_id)}

        # Extract MONDO data (API may return a list when multiple MONDO entries exist)
        if "mondo" in data:
            mondo = data["mondo"]
            if isinstance(mondo, list):
                mondo = mondo[0] if mondo else {}
            result["mondo"] = {
                "label": mondo.get("label"),
                "definition": mondo.get("definition"),
                "xrefs": mondo.get("xrefs"),
                "ancestors": mondo.get("ancestors"),
                "children": mondo.get("children"),
            }

        # Extract Disease Ontology data
        if "disease_ontology" in data:
            do = data["disease_ontology"]
            if isinstance(do, list):
                do = do[0] if do else {}
            result["disease_ontology"] = {
                "name": do.get("name"),
                "doid": do.get("doid"),
                "definition": do.get("def"),
                "xrefs": do.get("xrefs"),
                "ancestors": do.get("ancestors"),
                "synonyms": do.get("synonyms"),
            }

        # Extract CTD data
        if "ctd" in data:
            ctd = data["ctd"]
            if isinstance(ctd, list):
                ctd = ctd[0] if ctd else {}
            chems = ctd.get("chemical_related_to_disease", [])
            paths = ctd.get("pathway_related_to_disease", [])
            result["ctd"] = {
                "chemicals_count": len(chems) if isinstance(chems, list) else 1,
                "chemicals": chems[:20] if isinstance(chems, list) else [chems],
                "pathways_count": len(paths) if isinstance(paths, list) else 1,
                "pathways": paths[:20] if isinstance(paths, list) else [paths],
            }

        # Extract HPO data (API returns a list for diseases with multiple OMIM entries)
        if "hpo" in data:
            hpo = data["hpo"]
            if isinstance(hpo, list):
                # Merge phenotypes across all HPO entries
                all_phenos = []
                hpo_names = []
                omim_ids = []
                for entry in hpo:
                    if isinstance(entry, dict):
                        phenos = entry.get("phenotype_related_to_disease", [])
                        if isinstance(phenos, list):
                            all_phenos.extend(phenos)
                        elif phenos:
                            all_phenos.append(phenos)
                        if entry.get("disease_name"):
                            hpo_names.append(entry["disease_name"])
                        if entry.get("omim"):
                            omim_ids.append(entry["omim"])
                result["hpo"] = {
                    "disease_name": hpo_names[0] if hpo_names else None,
                    "omim": omim_ids,
                    "phenotypes_count": len(all_phenos),
                    "phenotypes": all_phenos[:20],
                }
            else:
                phenos = hpo.get("phenotype_related_to_disease", [])
                result["hpo"] = {
                    "disease_name": hpo.get("disease_name"),
                    "omim": hpo.get("omim"),
                    "inheritance": hpo.get("inheritance"),
                    "clinical_course": hpo.get("clinical_course"),
                    "phenotypes_count": len(phenos) if isinstance(phenos, list) else 1,
                    "phenotypes": phenos[:20] if isinstance(phenos, list) else [phenos],
                }

        # Extract DisGeNET data
        if "disgenet" in data:
            result["disgenet"] = data["disgenet"]

        return {
            "data": result,
            "metadata": {
                "source": "MyDisease.info (BioThings)",
                "disease_id": disease_id,
                "fields": fields_param,
            },
        }

    def _search_diseases(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search diseases by keyword."""
        query = arguments.get("query", "")
        if not query:
            return {
                "error": "query parameter is required (e.g., 'breast cancer', 'melanoma')"
            }

        size = min(arguments.get("size", 10), 100)
        fields_param = arguments.get(
            "fields",
            "mondo.label,disease_ontology.name,disease_ontology.doid,hpo.disease_name",
        )

        url = f"{MYDISEASE_BASE_URL}/query"
        params = {
            "q": query,
            "size": size,
            "fields": fields_param,
        }
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        hits = data.get("hits", [])
        diseases = []
        for h in hits:
            entry = {"disease_id": h.get("_id")}
            # Extract nested MONDO label
            if "mondo" in h:
                mondo = h["mondo"]
                entry["mondo_label"] = (
                    mondo.get("label") if isinstance(mondo, dict) else None
                )
            # Extract Disease Ontology name
            if "disease_ontology" in h:
                do = h["disease_ontology"]
                entry["do_name"] = do.get("name") if isinstance(do, dict) else None
                entry["doid"] = do.get("doid") if isinstance(do, dict) else None
            # Extract HPO disease name
            if "hpo" in h:
                hpo = h["hpo"]
                entry["hpo_disease_name"] = (
                    hpo.get("disease_name") if isinstance(hpo, dict) else None
                )
            diseases.append(entry)

        return {
            "data": {
                "total_hits": data.get("total", 0),
                "returned": len(diseases),
                "diseases": diseases,
            },
            "metadata": {
                "source": "MyDisease.info (BioThings)",
                "query": query,
            },
        }
