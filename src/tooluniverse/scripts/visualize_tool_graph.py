#!/usr/bin/env python3
"""
Tool Graph Visualizer Script

This script provides interactive visualization of tool compatibility graphs.
It can launch web-based interfaces for exploring tool relationships.

Usage:
    python visualize_tool_graph.py [graph_file] [options]

Examples:
    # Launch web viewer with default graph
    python visualize_tool_graph.py

    # Visualize specific graph file
    python visualize_tool_graph.py ./my_graph.json

    # Launch with specific port and open browser
    python visualize_tool_graph.py --port 5001 --open-browser

    # Generate static visualization image
    python visualize_tool_graph.py --export-image graph.png --format png
"""

import argparse
import json
import sys
import webbrowser
from pathlib import Path
from datetime import datetime

# Add parent directories to path for imports
script_dir = Path(__file__).parent
tooluniverse_dir = script_dir.parent
src_dir = tooluniverse_dir.parent
sys.path.insert(0, str(src_dir))

try:
    from flask import (
        Flask,
        render_template_string,
        jsonify,
    )

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    FLASK_IMPORT_ERROR = """
❌ Flask is required for web visualization but not installed.

To install graph visualization dependencies:
    pip install tooluniverse[graph]

Or install all optional dependencies:
    pip install tooluniverse[all]

Alternatively, use --export-image to create a static visualization.
"""


