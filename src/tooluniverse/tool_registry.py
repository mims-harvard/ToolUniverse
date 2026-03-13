"""Simplified tool registry for automatic tool discovery and registration."""

import importlib
import sys
import pkgutil
import os
import logging
import re
from pathlib import Path
from typing import Dict, Optional

# Initialize logger for this module
logger = logging.getLogger("ToolRegistry")

# Detect this module's package prefix (e.g. "tooluniverse" or "src.tooluniverse")
# so that lazy imports use the same namespace as the running code.
_PKG = __name__.rsplit(".", 1)[0]

# Global registries
_tool_registry = {}
_config_registry = {}
_list_config_registry: list = []  # Flat list of configs from sub-packages
_lazy_registry: Dict[str, str] = {}  # Maps tool names to module names
_discovery_completed = False
_lazy_cache = {}

# Global error tracking
_TOOL_ERRORS = {}

# Tracks which entry-point plugins have already been fully processed so that
# _discover_entry_point_plugins() is idempotent even if called multiple times.
_discovered_plugin_names: set = set()


def _extract_missing_package(error_msg: str) -> Optional[str]:
    """Extract package name from ImportError."""
    match = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_msg)
    if match:
        return match.group(1).split(".")[0]
    return None


def mark_tool_unavailable(tool_name: str, error: Exception, module: str = None):
    """Record tool failure."""
    _TOOL_ERRORS[tool_name] = {
        "error": str(error),
        "error_type": type(error).__name__,
        "module": module,
        "missing_package": _extract_missing_package(str(error)),
    }


def get_tool_errors() -> dict:
    """Get all tool errors."""
    return _TOOL_ERRORS.copy()


def register_tool(tool_type_name=None, config=None):
    """
    Decorator to automatically register tool classes and their configs.

    Usage:
        @register_tool('CustomToolName', config={...})
        class MyTool:
            pass
    """

    def decorator(cls):
        name = tool_type_name or cls.__name__
        _tool_registry[name] = cls

        if config is not None:
            # Add MCP annotations to config if it's a dict
            if isinstance(config, dict):
                from .tool_defaults import add_annotations_to_tool_config

                # Ensure config has type field for annotation calculation
                if "type" not in config:
                    config["type"] = name
                add_annotations_to_tool_config(config)

            _config_registry[name] = config
            logger.info(f"Registered tool with config: {name}")
        else:
            logger.debug(f"Registered tool: {name} -> {cls.__name__}")

        return cls

    return decorator


def register_external_tool(tool_name, tool_class):
    """Allow external registration of tool classes."""
    _tool_registry[tool_name] = tool_class
    logger.info(f"Externally registered tool: {tool_name}")


def register_config(tool_type_name, config):
    """Register a config for a tool type."""
    # Add MCP annotations to config if it's a dict
    if isinstance(config, dict):
        from .tool_defaults import add_annotations_to_tool_config

        # Ensure config has type field for annotation calculation
        if "type" not in config:
            config["type"] = tool_type_name
        add_annotations_to_tool_config(config)

    _config_registry[tool_type_name] = config
    logger.info(f"Registered config for: {tool_type_name}")


def get_tool_registry():
    """Get a copy of the current tool registry."""
    return _tool_registry.copy()


def get_config_registry():
    """Get a copy of the current config registry."""
    return _config_registry.copy()


def register_tool_configs(configs: list):
    """
    Register a list of tool configs from a sub-package (e.g. tooluniverse-circuit).

    Sub-package ``__init__.py`` files call this to make their JSON configs
    discoverable by ``ToolUniverse.load_tools()`` without requiring any
    entries in ``default_config.py``.

    Args:
        configs: List of tool config dicts, each containing at least a ``name`` key.
    """
    from .tool_defaults import add_annotations_to_tool_config

    for config in configs:
        if not isinstance(config, dict) or "name" not in config:
            continue
        add_annotations_to_tool_config(config)
        _list_config_registry.append(config)
    logger.info(f"Registered {len(configs)} sub-package tool configs")


