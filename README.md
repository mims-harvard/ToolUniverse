# <img src="docs/_static/logo.png" alt="ToolUniverse Logo" height="28" style="vertical-align: middle; margin-right: 8px;" /> ToolUniverse: Democratizing AI scientists
[![Documentation](https://img.shields.io/badge/Documentation-Available-green)](https://zitniklab.hms.harvard.edu/ToolUniverse/)
[![Paper](https://img.shields.io/badge/Paper-Arxiv-blue)](https://arxiv.org/abs/2509.23426)
[![PyPI version](https://badge.fury.io/py/tooluniverse.svg)](https://badge.fury.io/py/tooluniverse)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-Listed-blue)](https://registry.modelcontextprotocol.io)
[![🌐Web](https://img.shields.io/badge/Website-aiscientist.tools-blue)](https://aiscientist.tools)
[![Slack](https://img.shields.io/badge/Slack-Join_Community-orange)](https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ)
[![WeChat](https://img.shields.io/badge/WeChat-Community-07C160)](https://aiscientist.tools/wechat)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Follow-0077B5)](https://www.linkedin.com/in/shanghua-gao-96b0b3168/)
[![X](https://img.shields.io/badge/X-Follow-000000)](https://x.com/ScientistTools)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/tooluniverse?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=BLACK&left_text=downloads)](https://pepy.tech/projects/tooluniverse)

[//]: # (mcp-name: io.github.mims-harvard/tooluniverse)

## INSTALL ToolUniverse

<table>
<tr>
<td width="45%" valign="top">

**1️⃣ MCP Setup** – Add to your MCP config:
```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["tooluniverse"],
      "env": {"PYTHONIOENCODING": "utf-8"}
    }
  }
}
```

</td>
<td width="45%" valign="top">

**2️⃣ Install Agent Skills**
```bash
npx skills add mims-harvard/ToolUniverse
```

**3️⃣ Install Package** (Optional)
```bash
uv pip install tooluniverse
```

</td>
</tr>
</table>

> **Guided Setup:** Install skills first with `npx skills add mims-harvard/ToolUniverse`, then ask your AI coding agent **"setup tooluniverse"**. The `setup-tooluniverse` skill will walk you through MCP configuration, API keys, and validation step by step.

- **[Python Developer Guide](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/python_guide.html)**: Build AI scientists with the Python SDK
- **[AI Agent Platforms](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/index.html)**: Set up ToolUniverse with Cursor, Claude, Windsurf, Gemini, and more

## 🤖 Building AI Scientists with ToolUniverse in 5 minutes

<p align="center">
  <a href="https://www.youtube.com/watch?v=fManSJlSs60">
    <img src="https://github.com/user-attachments/assets/13ddb54c-4fcc-4507-8695-1c58e7bc1e68" width="600" />
  </a>
</p>

*Click the image above to watch the demonstration* [(YouTube)](https://www.youtube.com/watch?v=fManSJlSs60) [(Bilibili)](https://www.bilibili.com/video/BV1GynhzjEos/?share_source=copy_web&vd_source=b398f13447281e748f5c41057a2c6858)

## 🔬 What is ToolUniverse?

ToolUniverse is an ecosystem for creating AI scientist systems from any open or closed large language model (LLM). Powered by AI-Tool Interaction Protocol, it standardizes how LLMs identify and call tools, integrating more than **1000 machine learning models, datasets, APIs, and scientific packages** for data analysis, knowledge retrieval, and experimental design.

AI scientists are emerging computational systems that serve as collaborative partners in discovery. However, these systems remain difficult to build because they are bespoke, tied to rigid workflows, and lack shared environments that unify tools, data, and analysts into a common ecosystem.

ToolUniverse addresses this challenge by providing a standardized ecosystem that transforms any AI model into a powerful research scientist. By abstracting capabilities behind a unified interface, ToolUniverse wraps around any AI model (LLM, AI agent, or large reasoning model) and enables users to create and refine entirely custom AI scientists without additional training or finetuning.

**Key Features:**

- [**AI-Tool Interaction Protocol**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/interaction_protocol.html): Standardized interface governing how AI scientists issue tool requests and receive results
- [**Universal AI Model Support**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/index.html): Works with any LLM, AI agent, or large reasoning model (GPT5, Claude, Gemini, Qwen, Deepseek, open models)
- [**OpenRouter Integration**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/openrouter_support.html): Access 100+ models from OpenAI, Anthropic, Google, Qwen, and more through a single API
- [**MCP Tasks for Async Operations**](docs/MCP_TASKS_GUIDE.md): Native support for long-running operations (protein docking, molecular simulations) with automatic progress tracking, parallel execution, and cancellation
- [**Easy to Load & Find & Call Tool**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/index.html) (*[WebService](https://aiscientist.tools/), [PythonAPI](https://zitniklab.hms.harvard.edu/ToolUniverse/api/modules.html), [MCP](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/mcp_support.html)*): Maps natural-language descriptions to tool specifications and executes tools with structured results
- [**Tool Composition & Scientific Workflows**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/tool_composition.html): Chains tools for sequential or parallel execution in self-directed scientific workflows
- [**Continuous Expansion**](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/index.html): New tools can be easily registered locally or remotely without additional configuration
- [**Multi-Agent Tool Creation & Optimization**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/scientific_workflows.html): Multi-agent powered tool construction and iterative tool optimization
- [**20+ Pre-Built AI Scientist Skills**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/skills_showcase.html): End-to-end research workflows for drug discovery, precision oncology, rare disease diagnosis, pharmacovigilance, and more — installable with one command
- [**Compact Mode**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/compact_mode.html): Reduces 1000+ tools to 4-5 core discovery tools, saving ~99% context window while maintaining full capability
- [**Two-Tier Result Caching**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/cache_system.html): In-memory LRU + SQLite persistence with per-tool fingerprinting for 10x speedup, offline support, and reproducibility
- [**Literature Search Across 11+ Databases**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/literature_search_tools_tutorial.html): Unified search across PubMed, Semantic Scholar, ArXiv, BioRxiv, Europe PMC, and more with AI-powered query expansion
- [**Human Expert Feedback**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/expert_feedback.html): Human-in-the-loop consultation where AI agents can escalate to domain experts in real-time via a web dashboard
- [**Scientific Visualization**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/visualization_tutorial.html): Interactive 3D protein structures and 2D/3D molecule visualizations rendered as HTML
- [**Make Your Data Agent-Searchable**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/make_your_data_agent_searchable.html): Turn any text or JSON data into an agent-searchable collection with one CLI command, shareable on HuggingFace

<p align="center">
  <img src="https://github.com/user-attachments/assets/eb15bd7c-4e73-464b-8d65-733877c96a51" width="888" />
</p>

## 🔧 Usage & Integration

- **[Python SDK](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/python_guide.html)**: Load, find, and call 1000+ tools via Python
- **[MCP Support](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/mcp_support.html)**: Model Context Protocol integration for AI agents
- **[MCPB](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/mcpb_introduction.html)**: Standalone executable MCP server bundle
- **[HTTP API](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/http_api.html)**: Deploy remotely and access all methods with minimal client dependencies


## 🚀 AI Scientists Projects Powered by ToolUniverse

*Building your own project with ToolUniverse? We'd love to feature it here! Submit your project via [GitHub Pull Request](https://github.com/mims-harvard/ToolUniverse/pulls) or contact us.*

---
**TxAgent: AI Agent for Therapeutic Reasoning** [[Project]](https://zitniklab.hms.harvard.edu/TxAgent) [[Paper]](https://arxiv.org/pdf/2503.10970) [[PiPy]](https://pypi.org/project/txagent/) [[Github]](https://github.com/mims-harvard/TxAgent) [[HuggingFace]](https://huggingface.co/collections/mims-harvard/txagent-67c8e54a9d03a429bb0c622c)
> **TxAgent** is an AI agent for therapeutic reasoning that leverages ToolUniverse's comprehensive scientific tool ecosystem to solve complex therapeutic reasoning tasks. 


---
**Hypercholesterolemia Drug Discovery** [[Tutorial]](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/tooluniverse_case_study.html) [[Code]](https://colab.research.google.com/drive/1UwJ6RwyUoqI5risKQ365EeFdDQWOeOCv?usp=sharing)


## 🤝 Contribution and Community

We are currently looking for partners. If you’re interested, please reach out to [Shanghua Gao](shanghuagao@gmail.com).

**We are actively looking for core contributors for ToolUniverse!**
Please join our [Slack Channel](https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ) or reach out to [Shanghua Gao](mailto:shanghuagao@gmail.com)/[Marinka Zitnik](mailto:marinka@hms.harvard.edu).

**Get Involved:**

- **Report Issues**: [GitHub Issues](https://github.com/mims-harvard/ToolUniverse/issues)
- **Join Discussions**: [Slack Channel](https://github.com/mims-harvard/ToolUniverse/discussions)
- **Contact**: Reach out to [Shanghua Gao](shanghuagao@gmail.com)/[Marinka Zitnik](marinka@hms.harvard.edu)
- **Contribute**: See our [Contributing Guide](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/contributing/index.html)


### Leaders 
- **[Shanghua Gao](https://shgao.site)**
- **[Marinka Zitnik](https://zitniklab.hms.harvard.edu/)**

### Contributors

- **[Shanghua Gao](https://shgao.site)**
- **[Richard Zhu](https://www.linkedin.com/in/richard-zhu-4236901a7/)**
- **[Pengwei Sui](https://psui3905.github.io/)**
- **[Zhenglun Kong](https://zlkong.github.io/homepage/)**
- **[Sufian Aldogom](mailto:saldogom@mit.edu)**
- **[Yepeng Huang](https://yepeng.notion.site/Yepeng-Huang-16ad8dd1740080c28d4bd3e3d7c1080c)**
- **[Ayush Noori](https://www.ayushnoori.com/)**
- **[Reza Shamji](mailto:reza_shamji@hms.harvard.edu)**
- **[Krishna Parvataneni](mailto:krishna_parvataneni@hms.harvard.edu)**
- **[Theodoros Tsiligkaridis](https://sites.google.com/view/theo-t)**
- **[Marinka Zitnik](https://zitniklab.hms.harvard.edu/)**


## 📚 Documentation

### 🚀 Get Started
- **[Python Developer Guide](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/python_guide.html)**: Installation, SDK usage, and API reference
- **[AI Agent Platforms](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/index.html)**: Set up ToolUniverse with Cursor, Claude, Windsurf, and more
- **[AI Agent Skills](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/skills_showcase.html)**: Pre-built research skills for AI agents
- **[API Keys](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/api_keys.html)**: Configure API keys for external services

<<<<<<< HEAD
### 🚀 Getting Started
- **[Quick Start Tutorial](https://zitniklab.hms.harvard.edu/ToolUniverse/quickstart.html)**: 5-minute setup and first query
- **[Installation](https://zitniklab.hms.harvard.edu/ToolUniverse/installation.html)**: Complete installation options
- **[Getting Started](https://zitniklab.hms.harvard.edu/ToolUniverse/getting_started.html)**: Step-by-step tutorial
- **[AI-Tool Protocol](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/interaction_protocol.html)**: Understanding the interaction protocol

### 📖 User Guides
- **[Loading Tools](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/loading_tools.html)**: Complete Tutorial to loading tools
- **[Tool Discovery](https://zitniklab.hms.harvard.edu/ToolUniverse/tutorials/finding_tools.html)**: Find tools by keyword, LLM, and embedding search
- **[Tool Caller](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/tool_caller.html)**: Primary execution engine
- **[Tool Composition](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/tool_composition.html)**: Chain tools into workflows
- **[Scientific Workflows](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/scientific_workflows.html)**: Real-world research scenarios
- **[MCP Support](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/mcp_support.html)**: Model Context Protocol integration
- **[Logging](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/logging.html)**: Comprehensive logging configuration

### 🛠️ Advanced Features
- **[MCP Tasks & Async Operations](docs/MCP_TASKS_GUIDE.md)**: Long-running operations with progress tracking, parallel execution, and cancellation support
=======
### 💡 Tutorials & Advanced
- **[Tutorials Overview](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/index.html)**: Guides for tool discovery, agentic tools, literature search, and more
- **[AI-Tool Interaction Protocol](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/interaction_protocol.html)**: How AI scientists issue tool requests
- **[Scientific Workflows](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/scientific_workflows.html)**: Multi-agent tool creation and optimization
>>>>>>> origin/main
- **[Hooks System](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/hooks/index.html)**: Intelligent output processing

### 🔧 Expanding ToolUniverse
- **[Contributing Guide](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/contributing/index.html)**: How to contribute new tools
- **[Local Tools](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/local_tools/index.html)**: Create and register custom local tools
- **[Remote Tools](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/remote_tools/index.html)**: Integrate external services as tools
- **[Architecture](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/architecture.html)**: System architecture overview

### 📚 API Reference
- **[API Modules](https://zitniklab.hms.harvard.edu/ToolUniverse/api/modules.html)**: Complete Python API reference

→ **Browse All Documentation**: [ToolUniverse Documentation](https://zitniklab.hms.harvard.edu/ToolUniverse/)


### Citation

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

---

*Democratizing AI agents for science with ToolUniverse.*
