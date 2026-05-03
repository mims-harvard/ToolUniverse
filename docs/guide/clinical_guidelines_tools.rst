Clinical Guidelines Tools
=========================

ToolUniverse provides 8 clinical guideline tools for searching and extracting authoritative medical guidelines.

Tool List
---------

**Search Tools (6):**

* ``NICE_Clinical_Guidelines_Search`` - UK NICE official guidelines
* ``WHO_Guidelines_Search`` - WHO international guidelines 
* ``PubMed_Guidelines_Search`` - PubMed peer-reviewed guidelines
* ``EuropePMC_Guidelines_Search`` - Europe PMC guidelines
* ``TRIP_Database_Guidelines_Search`` - TRIP evidence-based database
* ``OpenAlex_Guidelines_Search`` - OpenAlex scholarly database

**Full-Text Extraction (2):**

* ``NICE_Guideline_Full_Text`` - Extract complete NICE guidelines (5,000-20,000+ chars)
* ``WHO_Guideline_Full_Text`` - Extract WHO content + PDF links (1,500+ chars)

Quick Start
-----------

.. code-block:: python

    from tooluniverse import ToolUniverse
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Search guidelines
    results = tu.run({
        "name": "NICE_Clinical_Guidelines_Search",
        "arguments": {
            "query": "diabetes",
            "limit": 5
        }
    })
    
    # Extract full text
    full_text = tu.run({
        "name": "NICE_Guideline_Full_Text",
        "arguments": {
            "url": results[0]['url']
        }
    })

Tool Comparison
---------------

+---------------------------+----------------------------------+---------------------------------------+
| Tool | Data Source | Features |
+===========================+==================================+=======================================+
| NICE_Clinical_Guidelines | UK NICE official website | Official UK guidelines with summaries |
+---------------------------+----------------------------------+---------------------------------------+
| WHO_Guidelines | WHO publications database | International health guidelines |
+---------------------------+----------------------------------+---------------------------------------+
| PubMed_Guidelines | NCBI PubMed database | Peer-reviewed with abstracts & PMIDs |
+---------------------------+----------------------------------+---------------------------------------+
| EuropePMC_Guidelines | Europe PMC database | European & international research |
+---------------------------+----------------------------------+---------------------------------------+
| TRIP_Database | TRIP evidence database | Evidence-based medicine focus |
+---------------------------+----------------------------------+---------------------------------------+
| OpenAlex_Guidelines | OpenAlex scholarly database | Comprehensive with citation counts |
+---------------------------+----------------------------------+---------------------------------------+

Usage Examples
--------------

Search NICE Guidelines
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    results = tu.run({
        "name": "NICE_Clinical_Guidelines_Search",
        "arguments": {
            "query": "type 2 diabetes",
            "limit": 5
        }
    })
    
    for guideline in results:
        print(f"{guideline['title']}")
        print(f"URL: {guideline['url']}")
        print(f"Summary: {guideline['summary'][:200]}...")

Search Multiple Sources
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    query = "hypertension"
    
    # Search NICE
    nice = tu.run({
        "name": "NICE_Clinical_Guidelines_Search",
        "arguments": {"query": query, "limit": 3}
    })
    
    # Search PubMed
    pubmed = tu.run({
        "name": "PubMed_Guidelines_Search",
        "arguments": {"query": query, "limit": 3}
    })
    
    # Search WHO
    who = tu.run({
        "name": "WHO_Guidelines_Search",
        "arguments": {"query": query, "limit": 3}
    })
    
    print(f"Found: NICE {len(nice)}, PubMed {len(pubmed)}, WHO {len(who)}")

Extract NICE Full Text
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Step 1: Search
    search = tu.run({
        "name": "NICE_Clinical_Guidelines_Search",
        "arguments": {"query": "diabetes", "limit": 1}
    })
    
    # Step 2: Extract full text
    full_text = tu.run({
        "name": "NICE_Guideline_Full_Text",
        "arguments": {"url": search[0]['url']}
    })
    
    print(f"Length: {full_text['full_text_length']:,} characters")
    print(f"Sections: {full_text['sections_count']}")
    print(f"Recommendations: {full_text['recommendations_count']}")
    print(f"\nContent:\n{full_text['full_text'][:500]}...")

Extract WHO Content + PDF
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Step 1: Search
    search = tu.run({
        "name": "WHO_Guidelines_Search",
        "arguments": {"query": "HIV", "limit": 1}
    })
    
    # Step 2: Extract content
    content = tu.run({
        "name": "WHO_Guideline_Full_Text",
        "arguments": {"url": search[0]['url']}
    })
    
    print(f"Content length: {content['content_length']:,} characters")
    print(f"Has PDF: {content['has_pdf']}")
    if content['has_pdf']:
        print(f"PDF URL: {content['pdf_download_url']}")

Complete Example
~~~~~~~~~~~~~~~~

See ``examples/clinical_guidelines_demo.py`` for a complete demonstration:

.. code-block:: bash

    python examples/clinical_guidelines_demo.py

FAQ
---

**Q: What's the difference between search tools and full-text tools?**

- **Search tools**: Return multiple results with title, URL, summary (200-2,500 chars each)
- **Full-text tools**: Extract complete guideline content (5,000-20,000+ chars) from a single URL

**Q: When should I use full-text tools?**

Use full-text tools when you need:

- Complete guideline content for detailed analysis
- All clinical recommendations extracted
- Content to feed into LLMs
- PDF download links for offline reading

**Q: Which tools return the most complete content?**

- **NICE search**: 300-2,500 char summaries
- **NICE full-text**: 5,000-20,000+ char complete guidelines
- **PubMed**: 200-2,000 char abstracts
- **WHO full-text**: 1,500+ chars + PDF links

**Q: How to filter by year?**

.. code-block:: python

    # OpenAlex supports year filtering
    results = tu.run({
        "name": "OpenAlex_Guidelines_Search",
        "arguments": {
            "query": "cancer screening",
            "year_from": 2023,
            "limit": 10
        }
    })

Return Fields
-------------

**Search Tools Return:**

- ``title``: Guideline title
- ``url``: Direct link to guideline
- ``summary``/``abstract``/``description``: Content summary (200-2,500 chars)
- Tool-specific: ``pmid``, ``doi``, ``authors``, ``date``, ``cited_by_count``, etc.

**NICE Full-Text Returns:**

- ``full_text``: Complete guideline (5,000-20,000+ chars)
- ``full_text_length``: Character count
- ``sections_count``: Number of sections
- ``recommendations``: List of recommendations
- ``recommendations_count``: Count
- ``metadata``: Publication info
- ``success``: Boolean status

**WHO Full-Text Returns:**

- ``overview``: Overview section
- ``main_content``: Main content
- ``content_length``: Character count
- ``has_pdf``: Boolean
- ``pdf_download_url``: PDF link (if available)
- ``key_facts``: List of key facts
- ``metadata``: Publication info
- ``success``: Boolean status

