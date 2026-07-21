import requests
from typing import Any, Dict
from urllib.parse import quote
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("MPDRESTTool")
class MPDRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Use ENCODE as alternative data source for biological samples.
            # MPD's own REST API (phenome.jax.org/api) has no endpoint that
            # takes a strain name + phenotype category directly -- confirmed
            # live, its phenotype endpoints require a measure ID or project
            # symbol the caller doesn't supply here.
            strain = arguments.get("strain", "C57BL/6J")
            limit = arguments.get("limit", 10)

            # searchTerm is a free-text match, unlike biosample_ontology.term_name
            # (a tissue/cell-type ontology field, not a strain field) -- confirmed
            # live the latter always returns zero results for real strain names,
            # while searchTerm correctly surfaces strain-mentioning experiments
            # (e.g. 292 hits for "C57BL/6J") and zero for strains ENCODE has no
            # data on (e.g. "DBA/2J").
            url = (
                "https://www.encodeproject.org/search/?type=Experiment"
                f"&searchTerm={quote(str(strain))}&format=json&limit={limit}"
            )

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            return {
                "status": "success",
                "data": data,
                "url": url,
                "query_info": {
                    "strain": strain,
                    "limit": limit,
                    "data_source": "ENCODE (MPD alternative)",
                    "note": (
                        "ENCODE has no mouse-phenotype-by-strain data model, so "
                        "results are general ENCODE experiments whose free text "
                        "mentions this strain, not curated MPD phenotype "
                        "measurements. 'phenotype_category' is not applied -- "
                        "ENCODE has no equivalent concept. For genuine curated "
                        "phenotype data, query the Mouse Phenome Database "
                        "directly at https://phenome.jax.org/api."
                    ),
                },
            }
        except Exception as e:
            return {"status": "error", "error": f"MPD API error: {str(e)}"}
