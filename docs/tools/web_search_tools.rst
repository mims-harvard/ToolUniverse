Web Search Tools
================

**Configuration File**: ``web_search_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``web_search_tools.json`` configuration file.

Available Tools
---------------

**web_api_documentation_search** (Type: WebAPIDocumentationSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specialized web search for API documentation, Python packages, and technical resources using DDGS...

.. dropdown:: web_api_documentation_search tool specification

   **Tool Information:**

   * **Name**: ``web_api_documentation_search``
   * **Type**: ``WebAPIDocumentationSearchTool``
   * **Description**: Specialized web search for API documentation, Python packages, and technical resources using DDGS with multiple search engines. Optimized for finding official documentation and library information.

   **Parameters:**

   * ``query`` (string) (required)
     Search query string (e.g., tool name, library name, API name)

   * ``max_results`` (integer) (optional)
     Maximum number of results to return

   * ``focus`` (string) (optional)
     Focus area for the search

   * ``backend`` (string) (optional)
     Search engine backend to use

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "web_api_documentation_search",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


**web_search** (Type: WebSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

General web search using DDGS (Dux Distributed Global Search) supporting multiple search engines ...

.. dropdown:: web_search tool specification

   **Tool Information:**

   * **Name**: ``web_search``
   * **Type**: ``WebSearchTool``
   * **Description**: General web search using DDGS (Dux Distributed Global Search) supporting multiple search engines including Google, Bing, Brave, Yahoo, and DuckDuckGo. No API keys required.

   **Parameters:**

   * ``query`` (string) (required)
     Search query string

   * ``max_results`` (integer) (optional)
     Maximum number of results to return

   * ``search_type`` (string) (optional)
     Type of search to perform

   * ``backend`` (string) (optional)
     Search engine backend to use

   * ``region`` (string) (optional)
     Search region/locale

   * ``safesearch`` (string) (optional)
     Safe search level

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "web_search",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
