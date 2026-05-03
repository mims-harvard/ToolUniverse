#!/usr/bin/env python3
"""
SMCP Server Entry Point

This module provides the command-line entry point for running the SMCP (Scientific Model Context Protocol) server.
It creates a minimal SMCP server that exposes all ToolUniverse tools as MCP tools.
"""

import argparse
import os
import sys
from .smcp import SMCP


def _add_profile_args(parser: argparse.ArgumentParser) -> None:
    """Add the shared --load / --workspace / --global argument group to *parser*."""
    group = parser.add_argument_group("Profile Configuration")
    group.add_argument(
        "--load",
        "-l",
        type=str,
        metavar="CONFIG",
        help="""Load profile configuration (preset/workspace).

Supports multiple formats:
  \u2022 HuggingFace:      username/repo, hf:username/repo@v1.0.0
  \u2022 Local files:      ./config.yaml, /absolute/path.yaml
  \u2022 HTTP URLs:        https://example.com/config.yaml

Examples:
  --load "community/proteomics-toolkit"
  --load "./my-config.yaml"
  --load "https://example.com/config.yaml"
        """,
    )
    group.add_argument(
        "--workspace",
        "-w",
        type=str,
        metavar="DIR",
        help="Local workspace directory to scan for tool files (*.py and *.json). "
        "Overrides TOOLUNIVERSE_HOME environment variable.",
    )
    group.add_argument(
        "--global",
        dest="use_global",
        action="store_true",
        help="Use the global workspace (~/.tooluniverse) instead of the local default "
        "(./.tooluniverse). Has no effect if --workspace or TOOLUNIVERSE_HOME is set.",
    )