def parse_arguments():
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description="Visualize tool compatibility graphs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Use default graph
  %(prog)s graph.json                   # Visualize specific graph
  %(prog)s --port 5001 --open-browser   # Custom port and auto-open
  %(prog)s --export-image graph.png     # Export static image
        """,
    )

    parser.add_argument(
        "graph_file", nargs="?", help="Path to graph JSON file (default: auto-detect)"
    )

    # Server options
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=5000,
        help="Port for web server (default: 5000)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host for web server (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--open-browser", "-o", action="store_true", help="Automatically open browser"
    )

    parser.add_argument(
        "--no-auto-reload",
        action="store_true",
        help="Disable auto-reload on file changes",
    )

    # Export options
    parser.add_argument(
        "--export-image",
        type=str,
        help="Export static image to file (requires additional dependencies)",
    )

    parser.add_argument(
        "--format",
        choices=["png", "svg", "pdf", "html"],
        default="png",
        help="Export format (default: png)",
    )

    # Display options
    parser.add_argument(
        "--theme",
        choices=["light", "dark", "auto"],
        default="auto",
        help="UI theme (default: auto)",
    )

    parser.add_argument(
        "--layout",
        choices=["force", "hierarchical", "circular", "random"],
        default="force",
        help="Graph layout algorithm (default: force)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    return parser.parse_args()


def find_graph_file(specified_path=None):
    """Find graph file to visualize."""

    # List of potential locations to search
    search_paths = []

    if specified_path:
        search_paths.append(Path(specified_path))

    # Add current directory and common output locations
    current_dir = Path.cwd()
    search_paths.extend(
        [
            current_dir / "tool_composition_graph.json",
            current_dir / "graph.json",
            current_dir / "tool_graph.json",
            script_dir.parent.parent.parent
            / "tool_composition_graph.json",  # Project root
            script_dir.parent.parent.parent / "graph.json",
            current_dir / "src" / "tooluniverse" / "tool_composition_graph.json",
        ]
    )

    # Find first existing file
    for path in search_paths:
        if path.exists() and path.is_file():
            return path

    return None


def load_graph_data(graph_file):
    """Load and validate graph data."""

    try:
        with open(graph_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate basic structure
        if not isinstance(data, dict):
            raise ValueError("Graph file must contain a JSON object")

        if "nodes" not in data or "edges" not in data:
            raise ValueError("Graph file must contain 'nodes' and 'edges' fields")

        return data

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    except Exception as e:
        raise ValueError(f"Error loading graph file: {e}")


def get_graph_summary(data):
    """Get summary information about the graph."""

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    summary = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "categories": set(),
        "edge_density": 0.0,
        "avg_compatibility": 0.0,
    }

    # Analyze nodes
    for node in nodes:
        if "category" in node:
            summary["categories"].add(node["category"])

    summary["category_count"] = len(summary["categories"])
    summary["categories"] = sorted(list(summary["categories"]))

    # Analyze edges
    if edges and nodes:
        max_edges = len(nodes) * (len(nodes) - 1)
        if max_edges > 0:
            summary["edge_density"] = len(edges) / max_edges

        # Calculate average compatibility
        scores = [
            edge.get("compatibility_score", 0)
            for edge in edges
            if "compatibility_score" in edge
        ]
        if scores:
            summary["avg_compatibility"] = sum(scores) / len(scores)

    return summary


def create_web_app(graph_data, theme="auto", layout="force"):
    """Create Flask web application for graph visualization."""

    if not FLASK_AVAILABLE:
        raise ImportError(FLASK_IMPORT_ERROR)

    app = Flask(__name__)

    # HTML template for the visualization
    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ToolUniverse Graph Visualizer</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: {{ 'white' if theme == 'light' else '#1a1a1a' if theme == 'dark' else 'white' }};
            color: {{ 'black' if theme == 'light' else '#e0e0e0' if theme == 'dark' else 'black' }};
        }

        .header {
            background: {{ '#f5f5f5' if theme == 'light' else '#2d2d2d' if theme == 'dark' else '#f5f5f5' }};
            padding: 20px;
            border-bottom: 1px solid {{ '#ddd' if theme == 'light' else '#444' if theme == 'dark' else '#ddd' }};
        }

        .header h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }

        .header .summary {
            margin-top: 10px;
            font-size: 14px;
            opacity: 0.8;
        }

        .controls {
            padding: 15px 20px;
            background: {{ '#fafafa' if theme == 'light' else '#252525' if theme == 'dark' else '#fafafa' }};
            border-bottom: 1px solid {{ '#eee' if theme == 'light' else '#333' if theme == 'dark' else '#eee' }};
        }

        .control-group {
            display: inline-block;
            margin-right: 20px;
            margin-bottom: 10px;
        }

        .control-group label {
            font-size: 12px;
            font-weight: 500;
            display: block;
            margin-bottom: 5px;
        }

        .control-group input, .control-group select {
            padding: 5px 8px;
            border: 1px solid {{ '#ccc' if theme == 'light' else '#555' if theme == 'dark' else '#ccc' }};
            border-radius: 4px;
            background: {{ 'white' if theme == 'light' else '#333' if theme == 'dark' else 'white' }};
            color: {{ 'black' if theme == 'light' else 'white' if theme == 'dark' else 'black' }};
        }

        .graph-container {
            position: relative;
            height: calc(100vh - 140px);
            overflow: hidden;
        }

        .node {
            cursor: pointer;
            stroke-width: 2px;
        }

        .edge {
            stroke: #999;
            stroke-opacity: 0.6;
            fill: none;
        }

        .node-label {
            font-size: 10px;
            text-anchor: middle;
            pointer-events: none;
            fill: {{ 'black' if theme == 'light' else 'white' if theme == 'dark' else 'black' }};
        }

        .tooltip {
            position: absolute;
            padding: 10px;
            background: {{ 'rgba(0,0,0,0.8)' if theme == 'light' else 'rgba(255,255,255,0.9)' if theme == 'dark' else 'rgba(0,0,0,0.8)' }};
            color: {{ 'white' if theme == 'light' else 'black' if theme == 'dark' else 'white' }};
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            z-index: 1000;
            max-width: 300px;
        }

        .legend {
            position: absolute;
            top: 20px;
            right: 20px;
            background: {{ 'rgba(255,255,255,0.95)' if theme == 'light' else 'rgba(0,0,0,0.85)' if theme == 'dark' else 'rgba(255,255,255,0.95)' }};
            padding: 15px;
            border-radius: 8px;
            border: 1px solid {{ '#ddd' if theme == 'light' else '#444' if theme == 'dark' else '#ddd' }};
            font-size: 12px;
            max-height: 300px;
            overflow-y: auto;
        }

        .stats {
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: {{ 'rgba(255,255,255,0.95)' if theme == 'light' else 'rgba(0,0,0,0.85)' if theme == 'dark' else 'rgba(255,255,255,0.95)' }};
            padding: 10px;
            border-radius: 4px;
            border: 1px solid {{ '#ddd' if theme == 'light' else '#444' if theme == 'dark' else '#ddd' }};
            font-size: 11px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>ToolUniverse Graph Visualizer</h1>
        <div class="summary">
            {{ summary.node_count }} tools, {{ summary.edge_count }} connections,
            {{ summary.category_count }} categories
        </div>
    </div>

    <div class="controls">
        <div class="control-group">
            <label>Search Tools:</label>
            <input type="text" id="searchInput" placeholder="Type tool name...">
        </div>

        <div class="control-group">
            <label>Category Filter:</label>
            <select id="categoryFilter">
                <option value="">All Categories</option>
                {% for category in summary.categories %}
                <option value="{{ category }}">{{ category }}</option>
                {% endfor %}
            </select>
        </div>

        <div class="control-group">
            <label>Min Compatibility:</label>
            <input type="range" id="compatibilitySlider" min="0" max="100" value="0">
            <span id="compatibilityValue">0</span>
        </div>

        <div class="control-group">
            <label>Layout:</label>
            <select id="layoutSelect">
                <option value="force" {{ 'selected' if layout == 'force' else '' }}>Force-Directed</option>
                <option value="circular" {{ 'selected' if layout == 'circular' else '' }}>Circular</option>
                <option value="hierarchical" {{ 'selected' if layout == 'hierarchical' else '' }}>Hierarchical</option>
            </select>
        </div>
    </div>

    <div class="graph-container">
        <svg id="graph"></svg>
        <div class="tooltip" id="tooltip" style="display: none;"></div>
        <div class="legend" id="legend"></div>
        <div class="stats" id="stats"></div>
    </div>

    <script>
        // Graph data from server
        const graphData = {{ graph_data | tojsonfilter }};

        // D3 visualization code
        const width = window.innerWidth;
        const height = window.innerHeight - 140;

        const svg = d3.select("#graph")
            .attr("width", width)
            .attr("height", height);

        const g = svg.append("g");

        // Zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", (event) => {
                g.attr("transform", event.transform);
            });

        svg.call(zoom);

        // Color scale for categories
        const categories = [...new Set(graphData.nodes.map(d => d.category || 'unknown'))];
        const colorScale = d3.scaleOrdinal(d3.schemeCategory10)
            .domain(categories);

        // Initialize simulation
        let simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2));

        // Current data for filtering
        let currentNodes = [...graphData.nodes];
        let currentEdges = [...graphData.edges];

        function updateVisualization() {
            // Clear existing elements
            g.selectAll("*").remove();

            // Create edges
            const edge = g.append("g")
                .selectAll("line")
                .data(currentEdges)
                .enter().append("line")
                .attr("class", "edge")
                .attr("stroke-width", d => Math.sqrt(d.compatibility_score || 50) / 5);

            // Create nodes
            const node = g.append("g")
                .selectAll("circle")
                .data(currentNodes)
                .enter().append("circle")
                .attr("class", "node")
                .attr("r", d => Math.sqrt(d.connections || 1) * 3 + 5)
                .attr("fill", d => colorScale(d.category || 'unknown'))
                .attr("stroke", "#fff")
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended));

            // Add labels
            const label = g.append("g")
                .selectAll("text")
                .data(currentNodes)
                .enter().append("text")
                .attr("class", "node-label")
                .text(d => d.name || d.id);

            // Tooltip interactions
            node.on("mouseover", showTooltip)
                .on("mouseout", hideTooltip);

            // Update simulation
            simulation.nodes(currentNodes);
            simulation.force("link").links(currentEdges);
            simulation.alpha(1).restart();

            simulation.on("tick", () => {
                edge
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                node
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);

                label
                    .attr("x", d => d.x)
                    .attr("y", d => d.y + 20);
            });

            updateStats();
        }

        function filterData() {
            const searchTerm = document.getElementById("searchInput").value.toLowerCase();
            const categoryFilter = document.getElementById("categoryFilter").value;
            const minCompatibility = parseInt(document.getElementById("compatibilitySlider").value);

            // Filter nodes
            currentNodes = graphData.nodes.filter(node => {
                const matchesSearch = !searchTerm ||
                    (node.name && node.name.toLowerCase().includes(searchTerm)) ||
                    (node.id && node.id.toLowerCase().includes(searchTerm));
                const matchesCategory = !categoryFilter || node.category === categoryFilter;
                return matchesSearch && matchesCategory;
            });

            const nodeIds = new Set(currentNodes.map(n => n.id));

            // Filter edges
            currentEdges = graphData.edges.filter(edge => {
                const hasValidNodes = nodeIds.has(edge.source) && nodeIds.has(edge.target);
                const meetsCompatibility = (edge.compatibility_score || 0) >= minCompatibility;
                return hasValidNodes && meetsCompatibility;
            });

            updateVisualization();
        }

        function updateStats() {
            const stats = document.getElementById("stats");
            stats.innerHTML = `
                <strong>Current View:</strong><br>
                Nodes: ${currentNodes.length}<br>
                Edges: ${currentEdges.length}<br>
                Density: ${(currentEdges.length / Math.max(1, currentNodes.length * (currentNodes.length - 1))).toFixed(3)}
            `;
        }

        function updateLegend() {
            const legend = document.getElementById("legend");
            legend.innerHTML = `
                <strong>Categories:</strong><br>
                ${categories.map(cat =>
                    `<div><span style="color: ${colorScale(cat)}">●</span> ${cat}</div>`
                ).join('')}
            `;
        }

        function showTooltip(event, d) {
            const tooltip = document.getElementById("tooltip");
            tooltip.innerHTML = `
                <strong>${d.name || d.id}</strong><br>
                Category: ${d.category || 'Unknown'}<br>
                Connections: ${d.connections || 0}<br>
                ${d.description ? `<br>${d.description}` : ''}
            `;
            tooltip.style.display = "block";
            tooltip.style.left = (event.pageX + 10) + "px";
            tooltip.style.top = (event.pageY - 10) + "px";
        }

        function hideTooltip() {
            document.getElementById("tooltip").style.display = "none";
        }

        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }

        // Event listeners
        document.getElementById("searchInput").addEventListener("input", filterData);
        document.getElementById("categoryFilter").addEventListener("change", filterData);
        document.getElementById("compatibilitySlider").addEventListener("input", function() {
            document.getElementById("compatibilityValue").textContent = this.value;
            filterData();
        });

        // Initialize
        updateLegend();
        updateVisualization();

        // Handle window resize
        window.addEventListener("resize", () => {
            const newWidth = window.innerWidth;
            const newHeight = window.innerHeight - 140;
            svg.attr("width", newWidth).attr("height", newHeight);
            simulation.force("center", d3.forceCenter(newWidth / 2, newHeight / 2));
            simulation.alpha(0.3).restart();
        });
    </script>
</body>
</html>
    """

    @app.route("/")
    def index():
        summary = get_graph_summary(graph_data)
        return render_template_string(
            HTML_TEMPLATE,
            graph_data=graph_data,
            summary=summary,
            theme=theme,
            layout=layout,
        )

    @app.route("/api/graph")
    def api_graph():
        return jsonify(graph_data)

    @app.route("/api/summary")
    def api_summary():
        return jsonify(get_graph_summary(graph_data))

    return app