def get_list_config_registry() -> list:
    """Return the flat list of configs registered by sub-packages."""
    return _list_config_registry.copy()


def clear_lazy_cache():
    """Clear the module-level lazy import cache.

    Built-in tool modules (in ``src/tooluniverse/tools/``) are cached after
    their first import.  Call this function in development environments when
    you have edited a built-in tool module and want the changes to take effect
    without restarting the process.  After calling this, the next access to the
    tool will re-import its module from disk.

    Note: this does NOT affect workspace user tool files; those are handled
    separately via mtime tracking in ``_import_user_python_tools()``.

    Example::

        from tooluniverse.tool_registry import clear_lazy_cache
        clear_lazy_cache()
        tu.refresh_tools()
    """
    _lazy_cache.clear()
    logger.debug(
        "Lazy import cache cleared; built-in tool modules will be re-imported on next access."
    )


def lazy_import_tool(tool_name):
    """
    Lazily import a tool by name without importing all tool modules.
    Only imports the specific module containing the requested tool.
    """
    global _tool_registry, _lazy_registry, _lazy_cache  # noqa: PLW0603

    # If tool is already in registry, return it
    if tool_name in _tool_registry:
        return _tool_registry[tool_name]

    # If we have a lazy mapping for this tool, import its module
    if tool_name in _lazy_registry:
        module_name = _lazy_registry[tool_name]

        # Ensure we have the full module path using the same package prefix
        # as this registry module itself (handles both "tooluniverse." and
        # "src.tooluniverse." namespaces in editable/dev installs).
        if not module_name.startswith(_PKG + "."):
            full_module_name = f"{_PKG}.{module_name}"
        else:
            full_module_name = module_name

        # Only import if we haven't cached this module yet
        module = _lazy_cache.get(full_module_name)
        if module is None:
            try:
                logger.debug(
                    f"Lazy importing module: {full_module_name} for tool: {tool_name}"
                )
                module = importlib.import_module(full_module_name)
                _lazy_cache[full_module_name] = module
                logger.debug(f"Successfully imported module: {full_module_name}")

            except ImportError as e:
                logger.warning(f"Failed to lazy import {full_module_name}: {e}")
                mark_tool_unavailable(tool_name, e, full_module_name)
                # Remove this bad mapping so we don't try again
                del _lazy_registry[tool_name]
                return None
            except Exception as e:
                logger.warning(f"Failed to load {full_module_name}: {e}")
                mark_tool_unavailable(tool_name, e, full_module_name)
                del _lazy_registry[tool_name]
                return None

        # Check if the tool is in the registry
        if tool_name in _tool_registry:
            return _tool_registry[tool_name]

        # Fallback: Check if the tool class exists directly in the module
        # This handles cases where @register_tool("Alias") is used, but we are looking
        # for the class name itself (e.g. MonarchTool vs Monarch), which AST discovery found.
        if hasattr(module, tool_name):
            tool_class = getattr(module, tool_name)
            # Optionally cache it in registry for next time?
            # _tool_registry[tool_name] = tool_class
            return tool_class

        logger.warning(
            f"Tool {tool_name} not found in module {full_module_name} (registry or attribute)"
        )

    # If still not found after lazy loading attempt, return None
    # Don't fall back to full discovery as that defeats the purpose of lazy loading
    logger.debug(f"Tool {tool_name} not found in lazy registry")
    return None


