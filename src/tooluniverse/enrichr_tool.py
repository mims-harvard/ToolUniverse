import json
import requests
import urllib.parse
import networkx as nx
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("EnrichrTool")
class EnrichrTool(BaseTool):
    """
    Tool to perform gene enrichment analysis using Enrichr.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Constants
        self.enrichr_url = "https://maayanlab.cloud/Enrichr/addList"
        self.enrichment_url = "https://maayanlab.cloud/Enrichr/enrich"

    def run(self, arguments):
        """Main entry point for the tool."""
        genes = arguments.get("gene_list")
        libs = arguments.get(
            "libs",
            [
                "WikiPathways_2024_Human",
                "Reactome_Pathways_2024",
                "MSigDB_Hallmark_2020",
                "GO_Molecular_Function_2023",
                "GO_Biological_Process_2023",
            ],
        )
        connected_path, connections = self.enrichr_api(genes, libs)
        # Convert to JSON string for schema compatibility
        import json

        result = {"connected_paths": connected_path, "connections": connections}
        return {"status": "success", "data": json.dumps(result, indent=2)}

    def get_official_gene_name(self, gene_name):
        """
        Retrieve the official gene symbol for a given gene name or synonym using the MyGene.info API.

        Parameters
            gene_name (str): The gene name or synonym to query.

        Returns
            str: The official gene symbol if found; otherwise, raises an Exception.
        """
        # URL-encode the gene_name to handle special characters
        encoded_gene_name = urllib.parse.quote(gene_name)
        url = f"https://mygene.info/v3/query?q={encoded_gene_name}&fields=symbol,alias&species=human"

        response = requests.get(url)
        if response.status_code != 200:
            return f"Error querying MyGene.info API: {response.status_code}"

        data = response.json()
        hits = data.get("hits", [])
        if not hits:
            return f"No data found for: {gene_name}. Please check the gene name and try again."

        # Attempt to find an exact match in the official symbol or among aliases.
        for hit in hits:
            symbol = hit.get("symbol", "")
            if symbol.upper() == gene_name.upper():
                print(
                    f"[enrichr_api] Using the official gene name: '{symbol}' instead of {gene_name}",
                    flush=True,
                )
                return symbol
            aliases = hit.get("alias", [])
            if any(gene_name.upper() == alias.upper() for alias in aliases):
                print(
                    f"[enrichr_api] Using the official gene name: '{symbol}' instead of {gene_name}",
                    flush=True,
                )
                return symbol

        # If no exact match is found, return the symbol of the top hit.
        top_hit = hits[0]
        symbol = top_hit.get("symbol", None)
        if symbol:
            print(
                f"[enrichr_api] Using the official gene name: '{symbol}' instead of {gene_name}",
                flush=True,
            )
            return symbol
        else:
            return f"No official gene symbol found for: {gene_name}. Please ensure it is correct."

    def submit_gene_list(self, gene_list):
        """
        Submit the gene list to Enrichr and return the user list ID.

        Parameters
            gene_list (str): Newline-separated string of gene names.

        Returns
            str: The user list ID from Enrichr.
        """
        payload = {
            "list": (None, gene_list),
            "description": (None, f"Gene list for {gene_list}"),
        }
        response = requests.post(self.enrichr_url, files=payload)

        if not response.ok:
            return "Error submitting gene list to Enrichr"

        return json.loads(response.text)["userListId"]

    def get_enrichment_results(self, user_list_id, library):
        """
        Fetch enrichment results for a specific library.

        Parameters
            user_list_id (str): The user list ID from Enrichr.
            library (str): The name of the enrichment library.

        Returns
            dict: The enrichment results.
        """
        query_string = f"?userListId={user_list_id}&backgroundType={library}"
        response = requests.get(self.enrichment_url + query_string)

        if not response.ok:
            return f"Error fetching enrichment results for {library}"

        return json.loads(response.text)

    def build_graph(self, genes, enrichment_results):
        """
        Initialize and build the graph with gene nodes and enriched terms.

        Parameters
            genes (list): List of gene names.
            enrichment_results (dict): Dictionary of enrichment results by library.

        Returns
            networkx.Graph: The constructed graph.
        """
        G = nx.Graph()

        # Add gene nodes
        for gene in genes:
            G.add_node(gene, type="gene")

        # Add enriched terms and edges
        for library, results in enrichment_results.items():
            for term in results:
                term_name = term[1]
                associated_genes = term[5]
                G.add_node(term_name, type="term", library=library)

                for gene in associated_genes:
                    if gene in genes:
                        G.add_edge(gene, term_name, weight=round(term[4], 2))

        return G

    def rank_paths_by_weight(self, G, source, target):
        """
        Find and rank paths between source and target based on total edge weight.

        Parameters
            G (networkx.Graph): The graph to search.
            source (str): The source node.
            target (str): The target node.

        Returns
            list: List of tuples (path, weight) sorted by weight descending.
        """
        all_paths = list(nx.all_simple_paths(G, source=source, target=target))
        path_weights = []

        for path in all_paths:
            total_weight = sum(
                G[path[i]][path[i + 1]].get("weight", 1) for i in range(len(path) - 1)
            )
            path_weights.append((path, total_weight))

        return sorted(path_weights, key=lambda x: x[1], reverse=True)

    def rank_paths_to_term(self, G, gene, term):
        """
        Find and rank paths from each gene to a specified term based on total edge weight.

        Parameters
            G (networkx.Graph): The graph to search.
            gene (str): The source gene.
            term (str): The target term.

        Returns
            list or None: List of tuples (path, weight) sorted by weight descending, or None if no paths.
        """
        all_paths = list(nx.all_simple_paths(G, source=gene, target=term))
        path_weights = []

        for path in all_paths:
            total_weight = sum(
                G[path[i]][path[i + 1]].get("weight", 1) for i in range(len(path) - 1)
            )
            path_weights.append((path, total_weight))

        if len(path_weights) != 0:
            return sorted(path_weights, key=lambda x: x[1], reverse=True)
        return None

    def enrichr_api(self, genes, libs):
        """
        Main API function to perform gene enrichment analysis.

        Parameters
            genes (list): List of gene names.
            libs (list): List of enrichment libraries to use.

        Returns
            tuple: (connected_path, connections) dictionaries.
        """
        # Convert each gene to its official name and log the result
        genes = [self.get_official_gene_name(gene) for gene in genes]
        print("Official gene names:", genes)

        # Ensure at least two genes are provided for path ranking
        if len(genes) < 2:
            raise ValueError(
                "At least two genes are required to rank paths between genes."
            )

        # Prepare the gene list for Enrichr submission
        gene_list_str = "\n".join(genes)
        user_list_id = self.submit_gene_list(gene_list_str)

        # Retrieve enrichment results for each specified library
        enrichment_results = {}
        for library in libs:
            results = self.get_enrichment_results(user_list_id, library)
            # Safely get the top 5 results; if the library key isn't found, default to an empty list
            enrichment_results[library] = results.get(library, [])[:5]

        # Build the graph from the gene list and enrichment results
        G = self.build_graph(genes, enrichment_results)

        # Rank paths from the first gene to the second (limit to top 20)
        ranked_paths = self.rank_paths_by_weight(G, genes[0], genes[1])
        connected_path = {}
        for path, weight in ranked_paths[:20]:
            connected_path[f"Path: {path}"] = f"Total Weight: {weight}"

        # Compute connectivity data for each gene and graph node (limit per pair)
        connections = {}
        for gene in genes:
            for term in G.nodes:
                paths_to_term = self.rank_paths_to_term(G, gene, term)
                if paths_to_term is not None:
                    connections[f"Connectivity: {gene} - {term}"] = paths_to_term[:5]

        # Check for empty outputs and print helper messages
        if not connected_path:
            print(
                f"[Enrichr] No ranked paths were found between the gene pair {genes}."
            )

        if not connections:
            print(
                f"[Enrichr] No connection between genes and terms in the enriched graph of {genes}."
            )

        return connected_path, connections