def export_static_image(graph_data, output_path, format_type="png"):
    """Export static image of the graph (requires additional dependencies)."""

    try:
        import matplotlib.pyplot as plt
        import networkx as nx

    except ImportError as e:
        missing_deps = []
        if "matplotlib" in str(e):
            missing_deps.append("matplotlib")
        if "networkx" in str(e):
            missing_deps.append("networkx")

        error_msg = f"""
❌ Static export requires additional dependencies: {", ".join(missing_deps)}

To install graph visualization dependencies:
    pip install tooluniverse[graph]

Or install manually:
    pip install matplotlib networkx
"""
        raise ImportError(error_msg)

    # Create NetworkX graph
    G = nx.Graph()

    # Add nodes
    for node in graph_data["nodes"]:
        G.add_node(node["id"], **node)

    # Add edges
    for edge in graph_data["edges"]:
        G.add_edge(edge["source"], edge["target"], **edge)

    # Create visualization
    plt.figure(figsize=(12, 8))

    # Layout
    if len(G.nodes()) < 100:
        pos = nx.spring_layout(G, k=1, iterations=50)
    else:
        pos = nx.spring_layout(G, k=3, iterations=20)

    # Draw nodes by category
    categories = set(node.get("category", "unknown") for node in graph_data["nodes"])
    colors = plt.cm.Set3(range(len(categories)))
    category_colors = dict(zip(categories, colors))

    for category in categories:
        nodes_in_category = [
            node["id"]
            for node in graph_data["nodes"]
            if node.get("category", "unknown") == category
        ]
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=nodes_in_category,
            node_color=[category_colors[category]],
            node_size=100,
            alpha=0.8,
            label=category,
        )

    # Draw edges
    nx.draw_networkx_edges(G, pos, alpha=0.3, width=0.5)

    # Add labels for important nodes
    if len(G.nodes()) < 50:
        nx.draw_networkx_labels(G, pos, font_size=8, font_weight="bold")

    plt.title(
        f"ToolUniverse Compatibility Graph\n{len(G.nodes())} tools, {len(G.edges())} connections"
    )
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.axis("off")
    plt.tight_layout()

    # Save
    plt.savefig(output_path, format=format_type, dpi=300, bbox_inches="tight")
    plt.close()

    return output_path


