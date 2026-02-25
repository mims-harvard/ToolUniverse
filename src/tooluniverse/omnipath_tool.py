# omnipath_tool.py
"""
OmniPath API tool for ToolUniverse.

OmniPath is the largest integrated database of intra- and intercellular
signaling knowledge. It combines data from 100+ resources including
CellPhoneDB, CellChatDB, CellTalkDB, SIGNOR, KEGG, Reactome, and more.

Provides access to:
- Ligand-receptor interactions (cell-cell communication)
- Intercellular role annotations (ligand/receptor classification)
- Signaling pathway interactions (directed, signed PPI)
- Protein complex compositions
- Cell communication annotations (from CellPhoneDB/CellChatDB/etc.)
- Enzyme-substrate (PTM) relationships

API: https://omnipathdb.org/
No authentication required. JSON format supported.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

OMNIPATH_BASE_URL = "https://omnipathdb.org"


@register_tool("OmniPathTool")
class OmniPathTool(BaseTool):
    """
    Tool for querying OmniPath intercellular and intracellular signaling data.

    OmniPath integrates 100+ databases covering:
    - Ligand-receptor interactions (14,000+ pairs)
    - Intercellular communication roles
    - Signaling pathway interactions
    - Protein complexes (22,000+)
    - Cell communication annotations
    - Enzyme-substrate relationships

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "ligand_receptor")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the OmniPath API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"OmniPath API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to OmniPath API at omnipathdb.org"}
        except requests.exceptions.HTTPError as e:
            return {"error": f"OmniPath API HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying OmniPath: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate OmniPath endpoint."""
        if self.endpoint == "ligand_receptor":
            return self._get_ligand_receptor(arguments)
        elif self.endpoint == "intercell":
            return self._get_intercell(arguments)
        elif self.endpoint == "signaling":
            return self._get_signaling(arguments)
        elif self.endpoint == "complexes":
            return self._get_complexes(arguments)
        elif self.endpoint == "annotations":
            return self._get_annotations(arguments)
        elif self.endpoint == "enz_sub":
            return self._get_enzyme_substrate(arguments)
        elif self.endpoint == "tf_target":
            return self._get_tf_target_interactions(arguments)
        elif self.endpoint == "dorothea":
            return self._get_dorothea_regulon(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _make_request(self, path: str, params: Dict[str, Any]) -> Any:
        """Make an HTTP request to OmniPath API."""
        url = f"{OMNIPATH_BASE_URL}/{path}"
        # Always request JSON format
        params["format"] = "json"
        response = requests.get(url, params=params, timeout=self.timeout)
        # Check for OmniPath text error responses
        if response.headers.get("content-type", "").startswith("text/plain"):
            text = response.text.strip()
            if (
                "not entirely good" in text.lower()
                or "unknown argument" in text.lower()
            ):
                raise ValueError(f"OmniPath API error: {text[:200]}")
        response.raise_for_status()
        return response.json()

    def _get_ligand_receptor(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get ligand-receptor interactions from the ligrecextra dataset."""
        params = {
            "genesymbols": "yes",
            "fields": "sources,references,curation_effort,type",
            "datasets": "ligrecextra",
        }

        # Add protein filters
        if arguments.get("partners"):
            params["partners"] = arguments["partners"]
        if arguments.get("sources"):
            params["sources"] = arguments["sources"]
        if arguments.get("targets"):
            params["targets"] = arguments["targets"]
        if arguments.get("databases"):
            params["databases"] = arguments["databases"]
        if arguments.get("organisms"):
            params["organisms"] = str(arguments["organisms"])
        if arguments.get("limit"):
            params["limit"] = str(arguments["limit"])

        # Must have at least one protein filter
        if not any(arguments.get(k) for k in ["partners", "sources", "targets"]):
            return {
                "error": "At least one of 'partners', 'sources', or 'targets' is required to query ligand-receptor interactions."
            }

        data = self._make_request("interactions/", params)

        if not isinstance(data, list):
            return {"error": f"Unexpected response format from OmniPath: {type(data)}"}

        interactions = []
        for item in data:
            interactions.append(
                {
                    "source_uniprot": item.get("source"),
                    "target_uniprot": item.get("target"),
                    "source_genesymbol": item.get("source_genesymbol"),
                    "target_genesymbol": item.get("target_genesymbol"),
                    "is_directed": bool(item.get("is_directed", 0)),
                    "is_stimulation": bool(item.get("is_stimulation", 0)),
                    "is_inhibition": bool(item.get("is_inhibition", 0)),
                    "sources": item.get("sources", []),
                    "curation_effort": item.get("curation_effort"),
                    "type": item.get("type"),
                }
            )

        # Sort by curation effort (most curated first)
        interactions.sort(key=lambda x: x.get("curation_effort") or 0, reverse=True)

        return {
            "data": interactions,
            "metadata": {
                "source": "OmniPath (omnipathdb.org)",
                "dataset": "ligrecextra",
                "total_interactions": len(interactions),
                "description": "Ligand-receptor interactions from CellPhoneDB, CellChatDB, CellTalkDB, and 20+ databases",
            },
        }

    def _get_intercell(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get intercellular communication role annotations."""
        params = {}

        if arguments.get("proteins"):
            params["proteins"] = arguments["proteins"]
        if arguments.get("categories"):
            params["categories"] = arguments["categories"]
        if arguments.get("scope"):
            params["scope"] = arguments["scope"]
        if arguments.get("transmitter") is not None:
            params["transmitter"] = "yes" if arguments["transmitter"] else "no"
        if arguments.get("receiver") is not None:
            params["receiver"] = "yes" if arguments["receiver"] else "no"
        if arguments.get("secreted") is not None:
            params["secreted"] = "yes" if arguments["secreted"] else "no"
        if arguments.get("limit"):
            params["limit"] = str(arguments["limit"])

        data = self._make_request("intercell/", params)

        if not isinstance(data, list):
            return {"error": f"Unexpected response format from OmniPath: {type(data)}"}

        results = []
        for item in data:
            results.append(
                {
                    "uniprot": item.get("uniprot"),
                    "genesymbol": item.get("genesymbol"),
                    "category": item.get("category"),
                    "parent": item.get("parent"),
                    "database": item.get("database"),
                    "scope": item.get("scope"),
                    "aspect": item.get("aspect"),
                    "consensus_score": item.get("consensus_score"),
                    "transmitter": item.get("transmitter", False),
                    "receiver": item.get("receiver", False),
                    "secreted": item.get("secreted", False),
                    "plasma_membrane_transmembrane": item.get(
                        "plasma_membrane_transmembrane", False
                    ),
                }
            )

        return {
            "data": results,
            "metadata": {
                "source": "OmniPath Intercell (omnipathdb.org)",
                "total_annotations": len(results),
                "description": "Intercellular communication role annotations from 40+ databases",
            },
        }

    def _get_signaling(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get intracellular signaling pathway interactions."""
        datasets = arguments.get("datasets") or "omnipath"
        params = {
            "genesymbols": "yes",
            "fields": "sources,references,curation_effort,type",
            "datasets": datasets,
        }

        if arguments.get("partners"):
            params["partners"] = arguments["partners"]
        if arguments.get("sources"):
            params["sources"] = arguments["sources"]
        if arguments.get("targets"):
            params["targets"] = arguments["targets"]
        if arguments.get("directed") is not None:
            params["directed"] = "yes" if arguments["directed"] else "no"
        if arguments.get("signed") is not None:
            params["signed"] = "yes" if arguments["signed"] else "no"
        if arguments.get("organisms"):
            params["organisms"] = str(arguments["organisms"])
        if arguments.get("limit"):
            params["limit"] = str(arguments["limit"])

        if not any(arguments.get(k) for k in ["partners", "sources", "targets"]):
            return {
                "error": "At least one of 'partners', 'sources', or 'targets' is required to query signaling interactions."
            }

        data = self._make_request("interactions/", params)

        if not isinstance(data, list):
            return {"error": f"Unexpected response format from OmniPath: {type(data)}"}

        interactions = []
        for item in data:
            interactions.append(
                {
                    "source_uniprot": item.get("source"),
                    "target_uniprot": item.get("target"),
                    "source_genesymbol": item.get("source_genesymbol"),
                    "target_genesymbol": item.get("target_genesymbol"),
                    "is_directed": bool(item.get("is_directed", 0)),
                    "is_stimulation": bool(item.get("is_stimulation", 0)),
                    "is_inhibition": bool(item.get("is_inhibition", 0)),
                    "consensus_direction": bool(item.get("consensus_direction", 0)),
                    "consensus_stimulation": bool(item.get("consensus_stimulation", 0)),
                    "consensus_inhibition": bool(item.get("consensus_inhibition", 0)),
                    "sources": item.get("sources", []),
                    "curation_effort": item.get("curation_effort"),
                    "type": item.get("type"),
                }
            )

        interactions.sort(key=lambda x: x.get("curation_effort") or 0, reverse=True)

        return {
            "data": interactions,
            "metadata": {
                "source": "OmniPath (omnipathdb.org)",
                "datasets": datasets,
                "total_interactions": len(interactions),
            },
        }

    def _get_complexes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein complex compositions."""
        proteins = arguments.get("proteins", "")
        if not proteins:
            return {
                "error": "proteins parameter is required (UniProt accession(s), e.g., P01137)"
            }

        params = {"proteins": proteins}
        if arguments.get("databases"):
            params["databases"] = arguments["databases"]

        data = self._make_request("complexes/", params)

        if not isinstance(data, list):
            return {"error": f"Unexpected response format from OmniPath: {type(data)}"}

        complexes = []
        for item in data:
            complexes.append(
                {
                    "name": item.get("name"),
                    "components": item.get("components"),
                    "components_genesymbols": item.get("components_genesymbols"),
                    "stoichiometry": item.get("stoichiometry"),
                    "sources": item.get("sources", []),
                    "references": item.get("references"),
                    "identifiers": item.get("identifiers"),
                }
            )

        return {
            "data": complexes,
            "metadata": {
                "source": "OmniPath Complexes (omnipathdb.org)",
                "query_proteins": proteins,
                "total_complexes": len(complexes),
                "description": "Protein complexes from CORUM, CellPhoneDB, ComplexPortal, and other databases",
            },
        }

    def _get_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get cell communication annotations from CellPhoneDB, CellChatDB, etc."""
        proteins = arguments.get("proteins", "")
        if not proteins:
            return {
                "error": "proteins parameter is required (UniProt accession(s) or gene symbol(s))"
            }

        databases = arguments.get("databases") or "CellPhoneDB,CellChatDB"
        genesymbols = arguments.get("genesymbols")
        if genesymbols is None:
            genesymbols = True

        params = {
            "proteins": proteins,
            "databases": databases,
            "genesymbols": "yes" if genesymbols else "no",
        }

        data = self._make_request("annotations/", params)

        if not isinstance(data, list):
            return {"error": f"Unexpected response format from OmniPath: {type(data)}"}

        annotations = []
        for item in data:
            annotations.append(
                {
                    "uniprot": item.get("uniprot"),
                    "genesymbol": item.get("genesymbol"),
                    "entity_type": item.get("entity_type"),
                    "source": item.get("source"),
                    "label": item.get("label"),
                    "value": item.get("value"),
                    "record_id": item.get("record_id"),
                }
            )

        return {
            "data": annotations,
            "metadata": {
                "source": "OmniPath Annotations (omnipathdb.org)",
                "databases_queried": databases,
                "total_annotations": len(annotations),
            },
        }

    def _get_enzyme_substrate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get enzyme-substrate (PTM) interactions."""
        params = {
            "genesymbols": "yes",
            "fields": "sources,references",
        }

        if arguments.get("enzymes"):
            params["enzymes"] = arguments["enzymes"]
        if arguments.get("substrates"):
            params["substrates"] = arguments["substrates"]
        if arguments.get("types"):
            params["types"] = arguments["types"]
        if arguments.get("organisms"):
            params["organisms"] = str(arguments["organisms"])
        if arguments.get("limit"):
            params["limit"] = str(arguments["limit"])

        if not any(arguments.get(k) for k in ["enzymes", "substrates"]):
            return {"error": "At least one of 'enzymes' or 'substrates' is required."}

        data = self._make_request("enz_sub/", params)

        if not isinstance(data, list):
            return {"error": f"Unexpected response format from OmniPath: {type(data)}"}

        results = []
        for item in data:
            results.append(
                {
                    "enzyme_uniprot": item.get("enzyme"),
                    "substrate_uniprot": item.get("substrate"),
                    "enzyme_genesymbol": item.get("enzyme_genesymbol"),
                    "substrate_genesymbol": item.get("substrate_genesymbol"),
                    "residue_type": item.get("residue_type"),
                    "residue_offset": item.get("residue_offset"),
                    "modification": item.get("modification"),
                    "sources": item.get("sources", []),
                }
            )

        return {
            "data": results,
            "metadata": {
                "source": "OmniPath Enzyme-Substrate (omnipathdb.org)",
                "total_ptms": len(results),
                "description": "PTM data from PhosphoSite, phosphoELM, dbPTM, SIGNOR, and other databases",
            },
        }

    def _get_tf_target_interactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tf_gene = arguments.get("tf_gene")
        target_gene = arguments.get("target_gene")
        confidence_level = arguments.get("confidence_level")

        if not tf_gene and not target_gene:
            return {"error": "At least one of 'tf_gene' or 'target_gene' is required"}

        params = {
            "genesymbols": "yes",
            "fields": "sources,references,curation_effort,type",
            "datasets": "dorothea,collectri",
        }

        if tf_gene:
            params["sources"] = tf_gene
        if target_gene:
            params["targets"] = target_gene

        data = self._make_request("interactions/", params)

        if not isinstance(data, list):
            return {"error": f"Unexpected response format from OmniPath: {type(data)}"}

        interactions = []
        for item in data:
            dorothea_level = item.get("dorothea_level")
            if (
                confidence_level
                and dorothea_level
                and dorothea_level != confidence_level
            ):
                continue

            interactions.append(
                {
                    "tf_uniprot": item.get("source"),
                    "target_uniprot": item.get("target"),
                    "tf_genesymbol": item.get("source_genesymbol"),
                    "target_genesymbol": item.get("target_genesymbol"),
                    "is_stimulation": bool(item.get("is_stimulation", 0)),
                    "is_inhibition": bool(item.get("is_inhibition", 0)),
                    "dorothea_level": dorothea_level,
                    "sources": item.get("sources", []),
                    "curation_effort": item.get("curation_effort"),
                }
            )

        interactions.sort(key=lambda x: x.get("curation_effort") or 0, reverse=True)

        return {
            "data": interactions,
            "metadata": {
                "source": "OmniPath DoRothEA + CollecTRI (omnipathdb.org)",
                "total_interactions": len(interactions),
                "description": "TF-target interactions from DoRothEA and CollecTRI regulons",
            },
        }

    def _get_dorothea_regulon(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tf_gene = arguments.get("tf_gene")
        if not tf_gene:
            return {"error": "'tf_gene' is required for DoRothEA regulon query"}

        confidence_levels = arguments.get("confidence_levels")

        params = {
            "genesymbols": "yes",
            "fields": "sources,references,curation_effort,type",
            "datasets": "dorothea",
            "sources": tf_gene,
        }

        data = self._make_request("interactions/", params)

        if not isinstance(data, list):
            return {"error": f"Unexpected response format from OmniPath: {type(data)}"}

        interactions = []
        for item in data:
            dorothea_level = item.get("dorothea_level")

            if confidence_levels:
                levels = [level.strip() for level in confidence_levels.split(",")]
                if dorothea_level not in levels:
                    continue

            interactions.append(
                {
                    "tf_genesymbol": item.get("source_genesymbol"),
                    "target_genesymbol": item.get("target_genesymbol"),
                    "target_uniprot": item.get("target"),
                    "mor": 1
                    if item.get("is_stimulation")
                    else (-1 if item.get("is_inhibition") else 0),
                    "is_stimulation": bool(item.get("is_stimulation", 0)),
                    "is_inhibition": bool(item.get("is_inhibition", 0)),
                    "dorothea_level": dorothea_level,
                    "sources": item.get("sources", []),
                    "curation_effort": item.get("curation_effort"),
                }
            )

        interactions.sort(key=lambda x: x.get("curation_effort") or 0, reverse=True)

        by_level = {}
        for i in interactions:
            lvl = i.get("dorothea_level") or "unknown"
            by_level.setdefault(lvl, []).append(i)

        return {
            "data": interactions,
            "metadata": {
                "source": "OmniPath DoRothEA (omnipathdb.org)",
                "tf_gene": tf_gene,
                "total_targets": len(interactions),
                "by_confidence_level": {k: len(v) for k, v in by_level.items()},
                "description": "DoRothEA regulon with mode of regulation (MoR): +1=activation, -1=repression",
            },
        }
