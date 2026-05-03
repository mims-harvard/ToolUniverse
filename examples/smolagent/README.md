# Smolagents Integration Examples

This directory contains examples demonstrating how to use `smolagents` agents within ToolUniverse.

## Files

- **use_smolagent_tool.py**: Example of using the `open_deep_research_agent` configured in `src/tooluniverse/data/smolagent_tools.json`. This agent replicates the functionality from `huggingface/smolagents/examples/open_deep_research`.

- **literature_search_example.py**: Example demonstrating the `advanced_literature_search_agent`, a sophisticated multi-agent system for comprehensive literature searches across multiple academic databases.

- **gradio_demo_literature_search.py**: Gradio web interface for the `advanced_literature_search_agent`, allowing interactive browser-based interaction.

- **gradio_demo_research.py**: Gradio web interface for the `open_deep_research_agent`, allowing interactive browser-based interaction.

## Running the Examples

### Basic Research Agent
```bash
python examples/smolagent/use_smolagent_tool.py
```

### Advanced Literature Search Agent
```bash
python examples/smolagent/literature_search_example.py
```

### Gradio Web Demos

The Gradio demos provide interactive web interfaces for the agents, allowing you to interact with them through a browser.

**Prerequisites**:
```bash
pip install 'smolagents[gradio]'
# Or separately:
pip install smolagents gradio
```

**Literature Search Agent Web Demo**:
```bash
python examples/smolagent/gradio_demo_literature_search.py
```

**Deep Research Agent Web Demo**:
```bash
python examples/smolagent/gradio_demo_research.py
```

After running either demo, the web interface will be available at `http://localhost:7860`. You can:
- Enter queries or tasks in the text input field
- View real-time execution progress (if streaming is enabled)
- See the agent's responses and results
- Interact with the agent through multiple conversation turns

**Note**: The Gradio interface automatically handles the input format. For `advanced_literature_search_agent`, enter your research query. For `open_deep_research_agent`, enter your research task.

## Features Demonstrated

### Basic Research Agent (`open_deep_research_agent`)
1. **SmolAgentTool Integration**: How to use smolagents (CodeAgent, ToolCallingAgent, ManagedAgent) as ToolUniverse tools
2. **Streaming Support**: Real-time output streaming from smolagents agents
3. **Mixed Tools**: Combining ToolUniverse tools with smolagents native tools
4. **Nested Agents**: Multi-agent systems using ManagedAgent with sub-agents
5. **Azure OpenAI**: Configuration with Azure OpenAI models (GPT-5)

### Advanced Literature Search Agent (`advanced_literature_search_agent`)
A sophisticated multi-agent system with:

1. **Query Planning Agent**: Analyzes user intent, decomposes queries, generates optimized search terms, and recommends databases
2. **Multi-Database Searcher**: Executes parallel searches across 12+ databases:
   - PubMed, Europe PMC, PMC (biomedical)
   - Semantic Scholar, OpenAlex (interdisciplinary)
   - ArXiv, BioRxiv, MedRxiv (preprints)
   - Crossref, DBLP, DOAJ, CORE (comprehensive coverage)
3. **Result Analyzer**: 
   - Intelligent deduplication (DOI, title similarity, author matching)
   - Comprehensive relevance scoring (citations, venue impact, recency, keyword match)
   - Theme clustering and quality assessment
4. **Literature Synthesizer**:
   - Extracts key findings and methodologies
   - Identifies research trends and gaps
   - Generates comprehensive reports with executive summaries
   - Ranks top papers with recommendations

**Key Capabilities**:
- Parallel multi-database searching with rate limit handling
- Smart deduplication across sources
- Relevance scoring with multiple factors
- Trend analysis and gap detection
- Structured markdown report generation

## Configuration

Agent configurations are defined in `src/tooluniverse/data/smolagent_tools.json`. The example uses:
- `open_deep_research_agent`: A ManagedAgent with sub-agents for web research and synthesis
- Azure OpenAI GPT-5 model
- Mixed tools: smolagents native tools (WebSearchTool, DuckDuckGoSearchTool, VisitWebpageTool) and ToolUniverse tools

## Requirements

- `smolagents` library installed (optional dependency)
- Azure OpenAI API credentials (or modify config to use other providers)
- For Gradio demos: `gradio` library installed (install with `pip install 'smolagents[gradio]'`)

## Troubleshooting

### Gradio Demo Issues

**Import Error**: If you see `ImportError: cannot import name 'GradioUI'`:
- Ensure you have installed both `smolagents` and `gradio`
- Try: `pip install --upgrade smolagents gradio`

**Agent Not Found**: If the tool is not found:
- Ensure `ToolUniverse` has loaded tools: `tu.load_tools()`
- Check that the agent name matches exactly (case-sensitive)
- Verify the agent is configured in `src/tooluniverse/data/smolagent_tools.json`

**Agent Initialization Failed**: If agent initialization fails:
- Check your API credentials (Azure OpenAI API key)
- Verify the model configuration in `smolagent_tools.json`
- Check that all required environment variables are set (e.g., `AZURE_OPENAI_API_KEY`)

**Port Already in Use**: If port 7860 is already in use:
- Stop other Gradio applications running on that port
- Or modify the launch call to use a different port (requires custom Gradio configuration)

