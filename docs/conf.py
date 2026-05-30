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
    "sphinx_tabs.tabs",
    "sphinx_design",
    # "notfound.extension",  # Temporarily disabled due to theme compatibility issue
    "sphinx_reredirects",
]

# HTML redirects for paths that moved during a docs reshuffle.
# Old path → new path. The ToolUniverse paper and external blog posts cite
# legacy URLs from before the docs were reorganised. Without these redirects
# every cited URL 404s. Each entry was verified against the live site:
# the destination must already return HTTP 200.
redirects = {
    # /tutorials/* → /guide/*
    "tutorials/tooluniverse_case_study": "../guide/tooluniverse_case_study.html",
    "tutorials/agentic_tools_tutorial": "../guide/agentic_tools_tutorial.html",
    "tutorials/literature_search_tools_tutorial": "../guide/literature_search_tools_tutorial.html",
    "tutorials/literature_search_web_ui_tutorial": "../guide/literature_search_web_ui_tutorial.html",
    "tutorials/visualization_tutorial": "../guide/visualization_tutorial.html",
    "tutorials/expert_feedback": "../guide/expert_feedback.html",
    "tutorials/finding_tools": "../guide/finding_tools.html",
    "tutorials/make_your_data_searchable": "../guide/make_your_data_agent_searchable.html",
    "tutorials/make_your_data_agent_searchable": "../guide/make_your_data_agent_searchable.html",
    "tutorials/build_search_and_share_datastores": "../guide/make_your_data_agent_searchable.html",
    "tutorials/skills": "../guide/skills_showcase.html",
    "tutorials/tool_finder": "../guide/finding_tools.html",
    "tutorials/overview": "../guide/index.html",
    # /tutorials/* → /tools/* and /expand_tooluniverse/*
    "tutorials/remote_tools": "../tools/remote_tools.html",
    "tutorials/mcp_integration": "../expand_tooluniverse/remote_tools/mcp_integration.html",
    # Top-level pages whose content moved into /about/ or /help/
    "getting_started": "guide/python_guide.html",
    "deployment": "about/deployment.html",
    "contributing": "about/contributing.html",
    "changelog": "about/changelog.html",
    "faq": "help/faq.html",
}

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "old_files",
    "old",
    "dev_docs",
    "tutorials/aiscientists",
    "translation_tools",
    "tutorials/overview.md",
    "tutorials/optimization",
    "guide/ODPHPtools_tutorial.md",
    # Internal meta-docs describing the folder structure or task list.
    # Not user-facing; kept in-tree as a developer reference only.
    "DOCUMENTATION_STRUCTURE.md",
]

# -- Options for HTML output with Shibuya theme -----------------------------
html_theme = "shibuya"
html_static_path = ["_static"]

# -- Shibuya theme configuration --------------------------------------------
html_theme_options = {
    # Navigation
    "nav_links": [
        {
            "title": "aiscientist.tools",
            "url": "https://aiscientist.tools",
        },
        {
            "title": "Home",
            "url": "index",
        },
        {
            "title": "AI Agents",
            "url": "guide/building_ai_scientists/index",
        },
        {
            "title": "Python",
            "url": "guide/python_guide",
        },
        {
            "title": "Tutorials",
            "url": "guide/index",
        },
        {
            "title": "Tools",
            "url": "tools/tools_config_index",
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