def run_http_server():
    """
    Run SMCP server with streamable-http transport on localhost:8000

    This function provides compatibility with the original MCP server's run_server function.
    """
    parser = argparse.ArgumentParser(
        description="Start SMCP (Scientific Model Context Protocol) Server with HTTP transport",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server with all tools using HTTP transport
  tooluniverse-smcp-server

  # Start with specific categories
  tooluniverse-smcp-server --categories uniprot ChEMBL opentarget

  # Start with hooks enabled
  tooluniverse-smcp-server --hooks-enabled

  # Start with specific hook type
  tooluniverse-smcp-server --hook-type SummarizationHook

  # Start with custom hook configuration
  tooluniverse-smcp-server --hook-config-file /path/to/hook_config.json

  # Start with compact mode (only expose core tools)
  tooluniverse-smcp-server --compact-mode

  # Load Profile configuration
  tooluniverse-smcp-server --load "community/proteomics-toolkit"
  tooluniverse-smcp-server --load "./my-config.yaml"
        """,
    )

    _add_profile_args(parser)

    # Hook configuration options
    hook_group = parser.add_argument_group("Hook Configuration")
    hook_group.add_argument(
        "--hooks-enabled",
        action="store_true",
        help="Enable output processing hooks (default: False)",
    )
    hook_group.add_argument(
        "--hook-type",
        choices=["SummarizationHook", "FileSaveHook"],
        help="Simple hook type selection (SummarizationHook or FileSaveHook)",
    )
    hook_group.add_argument(
        "--hook-config-file",
        type=str,
        help="Path to custom hook configuration JSON file",
    )

    # Server configuration options
    server_group = parser.add_argument_group("Server Configuration")
    server_group.add_argument(
        "--host", default="127.0.0.1", help="Server host address (default: 127.0.0.1)"
    )
    server_group.add_argument(
        "--port", type=int, default=8000, help="Server port (default: 8000)"
    )
    server_group.add_argument(
        "--name",
        default="ToolUniverse SMCP Server",
        help="Server name (default: ToolUniverse SMCP Server)",
    )
    parser.add_argument(
        "--compact-mode",
        action="store_true",
        help="Enable compact mode: only expose core tools (4 tools) to prevent context window overflow. All tools are still loaded in background for execute_tool to work.",
    )

    args = parser.parse_args()

    try:
        print("🚀 Starting ToolUniverse SMCP Server...")
        print("📡 Transport: streamable-http")
        print(f"🌐 Address: http://{args.host}:{args.port}")
        print(f"🏷️  Name: {args.name}")

        # Load hook configuration if specified
        hook_config = None
        if args.hook_config_file:
            import json

            with open(args.hook_config_file, "r", encoding="utf-8") as f:
                hook_config = json.load(f)
            print(f"🔗 Hook config loaded from: {args.hook_config_file}")

        # Determine hook settings
        hooks_enabled = (
            args.hooks_enabled or args.hook_type is not None or hook_config is not None
        )
        if hooks_enabled:
            if args.hook_type:
                print(f"🔗 Hooks enabled: {args.hook_type}")
            elif hook_config:
                hook_count = len(hook_config.get("hooks", []))
                print(f"🔗 Hooks enabled: {hook_count} custom hooks")
            else:
                print("🔗 Hooks enabled: default configuration")
        else:
            print("🔗 Hooks disabled")

        if args.compact_mode:
            print("📦 Compact mode enabled: only core tools will be exposed")

        print()

        # Create SMCP server with Profile support
        server = SMCP(
            name=args.name,
            profile=args.load,  # Pass Profile URI directly to SMCP
            workspace=args.workspace,
            use_global=args.use_global,
            auto_expose_tools=True,
            search_enabled=True,
            max_workers=5,
            hooks_enabled=hooks_enabled,
            hook_config=hook_config,
            hook_type=args.hook_type,
            compact_mode=args.compact_mode,
        )

        # Run server with streamable-http transport
        server.run_simple(transport="http", host=args.host, port=args.port)

    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


def run_stdio_server():
    """
    Run SMCP server with stdio transport for Claude Desktop integration

    This function provides compatibility with the original MCP server's run_claude_desktop function.
    It accepts the same arguments as run_smcp_server but forces transport='stdio'.
    """
    # Set environment variable and reconfigure logging for stdio mode
    os.environ["TOOLUNIVERSE_STDIO_MODE"] = "1"

    # Import and reconfigure logging to stderr
    from .logging_config import reconfigure_for_stdio

    reconfigure_for_stdio()
    # Ensure stdout is line-buffered for immediate JSON-RPC flushing in stdio mode
    try:
        import sys as _sys

        if hasattr(_sys.stdout, "reconfigure"):
            _sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Start SMCP (Scientific Model Context Protocol) Server with stdio transport",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server with all tools using stdio transport (hooks enabled by default)
  tooluniverse-smcp-stdio

  # Start with specific categories
  tooluniverse-smcp-stdio --categories uniprot ChEMBL opentarget

  # Enable hooks
  tooluniverse-smcp-stdio --hooks

  # Use FileSaveHook instead of SummarizationHook
  tooluniverse-smcp-stdio --hook-type FileSaveHook

  # Use custom hook configuration
  tooluniverse-smcp-stdio --hook-config-file /path/to/hook_config.json

  # Start with categories but exclude specific tools
  tooluniverse-smcp-stdio --categories uniprot ChEMBL --exclude-tools "ChEMBL_get_molecule_by_chembl_id"

  # Start with all tools but exclude entire categories
  tooluniverse-smcp-stdio --exclude-categories mcp_auto_loader_boltz mcp_auto_loader_expert_feedback

  # Load only specific tools by name
  tooluniverse-smcp-stdio --include-tools "UniProt_get_entry_by_accession" "ChEMBL_get_molecule_by_chembl_id"

  # Load tools from a file
  tooluniverse-smcp-stdio --tools-file "/path/to/tool_names.txt"

  # Load additional config files
  tooluniverse-smcp-stdio --tool-config-files "custom:/path/to/custom_tools.json"

  # Include/exclude specific tool types
  tooluniverse-smcp-stdio --include-tool-types "OpenTarget" "ToolFinderEmbedding"
  tooluniverse-smcp-stdio --exclude-tool-types "ToolFinderLLM" "Unknown"

  # List available categories
  tooluniverse-smcp-stdio --list-categories

  # List all available tools
  tooluniverse-smcp-stdio --list-tools

  # Start minimal server with just search tools
  tooluniverse-smcp-stdio --categories special_tools tool_finder

  # Start with compact mode (only expose core tools)
  tooluniverse-smcp-stdio --compact-mode

  # Load Profile configuration
  tooluniverse-smcp-stdio --load "hf:community/proteomics-toolkit"
  tooluniverse-smcp-stdio --load "./my-config.yaml"
  tooluniverse-smcp-stdio --load "https://example.com/config.yaml"
        """,
    )

    _add_profile_args(parser)

    # Tool selection options
    tool_group = parser.add_mutually_exclusive_group()
    tool_group.add_argument(
        "--categories",
        nargs="*",
        metavar="CATEGORY",
        help="Specific tool categories to load (e.g., uniprot ChEMBL opentarget). Use --list-categories to see available options.",
    )
    tool_group.add_argument(
        "--list-categories",
        action="store_true",
        help="List all available tool categories and exit",
    )

    # Tool exclusion options
    parser.add_argument(
        "--exclude-tools",
        nargs="*",
        metavar="TOOL_NAME",
        help='Specific tool names to exclude from loading (e.g., "tool1" "tool2"). Can be used with --categories.',
    )
    parser.add_argument(
        "--exclude-categories",
        nargs="*",
        metavar="CATEGORY",
        help="Tool categories to exclude from loading (e.g., mcp_auto_loader_boltz). Can be used with --categories.",
    )

    # Tool inclusion options
    parser.add_argument(
        "--include-tools",
        nargs="*",
        metavar="TOOL_NAME",
        help="Specific tool names to include (only these tools will be loaded). Overrides category selection.",
    )
    parser.add_argument(
        "--tools-file",
        metavar="FILE_PATH",
        help="Path to text file containing tool names to include (one per line). Overrides category selection.",
    )
    parser.add_argument(
        "--tool-config-files",
        nargs="*",
        metavar="CATEGORY:PATH",
        help='Additional tool config files to load. Format: "category:/path/to/config.json"',
    )

    # Tool type filtering options
    parser.add_argument(
        "--include-tool-types",
        nargs="*",
        metavar="TOOL_TYPE",
        help="Specific tool types to include (e.g., OpenTarget ToolFinderEmbedding). Only tools of these types will be loaded.",
    )
    parser.add_argument(
        "--exclude-tool-types",
        nargs="*",
        metavar="TOOL_TYPE",
        help="Tool types to exclude from loading (e.g., ToolFinderLLM Unknown). Useful for excluding specific tool type classes.",
    )

    # Listing options
    parser.add_argument(
        "--list-tools", action="store_true", help="List all available tools and exit"
    )

    # Server configuration (stdio-specific)
    parser.add_argument(
        "--name",
        default="ToolUniverse SMCP Server",
        help="Server name (default: ToolUniverse SMCP Server)",
    )
    parser.add_argument(
        "--no-search",
        action="store_true",
        help="Disable intelligent search functionality",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Maximum worker threads for concurrent execution (default: 5)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--compact-mode",
        action="store_true",
        help="Enable compact mode: only expose core tools (4 tools) to prevent context window overflow. All tools are still loaded in background for execute_tool to work.",
    )

    # Hook configuration options (default disabled for stdio)
    hook_group = parser.add_argument_group("Hook Configuration")
    hook_group.add_argument(
        "--hooks",
        action="store_true",
        help="Enable output processing hooks (default: disabled for stdio)",
    )
    hook_group.add_argument(
        "--hook-type",
        choices=["SummarizationHook", "FileSaveHook"],
        help="Hook type to use (default: SummarizationHook when hooks are enabled)",
    )
    hook_group.add_argument(
        "--hook-config-file",
        type=str,
        help="Path to custom hook configuration JSON file",
    )

    args = parser.parse_args()

    # Handle --list-categories
    if args.list_categories:
        try:
            from .execute_function import ToolUniverse

            tu = ToolUniverse()
            # Use ToolUniverse API to list categories consistently
            stats = tu.list_built_in_tools(mode="config", scan_all=False)

            print("Available tool categories:", file=sys.stderr)
            print("=" * 50, file=sys.stderr)

            categories = stats.get("categories", {})
            # Sort by count desc, then name asc
            sorted_items = sorted(
                categories.items(), key=lambda kv: (-kv[1].get("count", 0), kv[0])
            )
            for key, info in sorted_items:
                display = key.replace("_", " ").title()
                count = info.get("count", 0)
                print(f"  {display}: {count}", file=sys.stderr)

            print(
                f"\nTotal categories: {stats.get('total_categories', 0)}",
                file=sys.stderr,
            )
            print(
                f"Total unique tools: {stats.get('total_tools', 0)}",
                file=sys.stderr,
            )

            print(
                "\nTip: Use --exclude-categories or --include-tools to customize loading",
                file=sys.stderr,
            )

        except Exception as e:
            print(f"❌ Error listing categories: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Handle --list-tools
    if args.list_tools:
        try:
            from .execute_function import ToolUniverse

            tu = ToolUniverse()
            tu.load_tools()  # Load all tools to list them

            print("Available tools:", file=sys.stderr)
            print("=" * 50, file=sys.stderr)

            # Group tools by category (use ToolUniverse's canonical 'type' field)
            tools_by_category = {}
            for tool in tu.all_tools:
                # Handle both dict and object tool formats
                if isinstance(tool, dict):
                    tool_type = tool.get("type", "unknown")
                    tool_name = tool.get("name", "unknown")
                else:
                    tool_type = getattr(tool, "type", "unknown")
                    tool_name = getattr(tool, "name", "unknown")

                if tool_type not in tools_by_category:
                    tools_by_category[tool_type] = []
                tools_by_category[tool_type].append(tool_name)

            total_tools = 0
            for category in sorted(tools_by_category.keys()):
                tools = sorted(tools_by_category[category])
                print(f"\n📁 {category} ({len(tools)} tools):", file=sys.stderr)
                for tool in tools[:10]:  # Show first 10 tools per category
                    print(f"  {tool}", file=sys.stderr)
                if len(tools) > 10:
                    # Print remaining count to stderr
                    print(f"  ... and {len(tools) - 10} more tools", file=sys.stderr)
                total_tools += len(tools)

            print(f"\nTotal: {total_tools} tools available", file=sys.stderr)
            print(
                "\nNote: Use --exclude-tools to exclude specific tools by name",
                file=sys.stderr,
            )
            print(
                "      Use --exclude-categories to exclude entire categories",
                file=sys.stderr,
            )

        except Exception as e:
            print(f"❌ Error listing tools: {e}", file=sys.stderr)
            sys.exit(1)
        return

    try:
        print(f"🚀 Starting {args.name}...", file=sys.stderr)
        print("📡 Transport: stdio", file=sys.stderr)
        print(f"🔍 Search enabled: {not args.no_search}", file=sys.stderr)

        if args.categories is not None:
            if len(args.categories) == 0:
                print("📂 No categories specified, loading all tools", file=sys.stderr)
                tool_categories = None
            else:
                print(
                    f"📂 Tool categories: {', '.join(args.categories)}", file=sys.stderr
                )
                tool_categories = args.categories
        else:
            print("📂 Loading all tool categories", file=sys.stderr)
            tool_categories = None

        # Handle exclusions and inclusions
        exclude_tools = args.exclude_tools or []
        exclude_categories = args.exclude_categories or []
        include_tools = args.include_tools or []
        tools_file = args.tools_file
        include_tool_types = args.include_tool_types or []
        exclude_tool_types = args.exclude_tool_types or []

        # Parse tool config files
        tool_config_files = {}
        if args.tool_config_files:
            for config_spec in args.tool_config_files:
                if ":" in config_spec:
                    category, path = config_spec.split(":", 1)
                    tool_config_files[category] = path
                else:
                    print(
                        f"❌ Invalid tool config file format: {config_spec}",
                        file=sys.stderr,
                    )
                    print(
                        "   Expected format: 'category:/path/to/config.json'",
                        file=sys.stderr,
                    )
                    sys.exit(1)

        if exclude_tools:
            print(f"🚫 Excluding tools: {', '.join(exclude_tools)}", file=sys.stderr)
        if exclude_categories:
            print(
                f"🚫 Excluding categories: {', '.join(exclude_categories)}",
                file=sys.stderr,
            )
        if include_tools:
            print(
                f"✅ Including only specific tools: {len(include_tools)} tools",
                file=sys.stderr,
            )
        if tools_file:
            print(f"📄 Loading tools from file: {tools_file}", file=sys.stderr)
        if tool_config_files:
            print(
                f"📦 Additional config files: {', '.join(tool_config_files.keys())}",
                file=sys.stderr,
            )
        if include_tool_types:
            print(
                f"🎯 Including tool types: {', '.join(include_tool_types)}",
                file=sys.stderr,
            )
        if exclude_tool_types:
            print(
                f"🚫 Excluding tool types: {', '.join(exclude_tool_types)}",
                file=sys.stderr,
            )
        if args.compact_mode:
            print(
                "📦 Compact mode enabled: only core tools will be exposed",
                file=sys.stderr,
            )

        # Load hook configuration if specified
        hook_config = None
        if args.hook_config_file:
            import json

            with open(args.hook_config_file, "r", encoding="utf-8") as f:
                hook_config = json.load(f)
            print(
                f"🔗 Hook config loaded from: {args.hook_config_file}", file=sys.stderr
            )

        # Determine hook settings (default disabled for stdio)
        hooks_enabled = (
            args.hooks or args.hook_type is not None or hook_config is not None
        )

        # Set default hook type if hooks are enabled but no type specified
        hook_type = args.hook_type
        if hooks_enabled and hook_type is None:
            hook_type = "SummarizationHook"
        if hooks_enabled:
            if hook_type:
                print(f"🔗 Hooks enabled: {hook_type}", file=sys.stderr)
            elif hook_config:
                hook_count = len(hook_config.get("hooks", []))
                print(f"🔗 Hooks enabled: {hook_count} custom hooks", file=sys.stderr)
            else:
                print("🔗 Hooks enabled: default configuration", file=sys.stderr)
        else:
            print("🔗 Hooks disabled", file=sys.stderr)

        print(f"⚡ Max workers: {args.max_workers}", file=sys.stderr)
        print(file=sys.stderr)

        # Create SMCP server with Profile and tool configuration support
        server = SMCP(
            name=args.name,
            profile=args.load,  # Pass Profile URI directly to SMCP
            workspace=args.workspace,
            use_global=args.use_global,
            tool_categories=tool_categories,
            exclude_tools=exclude_tools,
            exclude_categories=exclude_categories,
            include_tools=include_tools,
            tools_file=tools_file,
            tool_config_files=tool_config_files,
            include_tool_types=include_tool_types,
            exclude_tool_types=exclude_tool_types,
            search_enabled=not args.no_search,
            max_workers=args.max_workers,
            hooks_enabled=hooks_enabled,
            hook_config=hook_config,
            hook_type=hook_type,
            compact_mode=args.compact_mode,
        )

        # Run server with stdio transport (forced)
        server.run_simple(transport="stdio")

    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def run_smcp_server():
    """
    Main entry point for the SMCP server command.

    This function is called when running `tooluniverse-smcp` from the command line.
    """
    parser = argparse.ArgumentParser(
        description="Start SMCP (Scientific Model Context Protocol) Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server with all tools on port 7890
  tooluniverse-smcp --port 7890

  # Start with specific categories
  tooluniverse-smcp --categories uniprot ChEMBL opentarget --port 8000

  # Start with categories but exclude specific tools
  tooluniverse-smcp --categories uniprot ChEMBL --exclude-tools "ChEMBL_get_molecule_by_chembl_id" --port 8000

  # Start with all tools but exclude entire categories
  tooluniverse-smcp --exclude-categories mcp_auto_loader_boltz mcp_auto_loader_expert_feedback --port 8000

  # Load only specific tools by name
  tooluniverse-smcp --include-tools "UniProt_get_entry_by_accession" "ChEMBL_get_molecule_by_chembl_id" --port 8000

  # Load tools from a file
  tooluniverse-smcp --tools-file "/path/to/tool_names.txt" --port 8000

  # Load additional config files
  tooluniverse-smcp --tool-config-files "custom:/path/to/custom_tools.json" --port 8000

  # Include/exclude specific tool types
  tooluniverse-smcp --include-tool-types "OpenTarget" "ToolFinderEmbedding" --port 8000
  tooluniverse-smcp --exclude-tool-types "ToolFinderLLM" "Unknown" --port 8000

  # List available categories
  tooluniverse-smcp --list-categories

  # List all available tools
  tooluniverse-smcp --list-tools

  # Start minimal server with just search tools
  tooluniverse-smcp --categories special_tools tool_finder --port 7000

  # Start with compact mode (only expose core tools)
  tooluniverse-smcp --compact-mode --port 8000

  # Start server for Claude Desktop (stdio transport)
  tooluniverse-smcp --transport stdio

  # Start with compact mode for Claude Desktop
  tooluniverse-smcp --compact-mode --transport stdio

  # Load Profile configuration
  tooluniverse-smcp --load "community/proteomics-toolkit" --port 8000
  tooluniverse-smcp --load "./my-config.yaml" --transport stdio
        """,
    )

    _add_profile_args(parser)

    # Tool selection options
    tool_group = parser.add_mutually_exclusive_group()
    tool_group.add_argument(
        "--categories",
        nargs="*",
        metavar="CATEGORY",
        help="Specific tool categories to load (e.g., uniprot ChEMBL opentarget). Use --list-categories to see available options.",
    )
    tool_group.add_argument(
        "--list-categories",
        action="store_true",
        help="List all available tool categories and exit",
    )

    # Tool exclusion options
    parser.add_argument(
        "--exclude-tools",
        nargs="*",
        metavar="TOOL_NAME",
        help='Specific tool names to exclude from loading (e.g., "tool1" "tool2"). Can be used with --categories.',
    )
    parser.add_argument(
        "--exclude-categories",
        nargs="*",
        metavar="CATEGORY",
        help="Tool categories to exclude from loading (e.g., mcp_auto_loader_boltz). Can be used with --categories.",
    )

    # Tool inclusion options
    parser.add_argument(
        "--include-tools",
        nargs="*",
        metavar="TOOL_NAME",
        help="Specific tool names to include (only these tools will be loaded). Overrides category selection.",
    )
    parser.add_argument(
        "--tools-file",
        metavar="FILE_PATH",
        help="Path to text file containing tool names to include (one per line). Overrides category selection.",
    )
    parser.add_argument(
        "--tool-config-files",
        nargs="*",
        metavar="CATEGORY:PATH",
        help='Additional tool config files to load. Format: "category:/path/to/config.json"',
    )

    # Tool type filtering options
    parser.add_argument(
        "--include-tool-types",
        nargs="*",
        metavar="TOOL_TYPE",
        help="Specific tool types to include (e.g., OpenTarget ToolFinderEmbedding). Only tools of these types will be loaded.",
    )
    parser.add_argument(
        "--exclude-tool-types",
        nargs="*",
        metavar="TOOL_TYPE",
        help="Tool types to exclude from loading (e.g., ToolFinderLLM Unknown). Useful for excluding specific tool type classes.",
    )

    # Listing options
    parser.add_argument(
        "--list-tools", action="store_true", help="List all available tools and exit"
    )

    # Server configuration
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="http",
        help="Transport protocol to use (default: http)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to for HTTP/SSE transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7000,
        help="Port to bind to for HTTP/SSE transport (default: 7000)",
    )
    parser.add_argument(
        "--name",
        default="ToolUniverse SMCP Server",
        help="Server name (default: ToolUniverse SMCP Server)",
    )
    parser.add_argument(
        "--no-search",
        action="store_true",
        help="Disable intelligent search functionality",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Maximum worker threads for concurrent execution (default: 5)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # Hook configuration options
    hook_group = parser.add_argument_group("Hook Configuration")
    hook_group.add_argument(
        "--hooks-enabled",
        action="store_true",
        help="Enable output processing hooks (default: False)",
    )
    hook_group.add_argument(
        "--hook-type",
        choices=["SummarizationHook", "FileSaveHook"],
        help="Simple hook type selection (SummarizationHook or FileSaveHook)",
    )
    hook_group.add_argument(
        "--hook-config-file",
        type=str,
        help="Path to custom hook configuration JSON file",
    )
    parser.add_argument(
        "--compact-mode",
        action="store_true",
        help="Enable compact mode: only expose core tools (4 tools) to prevent context window overflow. All tools are still loaded in background for execute_tool to work.",
    )

    args = parser.parse_args()

    # Handle --list-categories
    if args.list_categories:
        try:
            from .execute_function import ToolUniverse

            tu = ToolUniverse()
            # Use ToolUniverse API to list categories consistently
            stats = tu.list_built_in_tools(mode="config", scan_all=False)

            print("Available tool categories:")
            print("=" * 50)

            categories = stats.get("categories", {})
            # Sort by count desc, then name asc
            sorted_items = sorted(
                categories.items(), key=lambda kv: (-kv[1].get("count", 0), kv[0])
            )
            for key, info in sorted_items:
                display = key.replace("_", " ").title()
                count = info.get("count", 0)
                print(f"  {display}: {count}")

            print(f"\nTotal categories: {stats.get('total_categories', 0)}")
            print(f"Total unique tools: {stats.get('total_tools', 0)}")
            print(
                "\nTip: Use --exclude-categories or --include-tools to customize loading"
            )

        except Exception as e:
            print(f"❌ Error listing categories: {e}")
            sys.exit(1)
        return

    # Handle --list-tools
    if args.list_tools:
        try:
            from .execute_function import ToolUniverse

            tu = ToolUniverse()
            # Reuse ToolUniverse selection logic directly (applies API key skipping internally)
            tool_config_files = {}
            if args.tool_config_files:
                for config_spec in args.tool_config_files:
                    if ":" in config_spec:
                        category, path = config_spec.split(":", 1)
                        tool_config_files[category] = path

            tu.load_tools(
                tool_type=(
                    args.categories
                    if args.categories and len(args.categories) > 0
                    else None
                ),
                exclude_tools=args.exclude_tools,
                exclude_categories=args.exclude_categories,
                include_tools=args.include_tools,
                tool_config_files=(tool_config_files or None),
                tools_file=args.tools_file,
                include_tool_types=args.include_tool_types,
                exclude_tool_types=args.exclude_tool_types,
            )

            # Names of tools that are actually available under current configuration
            tool_names = tu.get_available_tools(name_only=True)

            print("Available tools (for this server configuration):")
            print("=" * 50)
            for name in sorted(tool_names)[:200]:  # cap output for readability
                print(f"  {name}")
            print(f"\nTotal: {len(tool_names)} tools available")
            print("\nNote: Use --exclude-tools to exclude specific tools by name")
            print("      Use --exclude-categories to exclude entire categories")

        except Exception as e:
            print(f"❌ Error listing tools: {e}")
            sys.exit(1)
        return

    try:
        print(f"🚀 Starting {args.name}...")
        print(f"📡 Transport: {args.transport}")
        if args.transport in ["http", "sse"]:
            print(f"🌐 Address: http://{args.host}:{args.port}")
        print(f"🔍 Search enabled: {not args.no_search}")

        if args.categories is not None:
            if len(args.categories) == 0:
                print("📂 No categories specified, loading all tools")
                tool_categories = None
            else:
                print(f"📂 Tool categories: {', '.join(args.categories)}")
                tool_categories = args.categories
        else:
            print("📂 Loading all tool categories")
            tool_categories = None

        # Handle exclusions and inclusions
        exclude_tools = args.exclude_tools or []
        exclude_categories = args.exclude_categories or []
        include_tools = args.include_tools or []
        tools_file = args.tools_file
        include_tool_types = args.include_tool_types or []
        exclude_tool_types = args.exclude_tool_types or []

        # Parse tool config files
        tool_config_files = {}
        if args.tool_config_files:
            for config_spec in args.tool_config_files:
                if ":" in config_spec:
                    category, path = config_spec.split(":", 1)
                    tool_config_files[category] = path
                else:
                    print(f"❌ Invalid tool config file format: {config_spec}")
                    print("   Expected format: 'category:/path/to/config.json'")
                    sys.exit(1)

        if exclude_tools:
            print(f"🚫 Excluding tools: {', '.join(exclude_tools)}")
        if exclude_categories:
            print(f"🚫 Excluding categories: {', '.join(exclude_categories)}")
        if include_tools:
            print(f"✅ Including only specific tools: {len(include_tools)} tools")
        if tools_file:
            print(f"📄 Loading tools from file: {tools_file}")
        if tool_config_files:
            print(f"📦 Additional config files: {', '.join(tool_config_files.keys())}")
        if include_tool_types:
            print(f"🎯 Including tool types: {', '.join(include_tool_types)}")
        if exclude_tool_types:
            print(f"🚫 Excluding tool types: {', '.join(exclude_tool_types)}")
        if args.compact_mode:
            print("📦 Compact mode enabled: only core tools will be exposed")

        # Load hook configuration if specified
        hook_config = None
        if args.hook_config_file:
            import json

            with open(args.hook_config_file, "r", encoding="utf-8") as f:
                hook_config = json.load(f)
            print(f"🔗 Hook config loaded from: {args.hook_config_file}")

        # Determine hook settings
        hooks_enabled = (
            args.hooks_enabled or args.hook_type is not None or hook_config is not None
        )
        if hooks_enabled:
            if args.hook_type:
                print(f"🔗 Hooks enabled: {args.hook_type}")
            elif hook_config:
                hook_count = len(hook_config.get("hooks", []))
                print(f"🔗 Hooks enabled: {hook_count} custom hooks")
            else:
                print("🔗 Hooks enabled: default configuration")
        else:
            print("🔗 Hooks disabled")

        print(f"⚡ Max workers: {args.max_workers}")
        print()

        # Create SMCP server with Profile and hook support
        server = SMCP(
            name=args.name,
            profile=args.load,  # Pass Profile URI directly to SMCP
            workspace=args.workspace,
            use_global=args.use_global,
            tool_categories=tool_categories,
            exclude_tools=exclude_tools,
            exclude_categories=exclude_categories,
            include_tools=include_tools,
            tools_file=tools_file,
            tool_config_files=tool_config_files,
            include_tool_types=include_tool_types,
            exclude_tool_types=exclude_tool_types,
            search_enabled=not args.no_search,
            max_workers=args.max_workers,
            hooks_enabled=hooks_enabled,
            hook_config=hook_config,
            hook_type=args.hook_type,
            compact_mode=args.compact_mode,
        )

        # Run server
        server.run_simple(transport=args.transport, host=args.host, port=args.port)

    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def run_default_stdio_server():
    """
    Default ToolUniverse command: MCP stdio server with compact mode on by default.
    """
    if "--help" in sys.argv or "-h" in sys.argv:
        sys.stdout.write(
            "usage: tooluniverse [options]\n\n"
            "Start ToolUniverse as an MCP stdio server (compact mode on by default).\n\n"
            "options:\n"
            "  -h, --help          show this help message and exit\n"
            "  --load CONFIG       Profile config to load (./my.yaml, hf:user/repo, https://...)\n"
            "  --workspace DIR     Local workspace directory (default: ./.tooluniverse)\n"
            "  --global            Use global workspace (~/.tooluniverse)\n"
            "  --verbose           Enable verbose logging\n\n"
            "examples:\n"
            "  tooluniverse\n"
            "  tooluniverse --load ./life-science.yaml\n"
            "  tooluniverse --load hf:community/genomics-tools\n"
            "  tooluniverse --global\n\n"
            "For advanced options (hooks, tool filtering, etc.) use:\n"
            "  tooluniverse-smcp-stdio --help\n"
        )
        sys.exit(0)

    if "--compact-mode" not in sys.argv:
        sys.argv.append("--compact-mode")
    run_stdio_server()


if __name__ == "__main__":
    run_smcp_server()
