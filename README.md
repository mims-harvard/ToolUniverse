# <img src="docs/_static/logo.png" alt="ToolUniverse Logo" height="28" style="vertical-align: middle; margin-right: 8px;" /> ToolUniverse: Democratizing AI scientists

[![Documentation](https://img.shields.io/badge/Documentation-Available-green)](https://zitniklab.hms.harvard.edu/ToolUniverse/)
[![Paper](https://img.shields.io/badge/Paper-Arxiv-blue)](https://arxiv.org/abs/2509.23426)
[![PyPI version](https://badge.fury.io/py/tooluniverse.svg)](https://badge.fury.io/py/tooluniverse)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-Listed-blue)](https://registry.modelcontextprotocol.io)
[![Website](https://img.shields.io/badge/Website-aiscientist.tools-blue)](https://aiscientist.tools)
[![Slack](https://img.shields.io/badge/Slack-Join_Community-orange)](https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ)
[![WeChat](https://img.shields.io/badge/WeChat-Community-07C160)](https://aiscientist.tools/wechat)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Follow-0077B5)](https://www.linkedin.com/in/shanghua-gao-96b0b3168/)
[![X](https://img.shields.io/badge/X-Follow-000000)](https://x.com/ScientistTools)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/tooluniverse?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=BLACK&left_text=downloads)](https://pepy.tech/projects/tooluniverse)

[//]: # (mcp-name: io.github.mims-harvard/tooluniverse)

## Install

**AI agent (recommended)** — open your AI agent and run:
```
Read https://aiscientist.tools/setup.md and set up ToolUniverse for me.
```
The agent will walk you through MCP configuration, API keys, skill installation, and validation.

<details>
<summary>or set up manually</summary>

Add to your MCP config file:
```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["--refresh", "tooluniverse"],
      "env": {"PYTHONIOENCODING": "utf-8"}
    }
  }
}
```

Install agent skills:
```bash
npx skills add mims-harvard/ToolUniverse
```
</details>

**Python developers** — install the SDK:
```bash
uv pip install tooluniverse
```

**[`tu` CLI](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/tu_cli.html)** — discover, inspect, run, and test tools from the terminal.
**[Python SDK](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/python_guide.html)** — programmatic access for building AI scientist systems.

## Building AI Scientists with ToolUniverse

<p align="center">
  <a href="https://www.youtube.com/watch?v=fManSJlSs60">
    <img src="https://github.com/user-attachments/assets/13ddb54c-4fcc-4507-8695-1c58e7bc1e68" width="600" />
  </a>
</p>

*Click to watch the demo* [(YouTube)](https://www.youtube.com/watch?v=fManSJlSs60) [(Bilibili)](https://www.bilibili.com/video/BV1GynhzjEos/?share_source=copy_web&vd_source=b398f13447281e748f5c41057a2c6858)

## What is ToolUniverse?

ToolUniverse is an ecosystem for creating AI scientist systems from any large language model. Powered by the AI-Tool Interaction Protocol, it standardizes how LLMs identify and call tools, integrating more than **1000 machine learning models, datasets, APIs, and scientific packages** for data analysis, knowledge retrieval, and experimental design.

**Key features:**

- [**AI-Tool Interaction Protocol**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/interaction_protocol.html): Standardized interface governing how AI scientists issue tool requests and receive results
- [**Universal AI Model Support**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/index.html): Works with Claude, GPT, Gemini, Qwen, Deepseek, and open models
- [**MCP Integration**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/mcp_support.html): Native Model Context Protocol server with configurable transport and tool selection
- [**Async Operations**](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/async_tools_guide.html): Long-running tasks (protein docking, molecular simulations) with progress tracking and parallel execution
- [**Tool Composition**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/tool_composition.html): Chain tools for sequential or parallel execution in self-directed workflows
- [**Compact Mode**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/compact_mode.html): Reduces 1000+ tools to 4-5 core discovery tools, saving ~99% context window
- [**CLI (`tu`)**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/tu_cli.html): Discover, inspect, run, and test tools directly from the terminal — 9 subcommands for interactive and scripted workflows
- [**Agent Skills**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/skills_showcase.html): 68 pre-built research workflows for drug discovery, precision oncology, rare disease diagnosis, pharmacovigilance, and more
- [**Literature Search**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/literature_search_tools_tutorial.html): Unified search across PubMed, Semantic Scholar, ArXiv, BioRxiv, Europe PMC, and more
- [**Two-Tier Result Caching**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/cache_system.html): In-memory LRU + SQLite persistence with per-tool fingerprinting for 10x speedup, offline support, and reproducibility
- [**Continuous Expansion**](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/index.html): Register new tools locally or remotely without additional configuration

<p align="center">
  <img src="https://github.com/user-attachments/assets/eb15bd7c-4e73-464b-8d65-733877c96a51" width="888" />
</p>

## AI Scientists Powered by ToolUniverse

*Building your project with ToolUniverse? Submit via [GitHub Pull Request](https://github.com/mims-harvard/ToolUniverse/pulls) or contact us.*

**TxAgent: AI Agent for Therapeutic Reasoning** [[Project]](https://zitniklab.hms.harvard.edu/TxAgent) [[Paper]](https://arxiv.org/pdf/2503.10970) [[PyPI]](https://pypi.org/project/txagent/) [[GitHub]](https://github.com/mims-harvard/TxAgent) [[HuggingFace]](https://huggingface.co/collections/mims-harvard/txagent-67c8e54a9d03a429bb0c622c)
> TxAgent leverages ToolUniverse's scientific tool ecosystem to solve complex therapeutic reasoning tasks.

---

**Medea: An Omics AI Agent for Therapeutic Discovery** [[Project]](https://medea.openscientist.ai) [[Paper]](https://www.biorxiv.org/content/early/2026/01/20/2026.01.16.696667) [[GitHub]](https://github.com/mims-harvard/Medea)
> Medea integrates ToolUniverse tools for multi-omics analysis to identify therapeutic targets and predict drug responses across cancer, autoimmune, and other diseases.

## Documentation

Full documentation: [zitniklab.hms.harvard.edu/ToolUniverse](https://zitniklab.hms.harvard.edu/ToolUniverse/)

- [CLI Reference (`tu`)](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/tu_cli.html)
- [Python Developer Guide](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/python_guide.html)
- [AI Agent Setup](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/index.html)
- [Agent Skills](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/skills_showcase.html)
- [Expand ToolUniverse](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/index.html)
- [API Reference](https://zitniklab.hms.harvard.edu/ToolUniverse/api/modules.html)

## Community

**[Shanghua Gao](https://shgao.site)**, the lead creator of this project, is currently on the job market.

[Slack](https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ) · [GitHub Issues](https://github.com/mims-harvard/ToolUniverse/issues) · [Shanghua Gao](mailto:shanghuagao@gmail.com) · [Marinka Zitnik](mailto:marinka@hms.harvard.edu)


**Leaders:** [Shanghua Gao](https://shgao.site) · [Marinka Zitnik](https://zitniklab.hms.harvard.edu/)

**Contributors:** [Shanghua Gao](https://shgao.site) · [Richard Zhu](https://www.linkedin.com/in/richard-zhu-4236901a7/) · [Pengwei Sui](https://psui3905.github.io/) · [Zhenglun Kong](https://zlkong.github.io/homepage/) · [Sufian Aldogom](mailto:saldogom@mit.edu) · [Yepeng Huang](https://yepeng.notion.site/Yepeng-Huang-16ad8dd1740080c28d4bd3e3d7c1080c) · [Ayush Noori](https://www.ayushnoori.com/) · [Reza Shamji](mailto:reza_shamji@hms.harvard.edu) · [Krishna Parvataneni](mailto:krishna_parvataneni@hms.harvard.edu) · [Theodoros Tsiligkaridis](https://sites.google.com/view/theo-t) · [Marinka Zitnik](https://zitniklab.hms.harvard.edu/)

## Citation

```
@article{gao2025democratizingaiscientistsusing,
      title={Democratizing AI scientists using ToolUniverse}, 
      author={Shanghua Gao and Richard Zhu and Pengwei Sui and Zhenglun Kong and Sufian Aldogom and Yepeng Huang and Ayush Noori and Reza Shamji and Krishna Parvataneni and Theodoros Tsiligkaridis and Marinka Zitnik},
      year={2025},
      eprint={2509.23426},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2509.23426}, 
}

@article{gao2025txagent,
      title={TxAgent: An AI Agent for Therapeutic Reasoning Across a Universe of Tools},
      author={Shanghua Gao and Richard Zhu and Zhenglun Kong and Ayush Noori and Xiaorui Su and Curtis Ginder and Theodoros Tsiligkaridis and Marinka Zitnik},
      year={2025},
      eprint={2503.10970},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2503.10970},
}
```
