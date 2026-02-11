# <img src="docs/_static/logo.png" alt="ToolUniverse Logo" height="28" style="vertical-align: middle; margin-right: 8px;" /> ToolUniverse: Democratizing AI scientists
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/tooluniverse?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=BLACK&left_text=downloads)](https://pepy.tech/projects/tooluniverse)
[![Paper](https://img.shields.io/badge/Paper-Arxiv-blue)](https://arxiv.org/abs/2509.23426)
[![PyPI version](https://badge.fury.io/py/tooluniverse.svg)](https://badge.fury.io/py/tooluniverse)
[![ToolUniverse](https://img.shields.io/badge/Code-ToolUniverse-purple)](https://github.com/mims-harvard/ToolUniverse)
[![Model context protocol (MCP)](https://img.shields.io/badge/Model_Context_Protocol_(MCP)_Supported-green)](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/mcp_support.html)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-Listed-blue)](https://registry.modelcontextprotocol.io)
[![MCPB](https://img.shields.io/badge/Download-MCPB-red)](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/mcpb_introduction.html)
[![Documentation](https://img.shields.io/badge/Documentation-Available-green)](https://zitniklab.hms.harvard.edu/ToolUniverse/)
[![🌐Web](https://img.shields.io/badge/Website-aiscientist.tools-blue)](https://aiscientist.tools)
[![Slack](https://img.shields.io/badge/Slack-Join_Community-orange)](https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ)

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

We are currently looking for partners. If you’re interested, please reach out to [Shanghua Gao](shanghuagao@gmail.com).

ToolUniverse is an ecosystem for creating AI scientist systems from any open or closed large language model (LLM). Powered by AI-Tool Interaction Protocol, it standardizes how LLMs identify and call tools, integrating more than **1000 machine learning models, datasets, APIs, and scientific packages** for data analysis, knowledge retrieval, and experimental design.

<div align="center">

[![Visit Website](https://img.shields.io/badge/Visit_Website-AIScientist.Tools-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://aiscientist.tools)

[![Join Slack Community](https://img.shields.io/badge/Join_Slack_Community-Get_Help_&_Connect-FF6B6B?style=for-the-badge&logo=slack&logoColor=white)](https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ)
[![Join WeChat Group](https://img.shields.io/badge/Join_WeChat_Group-Community_&_Discussion-07C160?style=for-the-badge&logo=wechat&logoColor=white)](https://aiscientist.tools/wechat)

[![Follow on LinkedIn](https://img.shields.io/badge/Follow_on_LinkedIn-Professional_Updates-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/tooluniverse-at-harvard-b9aa88385/)
[![Follow on X](https://img.shields.io/badge/Follow_on_X-Latest_Updates-000000?style=for-the-badge&logo=x&logoColor=white)](https://x.com/ScientistTools)

</div>
<p align="center">
  <img src="https://github.com/user-attachments/assets/13ddb54c-4fcc-4507-8695-1c58e7bc1e68" width="600" />
</p>

→ **Complete Tool List**: [Available Tools](https://zitniklab.hms.harvard.edu/ToolUniverse/tools/tools_config_index.html)

→ **Check our website for direct tool usage**: [AIScientist.Tools](https://aiscientist.tools/)


## 🤖 Building AI Scientists with ToolUniverse in 5 minutes

[![YouTube Video](https://img.youtube.com/vi/fManSJlSs60/maxresdefault.jpg)](https://www.youtube.com/watch?v=fManSJlSs60)
*Click the image above to watch the ToolUniverse demonstration*
[(Also in Bilibili)](https://www.bilibili.com/video/BV1GynhzjEos/?share_source=copy_web&vd_source=b398f13447281e748f5c41057a2c6858)

- **[Overview](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/index.html)**: Create AI scientists from any LLM
- **[Claude Desktop Integration](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/claude_desktop.html)**: Native MCP integration with Claude Desktop App
- **[Claude Code Integration](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/claude_code.html)**: AI scientist development in Claude Code environment
- **[Gemini CLI Integration](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/gemini_cli.html)**: Command-line scientific research with Google Gemini
- **[Qwen Code Integration](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/qwen_code.html)**: AI scientist workflows in Qwen Code environment
- **[GPT Codex CLI Integration](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/codex_cli.html)**: Terminal-based research with OpenAI Codex
- **[ChatGPT API Integration](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/chatgpt_api.html)**: Programmatic research with ChatGPT function calling

## 🔬 What is ToolUniverse?

AI scientists are emerging computational systems that serve as collaborative partners in discovery. However, these systems remain difficult to build because they are bespoke, tied to rigid workflows, and lack shared environments that unify tools, data, and analysts into a common ecosystem.

ToolUniverse addresses this challenge by providing a standardized ecosystem that transforms any AI model into a powerful research scientist. By abstracting capabilities behind a unified interface, ToolUniverse wraps around any AI model (LLM, AI agent, or large reasoning model) and enables users to create and refine entirely custom AI scientists without additional training or finetuning.

**Key Features:**

- [**AI-Tool Interaction Protocol**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/interaction_protocol.html): Standardized interface governing how AI scientists issue tool requests and receive results
- [**Universal AI Model Support**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/building_ai_scientists/index.html): Works with any LLM, AI agent, or large reasoning model (GPT5, Claude, Gemini, Qwen, Deepseek, open models)
- [**OpenRouter Integration**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/openrouter_support.html): Access 100+ models from OpenAI, Anthropic, Google, Qwen, and more through a single API
- [**MCP Tasks for Async Operations**](docs/MCP_TASKS_GUIDE.md): Native support for long-running operations (protein docking, molecular simulations) with automatic progress tracking, parallel execution, and cancellation
- [**Easy to Load & Find & Call Tool**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/index.html) (*[WebService](https://aiscientist.tools/), [PythonAPI](https://zitniklab.hms.harvard.edu/ToolUniverse/api/modules.html), [MCP](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/mcp_support.html)*): Maps natural-language descriptions to tool specifications and executes tools with structured results
- [**Tool Composition & Scientific Workflows**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/tool_composition.html): Chains tools for sequential or parallel execution in self-directed scientific workflows
- [**Continuous Expansion**](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/index.html): New tools can be easily registered locally or remotely without additional configuration
- [**Multi-Agent Tool Creation & Optimization**](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/scientific_workflows.html): Multi-agent powered tool construction and iterative tool optimization

<p align="center">
  <img src="https://github.com/user-attachments/assets/eb15bd7c-4e73-464b-8d65-733877c96a51" width="888" />
</p>


→ **Detailed Tutorials**: [Quick Start](https://zitniklab.hms.harvard.edu/ToolUniverse/quickstart.html) | [Installation Guide](https://zitniklab.hms.harvard.edu/ToolUniverse/installation.html) | [Getting Started](https://zitniklab.hms.harvard.edu/ToolUniverse/getting_started.html)

## 🔧 Usage & Integration

ToolUniverse supports multiple integration methods for different use cases:

### Python SDK Integration

```python
from tooluniverse import ToolUniverse

# Initialize and load tools
tu = ToolUniverse()
tu.load_tools()

# Find relevant tools
tools = tu.run({
    "name": "Tool_Finder_Keyword", # Tool_Finder (Embedding model, GPU required), Tool_Finder_LLM (LLM-based model)
    "arguments": {"description": "protein structure prediction", "limit": 10}
})

# Execute tools (sync context)
result = tu.run({
    "name": "UniProt_get_function_by_accession",
    "arguments": {"accession": "P05067"}
})

# Async execution for long-running operations
import asyncio

async def run_docking():
    # Same API works in async context!
    result = await tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
    return result

# Run multiple jobs in parallel
async def parallel_jobs():
    results = await asyncio.gather(
        tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR"),
        tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="1ABC"),
        tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="3XYZ"),
    )
    return results  # 3x faster than sequential!

```

→ **Complete Tutorials**: [Installation Tutorial](https://zitniklab.hms.harvard.edu/ToolUniverse/installation.html) | [MCP Tasks & Async Operations](docs/MCP_TASKS_GUIDE.md)

### MCP Support

```python
# run one command to launch the tooluniverse smcp server
tooluniverse-smcp
```

**Quick Setup for Claude Code:**
```bash
pip install tooluniverse
claude mcp add --transport stdio tooluniverse -- tooluniverse-smcp-stdio --compact-mode
```

→ **Complete Tutorial**: [MCP Support](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/mcp_support.html)

### MCPB Support

The **Model Context Protocol Bundle (MCPB)** wraps ToolUniverse as a standalone executable MCP server. This bundle is designed to work seamlessly with Claude Desktop and other MCPB-aware clients without complex environment setup.

> [Read our Introduction to MCPB](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/mcpb_introduction.html)

### 🌐 HTTP API - Remote Access

Deploy ToolUniverse on a **separate server** and access all 49+ methods remotely with minimal client dependencies!

**Server** (with full ToolUniverse):
```bash
pip install tooluniverse
tooluniverse-http-api --host 0.0.0.0 --port 8080
```

**Client** (only needs `requests` + `pydantic`):
```bash
pip install tooluniverse[client]  # Minimal installation
```

```python
from tooluniverse import ToolUniverseClient

client = ToolUniverseClient("http://your-server:8080")

# Use exactly like local ToolUniverse!
client.load_tools(tool_type=['uniprot', 'ChEMBL', 'opentarget'])
result = client.run_one_function({
    "name": "UniProt_get_entry_by_accession",
    "arguments": {"accession": "P05067"}
})
```

**Key Features:**
- ✅ **Auto-updating**: New methods work automatically (zero maintenance!)
- ✅ **Minimal client**: Only `requests` + `pydantic` required
- ✅ **Full API access**: All ToolUniverse methods available remotely
- ✅ **Stateful server**: Maintains loaded tools across requests

→ **Complete Guide**: [HTTP API Documentation](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/http_api.html)


## 🚀 AI Scientists Projects Powered by ToolUniverse

*Building your own project with ToolUniverse? We'd love to feature it here! Submit your project via [GitHub Pull Request](https://github.com/mims-harvard/ToolUniverse/pulls) or contact us.*

---
**TxAgent: AI Agent for Therapeutic Reasoning** [[Project]](https://zitniklab.hms.harvard.edu/TxAgent) [[Paper]](https://arxiv.org/pdf/2503.10970) [[PiPy]](https://pypi.org/project/txagent/) [[Github]](https://github.com/mims-harvard/TxAgent) [[HuggingFace]](https://huggingface.co/collections/mims-harvard/txagent-67c8e54a9d03a429bb0c622c)
> **TxAgent** is an AI agent for therapeutic reasoning that leverages ToolUniverse's comprehensive scientific tool ecosystem to solve complex therapeutic reasoning tasks. 


---
**Hypercholesterolemia Drug Discovery** [[Tutorial]](https://zitniklab.hms.harvard.edu/ToolUniverse/tutorials/tooluniverse_case_study.html) [[Code]](https://colab.research.google.com/drive/1UwJ6RwyUoqI5risKQ365EeFdDQWOeOCv?usp=sharing)
<p align="center">
  <img src="https://github.com/user-attachments/assets/cc53e9b0-94d3-407d-a015-71762ddb9836" width="600" />
</p>



## 🤝 Contribution and Community

**We are actively looking for core contributors for ToolUniverse!**
Please join our [Slack Channel](https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ) or reach out to [Shanghua Gao](mailto:shanghuagao@gmail.com)/[Marinka Zitnik](mailto:marinka@hms.harvard.edu).

**Get Involved:**

- **Report Issues**: [GitHub Issues](https://github.com/mims-harvard/ToolUniverse/issues)
- **Join Discussions**: [Slack Channel](https://github.com/mims-harvard/ToolUniverse/discussions)
- **Contact**: Reach out to [Shanghua Gao](shanghuagao@gmail.com)/[Marinka Zitnik](marinka@hms.harvard.edu)
- **Contribute**: See our [Contributing Tutorial](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/comprehensive_tool_guide.html)


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

Our comprehensive documentation covers everything from quick start to advanced workflows:

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
- **[Hooks System](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/hooks/index.html)**: Intelligent output processing
  - **[Hook Configuration](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/hooks/hook_configuration.html)**: Configure hooks for different outputs
  - **[File Save Hook](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/hooks/file_save_hook.html)**: Save tool outputs to files
  - **[Summarization Hook](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/hooks/summarization_hook.html)**: Summarize tool outputs
  - **[Server Stdio Hooks](https://zitniklab.hms.harvard.edu/ToolUniverse/guide/hooks/server_stdio_hooks.html)**: Server communication hooks
- **[Expert Feedback](https://zitniklab.hms.harvard.edu/ToolUniverse/tutorials/expert_feedback.html)**: Human-in-the-loop consultation
- **[Agentic Tools](https://zitniklab.hms.harvard.edu/ToolUniverse/tutorials/agentic_tools_tutorial.html)**: AI-powered tool development
- **[Case Study](https://zitniklab.hms.harvard.edu/ToolUniverse/tutorials/tooluniverse_case_study.html)**: End-to-end drug discovery workflow
- **[Tool Optimization](https://zitniklab.hms.harvard.edu/ToolUniverse/tutorials/optimization/Tool_Description_Optimizer_Tutorial.html)**: Optimize tool descriptions for better performance

### 🔧 Expanding ToolUniverse
- **[Architecture](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/architecture.html)**: System architecture overview
- **[Local Tool Registration](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/local_tool_registration.html)**: Create custom tools
- **[Remote Tool Registration](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/remote_tool_registration.html)**: Integrate external services
- **[Contributing Tools](https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/comprehensive_tool_guide.html)**: Complete contribution guide
- **[Adding Tools Tutorial](https://zitniklab.hms.harvard.edu/ToolUniverse/tutorials/addtools/Adding_Tools_Tutorial.html)**: Step-by-step tool addition guide
- **[MCP Tool Registration](https://zitniklab.hms.harvard.edu/ToolUniverse/tutorials/addtools/mcp_tool_registration_en.html)**: Register tools via MCP

### 📚 API Reference
- **[API Directory](https://zitniklab.hms.harvard.edu/ToolUniverse/api/modules.html)**: Complete module listing
- **[Core Modules](https://zitniklab.hms.harvard.edu/ToolUniverse/api/tooluniverse.html)**: Main ToolUniverse class and utilities
- **[Tool Classes](https://zitniklab.hms.harvard.edu/ToolUniverse/api/tooluniverse.base_tool.html)**: Base tool classes and implementations
- **[Compose Scripts](https://zitniklab.hms.harvard.edu/ToolUniverse/api/tooluniverse.compose_scripts.html)**: Tool composition utilities
- **[MCP Integration](https://zitniklab.hms.harvard.edu/ToolUniverse/api/tooluniverse.mcp_integration.html)**: Model Context Protocol support

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
