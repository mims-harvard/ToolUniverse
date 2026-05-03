Wikipedia Tools
===============

**Configuration File**: ``wikipedia_tools.json``
**Tool Type**: Local
**Tools Count**: 3

This page contains all tools defined in the ``wikipedia_tools.json`` configuration file.

Available Tools
---------------

**Wikipedia_get_content** (Type: WikipediaContentTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract content from a Wikipedia article. Can extract introduction, summary, or full article cont...

.. dropdown:: Wikipedia_get_content tool specification

   **Tool Information:**

   * **Name**: ``Wikipedia_get_content``
   * **Type**: ``WikipediaContentTool``
   * **Description**: Extract content from a Wikipedia article. Can extract introduction, summary, or full article content. No API key required.

   **Parameters:**

   * ``title`` (string) (required)
     Wikipedia article title (exact title as it appears on Wikipedia)

   * ``language`` (string) (optional)
     Wikipedia language code (e.g., 'en' for English, 'zh' for Chinese). Default: 'en'

   * ``extract_type`` (string) (optional)
     Type of content to extract: 'intro' (first paragraph only), 'summary' (first few paragraphs, default), or 'full' (entire article)

   * ``max_chars`` (integer) (optional)
     Maximum characters to return for intro/summary (ignored for 'full'). Default: 2000

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Wikipedia_get_content",
          "arguments": {
              "title": "example_value"
          }
      }
      result = tu.run(query)


**Wikipedia_get_summary** (Type: WikipediaSummaryTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get a brief summary/introduction from a Wikipedia article. This is a convenience tool that extrac...

.. dropdown:: Wikipedia_get_summary tool specification

   **Tool Information:**

   * **Name**: ``Wikipedia_get_summary``
   * **Type**: ``WikipediaSummaryTool``
   * **Description**: Get a brief summary/introduction from a Wikipedia article. This is a convenience tool that extracts just the first paragraph(s) of an article. No API key required.

   **Parameters:**

   * ``title`` (string) (required)
     Wikipedia article title (exact title as it appears on Wikipedia)

   * ``language`` (string) (optional)
     Wikipedia language code (e.g., 'en' for English). Default: 'en'

   * ``max_chars`` (integer) (optional)
     Maximum characters to return. Default: 500

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Wikipedia_get_summary",
          "arguments": {
              "title": "example_value"
          }
      }
      result = tu.run(query)


**Wikipedia_search** (Type: WikipediaSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search Wikipedia articles using MediaWiki API. Returns a list of matching articles with titles, s...

.. dropdown:: Wikipedia_search tool specification

   **Tool Information:**

   * **Name**: ``Wikipedia_search``
   * **Type**: ``WikipediaSearchTool``
   * **Description**: Search Wikipedia articles using MediaWiki API. Returns a list of matching articles with titles, snippets, and metadata. No API key required.

   **Parameters:**

   * ``query`` (string) (required)
     Search query string to find Wikipedia articles

   * ``limit`` (integer) (optional)
     Maximum number of results to return (default: 10, max: 50)

   * ``language`` (string) (optional)
     Wikipedia language code (e.g., 'en' for English, 'zh' for Chinese, 'fr' for French). Default: 'en'

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Wikipedia_search",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