def main():
    """Main function."""

    args = parse_arguments()

    print("ToolUniverse Graph Visualizer")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Find graph file
    graph_file = find_graph_file(args.graph_file)

    if not graph_file:
        print("❌ No graph file found!")
        print("\nSearched in:")
        print("  - ./tool_composition_graph.json")
        print("  - ./graph.json")
        print("  - ./tool_graph.json")
        if args.graph_file:
            print(f"  - {args.graph_file}")
        print("\nTo generate a graph, run:")
        print("python generate_tool_graph.py")
        return 1

    if args.verbose:
        print(f"Loading graph from: {graph_file}")

    # Load graph data
    try:
        graph_data = load_graph_data(graph_file)
        summary = get_graph_summary(graph_data)

        print(f"✅ Loaded graph: {graph_file}")
        print(f"   Nodes: {summary['node_count']}")
        print(f"   Edges: {summary['edge_count']}")
        print(f"   Categories: {summary['category_count']}")
        print(f"   Density: {summary['edge_density']:.3f}")
        print()

    except Exception as e:
        print(f"❌ Error loading graph: {e}")
        return 1

    # Export static image if requested
    if args.export_image:
        try:
            print(f"Exporting static image to {args.export_image}...")
            export_static_image(graph_data, args.export_image, args.format)
            print(f"✅ Image exported: {args.export_image}")
            return 0
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return 1

    # Launch web visualizer
    if not FLASK_AVAILABLE:
        print(FLASK_IMPORT_ERROR)
        return 1

    try:
        app = create_web_app(graph_data, args.theme, args.layout)

        print("🚀 Starting web server...")
        print(f"   Host: {args.host}")
        print(f"   Port: {args.port}")
        print(f"   URL: http://{args.host}:{args.port}")

        if args.open_browser:
            print("   Opening browser...")

        print("\nPress Ctrl+C to stop the server")
        print()

        # Open browser if requested
        if args.open_browser:
            import threading
            import time

            def open_browser():
                time.sleep(1.5)  # Wait for server to start
                webbrowser.open(f"http://{args.host}:{args.port}")

            threading.Thread(target=open_browser, daemon=True).start()

        # Run the server
        app.run(
            host=args.host,
            port=args.port,
            debug=not args.no_auto_reload,
            use_reloader=not args.no_auto_reload,
        )

    except KeyboardInterrupt:
        print("\n👋 Server stopped.")
        return 0
    except Exception as e:
        print(f"❌ Server error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
