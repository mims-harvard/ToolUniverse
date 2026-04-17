# Patent Tools Tier 1 Implementation Plan

| Field         | Value                                                        |
|---------------|--------------------------------------------------------------|
| Goal          | 6 USPTO patent tools + 1 base class for FTO analysis         |
| Architecture  | JSON-config tools, XML parser, DSAPITool base, batch pipeline |
| Tech Stack    | Python 3.12, httpx, lxml, ToolUniverse tool framework        |

## Tasks

| #  | Task                                          | Status |
|----|-----------------------------------------------|--------|
| 1  | JSON config: USPTO_get_patent_assignment      | DONE   |
| 2  | JSON config: USPTO_get_patent_transactions    | DONE   |
| 3  | USPTO_patent_number_to_application resolver   | DONE   |
| 4  | USPTO_get_patent_claims (XML download + parse)| DONE   |
| 5  | DSAPITool base class                          | DONE   |
| 6  | USPTO_search_enriched_citations               | DONE   |
| 7  | USPTO_patent_deep_lookup batch pipeline       | DONE   |
| 8  | Integration tests with 3 test patents         | DONE   |
| 9  | API reference documentation                   | DONE   |

Full implementation is on branch `feat/patent-tools-tier1`.
