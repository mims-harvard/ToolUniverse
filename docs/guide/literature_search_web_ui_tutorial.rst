Wide Research Web UI Tutorial
==============================

This tutorial demonstrates how to use the ToolUniverse Wide Research Web UI, a powerful web-based interface that provides intelligent literature search and analysis capabilities across multiple academic databases.

Overview
--------

The Wide Research Web UI is a comprehensive web application that combines:

- **Multi-database search** across 11+ academic databases
- **AI-powered query expansion** for better search results
- **Intelligent summarization** with temporal and thematic analysis
- **Modern web interface** with paper card display
- **Real-time search status** and tool usage tracking

Key Features
~~~~~~~~~~~~

- **Unified Search Interface**: Search across ArXiv, PubMed, Crossref, Semantic Scholar, OpenAlex, DBLP, DOAJ, Europe PMC, HAL, MedRxiv, and Unpaywall
- **Smart Query Processing**: AI-powered query expansion to generate multiple search terms
- **Intelligent Analysis**: Comprehensive literature review generation with:
  - Research overview and scope analysis
  - Temporal analysis of research trends
  - Thematic analysis of research areas
  - Key contributions identification
  - Research gaps and future directions
- **Paper Card Display**: Modern, responsive interface showing papers with source identification
- **Real-time Status**: Live updates on tool usage and search progress

Quick Start
-----------

Starting the Web UI
~~~~~~~~~~~~~~~~~~~

The easiest way to start the Wide Research Web UI is using the command-line tool:

.. code-block:: bash

    tooluniverse-wide-research

This will start the web server and display:

.. code-block:: text

    🚀 Starting ToolUniverse Wide Research Web UI...
    📚 Available tools: ArXiv, PubMed, Crossref, Semantic Scholar, OpenAlex, DBLP, DOAJ, Europe PMC, HAL, MedRxiv, Unpaywall
    🌐 Web interface will be available at: http://localhost:5001
    🔍 API endpoint: http://localhost:5001/api/search
    📖 Documentation: http://localhost:5001/api/tools
    ============================================================
    Press Ctrl+C to stop the server
    ============================================================

Access the web interface by opening http://localhost:5001 in your browser.

Alternative Startup Methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also start the web UI directly:

.. code-block:: bash

    # Method 1: Direct Python execution
    cd /path/to/ToolUniverse/src/tooluniverse/web_tools/literature_search_ui
    python simple_app.py

    # Method 2: Using Python module
    python -m tooluniverse.web_tools.literature_search_ui.simple_app

Using the Web Interface
-----------------------

Basic Search
~~~~~~~~~~~~

1. **Enter your search query** in the search box
2. **Choose search options**:
   - Enable "AI Query Split" to automatically expand your search terms
   - Enable "AI Summary" to generate intelligent literature analysis
   - Adjust the result limit (default: 10)
3. **Click "Search Literature"** to start the search

Example searches:
- "machine learning deep learning"
- "cancer immunotherapy"
- "quantum computing algorithms"
- "renewable energy storage"
- "artificial intelligence ethics"

Understanding the Results
~~~~~~~~~~~~~~~~~~~~~~~~~

The web interface displays results in several sections:

**Search Status**
- Real-time updates on which tools are being used
- Success/failure status for each database
- Total number of papers found

**Paper Cards**
Each paper is displayed as a card showing:
- **Title** and **Authors**
- **Publication year** and **Source database**
- **Abstract** (truncated with expand option)
- **Journal/Venue** information
- **DOI** and **Direct links**
- **Source badge** with color-coded identification

**Intelligent Summary** (when enabled)
- **Research Overview**: Scope, recent activity, data sources
- **Research Timeline**: Temporal analysis of publication trends
- **Research Themes**: Primary research areas and methodological approaches
- **Key Contributions**: Notable papers and their significance
- **Research Trends**: Collaboration patterns and emerging patterns
- **Research Gaps**: Identified gaps and future opportunities
- **Methodology**: Information about the search process

Advanced Features
-----------------

AI Query Expansion
~~~~~~~~~~~~~~~~~~

When "AI Query Split" is enabled, the system automatically:

1. **Analyzes your query** to identify key concepts
2. **Generates related terms** and synonyms
3. **Creates multiple search variations** for comprehensive coverage
4. **Searches each variation** across all databases

Example:
- Input: "machine learning"
- Expanded queries: ["machine learning", "deep learning", "neural networks", "AI applications"]

Intelligent Summarization
~~~~~~~~~~~~~~~~~~~~~~~~~

The AI summary provides comprehensive analysis including:

**Temporal Analysis**
- Recent developments (2021+)
- Historical context by decade
- Publication trends over time
- Key papers from each period

**Thematic Analysis**
- Primary research areas (Machine Learning, Computer Vision, NLP, etc.)
- Methodological approaches (Deep Learning, Statistical Methods, etc.)
- Research focus distribution

**Key Contributions**
- Most important papers identified
- Author collaboration patterns
- Source diversity analysis

**Research Gaps & Future Directions**
- Emerging trends and patterns
- Identified research gaps
- Future research opportunities

API Usage
---------

The web UI also provides RESTful API endpoints for programmatic access:

Search Endpoint
~~~~~~~~~~~~~~~

