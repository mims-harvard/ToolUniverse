# Human Expert Feedback
![Web UI](../_static/expert_feedback_ui.jpg)
## Overview

The Human Expert Feedback System is a sophisticated **human-in-the-loop** consultation platform designed for ToolUniverse. It enables AI systems to seamlessly consult with human experts when encountering complex decisions, particularly in medical and scientific domains where expert knowledge is crucial.

### Key Capabilities

- **🔄 Real-time Consultation**: Submit questions to human experts and receive responses in real-time
- **🌐 Modern Web Interface**: Beautiful, responsive dashboard with auto-refresh for expert interactions
- **⚡ MCP Integration**: Built on Model Context Protocol for seamless ToolUniverse integration
- **🎨 Priority Management**: Support for normal, high, and urgent priority requests with visual indicators
- **📱 Multi-Interface**: Web-based and terminal-based interfaces for different user preferences
- **🔌 Flexible Deployment**: Auto-port discovery and custom configuration options

### Use Cases

- **Medical AI**: Get expert medical opinions for complex patient cases
- **Scientific Research**: Consult domain experts for research methodology and analysis
- **Drug Discovery**: Expert review of molecular compounds and drug interactions
- **Clinical Decision Support**: Real-time consultation for treatment recommendations
- **Research Validation**: Expert validation of AI-generated hypotheses and findings

## Quick Start

### Install Package
```bash
pip install tooluniverse
```

### Start Expert Feedback Server
```bash
tooluniverse-expert-feedback --start-server
# This starts:
# 🔌 Router-ToolUniverse Server on port 9876 (for ToolUniverse)
# � Router-Expert Server on port 9877 (for Expert Web Interface)
```

### Start Web Interface (On Expert Side)
```bash
# Interactive setup - will prompt for API server details
tooluniverse-expert-feedback-web

# Alternative: Use environment variables (for automation)
export EXPERT_FEEDBACK_API_HOST="192.168.1.100"  # API Server IP
export EXPERT_FEEDBACK_API_PORT="9877"           # API Server port
tooluniverse-expert-feedback-web
```

**Interactive Setup Process:**
1. Run `tooluniverse-expert-feedback-web`
2. Enter Router-Expert server IP (or press Enter for localhost)
3. Enter Router-Expert server port (or press Enter for 9877)
4. Web interface opens automatically at http://localhost:8090

## Architecture

**Dual Server Design:**
- **Router-ToolUniverse Server (Port 9876)**: Handles ToolUniverse tool calls
- **Router-Expert Server (Port 9877)**: Handles expert web interface communication
- **Shared Data**: Both servers access the same expert system instance


## Usage in ToolUniverse

**Set Environment Variable:**

In the environment where agent runs tools:
```bash
export EXPERT_FEEDBACK_MCP_SERVER_URL="localhost:9876"  # Use actual MCP port
```

```python
from tooluniverse import ToolUniverse

tooluni = ToolUniverse()
tooluni.load_tools()

# Submit question to expert
result = tooluni.run({
    "name": "expert_consult_human_expert",
    "arguments": {
        "question": "What is the recommended dosage of aspirin for elderly patients?",
        "specialty": "cardiology",
        "priority": "high"  # normal, high, urgent
    }
})
```

## Available Tools

| Tool | Purpose |
|------|---------|
| `consult_human_expert` | Submit questions to experts |
| `get_expert_response` | Check for expert responses |
| `list_pending_expert_requests` | View pending requests |
| `submit_expert_response` | Submit expert responses |
| `get_expert_status` | Get system status |

## Command Options

```bash
# Start server (auto port)
tooluniverse-expert-feedback --start-server

# Start server (fixed port)
tooluniverse-expert-feedback --start-server --port 8000

# Interactive web interface for experts
tooluniverse-expert-feedback-web
```

## Files

- **`tooluniverse-expert-feedback`** -  Router server
- **`tooluniverse-expert-feedback-web`** - Launcher Router-Expert with auto-detection
- **`simple_test.py`** - Basic test script

## Web Interface Features

- **Modern UI**: Gradient backgrounds, card layouts, responsive design
- **Auto-refresh**: 15-second updates with countdown timer
- **Priority colors**: Normal (blue), High (orange), Urgent (red + animation)
- **Real-time notifications**: Toast messages for user actions
- **Mobile-friendly**: Works on all screen sizes

---

*🧑‍⚕️ Built for professionals and AI systems*
