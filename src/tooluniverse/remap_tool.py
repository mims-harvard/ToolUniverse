import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("ReMapRESTTool")
class ReMapRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30
        fields = tool_config.get("fields", {})
        self.endpoint_template = fields.get(
            "endpoint",
            "https://www.encodeproject.org/search/?type=Experiment&assay_title=TF+ChIP-seq&target.label={gene_name}&biosample_ontology.term_name={cell_type}&format=json&limit={limit}",
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            gene_name = arguments.get("gene_name", "")
            if not gene_name:
                return {"status": "error", "error": "gene_name is required"}
            cell_type = arguments.get("cell_type", "HepG2")
            limit = min(int(arguments.get("limit", 10)), 50)

            url = self.endpoint_template.format(
                gene_name=gene_name,
                cell_type=cell_type,
                limit=limit,
            )

            response = self.session.get(url, timeout=self.timeout)
            # ENCODE returns HTTP 404 when the search yields zero results;
            # treat that as an empty result set rather than a hard error.
            if response.status_code == 404:
                resp_data = {}
                try:
                    resp_data = response.json()
                except Exception:
                    pass
                raw_experiments = resp_data.get("@graph", [])
                return {
                    "status": "success",
                    "data": {
                        "experiments": [],
                        "count": 0,
                        "gene_name": gene_name,
                        "cell_type": cell_type,
                        "url": url,
                        "note": "No experiments found for this gene/cell-type combination.",
                    },
                }
            response.raise_for_status()
            resp_data = response.json()

            raw_experiments = resp_data.get("@graph", [])
            experiments = [
                {
                    "accession": e.get("accession"),
                    "assay_title": e.get("assay_title"),
                    "target": e.get("target"),
                    "biosample_ontology": e.get("biosample_ontology"),
                    "description": e.get("description"),
                    "status": e.get("status"),
                }
                for e in raw_experiments
            ]

            return {
                "status": "success",
                "data": {
                    "experiments": experiments,
                    "count": len(experiments),
                    "gene_name": gene_name,
                    "cell_type": cell_type,
                    "url": url,
                },
            }
        except Exception as e:
            return {"status": "error", "error": f"ReMap API error: {str(e)}"}
