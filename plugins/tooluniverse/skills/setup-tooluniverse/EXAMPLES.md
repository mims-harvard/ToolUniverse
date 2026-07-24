# Setup ToolUniverse - Usage Examples

Real-world examples of using the setup-tooluniverse skill.

## Example 1: First-Time Setup for Cursor

**User Request**: "I want to use ToolUniverse in Cursor"

**Agent Response**:

1. **Check Prerequisites**
   ```bash
   python scripts/check_prerequisites.py
   ```
   
   Output shows:
   - ✓ Python 3.12 (compatible)
   - ✓ pip available
   - ✓ uv available
   - ✓ Cursor config found

2. **Install ToolUniverse**
   ```bash
   pip install tooluniverse
   ```

3. **Verify Installation**
   ```bash
   python scripts/verify_installation.py
   ```
   
   Output shows:
   - ✓ Import successful (v1.0.17)
   - ✓ Loaded 764 tools
   - ✓ CLI commands available

4. **Configure MCP**
   
   Create `~/Library/Application Support/Cursor/User/mcp.json`:
   ```json
   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": ["--compact-mode"]
       }
     }
   }
   ```

5. **Test Configuration**
   ```bash
   python scripts/test_mcp_connection.py
   ```
   
   Output shows:
   - ✓ Config found and valid
   - ✓ ToolUniverse configured
   - ✓ Compact mode enabled
   - ✓ Command available

6. **Restart Cursor** and verify MCP server appears

## Example 2: Troubleshooting Installation

**User Request**: "ToolUniverse isn't working in Cursor"

**Agent Response**:

1. **Run Diagnostics**
   ```bash
   python scripts/diagnose_setup.py
   ```
   
   Report identifies issues:
   - ❌ tooluniverse-smcp-stdio not found in PATH
   - ⚠️ Multiple Python installations detected

2. **Fix PATH Issue**
   ```bash
   # Find where pip installed scripts
   python -m pip show tooluniverse | grep Location
   
   # Add to PATH in ~/.zshrc or ~/.bashrc
   export PATH="$HOME/.local/bin:$PATH"
   
   # Reload shell
   source ~/.zshrc
   ```

3. **Verify Fix**
   ```bash
   which tooluniverse-smcp-stdio
   # Should show: /Users/username/.local/bin/tooluniverse-smcp-stdio
   ```

4. **Retest**
   ```bash
   python scripts/verify_installation.py
   # Should now show all checks passing
   ```

## Example 3: Development Setup

**User Request**: "I'm developing ToolUniverse tools and need to test them"

**Agent Response**:

1. **Clone Repository**
   ```bash
   git clone https://github.com/mims-harvard/ToolUniverse.git
   cd ToolUniverse
   ```

2. **Install in Development Mode**
   ```bash
   pip install -e .
   ```

3. **Configure MCP for Development**
   
   In `mcp.json`:
   ```json
   {
     "mcpServers": {
       "tooluniverse-dev": {
         "command": "python3",
         "args": [
           "-m",
           "tooluniverse.smcp_server",
           "--compact-mode",
           "--verbose"
         ],
         "cwd": "/path/to/ToolUniverse"
       }
     }
   }
   ```

4. **Verify Development Setup**
   ```bash
   python scripts/verify_installation.py
   ```
   
   Shows development version is active

## Example 4: Context Overflow Issue

**User Request**: "Cursor is super slow and keeps erroring when ToolUniverse loads"

**Agent Response**:

**Diagnosis**: Not using compact mode, causing context overflow.

1. **Check Current Config**
   ```bash
   python scripts/test_mcp_connection.py
   ```
   
   Output shows:
   - ⚠️ Compact mode NOT enabled

2. **Fix Configuration**
   
   Update `mcp.json` to add `--compact-mode`:
   ```json
   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": ["--compact-mode"]  // ← Add this
       }
     }
   }
   ```

3. **Restart Cursor**

4. **Verify Fix**
   - MCP server should load quickly
   - Only 5 tools shown in tool list
   - Can still execute all 764+ tools via execute_tool

## Example 5: Specific Tool Categories

**User Request**: "I only need protein and chemistry tools"

**Agent Response**:

1. **List Available Categories**
   ```bash
   python scripts/list_tool_categories.py
   ```
   
   Shows categories like:
   - UniProt (45 tools)
   - ChEMBL (38 tools)
   - PDB (25 tools)
   - etc.

2. **Configure Specific Categories**
   
   In `mcp.json`:
   ```json
   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": [
           "--categories",
           "UniProt",
           "ChEMBL",
           "PDB"
         ]
       }
     }
   }
   ```

3. **Restart and Verify**

**Note**: Even with specific categories, may cause context issues. Compact mode still recommended.

## Example 6: UV Installation for Better Isolation

**User Request**: "I want to keep ToolUniverse isolated from my other Python projects"

**Agent Response**:

1. **Install UV**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Create Dedicated Environment**
   ```bash
   mkdir -p ~/tooluniverse-env
   cd ~/tooluniverse-env
   uv pip install tooluniverse
   ```

3. **Configure MCP with UV**
   
   In `mcp.json`:
   ```json
   {
     "mcpServers": {
       "tooluniverse": {
         "command": "uv",
         "args": [
           "--directory",
           "/Users/username/tooluniverse-env",
           "run",
           "tooluniverse-smcp-stdio",
           "--compact-mode"
         ]
       }
     }
   }
   ```

4. **Test**
   ```bash
   python scripts/test_mcp_connection.py
   ```

## Example 7: Python Version Incompatibility

**User Request**: "Getting error about Python version"

**Agent Response**:

1. **Check Version**
   ```bash
   python3 --version
   # Output: Python 3.9.7
   ```
   
   **Problem**: ToolUniverse requires 3.10-3.13

2. **Install Compatible Python**
   
   macOS:
   ```bash
   brew install python@3.12
   ```
   
   Ubuntu:
   ```bash
   sudo apt install python3.12 python3.12-pip
   ```

3. **Install with Specific Version**
   ```bash
   python3.12 -m pip install tooluniverse
   ```

4. **Update MCP Config**
   
   If needed, specify Python version:
   ```json
   {
     "mcpServers": {
       "tooluniverse": {
         "command": "python3.12",
         "args": [
           "-m",
           "tooluniverse.smcp_server",
           "--compact-mode"
         ]
       }
     }
   }
   ```

## Example 8: Windows Setup

**User Request**: "Setting up on Windows 11"

**Agent Response**:

1. **Check Prerequisites** (PowerShell)
   ```powershell
   python --version
   # Should show 3.10-3.13
   
   pip --version
   ```

2. **Install ToolUniverse**
   ```powershell
   pip install tooluniverse
   ```

3. **Find Config Location**
   ```
   %APPDATA%\Cursor\User\mcp.json
   ```

4. **Create Config**
   ```json
   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": ["--compact-mode"]
       }
     }
   }
   ```

5. **Test** (PowerShell)
   ```powershell
   python scripts/verify_installation.py
   ```

## Example 9: API Keys Configuration

**User Request**: "Some tools need API keys, how do I configure them?"

**Agent Response**:

1. **Check Which Tools Need Keys**
   
   Most tools don't need API keys. Optional ones:
   - OpenAI/Anthropic: For agentic tools
   - UMLS: For medical terminology

2. **Configure via Environment**
   
   Create `.env` file in project:
   ```bash
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   UMLS_API_KEY=your-key
   ```

3. **Or Configure in MCP**
   
   In `mcp.json`:
   ```json
   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": ["--compact-mode"],
         "env": {
           "OPENAI_API_KEY": "sk-...",
           "UMLS_API_KEY": "your-key"
         }
       }
     }
   }
   ```

**Security Note**: Don't commit API keys to git!

## Example 10: Complete Fresh Setup

**User Request**: "Walk me through complete setup from scratch"

**Agent Response**:

```bash
# 1. Check prerequisites
cd ~/.cursor/skills/setup-tooluniverse
python scripts/check_prerequisites.py

# 2. Install ToolUniverse
pip install tooluniverse

# 3. Verify installation
python scripts/verify_installation.py

# 4. Create MCP config
cat > ~/Library/Application\ Support/Cursor/User/mcp.json << 'EOF'
{
  "mcpServers": {
    "tooluniverse": {
      "command": "tooluniverse-smcp-stdio",
      "args": ["--compact-mode"]
    }
  }
}
EOF

# 5. Test configuration
python scripts/test_mcp_connection.py

# 6. Restart Cursor (manual step)

# 7. Verify in Cursor
# - Check MCP servers list
# - Try: list_tools
# - Try: grep_tools with keyword "protein"
```

**Expected Timeline**: 5-10 minutes total

## Common Error Messages and Solutions

### "Command not found: tooluniverse-smcp-stdio"

**Solution**: Scripts directory not in PATH
```bash
pip install --force-reinstall tooluniverse
# or add to PATH: export PATH="$HOME/.local/bin:$PATH"
```

### "requires-python = '>=3.10'"

**Solution**: Python version too old
```bash
# Install compatible Python
brew install python@3.12  # macOS
# or download from python.org
```

### "ModuleNotFoundError: No module named 'tooluniverse'"

**Solution**: Not installed or wrong Python
```bash
# Verify installation
pip show tooluniverse

# If not installed
pip install tooluniverse
```

### "Context window overflow" or slow performance

**Solution**: Enable compact mode
```json
"args": ["--compact-mode"]  // Add to mcp.json
```

### "Directory not found" (uv configs)

**Solution**: Create directory
```bash
mkdir -p ~/tooluniverse-env
cd ~/tooluniverse-env
uv pip install tooluniverse
```