def _discover_from_ast():
    """
    Discover tools by parsing AST of files in the package.
    Returns: Dict[tool_name, module_name]
    """
    import ast
    import tooluniverse

    mapping = {}
    try:
        package_path = tooluniverse.__path__[0]
    except (ImportError, AttributeError):
        logger.warning("Cannot import tooluniverse package for AST discovery")
        return {}

    logger.debug(f"AST scanning directory: {package_path}")

    # Directories to exclude from scanning
    EXCLUDED_DIRS = {
        "tools",
        "space",
        "data",
        "compose_scripts",
        "cache",
        "remote",
        "scripts",
        "__pycache__",
        "tests",
        "venv",
        "build",
        "dist",
        ".git",
        ".idea",
        ".vscode",
    }

    # Walk through the directory
    for root, dirs, files in os.walk(package_path):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for file in files:
            if not file.endswith(".py"):
                continue

            # Skip known non-tool files
            if file in [
                "__init__.py",
                "main.py",
                "generate_tools.py",
                "conftest.py",
                "setup.py",
            ]:
                continue

            # Determine if this is an explicit tool file (legacy naming convention)
            is_explicit_tool_file = (
                file.endswith("_tool.py")
                or file.endswith("_tools.py")
                or file in ["compose_tool.py", "agentic_tool.py"]
            )

            file_path = os.path.join(root, file)

            # Determine module name relative to tooluniverse package
            rel_path = os.path.relpath(file_path, package_path)
            module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        node = ast.parse(f.read())
                        for n in node.body:
                            if isinstance(n, ast.ClassDef):
                                # Skip private classes
                                if n.name.startswith("_"):
                                    continue

                                has_registered_alias = False

                                for decorator in n.decorator_list:
                                    if not isinstance(decorator, ast.Call):
                                        continue
                                    func = decorator.func
                                    is_register_tool = (
                                        isinstance(func, ast.Name)
                                        and func.id == "register_tool"
                                    ) or (
                                        isinstance(func, ast.Attribute)
                                        and func.attr == "register_tool"
                                    )
                                    if not is_register_tool:
                                        continue
                                    has_registered_alias = True
                                    if decorator.args:
                                        arg = decorator.args[0]
                                        if isinstance(arg, ast.Constant) and isinstance(
                                            arg.value, str
                                        ):
                                            mapping[arg.value] = module_name

                                if has_registered_alias or is_explicit_tool_file:
                                    mapping[n.name] = module_name

                    except SyntaxError:
                        logger.warning(f"Syntax error parsing {file_path}")
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")

    return mapping


def build_lazy_registry(package_name=None):
    """
    Build a mapping of tool names to module names.
    Prioritizes pre-computed static registry (for bundles/frozen envs).
    Falls back to AST analysis if static registry is missing.
    """
    global _lazy_registry  # noqa: PLW0603

    if package_name is None:
        package_name = "tooluniverse"

    # 1. Try to load pre-computed static registry (for frozen environments)
    try:
        from tooluniverse._lazy_registry_static import STATIC_LAZY_REGISTRY

        logger.debug(
            f"Loaded static lazy registry with {len(STATIC_LAZY_REGISTRY)} classes."
        )
        _lazy_registry.update(STATIC_LAZY_REGISTRY)

        # Supplement with AST discovery so newly-added tool files (not yet in the
        # static registry) are automatically found without requiring a manual rebuild.
        ast_mappings = _discover_from_ast()
        new_from_ast = 0
        for tool_name, module_name in ast_mappings.items():
            if tool_name not in _lazy_registry:
                _lazy_registry[tool_name] = module_name
                new_from_ast += 1
        if new_from_ast:
            logger.debug(
                f"AST discovery added {new_from_ast} tool(s) not in static registry."
            )

        # Still auto-import sub-packages so their __init__.py files can register
        # configs even when the static registry is used (e.g. tooluniverse[circuit]).
        _auto_import_subpackages(package_name)
        # Discover entry-point plugins (new-style external packages).
        _discover_entry_point_plugins()
        return _lazy_registry.copy()
    except ImportError:
        logger.debug("No static lazy registry found. Proceeding with AST discovery.")

    logger.debug(f"Building lazy registry using AST for package: {package_name}")

    # 2. Use AST-based discovery as the primary source of truth (dev environment)
    ast_mappings = _discover_from_ast()

    for tool_name, module_name in ast_mappings.items():
        _lazy_registry[tool_name] = module_name

    # 3. Auto-import installed tooluniverse sub-packages so their __init__.py
    #    files can call register_tool_configs() and populate _list_config_registry.
    #    We import them here (after AST scan) to avoid circular imports during scan.
    _auto_import_subpackages(package_name)

    # 4. Discover entry-point plugins (new-style flat packages).
    _discover_entry_point_plugins()

    logger.info(
        f"Built lazy registry: {len(_lazy_registry)} classes discovered via AST (no modules imported)"
    )
    return _lazy_registry.copy()


