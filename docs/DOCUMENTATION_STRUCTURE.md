# Documentation Structure

This document describes how the docs folder is organized to match the doctree (sidebar navigation).

## Overview

```
docs/
├── index.rst                          (main entry)
├── sitemap.rst                        (standalone reference page)
├── guide/                             (Get Started + Tutorials & Advanced)
│   ├── python_guide.rst               ← Get Started
│   ├── coding_api.rst                ← under Python Guide
│   ├── interaction_protocol.rst       ← under Python Guide
│   ├── loading_tools.rst              ← under Python Guide
│   ├── listing_tools.rst              ← under Python Guide
│   ├── finding_tools.rst              ← under Python Guide
│   ├── tool_caller.rst                ← under Python Guide
│   ├── tool_composition.rst           ← under Python Guide
│   ├── toolspace.rst                  ← under Python Guide
│   ├── examples.rst                   ← under Python Guide
│   ├── tooluniverse_case_study.rst    ← under Python Guide
│   ├── http_api.rst                   ← under Python Guide
│   ├── skills_showcase.rst            ← Get Started
│   ├── api_keys.rst                   ← Get Started
│   ├── building_ai_scientists/        ← Get Started
│   │   ├── index.rst
│   │   ├── 12 platform .rst files
│   │   ├── mcp_support.rst, mcpb_introduction.rst, mcp_name_shortening.rst
│   │   └── compact_mode.rst
│   ├── index.rst                      ← Tutorials & Advanced
│   ├── agentic_tools_tutorial.rst     ← Tutorials & Advanced
│   ├── literature_search_*.rst        ← Tutorials & Advanced
│   ├── clinical_guidelines_tools.rst   ← Tutorials & Advanced
│   ├── scientific_workflows.rst       ← Tutorials & Advanced
│   ├── expert_feedback.md             ← Tutorials & Advanced
│   ├── make_your_data_agent_searchable.rst ← Tutorials & Advanced
│   ├── visualization_tutorial.rst     ← Tutorials & Advanced
│   ├── hooks/                         ← Tutorials & Advanced
│   ├── cache_system.rst, logging.rst, etc. ← Tutorials & Advanced
│   └── ...
├── expand_tooluniverse/               (Expand ToolUniverse)
├── tools/                             (Tools Catalog)
├── api/                               (API Reference)
├── reference/                         (Help & Reference)
│   ├── cli_tools.rst
│   ├── environment_variables.rst
│   ├── data_sources.rst
│   └── glossary.rst
├── help/                              (Help & Reference)
│   ├── index.rst
│   ├── faq.rst
│   ├── troubleshooting.rst
│   └── wechat_community.rst
├── about/                             (Help & Reference)
│   ├── index.rst, contributing.rst, deployment.rst, license.rst
│   ├── changelog.rst
│   └── faq.rst
├── old/                               (legacy/deprecated)
└── dev_docs/                          (internal developer docs)
```

## Doctree Sections

- **Get Started**: `guide/python_guide`, `guide/building_ai_scientists/index`, `guide/skills_showcase`, `guide/api_keys`
- **Tutorials & Advanced**: `guide/index` and all tutorial/advanced pages under `guide/`
- **Expand ToolUniverse**: `expand_tooluniverse/`
- **Tools Catalog**: `tools/`
- **API Reference**: `api/`
- **Help & Reference**: `reference/`, `help/`, `about/`, `expand_tooluniverse/reference/`

Files live in the same directory as their doctree siblings so the folder structure matches the sidebar.
