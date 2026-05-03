from typing import Dict, Any, List, Optional
import requests
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("PathwayCommonsTool")
class PathwayCommonsTool(BaseTool):
    """
    Tool for interacting with Pathway Commons (PC2).
    """

    BASE_URL = "https://www.pathwaycommons.org/pc2"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the Pathway Commons tool action.
        """
        action = arguments.get("action")

        if action == "search_pathways":
            return self.search_pathways(
                keyword=arguments.get("keyword"),
                datasource=arguments.get("datasource"),
                limit=arguments.get("limit", 10),
            )
        elif action == "get_interaction_graph":
            gene_list = arguments.get("gene_list")
            if not gene_list:
                raise ValueError("gene_list is required for get_interaction_graph")
            return self.get_interaction_graph(gene_list)
        else:
            raise ValueError(f"Unknown action: {action}")

    def search_pathways(
        self, keyword: str, datasource: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search for pathways.
        """
        url = f"{self.BASE_URL}/search"
        params = {"q": keyword, "type": "Pathway", "format": "json"}

        if datasource:
            params["datasource"] = datasource

        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            pathways = []
            for hit in data.get("searchHit", [])[:limit]:
                pathways.append(
                    {
                        "name": hit.get("name"),
                        "uri": hit.get("uri"),
                        "source": hit.get("dataSource"),
                        "organism": hit.get("organism"),
                    }
                )

            return {"total_hits": data.get("numHits"), "pathways": pathways}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_interaction_graph(self, gene_list: List[str]) -> Dict[str, Any]:
        """
        Get SIF graph for genes.
        WARNING: The 'graph' endpoint usually returns SIF text, not JSON.
        We will return the raw text or parse it if simple.
        SIF format: source relation target
        """
        url = f"{self.BASE_URL}/graph"
        # source parameter takes list of gene symbols
        # kind=neighborhood is common, or pathsbetween
        # Let's assume pathsbetween for list of genes if size > 1, or neighborhood if size=1?
        # Simpler: just use 'neighborhood' for all provided genes? Or simple interaction search?
        # Docs usually say `source=A,B,C`.

        genes_str = ",".join(gene_list)
        params = {
            "source": genes_str,
            "kind": "neighborhood",  # Get neighborhood of these genes
            "format": "SIF",
        }

        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()

            # SIF is tab separated lines
            lines = response.text.strip().split("\n")
            interactions = []
            for line in lines:
                parts = line.split("\t")
                if len(parts) >= 3:
                    interactions.append(
                        {"source": parts[0], "relation": parts[1], "target": parts[2]}
                    )

            return {"format": "SIF", "interactions": interactions}
        except Exception as e:
            return {"status": "error", "error": str(e)}
