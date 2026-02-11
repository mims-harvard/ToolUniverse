# Configuration file for Sphinx documentation with Shibuya theme.
# Modern, elegant theme with excellent sidebar navigation and i18n support

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------
project = "ToolUniverse"
copyright = "2025, Shanghua Gao"
author = "Shanghua Gao"
release = "1.0.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx.ext.githubpages",
    "sphinx.ext.autosummary",
    "sphinx.ext.autosectionlabel",
    "myst_parser",
    "sphinx_copybutton",
    # "sphinx_tabs.tabs",  # Temporarily disabled due to Sphinx 9.x compatibility issue
    "sphinx_design",
    # "notfound.extension",  # Temporarily disabled due to theme compatibility issue
]

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "old_files",
    "old",  # Exclude backup documentation

    "tutorials/aiscientists",
    "translation_tools",
    "tutorials/overview.md",
    "tutorials/optimization",
    "guide/ODPHPtools_tutorial.md",
]

# -- Options for HTML output with Shibuya theme -----------------------------
html_theme = "shibuya"
html_static_path = ["_static"]

# -- Shibuya theme configuration --------------------------------------------
html_theme_options = {
    # Navigation
    "nav_links": [
        {
            "title": "🏠 Home",
            "url": "index",
        },
        {
            "title": "💻 Python",
            "url": "guide/python_guide",
        },
        {
            "title": "📖 Tutorials",
            "url": "guide/index",
        },
        {
            "title": "🤖 AI Agents",
            "url": "guide/building_ai_scientists/index",
        },
        {
            "title": "🔧 Tools",
            "url": "tools/tools_config_index",
        },
        {
            "title": "🎯 Contribution",
            "url": "expand_tooluniverse/index",
        },
        {
            "title": "📚 API",
            "url": "api/modules",
        },
        {
            "title": "🔑 API Keys",
            "url": "guide/api_keys",
        },
    ],
    
    # GitHub integration
    "github_url": "https://github.com/mims-harvard/ToolUniverse",
    
    # Design options
    "page_layout": "default",
    "color_mode": "auto",  # auto, light, dark
    "accent_color": "blue",
    
    # Logo configuration
    "light_logo": "_static/logo.png",
    "dark_logo": "_static/logo.png",
    
    # Sidebar configuration
    "globaltoc_expand_depth": 2,    # Expand 2 levels by default
    "toctree_collapse": True,       # Allow collapsing sections
    "toctree_titles_only": False,   # Show full navigation including children
    "toctree_includehidden": True,  # Include hidden toctrees in navigation
    
    # Social links (disabled)
    "twitter_site": "",
    "twitter_creator": "",
    "twitter_url": "",
    "discord_url": "",
    "discussion_url": "",
    
    # Carbon ads (disabled)
    "carbon_ads_code": "",
    "carbon_ads_placement": "",
    
    # Ethical ads (disabled)
    "ethical_ads_publisher": "",
}

# HTML options
html_title = f"{project} Documentation"
html_short_title = project
html_logo = "_static/logo.png" if os.path.exists("_static/logo.png") else None
html_favicon = "_static/logo_transparent.png" if os.path.exists("_static/logo_transparent.png") else None

# Let Shibuya use its default sidebar layout
# Left sidebar: global navigation (from toctree, titles only)
# Right sidebar: page TOC (in-page sections) - handled automatically by Shibuya

# Custom CSS
html_css_files = [
    "custom.css",
    "language_switcher.css",
    "custom_modern.css",  # Modern interactive styles
]

# Custom JavaScript
html_js_files = [
    "language_switcher.js",
    "sidebar_control.js",  # Custom per-section sidebar expansion control
]

# -- Autodoc configuration ---------------------------------------------------
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
    "show-inheritance": True,
}

# Skip problematic modules that have import issues or blocking operations
autodoc_mock_imports = [
    "flask_cors",
    "tooluniverse.web_tools.literature_search_ui",
    "tooluniverse.visualization_tool",
    "tooluniverse.tool_graph_web_ui",
    "tooluniverse.web_search_tool",
]

autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"
autodoc_class_signature = "separated"
autodoc_member_order = "bysource"

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True
napoleon_type_aliases = None
napoleon_attr_annotations = True

# MyST Parser settings
myst_enable_extensions = [
    "dollarmath",
    "amsmath",
    "deflist",
    "html_admonition",
    "html_image",
    "colon_fence",
    "attrs_inline",
    "attrs_block",
    # "linkify",  # Disabled - requires linkify-it-py
]

# Todo extension settings
todo_include_todos = True

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "requests": ("https://docs.python-requests.org/en/latest/", None),
}

# Sphinx-copybutton settings
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# Autosummary settings
autosummary_generate = True
autosummary_imported_members = True

# Autosectionlabel settings
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 2  # Don't label deep sections in docstrings

# Source file suffixes
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Master document
master_doc = "index"

# HTML options
html_show_sourcelink = True
html_show_sphinx = False
html_show_copyright = True

# Language and search
language = "en"
html_search_language = "en"

# Syntax highlighting
pygments_style = "default"
pygments_dark_style = "monokai"

# -- Internationalization (i18n) support -------------------------------------
locale_dirs = ["locale/"]
gettext_compact = False
gettext_uuid = True
gettext_location = True
gettext_auto_build = True

# Supported languages for version switcher
languages = {
    "en": "English",
    "zh_CN": "简体中文",
}

# -- Enhanced setup function -------------------------------------------------
def setup(app):
    """Custom Sphinx setup function."""
    app.add_css_file("custom.css")
    
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
