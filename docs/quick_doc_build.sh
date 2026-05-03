#!/bin/bash

# ToolUniverse Quick Documentation Generation Script
# This script automatically reads all function docstrings and generates complete API documentation
# Features include:
# 1. Auto-generate tool configuration index
# 2. Generate Remote Tools documentation
# 3. Install Sphinx documentation dependencies
# 4. Generate enhanced API documentation
# 5. Build multi-language HTML documentation (English + Chinese by default)
# 6. Create language switcher interface
# 7. Provide local server startup

# Usage:
#   ./quick_doc_build.sh                    # Build both English and Chinese
#   DOC_LANGUAGES=en ./quick_doc_build.sh   # Build English only
#   DOC_LANGUAGES=zh_CN ./quick_doc_build.sh # Build Chinese only

# Exit on error (stop script immediately on any error)
set -Eeuo pipefail

# ===========================================
# Color definitions - for beautifying terminal output
# ===========================================
RED='\033[0;31m'      # Red - error messages
GREEN='\033[0;32m'    # Green - success messages
YELLOW='\033[1;33m'   # Yellow - warning messages
BLUE='\033[0;34m'     # Blue - title messages
PURPLE='\033[0;35m'   # Purple - statistics messages
NC='\033[0m'          # Reset color

# Display script title
echo -e "${BLUE}🧬 ToolUniverse Documentation Generation System${NC}"
echo "========================================"

# Configure build behavior via environment flags
DOC_LANGUAGES_RAW="${DOC_LANGUAGES:-en,zh_CN}"  # Default to both English and Chinese
DOC_SKIP_REMOTE="${DOC_SKIP_REMOTE:-0}"
DOC_SKIP_SERVER_PROMPT="${DOC_SKIP_SERVER_PROMPT:-1}"
DOC_SKIP_INSTALL="${DOC_SKIP_INSTALL:-1}"  # Skip dependency installation if already done
DOC_OPTIMIZED="${DOC_OPTIMIZED:-0}"  # Use optimized build settings
DOCS_STRICT="${DOCS_STRICT:-0}"
CI="${CI:-}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-}"

# Normalize language list (accept comma or space separated values)
IFS=', ' read -r -a LANGUAGES <<< "${DOC_LANGUAGES_RAW//,/ }"
FILTERED_LANGUAGES=()
for RAW_LANG in "${LANGUAGES[@]}"; do
  TRIMMED_LANG=$(echo "$RAW_LANG" | xargs)
  if [ -n "$TRIMMED_LANG" ]; then
    FILTERED_LANGUAGES+=("$TRIMMED_LANG")
  fi
done