def _read_profile_yaml(directory, context: str = "") -> dict:
    """
    Read ``profile.yaml`` from *directory* if it exists.

    Logs the pack name/description at INFO level so users can see which
    tool packs were loaded.  Also logs a WARNING for any ``required_env``
    variables that are missing from the environment — this is the earliest
    point at which a user can be told "you need DIGIKEY_CLIENT_ID".

    Returns the parsed config dict (empty dict if no file or parse error).
    """
    profile_file = Path(directory) / "profile.yaml"
    if not profile_file.exists():
        return {}

    try:
        import yaml

        with open(profile_file, "r", encoding="utf-8") as _f:
            config = yaml.safe_load(_f) or {}
    except Exception as exc:
        logger.debug(f"{context}: could not read profile.yaml: {exc}")
        return {}

    name = config.get("name", "")
    description = config.get("description", "").strip()
    label = f"{name} — {description}" if description else name
    if label:
        logger.info(f"Tool pack loaded: {label} ({context})")

    missing = [var for var in config.get("required_env", []) if not os.environ.get(var)]
    if missing:
        # Feature-23B-06: downgrade to DEBUG so the circuit/plugin env-var notice
        # does not spam every `tu` invocation (including `tu --help`).
        # The tools affected are already excluded from the loaded registry;
        # a summary INFO-level message is emitted by execute_function.py.
        logger.debug(f"{context} requires env var(s) not set: {', '.join(missing)}")

    return config


def reset_plugin_discovery():
    """Clear the set of already-discovered plugin names.

    Call this before ``build_lazy_registry()`` (or ``refresh_tools()``) when a
    new plugin package has been installed in the current process and you want
    ``_discover_entry_point_plugins()`` to pick it up without restarting.
    """
    _discovered_plugin_names.clear()
    logger.debug(
        "Plugin discovery cache cleared; next scan will re-discover all plugins."
    )