.. code-block:: bash

    POST http://localhost:5001/api/search
    Content-Type: application/json

    {
        "query": "machine learning",
        "use_ai_split": true,
        "use_ai_summary": true,
        "limit": 10
    }

Response format:

.. code-block:: javascript

    {
        "success": true,
        "query": "machine learning",
        "search_terms": ["machine learning", "deep learning", "neural networks"],
        "total_results": 25,
        "tools_used": ["ArXiv_search_papers", "PubMed_search_articles", "Crossref_search_works"],
        "results": [
            {
                "query": "machine learning",
                "total_results": 8,
                "tools_used": ["ArXiv_search_papers"],
                "results_by_tool": {
                    "ArXiv_search_papers": {
                        "status": "success",
                        "results": [...],
                        "count": 8
                    }
                }
            }
        ],
        "summary": "# Literature Review: machine learning\n\n## 📊 Research Overview\n..."
    }

Tool Information Endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    GET http://localhost:5001/api/tools
    ```

Returns information about available search tools and their capabilities.

Search History Endpoint
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    GET http://localhost:5001/api/history
    ```

Returns the last 10 search queries and their results.

Configuration
-------------

Environment Detection
~~~~~~~~~~~~~~~~~~~~~

The web UI automatically detects your ToolUniverse environment:

- **Full Mode**: When ToolUniverse is available, uses all integrated tools
- **Demo Mode**: When ToolUniverse is not available, uses simulated data

You can check the mode in the startup messages or by calling the tools endpoint.

Customization
~~~~~~~~~~~~~

The web UI can be customized by modifying:

- **Port**: Change the default port (5001) in `simple_app.py`
- **Result limits**: Adjust default limits in the interface
- **Database selection**: Enable/disable specific databases
- **UI styling**: Modify the HTML/CSS templates

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Port Already in Use**
- The default port 5001 is already occupied
- Solution: Kill the process using the port or change the port in the code

**ToolUniverse Not Found**
- ToolUniverse is not properly installed or configured
- Solution: Install ToolUniverse or run in demo mode

**No Results Found**
- Search query might be too specific
- Try broader terms or enable AI query expansion
- Check if databases are accessible

**Slow Performance**
- Large result sets or many databases can slow down searches
- Reduce the result limit
- Disable some databases if not needed

**API Errors**
- Check network connectivity
- Verify API endpoints are accessible
- Check for rate limiting

Best Practices
--------------

Search Optimization
~~~~~~~~~~~~~~~~~~~

1. **Use specific, relevant keywords**
2. **Enable AI query expansion** for comprehensive coverage
3. **Start with moderate result limits** (5-10) for faster searches
4. **Use the intelligent summary** to understand research landscape

Result Analysis
~~~~~~~~~~~~~~~

1. **Review the paper cards** for relevant publications
2. **Read the intelligent summary** for research insights
3. **Check source diversity** to ensure comprehensive coverage
4. **Use the timeline analysis** to understand research evolution

Workflow Integration
~~~~~~~~~~~~~~~~~~~~

1. **Start with broad searches** to understand the field
2. **Refine queries** based on initial results
3. **Use multiple search sessions** for different aspects
4. **Export results** for further analysis

Example Workflows
-----------------

Literature Review Preparation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Initial broad search**: "artificial intelligence"
2. **Enable AI expansion** and summary
3. **Review thematic analysis** to identify key areas
4. **Focus on specific themes**: "computer vision", "natural language processing"
5. **Use temporal analysis** to understand recent developments
6. **Identify research gaps** for your contribution

Research Gap Analysis
~~~~~~~~~~~~~~~~~~~~~

1. **Search your research area**: "quantum machine learning"
2. **Enable intelligent summary** to see research gaps
3. **Review recent papers** (last 2-3 years)
4. **Analyze collaboration patterns** for potential partnerships
5. **Identify future directions** mentioned in the summary

Competitive Analysis
~~~~~~~~~~~~~~~~~~~~

1. **Search for key researchers** in your field
2. **Use author names** in search queries
3. **Review recent publications** from competitors
4. **Analyze research trends** to understand market direction
5. **Identify emerging areas** for early entry

Complete Example
----------------

Here's a complete example of using the Wide Research Web UI:

1. **Start the web UI**:

   .. code-block:: bash

       tooluniverse-wide-research

2. **Open your browser** and go to http://localhost:5001

3. **Perform a search**:
   - Query: "deep learning computer vision"
   - Enable AI Query Split: ✓
   - Enable AI Summary: ✓
   - Limit: 5

4. **Review the results**:
   - Check the paper cards for relevant publications
   - Read the intelligent summary for insights
   - Note the research timeline and themes

5. **Refine your search**:
   - Try more specific terms: "object detection deep learning"
   - Focus on recent papers: adjust date filters
   - Explore related themes from the summary

6. **Export results**:
   - Use the API to programmatically access results
   - Save interesting papers for further reading
   - Use the summary for your literature review

This tutorial provides a comprehensive guide to using the ToolUniverse Wide Research Web UI. The interface combines the power of multiple academic databases with intelligent analysis to provide a complete literature research solution.

For more information about individual tools, see the `literature search tools tutorial <literature_search_tools_tutorial.html>`_.

For API reference, see the `API documentation <../api/index.html>`_.