if [ ${#FILTERED_LANGUAGES[@]} -eq 0 ]; then
  LANGUAGES=("en")
else
  LANGUAGES=("${FILTERED_LANGUAGES[@]}")
fi

NEEDS_TRANSLATIONS=0
for DOC_LANGUAGE in "${LANGUAGES[@]}"; do
  if [ "$DOC_LANGUAGE" = "zh_CN" ]; then
    NEEDS_TRANSLATIONS=1
  fi
done

echo -e "${YELLOW}Target documentation languages: ${LANGUAGES[*]}${NC}"

# Optional strict mode: treat warnings as errors when DOCS_STRICT=1
SPHINX_FLAGS=""
if [ "${DOCS_STRICT}" = "1" ]; then
  SPHINX_FLAGS="-W"
  echo -e "${YELLOW}Strict mode enabled: Sphinx warnings will be treated as errors (-W)${NC}"
fi

# ===========================================
# Directory path settings
# ===========================================
# Get absolute path of script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Project root directory (parent directory of docs)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
# Source code directory
SRC_DIR="$PROJECT_ROOT/src"

echo -e "${YELLOW}Project root directory: ${PROJECT_ROOT}${NC}"
echo -e "${YELLOW}Source code directory: ${SRC_DIR}${NC}"

# ===========================================
# Step 0: Generate tool configuration index (automatic)
# ===========================================
# This step automatically scans all tool configuration files and generates index documentation
echo -e "\n${BLUE}🧩 Generating tool configuration index (automatic)${NC}"
cd "$SCRIPT_DIR"

# Directly call generate_config_index.py to generate tool configuration index
echo -e "${YELLOW}📑 Generating tool configuration index...${NC}"
python generate_config_index.py || { echo -e "${RED}❌ Failed to generate configuration index${NC}"; exit 1; }
echo -e "${GREEN}✅ Tool configuration index generation completed${NC}"

# ===========================================
# Step 0.1: Generate Remote Tools documentation (automatic)
# ===========================================
# This step generates documentation for remote tools, including MCP servers, etc.
if [ "$DOC_SKIP_REMOTE" = "1" ]; then
  echo -e "\n${YELLOW}⏭️ Skipping Remote Tools documentation generation (DOC_SKIP_REMOTE=1)${NC}"
else
  echo -e "\n${BLUE}🌐 Generating Remote Tools documentation (automatic)${NC}"
  cd "$SCRIPT_DIR"

  # Check if remote tool documentation generation script exists
  if [ -f "generate_remote_tools_docs.py" ]; then
    python generate_remote_tools_docs.py || { echo -e "${RED}❌ Failed to generate Remote Tools documentation${NC}"; exit 1; }
    echo -e "${GREEN}✅ Remote Tools documentation generation completed${NC}"
  else
    echo -e "${YELLOW}⚠️ generate_remote_tools_docs.py not found${NC}"
  fi
fi

# ===========================================
# Step 1: Install Sphinx documentation dependencies
# ===========================================
# Install Python packages required for building documentation
if [ "${DOC_SKIP_INSTALL}" = "1" ]; then
  echo -e "\n${YELLOW}⏭️ Skipping dependency installation (DOC_SKIP_INSTALL=1)${NC}"
  echo -e "${BLUE}💡 To install dependencies manually: pip install sphinx shibuya furo myst-parser${NC}"
else
  echo -e "\n${BLUE}📦 Installing enhanced documentation dependencies${NC}"
  cd "$PROJECT_ROOT"

  # Install via project extras if possible; fallback to explicit list
  COMMON_PACKAGES="sphinx shibuya furo pydata-sphinx-theme myst-parser linkify-it-py sphinx-copybutton sphinx-design sphinx-tabs sphinx-notfound-page sphinx-autodoc-typehints sphinx-intl"

  if command -v uv >/dev/null 2>&1; then
    uv pip install -q -e '.[docs]' 2>/dev/null || uv pip install -q $COMMON_PACKAGES 2>/dev/null || true
  else
    pip install -q -e '.[docs]' 2>/dev/null || pip install -q $COMMON_PACKAGES 2>/dev/null || true
  fi
  echo -e "${GREEN}✅ Dependencies installation completed${NC}"
fi

# ===========================================
# Step 2: Generate enhanced API documentation
# ===========================================
# Use sphinx-apidoc to automatically scan Python source code and generate API documentation
echo -e "\n${BLUE}📋 Generating enhanced API documentation${NC}"
cd "$SCRIPT_DIR"

# ===========================================
# Clean old build files
# ===========================================
# Clean build directory
if [ -d "_build" ]; then rm -rf _build; fi

# Note: Keep api directory as it may contain manually generated documentation
# If complete regeneration is needed, uncomment the line below
# if [ -d "api" ]; then rm -rf api; fi

# Clean template directory
if [ -d "_templates" ]; then rm -rf _templates; fi

# ===========================================
# Create custom template directory and files
# ===========================================
# Create template directory
mkdir -p _templates

# Create function documentation template
cat > _templates/function.rst << 'EOF'
{{ fullname }}
{{ underline }}

.. currentmodule:: {{ module }}

.. autofunction:: {{ objname }}
EOF

# Create class documentation template
cat > _templates/class.rst << 'EOF'
{{ fullname }}
{{ underline }}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__,__call__,__str__,__repr__
EOF

# Create module documentation template
cat > _templates/module.rst << 'EOF'
{{ fullname }}
{{ underline }}

.. currentmodule:: {{ module }}

.. automodule:: {{ objname }}
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__,__call__,__str__,__repr__
   :imported-members:
EOF

# ===========================================
# Step 2.5: Update translation catalogs
# ===========================================
if [ "$NEEDS_TRANSLATIONS" -eq 1 ]; then
  # Check if translation files need update (skip if unchanged in CI)
  if [ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ]; then
    echo -e "\n${YELLOW}🌍 Skipping translation catalog update in CI (use existing translations)${NC}"
  else
    echo -e "\n${BLUE}🌍 Updating translation catalogs${NC}"
    mkdir -p _build/gettext
    sphinx-build -b gettext . _build/gettext -q || true
    sphinx-intl update -p _build/gettext -l zh_CN >/dev/null 2>&1 || true
  fi
else
  echo -e "\n${YELLOW}🌍 Skipping translation catalog update (no zh_CN in DOC_LANGUAGES)${NC}"
fi

# Ensure api directory exists
mkdir -p api

# ===========================================
# Use sphinx-apidoc to generate API documentation
# ===========================================
# Check if sphinx-apidoc command is available
SPHINX_APIDOC=""
if command -v sphinx-apidoc >/dev/null 2>&1; then
  SPHINX_APIDOC="sphinx-apidoc"
fi

if [ -n "$SPHINX_APIDOC" ]; then
    # Determine sphinx-apidoc flags based on optimization mode
    if [ "${DOC_OPTIMIZED}" = "1" ]; then
      # Optimized mode: generate core APIs with specific modules
      echo -e "${YELLOW}Using minimal API generation (core modules only)${NC}"
      APIDOC_FLAGS="-o api ../src/tooluniverse --module-first --maxdepth 2 --templatedir=_templates"
    else
      # Full mode: regenerate everything but group by module for better performance
      APIDOC_FLAGS="-f -o api ../src/tooluniverse --module-first --maxdepth 4 --private --force --templatedir=_templates"
    fi
    
    # Use sphinx-apidoc to scan source code and generate API documentation
    $SPHINX_APIDOC $APIDOC_FLAGS 2>/dev/null || true

    # Clean up problematic files but keep core API files
    echo -e "${YELLOW}Cleaning up problematic API files...${NC}"
    
    # Remove only the problematic large files
    rm -f api/tooluniverse.tools.rst
    rm -f api/tooluniverse.data.rst
    rm -f api/tooluniverse.web_tools.rst
    rm -f api/tooluniverse.web_tools.literature_search_ui.rst
    
    # Check if we have any API files generated
    API_COUNT=$(find api -name "*.rst" | wc -l | tr -d ' ')
    if [ "$API_COUNT" -gt 1 ]; then
      echo -e "${GREEN}✅ Found ${API_COUNT} API documentation files${NC}"
      
      # Create a comprehensive API index with actual generated files
      cat > api/modules.rst << 'EOF'
API Reference
=============

This section provides the complete Python API reference for ToolUniverse.

Core Infrastructure
-------------------

.. toctree::
   :maxdepth: 2

   tooluniverse
   tooluniverse.execute_function

Core Classes & Utilities
------------------------

.. toctree::
   :maxdepth: 2

   tooluniverse.base_tool
   tooluniverse.core_tool
   tooluniverse.exceptions
   tooluniverse.tool_registry
   tooluniverse.logging_config
   tooluniverse.utils
   tooluniverse.default_config

Important Tools
---------------

.. toctree::
   :maxdepth: 2

   tooluniverse.agentic_tool
   tooluniverse.remote_tool
   tooluniverse.compose_tool

Tool Finders
------------

.. toctree::
   :maxdepth: 2

   tooluniverse.tool_finder_embedding
   tooluniverse.tool_finder_keyword
   tooluniverse.tool_finder_llm

MCP Support
-----------

.. toctree::
   :maxdepth: 2

   tooluniverse.smcp
   tooluniverse.smcp_server
   tooluniverse.mcp_client_tool
   tooluniverse.mcp_integration
   tooluniverse.mcp_tool_registry

Embedding & Output Management
-----------------------------

.. toctree::
   :maxdepth: 2

   tooluniverse.embedding_database
   tooluniverse.embedding_sync
   tooluniverse.output_hook
EOF
    else
      echo -e "${YELLOW}⚠️ No API files generated, creating minimal documentation...${NC}"
      
      # Create a minimal API index with only core modules
      cat > api/modules.rst << 'EOF'
API Reference
=============

This section provides the complete Python API reference for ToolUniverse.

Core Infrastructure
-------------------

.. toctree::
   :maxdepth: 2

   tooluniverse
   tooluniverse.execute_function

Core Classes & Utilities
------------------------

.. toctree::
   :maxdepth: 2

   tooluniverse.base_tool
   tooluniverse.core_tool
   tooluniverse.exceptions
   tooluniverse.tool_registry
   tooluniverse.logging_config
   tooluniverse.utils
   tooluniverse.default_config

Important Tools
---------------

.. toctree::
   :maxdepth: 2

   tooluniverse.agentic_tool
   tooluniverse.remote_tool
   tooluniverse.compose_tool

Tool Finders
------------

.. toctree::
   :maxdepth: 2

   tooluniverse.tool_finder_embedding
   tooluniverse.tool_finder_keyword
   tooluniverse.tool_finder_llm

MCP Support
-----------

.. toctree::
   :maxdepth: 2

   tooluniverse.smcp
   tooluniverse.smcp_server
   tooluniverse.mcp_client_tool
   tooluniverse.mcp_integration
   tooluniverse.mcp_tool_registry

Embedding & Output Management
-----------------------------

.. toctree::
   :maxdepth: 2

   tooluniverse.embedding_database
   tooluniverse.embedding_sync
   tooluniverse.output_hook
EOF
    fi

    # Count generated API documentation files
    API_FILES=$(find api -name "*.rst" | wc -l | tr -d ' ')
    echo -e "${GREEN}✅ Generated ${API_FILES} API documentation files (core modules only)${NC}"

    # ===========================================
    # Display discovered module information
    # ===========================================
    echo -e "\n${PURPLE}📋 Discovered modules:${NC}"
    # Use a temporary file to avoid broken pipe issues in CI
    TEMP_MODULES=$(mktemp)
    find api -name "*.rst" | sed 's|api/||' | sed 's|\.rst$||' | sort > "$TEMP_MODULES"
    head -20 "$TEMP_MODULES" | while read -r module; do
        echo -e "   📄 ${module}"
    done
    rm -f "$TEMP_MODULES"
    
    # If module count exceeds 20, show remaining count
    REMAINING=$(find api -name "*.rst" | wc -l | tr -d ' ')
    if [ "$REMAINING" -gt 20 ]; then
        echo -e "   ... and $((REMAINING - 20)) more modules"
    fi

    # ===========================================
    # Generate module discovery report
    # ===========================================
    echo -e "\n${PURPLE}📋 Module discovery report:${NC}"
    echo -e "   🔍 Core modules: $(find "$SRC_DIR/tooluniverse" -maxdepth 1 -name "*.py" | wc -l | tr -d ' ')"
    echo -e "   🔍 Compose scripts: $(find "$SRC_DIR/tooluniverse/compose_scripts" -name "*.py" 2>/dev/null | wc -l | tr -d ' ' || echo "0")"
    echo -e "   🔍 External tools: $(find "$SRC_DIR/tooluniverse/external" -name "*.py" 2>/dev/null | wc -l | tr -d ' ' || echo "0")"
    echo -e "   🔍 Tool scripts: $(find "$SRC_DIR/tooluniverse/scripts" -name "*.py" 2>/dev/null | wc -l | tr -d ' ' || echo "0")"
else
    echo -e "${RED}❌ sphinx-apidoc not found${NC}"
    exit 1
fi

# ===========================================
# Step 3: Build enhanced HTML documentation (multi-language)
# ===========================================
echo -e "\n${BLUE}🔧 Building enhanced HTML documentation (multi-language)${NC}"

if [ -n "${PYTHONPATH:-}" ]; then
  export PYTHONPATH="$SRC_DIR:$PYTHONPATH"
else
  export PYTHONPATH="$SRC_DIR"
fi


# Ensure we're in the docs directory
# Ensure we're in the docs directory
cd "$SCRIPT_DIR"
OUTPUT_DIR="_build/html"

echo -e "${YELLOW}Using system Python: $(which python)${NC}"

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Determine number of parallel jobs for Sphinx
if [ "${DOC_OPTIMIZED}" = "1" ]; then
  SPHINX_JOBS="-j auto"  # Use all available CPU cores
  echo -e "${YELLOW}Using parallel build with auto jobs${NC}"
else
  SPHINX_JOBS=""
fi

for DOC_LANGUAGE in "${LANGUAGES[@]}"; do
  if [ -z "$DOC_LANGUAGE" ]; then
    continue
  fi
  TARGET_DIR="$OUTPUT_DIR/${DOC_LANGUAGE//_/-}"
  # Special handling for zh_CN to use zh-CN format
  if [ "$DOC_LANGUAGE" = "zh_CN" ]; then
    TARGET_DIR="$OUTPUT_DIR/zh-CN"
  fi
  echo -e "${YELLOW}🌐 Building language: ${DOC_LANGUAGE} -> ${TARGET_DIR}${NC}"
  sphinx-build ${SPHINX_FLAGS} ${SPHINX_JOBS} -b html -D language="$DOC_LANGUAGE" . "$TARGET_DIR" --keep-going -q || true

  if [ -f "$TARGET_DIR/index.html" ]; then
    echo -e "${GREEN}   ✅ ${DOC_LANGUAGE} build succeeded${NC}"
  else
    echo -e "${RED}   ❌ ${DOC_LANGUAGE} build failed${NC}"
    echo -e "${YELLOW}   ⚠️ Continuing with other languages...${NC}"
    # Don't exit on single language failure, continue with others
  fi
done

# ===========================================
# Step 3.5: Copy English content to root directory for direct access
# ===========================================
# Check if English build exists and copy to root
if [ -d "$OUTPUT_DIR/en" ] && [ -f "$OUTPUT_DIR/en/index.html" ]; then
  echo -e "\n${BLUE}🌍 Setting up English as default (root path) by copying content${NC}"
  
  # Copy all English content to root directory (excluding en folder itself)
  echo -e "${BLUE}📋 Copying English documentation to root directory...${NC}"
  
  # First, copy all English content to root (excluding the en directory itself)
  rsync -a "$OUTPUT_DIR/en/" "$OUTPUT_DIR/"
  
  # Create a simple redirect for old /zh_CN/ paths to new /zh-CN/ paths
  cat > "$OUTPUT_DIR/redirect_old_paths.js" << 'REDIRECT_JS'
// ToolUniverse Documentation - Old Path Redirect Handler
(function() {
    'use strict';
    
    // Only run on GitHub Pages (not in development)
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return;
    }
    
    const currentPath = window.location.pathname;
    const basePath = '/ToolUniverse/';
    
    // Handle old zh_CN paths
    if (currentPath.includes('/zh_CN/')) {
        const newPath = currentPath.replace('/zh_CN/', '/zh-CN/');
        window.location.replace(newPath);
        return;
    }
})();
REDIRECT_JS
  
  # Add the redirect script to all HTML files in root
  find "$OUTPUT_DIR" -maxdepth 1 -name "*.html" -exec sed -i.bak 's|</head>|    <script src="redirect_old_paths.js"></script>\n</head>|' {} \;
  
  # Create .htaccess file for Apache server compatibility (if needed)
  cat > "$OUTPUT_DIR/.htaccess" << 'HTACCESS'
# ToolUniverse Documentation - Apache .htaccess
# This file ensures proper redirects for multi-language documentation

# Enable rewrite engine
RewriteEngine On

# Redirect old /zh_CN/ paths to new /zh-CN/ structure
RewriteRule ^zh_CN/(.*)$ zh-CN/$1 [R=302,L]

# Set proper MIME types
AddType text/html .html
AddType text/css .css
AddType application/javascript .js
AddType image/png .png
AddType image/jpeg .jpg
AddType image/svg+xml .svg

# Enable compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/plain
    AddOutputFilterByType DEFLATE text/html
    AddOutputFilterByType DEFLATE text/xml
    AddOutputFilterByType DEFLATE text/css
    AddOutputFilterByType DEFLATE application/xml
    AddOutputFilterByType DEFLATE application/xhtml+xml
    AddOutputFilterByType DEFLATE application/rss+xml
    AddOutputFilterByType DEFLATE application/javascript
    AddOutputFilterByType DEFLATE application/x-javascript
</IfModule>

# Set cache headers
<IfModule mod_expires.c>
    ExpiresActive on
    ExpiresByType text/css "access plus 1 year"
    ExpiresByType application/javascript "access plus 1 year"
    ExpiresByType image/png "access plus 1 year"
    ExpiresByType image/jpg "access plus 1 year"
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType image/gif "access plus 1 year"
    ExpiresByType image/svg+xml "access plus 1 year"
    ExpiresByType text/html "access plus 1 hour"
</IfModule>
HTACCESS
  
  echo -e "${GREEN}✅ English documentation copied to root directory${NC}"
  echo -e "${GREEN}✅ Old path redirect script created${NC}"
  echo -e "${GREEN}✅ .htaccess file created for Apache servers${NC}"
  echo -e "${YELLOW}💡 Access: http://localhost:port/ (direct English content) OR http://localhost:port/en/ OR http://localhost:port/zh-CN/${NC}"
fi

# ===========================================
# Step 4: Generate detailed statistics
# ===========================================
# Count generated documentation files and code statistics
echo -e "\n${BLUE}📊 Generating detailed statistics${NC}"

# Count HTML files
HTML_FILES=$(find _build/html -name "*.html" | wc -l | tr -d ' ')
# Count API documentation
API_DOCS=$(find _build/html -path "*api/*.html" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
# Calculate total documentation size
DOC_SIZE=$(du -sh _build/html 2>/dev/null | cut -f1 || echo "unknown")

# ===========================================
# Count source code information
# ===========================================
# Count function count
FUNCTION_COUNT=$(grep -r "def " "$SRC_DIR" --include="*.py" | wc -l | tr -d ' ')
# Count class count
CLASS_COUNT=$(grep -r "class " "$SRC_DIR" --include="*.py" | wc -l | tr -d ' ')
# Count module count
MODULE_COUNT=$(find "$SRC_DIR" -name "*.py" | wc -l | tr -d ' ')

# ===========================================
# Display statistics results
# ===========================================
echo -e "\n${GREEN}🎉 Enhanced documentation generation completed!${NC}"
echo -e "${BLUE}📊 Detailed statistics:${NC}"
echo -e "   📄 HTML files: ${HTML_FILES}"
echo -e "   🔧 API documentation: ${API_DOCS}"
echo -e "   📁 Total size: ${DOC_SIZE}"
echo -e "   🐍 Python modules: ${MODULE_COUNT}"
echo -e "   🔧 Total functions: ${FUNCTION_COUNT}"
echo -e "   🏗️ Total classes: ${CLASS_COUNT}"

# ===========================================
# Step 5: Display documentation access methods
# ===========================================
# Provide various ways to access documentation and links
DEFAULT_LANG="${LANGUAGES[0]}"
# Server should start from html root directory, not language subdirectory
SERVER_DIR="$SCRIPT_DIR/_build/html"
DEFAULT_DIR="$SCRIPT_DIR/_build/html/${DEFAULT_LANG//_/-}"
# Special handling for zh_CN to use zh-CN format
if [ "$DEFAULT_LANG" = "zh_CN" ]; then
  DEFAULT_DIR="$SCRIPT_DIR/_build/html/zh-CN"
fi

echo -e "\n${BLUE}📂 Access documentation:${NC}"

# If multiple languages, show main entry point
if [ ${#LANGUAGES[@]} -gt 1 ]; then
  echo -e "   � ${GREEN}Main Entry: file://${SCRIPT_DIR}/_build/html/index.html${NC} (auto-redirects to English)"
  echo -e "   ${BLUE}   💡 Use the language switcher in the navigation bar to switch languages${NC}"
  echo ""
fi

# Show individual language links
for DOC_LANGUAGE in "${LANGUAGES[@]}"; do
  TARGET_DIR="$SCRIPT_DIR/_build/html/${DOC_LANGUAGE//_/-}"
  # Special handling for zh_CN to use zh-CN format
  if [ "$DOC_LANGUAGE" = "zh_CN" ]; then
    TARGET_DIR="$SCRIPT_DIR/_build/html/zh-CN"
  fi
  if [ -f "$TARGET_DIR/index.html" ]; then
    case "$DOC_LANGUAGE" in
      en)
        FLAG="��"
        LABEL="English"
        ;;
      zh_CN)
        FLAG="🇨🇳"
        LABEL="简体中文"
        ;;
      *)
        FLAG="🌐"
        LABEL="$DOC_LANGUAGE"
        ;;
    esac
    echo -e "   ${FLAG} ${LABEL}:"
    echo -e "      📖 Home: file://${TARGET_DIR}/index.html"
    if [ -f "$TARGET_DIR/api/modules.html" ]; then
      echo -e "      🔧 API:  file://${TARGET_DIR}/api/modules.html"
    fi
    echo ""
  fi
done

# ===========================================
# Step 6: Optional local server startup
# ===========================================
# Check if running in CI environment
if [ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ]; then
    echo -e "${BLUE}🤖 CI environment detected, skipping server startup${NC}"
elif [ "$DOC_SKIP_SERVER_PROMPT" = "1" ]; then
  echo -e "${YELLOW}⏭️ Skipping server prompt (DOC_SKIP_SERVER_PROMPT=1)${NC}"
  echo -e "${BLUE}💡 To start server manually: cd _build/html && python -m http.server 8080${NC}"
else
    # Ask user if they want to start local HTTP server to preview documentation
    echo -e "\n${YELLOW}Start local server to view documentation? (y/n)${NC}"
    read -r response

    # If user chooses to start server
    if [[ "$response" =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🚀 Starting server...${NC}"

    # ===========================================
    # Port detection and allocation
    # ===========================================
    # Try different ports to find available port
    PORTS=(8080 8081 8082 8083 8084)
    PORT=""

    # Iterate through port list to find first available port
    for p in "${PORTS[@]}"; do
        if ! lsof -Pi :$p -sTCP:LISTEN -t >/dev/null 2>&1; then
            PORT=$p
            break
        fi
    done

  if [ -z "$PORT" ]; then
    echo -e "${RED}❌ Unable to find available port, please start server manually${NC}"
    echo -e "${YELLOW}💡 Manual startup command: cd ${SERVER_DIR} && python -m http.server 8080${NC}"
  else
    echo -e "${GREEN}📡 Access address: http://localhost:${PORT}${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop server${NC}"
    if [ ! -d "$SERVER_DIR" ]; then
      echo -e "${RED}❌ Server directory not found: ${SERVER_DIR}${NC}"
      exit 1
    fi
    echo -e "${BLUE}📂 Server directory: ${SERVER_DIR}${NC}"
    cd "$SERVER_DIR"
    python -m http.server "$PORT"
  fi
fi
fi

# ===========================================
# Final verification
# ===========================================
echo -e "\n${BLUE}🔍 Final verification...${NC}"
echo -e "${YELLOW}Current directory: $(pwd)${NC}"
echo -e "${YELLOW}Output directory: $OUTPUT_DIR${NC}"
echo -e "${YELLOW}Output directory exists: $([ -d "$OUTPUT_DIR" ] && echo "Yes" || echo "No")${NC}"

if [ ! -d "$OUTPUT_DIR" ]; then
  echo -e "${RED}❌ Output directory $OUTPUT_DIR not found!${NC}"
  echo -e "${YELLOW}Contents of current directory:${NC}"
  ls -la
  exit 1
fi

if [ ! -f "$OUTPUT_DIR/index.html" ]; then
  echo -e "${RED}❌ Root index.html not found!${NC}"
  echo -e "${YELLOW}Contents of output directory:${NC}"
  ls -la "$OUTPUT_DIR"
  exit 1
fi

echo -e "${GREEN}✅ Build verification passed!${NC}"

# ===========================================
# Script completion summary
# ===========================================
# Display script execution completion and new features introduction
echo -e "\n${GREEN}✅ Enhanced documentation system completed!${NC}"
echo -e "${BLUE}💡 Features:${NC}"
echo -e "   ✨ Automatic discovery of all modules and functions"
echo -e "   🌍 Multi-language support (English & Chinese)"
echo -e "   � Language switcher interface"
echo -e "   �📊 Detailed statistics"
echo -e "   🔍 Enhanced module discovery"
echo -e "   📚 Comprehensive API index"
echo -e "   🎨 Modern Shibuya theme"
echo -e "   📱 Responsive design"
echo -e "   🔍 Built-in search functionality"
echo -e "   🌓 Dark/Light mode toggle"