def _discover_entry_point_plugins(force: bool = False):
    """
    Discover and eagerly load installed tooluniverse plugins registered via
    the ``tooluniverse.plugins`` entry point group.

    Plugin packages declare themselves in ``pyproject.toml``::

        [project.entry-points."tooluniverse.plugins"]
        my-tools = "my_tools_package"

    The entry point value must be an importable Python package.  When
    discovered, every ``.py`` file in the package directory (excluding
    ``__init__.py``) is imported so that ``@register_tool`` decorators fire
    and the tool classes land in ``_tool_registry``.  JSON config files
    inside ``data/`` and the package root are loaded into
    ``_list_config_registry``.

    This allows external plugin packages to have exactly the same directory
    layout as a local workspace (``data/``, tool ``.py`` files, optional
    ``profile.yaml``) — the only extra piece needed for a distributable
    package is the ``pyproject.toml`` entry point declaration.
    """
    import json as _json

    try:
        from importlib.metadata import entry_points

        eps = entry_points(group="tooluniverse.plugins")
    except Exception as exc:
        logger.debug(f"Could not read tooluniverse.plugins entry points: {exc}")
        return

    for ep in eps:
        # Skip plugins already processed in a previous call (idempotency guard).
        # The guard is bypassed when force=True (e.g. after a new pip install).
        if not force and ep.name in _discovered_plugin_names:
            logger.debug(f"Plugin '{ep.name}': already loaded, skipping")
            continue
        # Remove from processed set so the plugin is fully re-scanned below.
        _discovered_plugin_names.discard(ep.name)

        try:
            plugin_module = ep.load()
        except Exception as exc:
            logger.debug(f"Plugin '{ep.name}': failed to load '{ep.value}': {exc}")
            continue

        if not hasattr(plugin_module, "__file__") or plugin_module.__file__ is None:
            logger.debug(f"Plugin '{ep.name}': no __file__, skipping")
            continue

        plugin_dir = Path(plugin_module.__file__).parent
        pkg_name = getattr(plugin_module, "__name__", None)
        if not pkg_name:
            continue

        # Read profile.yaml if present — log pack identity and check required_env
        _read_profile_yaml(plugin_dir, context=f"plugin '{ep.name}'")

        logger.debug(f"Plugin '{ep.name}' at {plugin_dir} (package={pkg_name})")

        # Import .py tool files so @register_tool decorators fire
        _SKIP = {"__init__.py", "setup.py", "conftest.py"}
        imported = 0
        for py_file in sorted(plugin_dir.glob("*.py")):
            if py_file.name in _SKIP:
                continue
            mod_name = f"{pkg_name}.{py_file.stem}"
            try:
                importlib.import_module(mod_name)
                imported += 1
                logger.debug(f"  Plugin '{ep.name}': imported {mod_name}")
            except Exception as exc:
                mark_tool_unavailable(py_file.stem, exc, mod_name)
                logger.debug(
                    f"  Plugin '{ep.name}': could not import {mod_name}: {exc}"
                )

        # Load JSON configs from data/ sub-directory and flat package root
        configs = []
        for search_dir in [plugin_dir / "data", plugin_dir]:
            if not search_dir.is_dir():
                continue
            for json_file in sorted(search_dir.glob("*.json")):
                try:
                    with open(json_file, "r", encoding="utf-8") as _f:
                        data = _json.load(_f)
                    if isinstance(data, list):
                        configs.extend(data)
                    elif isinstance(data, dict) and "name" in data:
                        configs.append(data)
                except Exception as exc:
                    logger.debug(
                        f"  Plugin '{ep.name}': could not load {json_file}: {exc}"
                    )

        if configs:
            from .tool_defaults import add_annotations_to_tool_config

            n = 0
            for cfg in configs:
                if isinstance(cfg, dict) and "name" in cfg:
                    add_annotations_to_tool_config(cfg)
                    _list_config_registry.append(cfg)
                    n += 1
            logger.info(
                f"Plugin '{ep.name}': {n} tool configs loaded, "
                f"{imported} modules imported from {plugin_dir}"
            )
        else:
            if imported:
                logger.debug(
                    f"Plugin '{ep.name}': {imported} modules imported, no JSON configs"
                )

        # Mark this plugin as fully processed so re-calls are no-ops
        _discovered_plugin_names.add(ep.name)


def _auto_import_subpackages(package_name: str = "tooluniverse"):
    """
    Import all installed sub-packages of ``package_name`` so their
    ``__init__.py`` files run and can self-register configs/tools.

    Only packages that have their own ``__init__.py`` are imported; plain
    directories (like ``data/``, ``cache/``) are skipped automatically.
    Errors are logged but never propagated — a broken sub-package must not
    prevent the main package from starting.
    """
    try:
        pkg = importlib.import_module(package_name)
    except ImportError:
        return

    for pkg_dir in pkg.__path__:
        try:
            base = Path(pkg_dir)
        except Exception:
            continue
        for subpkg in sorted(base.iterdir()):
            if not subpkg.is_dir():
                continue
            if not (subpkg / "__init__.py").exists():
                continue
            # Skip the built-in sub-packages that are part of the main repo
            # (they register themselves via the standard decorator path).
            # We only want EXTERNALLY installed sub-packages.
            # Heuristic: skip directories that are inside the main package dir
            # that lives in the editable-install source tree.
            full_mod = f"{package_name}.{subpkg.name}"
            if full_mod in sys.modules:
                continue
            try:
                importlib.import_module(full_mod)
                logger.debug(f"Auto-imported sub-package: {full_mod}")
            except Exception as exc:
                logger.debug(f"Could not auto-import sub-package {full_mod}: {exc}")


