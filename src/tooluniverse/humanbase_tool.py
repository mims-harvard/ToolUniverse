import networkx as nx
import requests
import urllib.parse
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("HumanBaseTool")
class HumanBaseTool(BaseTool):
    """
    Tool to retrieve protein-protein interactions and biological processes from HumanBase.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)

    def run(self, arguments):
        """Main entry point for the tool."""
        # Feature-111A-007: 'genes' as alias for 'gene_list'
        gene_list = arguments.get("gene_list") or arguments.get("genes")
        tissue = arguments.get("tissue", "brain")
        max_node = arguments.get("max_node") or arguments.get("top_n") or 10
        interaction = arguments.get("interaction", None)
        string_mode = arguments.get("string_mode", True)

        graph, bp_collection = self.humanbase_ppi_retrieve(
            gene_list, tissue, max_node, interaction
        )

        if graph.number_of_nodes() == 0:
            return {
                "status": "error",
                "error": (
                    "HumanBase network API returned no interaction data. "
                    "The API may be temporarily unavailable or the tissue "
                    f"'{tissue}' may not be supported. Try "
                    "STRING_get_interaction_partners as an alternative."
                ),
                "query": {"genes": gene_list, "tissue": tissue},
                "biological_processes": bp_collection,
            }

        if string_mode:
            result = self._convert_to_string(graph, bp_collection, gene_list, tissue)
            return {"status": "success", "data": result}
        else:
            # For non-string mode, return structured data
            return {
                "status": "success",
                "data": {"graph": graph, "biological_processes": bp_collection},
            }

    def get_official_gene_name(self, gene_name):
        """
        Retrieve the official gene symbol for a given gene name or synonym using the MyGene.info API.

        Parameters
            gene_name (str): The gene name or synonym to query.

        Returns
            str: The official gene symbol if found; otherwise, an error message string.
        """
        encoded_gene_name = urllib.parse.quote(gene_name)
        url = f"https://mygene.info/v3/query?q={encoded_gene_name}&fields=symbol,alias&species=human"

        response = requests.get(url)
        if response.status_code != 200:
            return f"Error querying MyGene.info API: {response.status_code}"

        data = response.json()
        hits = data.get("hits", [])
        if not hits:
            return f"No data found for: {gene_name}. Please check the gene name and try again."

        for hit in hits:
            symbol = hit.get("symbol", "")
            if symbol.upper() == gene_name.upper():
                print(
                    f"[humanbase_tool] Using the official gene name: '{symbol}' instead of {gene_name}",
                    flush=True,
                )
                return symbol
            aliases = hit.get("alias", [])
            if any(gene_name.upper() == alias.upper() for alias in aliases):
                print(
                    f"[humanbase_tool] Using the official gene name: '{symbol}' instead of {gene_name}",
                    flush=True,
                )
                return symbol

        top_hit = hits[0]
        symbol = top_hit.get("symbol", None)
        if symbol:
            print(
                f"[humanbase_tool] Using the official gene name: '{symbol}' instead of {gene_name}",
                flush=True,
            )
            return symbol
        else:
            return f"No official gene symbol found for: {gene_name}. Please ensure it is correct."

    def get_entrez_ids(self, gene_names):
        """
        Convert gene names to Entrez IDs using NCBI Entrez API.

        Parameters
            gene_names (list): List of gene names to convert.

        Returns
            list: List of Entrez IDs corresponding to the gene names.
        """
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        entrez_ids = []
        gene_names = [self.get_official_gene_name(gene) for gene in gene_names]

        for gene in gene_names:
            params = {
                "db": "gene",
                "term": f"{gene}[gene] AND Homo sapiens[orgn]",
                "retmode": "xml",
                "retmax": "1",
            }

            response = requests.get(url, params=params)

            if response.status_code == 200:
                xml_data = response.text
                start_idx = xml_data.find("<Id>")
                end_idx = xml_data.find("</Id>")

                if start_idx != -1 and end_idx != -1:
                    entrez_ids.append(xml_data[start_idx + 4 : end_idx])
                else:
                    entrez_ids.append(None)
            else:
                return f"Error fetching data for gene: {gene}. Please check whether the gene uses official gene name."

        return entrez_ids

    def humanbase_ppi_retrieve(self, genes, tissue, max_node=10, interaction=None):
        """
        Retrieve protein-protein interactions and biological processes from HumanBase.

        Parameters
            genes (list): List of gene names to analyze.
            tissue (str): Tissue type for tissue-specific interactions.
            max_node (int): Maximum number of nodes to retrieve.
            interaction (str): Specific interaction type to filter by.

        Returns
            tuple: (NetworkX Graph of interactions, list of biological processes)
        """
        entrez_result = self.get_entrez_ids(genes)

        # get_entrez_ids may return a string error message instead of a list
        if isinstance(entrez_result, str):
            return nx.Graph(), None

        # Filter out None values (genes that could not be resolved)
        genes = [g for g in entrez_result if g is not None]
        if not genes:
            return nx.Graph(), None

        tissue = tissue.replace(" ", "-").replace("_", "-").lower()
        # Map common tissue names to valid HumanBase API slugs
        _TISSUE_ALIASES = {
            "breast": "mammary-gland",
            "prostate": "prostate-gland",
            "kidney": "kidney-cortex",
            "intestine": "small-intestine",
            "bowel": "small-intestine",
            "adipose": "adipose-tissue",
            "fat": "adipose-tissue",
            "skin": "skin-fibroblast",
            "immune": "blood",
            "pbmc": "blood",
        }
        tissue = _TISSUE_ALIASES.get(tissue, tissue)

        # HumanBase API requires giant_version parameter.
        # Slugs ending in "-v3" use giant_version=v3; others use v1.
        giant_version = "v3" if tissue.endswith("-v3") else "v1"

        interaction_types = [
            "co-expression",
            "interaction",
            "tf-binding",
            "gsea-microrna-targets",
            "gsea-perturbations",
        ]

        if not interaction or interaction not in interaction_types:
            interaction = "&datatypes=".join(interaction_types)

        gene_id = "&entrez=".join(genes)
        G = nx.Graph()
        bp_collection = None

        network_url = f"https://hb.flatironinstitute.org/api/integrations/{tissue}/network/?giant_version={giant_version}&datatypes={interaction}&entrez={gene_id}&node_size={max_node}"
        edge_type_url = "https://hb.flatironinstitute.org/api/integrations/{tissue}/evidence/?giant_version={giant_version}&limit=20&source={source}&target={target}"

        try:
            response = requests.get(network_url, timeout=15)
            if response.status_code == 404:
                return nx.Graph(), None
            response.raise_for_status()
            data = response.json()

            if "genes" in data:
                G.add_nodes_from(
                    [
                        (
                            g["standard_name"],
                            {"entrez": g["entrez"], "description": g["description"]},
                        )
                        for g in data["genes"]
                    ]
                )

            if "edges" in data:
                for e in data["edges"]:
                    source = data["genes"][e["source"]]["standard_name"]
                    target = data["genes"][e["target"]]["standard_name"]
                    weight = e["weight"]

                    edge_response = requests.get(
                        edge_type_url.format(
                            tissue=tissue,
                            giant_version=giant_version,
                            source=G.nodes[source]["entrez"],
                            target=G.nodes[target]["entrez"],
                        )
                    )
                    edge_response.raise_for_status()
                    edge_data = edge_response.json()
                    edge_info = {
                        t["title"]: t["weight"] for t in edge_data["datatypes"]
                    }

                    G.add_edge(source, target, weight=weight, interaction=edge_info)

        except requests.exceptions.RequestException as exc:
            print(f"Error retrieving PPI data: {exc}")

        bp_url = f"https://hb.flatironinstitute.org/api/terms/annotated/?database=gene-ontology-bp&entrez={gene_id}&max_term_size=20"

        try:
            response = requests.get(bp_url)
            response.raise_for_status()
            data = response.json()

            if data:
                # Grab the top 20 common pathways
                bp_collection = [bp_entity["title"] for bp_entity in data]
            else:
                print(f"[{genes}] No Gene Ontology Process recorded.")

        except requests.exceptions.RequestException as exc:
            print(f"Error retrieving biological process data: {exc}")

        return G, bp_collection

    def _convert_to_string(self, graph, bp_collection, original_genes, tissue):
        """
        Convert NetworkX graph and biological processes to string representation.

        Parameters
            graph (networkx.Graph): The network graph.
            bp_collection (list): List of biological processes.
            original_genes (list): Original gene list provided by user.
            tissue (str): Tissue type used for analysis.

        Returns
            str: Comprehensive string representation of the network data.
        """
        output = []

        # Header information
        output.append("🧬 HUMANBASE PROTEIN-PROTEIN INTERACTION NETWORK")
        output.append("=" * 50)
        output.append(f"Query Genes: {', '.join(original_genes)}")
        output.append(f"Tissue: {tissue.capitalize()}")
        output.append(f"Analysis Date: {self._get_current_timestamp()}")
        output.append("")

        # Network summary
        num_nodes = graph.number_of_nodes()
        num_edges = graph.number_of_edges()

        output.append("📊 NETWORK SUMMARY")
        output.append("-" * 20)
        output.append(f"Total Proteins: {num_nodes}")
        output.append(f"Total Interactions: {num_edges}")

        if num_nodes > 0:
            density = nx.density(graph)
            output.append(f"Network Density: {density:.3f}")

        output.append("")

        # Node information
        if num_nodes > 0:
            output.append("🔗 PROTEIN NODES")
            output.append("-" * 15)
            for i, (node, data) in enumerate(graph.nodes(data=True), 1):
                entrez_id = data.get("entrez", "N/A")
                description = data.get("description", "No description available")
                degree = graph.degree(node)
                output.append(f"{i:2d}. {node} (Entrez: {entrez_id})")
                output.append(f"    Description: {description}")
                output.append(f"    Connections: {degree}")
                output.append("")

        # Edge information
        if num_edges > 0:
            output.append("⚡ PROTEIN INTERACTIONS")
            output.append("-" * 22)
            for i, (source, target, data) in enumerate(graph.edges(data=True), 1):
                weight = data.get("weight", "N/A")
                interaction_info = data.get("interaction", {})

                output.append(f"{i:2d}. {source} ↔ {target}")
                output.append(f"    Weight: {weight}")

                if interaction_info:
                    output.append("    Evidence Types:")
                    for evidence_type, evidence_weight in interaction_info.items():
                        output.append(f"      • {evidence_type}: {evidence_weight}")
                else:
                    output.append(
                        "    Evidence Types: No detailed information available"
                    )
                output.append("")

        # Biological processes
        if bp_collection:
            output.append("🧬 ASSOCIATED BIOLOGICAL PROCESSES")
            output.append("-" * 35)
            output.append(f"Total Processes: {len(bp_collection)}")
            output.append("")

            for i, process in enumerate(bp_collection, 1):
                output.append(f"{i:2d}. {process}")
            output.append("")
        else:
            output.append("🧬 ASSOCIATED BIOLOGICAL PROCESSES")
            output.append("-" * 35)
            output.append("No biological processes found for this gene set.")
            output.append("")

        # Network analysis summary
        if num_nodes > 1:
            output.append("📈 NETWORK ANALYSIS")
            output.append("-" * 18)

            # Most connected proteins
            if num_nodes > 0:
                degrees = [(node, graph.degree(node)) for node in graph.nodes()]
                degrees.sort(key=lambda x: x[1], reverse=True)

                output.append("Most Connected Proteins:")
                for i, (node, degree) in enumerate(degrees[:5], 1):
                    output.append(f"  {i}. {node}: {degree} connections")
                output.append("")

            # Connectivity
            is_connected = nx.is_connected(graph)
            output.append(
                f"Network Connectivity: {'Fully connected' if is_connected else 'Disconnected components'}"
            )

            if is_connected and num_nodes > 1:
                try:
                    diameter = nx.diameter(graph)
                    avg_path_length = nx.average_shortest_path_length(graph)
                    output.append(f"Network Diameter: {diameter}")
                    output.append(f"Average Path Length: {avg_path_length:.2f}")
                except Exception:
                    pass

            # Clustering
            try:
                clustering = nx.average_clustering(graph)
                output.append(f"Average Clustering: {clustering:.3f}")
            except Exception:
                pass

            output.append("")

        # Footer
        output.append("📝 NOTES")
        output.append("-" * 8)
        output.append(
            "• Interaction weights represent confidence scores from HumanBase"
        )
        output.append("• Evidence types indicate the source of interaction data")
        output.append(
            "• Biological processes are derived from Gene Ontology annotations"
        )
        output.append(
            "• Network analysis metrics help understand protein relationship patterns"
        )

        return "\n".join(output)

    def _get_current_timestamp(self):
        """Get current timestamp for the report."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
