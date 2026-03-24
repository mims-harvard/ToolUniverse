"""
ELM (Eukaryotic Linear Motif) Tool - Short Linear Motifs in Proteins

Provides access to the ELM database for querying experimentally validated
short linear motifs (SLiMs) in proteins. SLiMs are compact protein interaction
interfaces involved in regulatory functions like degradation, localization,
post-translational modification, and docking.

ELM categorizes motifs into functional classes:
- CLV: Cleavage sites (protease recognition)
- DEG: Degradation motifs (degrons)
- DOC: Docking motifs (protein-protein interaction)
- LIG: Ligand binding motifs
- MOD: Post-translational modification sites
- TRG: Targeting/localization signals

API base: http://elm.eu.org
No authentication required. Data returned as TSV, parsed to JSON.

Reference: Kumar et al., Nucleic Acids Res. 2022
"""

import csv
import io
import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool


ELM_BASE_URL = "http://elm.eu.org"


@register_tool("ELMTool")
class ELMTool(BaseTool):
    """
    Tool for querying the ELM (Eukaryotic Linear Motif) database.

    Supported operations:
    - get_instances: Get experimentally validated motif instances for a protein
    - list_classes: List all ELM motif classes with regex patterns
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ELM tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "get_instances": self._get_instances,
            "list_classes": self._list_classes,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, list(handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "ELM API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to ELM"}
        except Exception as e:
            return {"status": "error", "error": "ELM error: {}".format(str(e))}

    def _parse_tsv(self, text: str) -> List[Dict[str, str]]:
        """Parse ELM TSV response, skipping comment lines."""
        lines = [line for line in text.strip().split("\n") if not line.startswith("#")]
        if not lines:
            return []
        reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter="\t")
        return [{k: (v or "") for k, v in row.items()} for row in reader]

    def _get_instances(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get experimentally validated motif instances for a protein."""
        uniprot_id = arguments.get("uniprot_id") or arguments.get("uniprot_acc")
        if not uniprot_id:
            return {
                "status": "error",
                "error": "Missing required parameter: uniprot_id (or uniprot_acc)",
            }

        motif_type = arguments.get("motif_type")

        resp = self.session.get(
            "{}/instances.tsv?q={}".format(ELM_BASE_URL, uniprot_id),
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": "ELM returned HTTP {}".format(resp.status_code),
            }

        rows = self._parse_tsv(resp.text)
        if not rows:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "uniprot_id": uniprot_id,
                    "total_instances": 0,
                    "message": "No motif instances found for {}".format(uniprot_id),
                },
            }

        results = []
        for row in rows:
            elm_id = row.get("ELMIdentifier", "")
            elm_type = row.get("ELMType", "")

            if motif_type and elm_type.upper() != motif_type.upper():
                continue

            start = row.get("Start", "")
            end = row.get("End", "")
            refs = row.get("References", "")
            methods = row.get("Methods", "")
            pdb = row.get("PDB", "")

            results.append(
                {
                    "accession": row.get("Accession", ""),
                    "elm_identifier": elm_id,
                    "elm_type": elm_type,
                    "protein_name": row.get("ProteinName", ""),
                    "start": int(start) if start.isdigit() else None,
                    "end": int(end) if end.isdigit() else None,
                    "references": [r.strip() for r in refs.split(" ") if r.strip()]
                    if refs
                    else [],
                    "methods": [m.strip() for m in methods.split(";") if m.strip()]
                    if methods
                    else [],
                    "instance_logic": row.get("InstanceLogic", ""),
                    "pdb_ids": [p.strip() for p in pdb.split(" ") if p.strip()]
                    if pdb
                    else [],
                    "organism": row.get("Organism", ""),
                }
            )

        type_summary = {}
        for r in results:
            t = r["elm_type"]
            type_summary[t] = type_summary.get(t, 0) + 1

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "uniprot_id": uniprot_id,
                "total_instances": len(results),
                "motif_type_summary": type_summary,
            },
        }

    def _list_classes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List ELM motif classes with regex patterns and descriptions."""
        motif_type = arguments.get("motif_type")
        query = arguments.get("query")
        max_results = arguments.get("max_results", 50)

        resp = self.session.get(
            "{}/elms/elms_index.tsv".format(ELM_BASE_URL),
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": "ELM returned HTTP {}".format(resp.status_code),
            }

        rows = self._parse_tsv(resp.text)

        results = []
        for row in rows:
            elm_id = row.get("ELMIdentifier", "")
            description = row.get("Description", "")
            func_name = row.get("FunctionalSiteName", "")

            if motif_type:
                prefix = elm_id.split("_")[0] if "_" in elm_id else ""
                if prefix.upper() != motif_type.upper():
                    continue

            if query:
                q_lower = query.lower()
                searchable = "{}|{}|{}".format(elm_id, description, func_name).lower()
                if q_lower not in searchable:
                    continue

            instances = row.get("#Instances", "0")
            pdb_instances = row.get("#Instances_in_PDB", "0")

            results.append(
                {
                    "accession": row.get("Accession", ""),
                    "elm_identifier": elm_id,
                    "functional_site_name": func_name,
                    "description": description,
                    "regex": row.get("Regex", ""),
                    "probability": float(row.get("Probability", "0") or "0"),
                    "num_instances": int(instances) if instances.isdigit() else 0,
                    "num_pdb_instances": int(pdb_instances)
                    if pdb_instances.isdigit()
                    else 0,
                }
            )

        total = len(results)
        results = results[:max_results]

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_classes": total,
                "returned": len(results),
                "filter_type": motif_type,
                "filter_query": query,
            },
        }