def auto_discover_tools(package_name=None, lazy=True):
    """
    Automatically discover and import all tool modules.
    If lazy=True, only builds the mapping without importing any modules.
    If lazy=False, imports all tool modules immediately.
    """
    global _discovery_completed

    if package_name is None:
        package_name = "tooluniverse"

    # In lazy mode, just build the registry without importing anything
    if lazy:
        if not _lazy_registry:
            build_lazy_registry(package_name)

            # CRITICAL FIX FOR FROZEN/BUNDLED ENVIRONMENTS:
            # If AST discovery yielded 0 results (e.g. no .py files found in Nuitka/PyInstaller bundle),
            # we MUST fallback to eager loading using pkgutil/importlib.
            # Otherwise, the server will start but have 0 tools, causing client timeouts/errors.
            if not _lazy_registry:
                logger.warning(
                    "Lazy discovery returned 0 tools (likely frozen/bundled environment). "
                    "Falling back to eager loading."
                )
                return auto_discover_tools(package_name, lazy=False)

            logger.debug(
                f"Lazy discovery complete. Registry contains {len(_lazy_registry)} tool mappings (no modules imported)"
            )
        return _lazy_registry.copy()

    # Return cached registry if full discovery already done
    if _discovery_completed:
        return _tool_registry.copy()

    try:
        package = importlib.import_module(package_name)
        package_path = package.__path__
    except (ImportError, AttributeError):
        logger.warning(f"Could not import package {package_name}")
        return _tool_registry.copy()

    logger.info(
        f"Auto-discovering tools in package: {package_name} (lazy={lazy}) - importing ALL modules"
    )

    # Import all tool modules (non-lazy mode)
    imported_count = 0
    # Use pkgutil to find modules, but rely on our AST mapping logic implicitly
    # or just iterate all modules found
    for _importer, modname, _ispkg in pkgutil.iter_modules(package_path):
        if "_tool" in modname or modname in ["compose_tool", "agentic_tool"]:
            if modname == "generate_tools":
                continue
            try:
                importlib.import_module(f"{package_name}.{modname}")
                logger.debug(f"Imported tool module: {modname}")
                imported_count += 1
            except Exception as e:
                logger.warning(f"Could not import {modname}: {type(e).__name__}: {e}")

    # Discover entry-point plugins (not in tooluniverse.* namespace, so pkgutil
    # won't find them above — must be discovered explicitly).
    _discover_entry_point_plugins()

    _discovery_completed = True
    logger.info(
        f"Full discovery complete. Imported {imported_count} modules, registered {len(_tool_registry)} tools"
    )
    return _tool_registry.copy()


def get_tool_class_lazy(tool_name):
    """
    Get a tool class by name, using lazy loading if possible.
    Only imports the specific module needed, not all modules.
    """
    # First try lazy import
    tool_class = lazy_import_tool(tool_name)
    if tool_class:
        return tool_class

    # If lazy loading fails and we haven't done full discovery yet,
    # check if the tool exists in the current registry
    if tool_name in _tool_registry:
        return _tool_registry[tool_name]

    # As a last resort, if full discovery hasn't been done, do it
    # But this should be rare with a properly configured lazy registry
    if not _discovery_completed:
        logger.warning(
            f"Tool {tool_name} not found in lazy registry, falling back to full discovery"
        )
        auto_discover_tools(lazy=False)
        return _tool_registry.get(tool_name)

    return None
