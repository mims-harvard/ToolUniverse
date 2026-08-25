"""
Python Code Execution Tools for ToolUniverse

This module provides two specialized tools for executing Python code:
1. python_code_executor - Execute Python code snippets safely in sandboxed environment
2. python_script_runner - Run Python script files in isolated subprocess
"""

import ast
import io
import locale
import os
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from importlib import metadata as importlib_metadata
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool


class BasePythonExecutor:
    """Base class for Python execution tools with shared security features."""

    # Safe builtins (whitelist approach)
    SAFE_BUILTINS = {
        "print",
        "len",
        "range",
        "enumerate",
        "zip",
        "map",
        "filter",
        "sorted",
        "sum",
        "min",
        "max",
        "abs",
        "round",
        "int",
        "float",
        "str",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "isinstance",
        "any",
        "all",
        "reversed",
        "slice",
        "type",
        # Note: getattr/setattr are intentionally NOT exposed. They allow
        # string-based attribute access (e.g. getattr(obj, "__class__")) that
        # bypasses the AST-level dunder check below and enables sandbox escape
        # through the interpreter's class hierarchy.
        "hasattr",
        "callable",
        "__import__",  # Needed for import statements
    }

    # Default allowed modules
    DEFAULT_ALLOWED_MODULES = {
        "math",
        "json",
        "datetime",
        "collections",
        "itertools",
        "re",
        "typing",
        "dataclasses",
        "decimal",
        "fractions",
        "statistics",
        "random",
        # Mathematical computing libraries
        "sympy",
        "numpy",
        "scipy",
        "matplotlib",
    }

    # Forbidden AST node types and their dangerous attributes
    FORBIDDEN_AST_NODES = {
        "Import": ["os", "sys", "subprocess", "socket", "urllib", "requests", "http"],
        "Call": ["open", "eval", "exec", "compile", "__import__", "input", "raw_input"],
        "Attribute": ["__import__", "open", "file"],
    }

    # Dangerous attribute names that pivot out of the sandbox.
    #
    # The allowed scientific modules (numpy, scipy, matplotlib, ...) transitively
    # expose dangerous stdlib modules as PLAIN, non-dunder attributes — e.g.
    # `numpy.ctypeslib` (-> ctypes -> CDLL -> native code), `matplotlib.os`,
    # `matplotlib.subprocess`, `random._os`, `collections._sys`. Reaching any of
    # them is arbitrary code execution (`ctypes.CDLL(None).system(...)`), and none
    # require a dunder, a forbidden import, or a forbidden call — so the existing
    # checks did not catch them.
    #
    # Because `getattr`/`globals`/`vars`/`eval`/`exec`/`compile` are all withheld
    # from the builtins whitelist, the ONLY way user code can reach an attribute is
    # the literal `obj.name` syntax, which is visible in the AST. Denying these
    # attribute names (normalized: leading underscores stripped, lower-cased, so
    # `_os`/`_sys` alias forms are also caught) therefore soundly blocks the pivot.
    #
    # Legitimate numeric attributes are deliberately NOT listed: numpy.random,
    # scipy.signal, scipy.fft, numpy.linalg, numpy.trace, re.compile, etc.
    DANGEROUS_ATTRIBUTE_NAMES = frozenset(
        {
            # OS / process / system modules
            "os",
            "sys",
            "subprocess",
            "posix",
            "nt",
            "socket",
            "platform",
            "shutil",
            "pathlib",
            "pty",
            "multiprocessing",
            "mmap",
            "fcntl",
            "resource",
            "termios",
            "tty",
            # import / introspection -> builtins, frames, code objects
            "importlib",
            "imp",
            "builtins",
            "runpy",
            "gc",
            "inspect",
            "types",
            "ctypes",
            "ctypeslib",
            "cffi",
            "pickle",
            "marshal",
            "pdb",
            "sysconfig",
            "distutils",
            "f2py",
            # FFI loaders (defense in depth; normally reached only via ctypes)
            "cdll",
            "windll",
            "oledll",
            "pydll",
            "libraryloader",
            "loadlibrary",
            "dlopen",
            # process-exec primitives (defense in depth)
            "system",
            "popen",
            "fork",
            "forkpty",
            "kill",
            "killpg",
            "execl",
            "execle",
            "execlp",
            "execlpe",
            "execv",
            "execve",
            "execvp",
            "execvpe",
            "spawnl",
            "spawnle",
            "spawnlp",
            "spawnlpe",
            "spawnv",
            "spawnve",
            "spawnvp",
            "spawnvpe",
            "getoutput",
            "getstatusoutput",
            "check_output",
            "check_call",
            # code-generation pivot that exec()s generated source
            "lambdify",
            # builtins module + its aliases (e.g. the enum module exposes it as
            # `bltns`): reaching it hands back getattr/eval/exec and re-enables
            # the class-hierarchy escape.
            "builtin",
            "bltns",
            # introspection builtins that re-enable string-based dunder traversal
            # or frame walking if reached through any module attribute.
            "getattr",
            "setattr",
            "delattr",
            "vars",
            "globals",
            "locals",
            "memoryview",
            "breakpoint",
            "currentframe",
        }
    )

    @classmethod
    def _is_dangerous_attribute(cls, name: Any) -> bool:
        """True for attribute names that pivot to native code / os / subprocess.

        Normalizes leading underscores and case so alias forms like ``_os`` and
        ``CDLL`` are caught the same as ``os`` / ``cdll``.
        """
        if not isinstance(name, str):
            return False
        return name.lstrip("_").lower() in cls.DANGEROUS_ATTRIBUTE_NAMES

    def __init__(self, tool_config: Dict[str, Any]):
        """Initialize the executor with tool configuration."""
        self.tool_config = tool_config
        self.allowed_modules = set(self.DEFAULT_ALLOWED_MODULES)

        # Add custom allowed modules if specified
        if "allowed_imports" in tool_config:
            self.allowed_modules.update(tool_config["allowed_imports"])

    def _is_module_allowed(self, name: str) -> bool:
        """Return whether *name* is an allowed module or one of its submodules."""
        if name in self.allowed_modules:
            return True

        for allowed in self.allowed_modules:
            prefix = f"{allowed}."
            if name.startswith(prefix):
                submodule_parts = name[len(prefix) :].split(".")
                return not any(
                    self._is_dangerous_attribute(part) for part in submodule_parts
                )

        return False

    @staticmethod
    def _is_dunder(name: Any) -> bool:
        """Return True for double-underscore names like ``__class__``.

        These names are the entry points used to walk out of the sandbox via the
        interpreter's class hierarchy (``__class__`` -> ``__bases__`` ->
        ``__subclasses__`` -> ``__init__`` -> ``__globals__`` -> ``__builtins__``).
        """
        return (
            isinstance(name, str)
            and len(name) > 4
            and name.startswith("__")
            and name.endswith("__")
        )

    def _check_ast_safety(self, code: str) -> tuple[bool, List[str]]:
        """
        Check code AST for dangerous operations.

        Returns:
            (is_safe, warnings)
        """
        warnings = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"Syntax error: {e.msg} at line {e.lineno}"]

        for node in ast.walk(tree):
            # Check for forbidden imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Check if import is forbidden AND not explicitly allowed
                    if (
                        alias.name in self.FORBIDDEN_AST_NODES["Import"]
                        and alias.name not in self.allowed_modules
                    ):
                        warnings.append(f"Forbidden import: {alias.name}")

            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                module_parts = module_name.split(".") if module_name else []
                module_root = module_parts[0] if module_parts else ""

                if (
                    module_root in self.FORBIDDEN_AST_NODES["Import"]
                    and module_root not in self.allowed_modules
                ):
                    warnings.append(f"Forbidden import: {module_name}")

                dangerous_module_parts = [
                    part
                    for part in module_parts[1:]
                    if self._is_dangerous_attribute(part)
                ]
                if dangerous_module_parts:
                    warnings.append(
                        f"Forbidden import path (sandbox escape): {module_name}"
                    )

                for alias in node.names:
                    if alias.name == "*":
                        warnings.append(
                            "Forbidden wildcard import: imported names cannot be "
                            "validated safely"
                        )
                    elif self._is_dangerous_attribute(alias.name):
                        warnings.append(
                            f"Forbidden imported name (sandbox escape): {alias.name}"
                        )

            # Check for forbidden function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.FORBIDDEN_AST_NODES["Call"]:
                        warnings.append(f"Forbidden function call: {node.func.id}")
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in self.FORBIDDEN_AST_NODES["Call"]:
                        warnings.append(f"Forbidden method call: {node.func.attr}")

            # Block ALL dunder attribute access (e.g. obj.__class__). A name-based
            # denylist of specific dangerous attributes is not sound; any dunder
            # can be chained to reach a live os/subprocess reference, so deny the
            # whole class of attribute access rather than enumerate it.
            elif isinstance(node, ast.Attribute):
                if self._is_dunder(node.attr):
                    warnings.append(f"Forbidden dunder attribute access: {node.attr}")
                elif node.attr in self.FORBIDDEN_AST_NODES["Attribute"]:
                    warnings.append(f"Forbidden attribute access: {node.attr}")
                elif self._is_dangerous_attribute(node.attr):
                    # Blocks module-pivot / FFI escapes such as numpy.ctypeslib,
                    # matplotlib.subprocess, random._os, ...CDLL, os.system.
                    warnings.append(
                        f"Forbidden attribute access (sandbox escape): {node.attr}"
                    )

            # Block bare dunder names (e.g. __builtins__, __import__) so they
            # cannot be read directly out of the execution namespace.
            elif isinstance(node, ast.Name):
                if self._is_dunder(node.id):
                    warnings.append(f"Forbidden dunder name: {node.id}")

            # Block dunder string literals. With getattr removed this is defense
            # in depth: it stops string-based traversal such as
            # globals()["__builtins__"] or vars(obj)["__class__"].
            elif isinstance(node, ast.Constant):
                if self._is_dunder(node.value):
                    warnings.append(f"Forbidden dunder string literal: {node.value}")

        return len(warnings) == 0, warnings

    def _create_safe_globals(
        self, additional_vars: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a safe globals dictionary with restricted builtins."""
        # Create restricted builtins
        safe_builtins = {}
        for name in self.SAFE_BUILTINS:
            if hasattr(__builtins__, name):
                safe_builtins[name] = getattr(__builtins__, name)
            elif hasattr(__builtins__, "__dict__") and name in __builtins__.__dict__:
                safe_builtins[name] = __builtins__.__dict__[name]
            else:
                # Try to get from builtins module directly
                try:
                    import builtins

                    if hasattr(builtins, name):
                        safe_builtins[name] = getattr(builtins, name)
                except ImportError:
                    pass

        # Create safe __import__ function
        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            """Safe import function that only allows pre-approved modules."""
            if self._is_module_allowed(name):
                return __import__(name, globals, locals, fromlist, level)
            else:
                raise ImportError(
                    f"Module '{name}' is not allowed. Allowed modules: {list(self.allowed_modules)}"
                )

        safe_builtins["__import__"] = safe_import

        # Pre-import allowed modules
        safe_modules = {}
        for module_name in self.allowed_modules:
            try:
                safe_modules[module_name] = __import__(module_name)
            except ImportError:
                pass  # Skip modules that can't be imported

        globals_dict = {"__builtins__": safe_builtins, **safe_modules}

        # Add additional variables
        if additional_vars:
            globals_dict.update(additional_vars)

        return globals_dict

    def _capture_output(self, func, *args, **kwargs):
        """Capture stdout and stderr during function execution."""
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        try:
            result = func(*args, **kwargs)
            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()
            return result, stdout_content, stderr_content
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _handle_timeout(self, signum, frame):
        """Handle execution timeout."""
        raise TimeoutError("Code execution timed out")

    def _execute_with_timeout(self, func, timeout_seconds: int, *args, **kwargs):
        """Execute function with timeout using signal or threading."""
        import threading

        # Check if we're in the main thread
        is_main_thread = threading.current_thread() is threading.main_thread()

        # Use threading timeout if not in main thread or on Windows
        if not is_main_thread or not hasattr(signal, "SIGALRM"):
            # Use threading timeout (works in all threads)
            result_container = [None]
            exception_container = [None]

            def target():
                try:
                    result_container[0] = func(*args, **kwargs)
                except Exception as e:
                    exception_container[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout_seconds)

            if thread.is_alive():
                raise TimeoutError("Code execution timed out")

            if exception_container[0]:
                raise exception_container[0]

            return result_container[0]

        # Use signal timeout only in main thread on Unix systems
        else:
            try:
                old_handler = signal.signal(signal.SIGALRM, self._handle_timeout)
                signal.alarm(timeout_seconds)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
            except (ValueError, AttributeError):
                # Fallback to threading if signal fails for any reason
                result_container = [None]
                exception_container = [None]

                def target():
                    try:
                        result_container[0] = func(*args, **kwargs)
                    except Exception as e:
                        exception_container[0] = e

                thread = threading.Thread(target=target)
                thread.daemon = True
                thread.start()
                thread.join(timeout_seconds)

                if thread.is_alive():
                    raise TimeoutError("Code execution timed out")

                if exception_container[0]:
                    raise exception_container[0]

                return result_container[0]

    def _format_error_response(
        self,
        error: Exception,
        error_type: str,
        stdout: str = "",
        stderr: str = "",
        execution_time: float = 0,
    ) -> Dict[str, Any]:
        """Format error response with detailed information."""
        return {
            "success": False,
            "result": None,
            "stdout": stdout,
            "stderr": stderr,
            "execution_time_ms": int(execution_time * 1000),
            "memory_used_mb": 0,  # Not easily measurable in this context
            "error": str(error),
            "error_type": error_type,
            "traceback": traceback.format_exc(),
            "metadata": {
                "code_lines": 0,
                "ast_warnings": [],
                "allowed_modules": list(self.allowed_modules),
            },
        }

    def _format_success_response(
        self,
        result: Any,
        stdout: str,
        stderr: str,
        execution_time: float,
        code_lines: int = 0,
        ast_warnings: List[str] = None,
    ) -> Dict[str, Any]:
        """Format success response with execution details."""
        return {
            "success": True,
            "result": result,
            "stdout": stdout,
            "stderr": stderr,
            "execution_time_ms": int(execution_time * 1000),
            "memory_used_mb": 0,  # Not easily measurable in this context
            "error": None,
            "error_type": None,
            "traceback": None,
            "metadata": {
                "code_lines": code_lines,
                "ast_warnings": ast_warnings or [],
                "allowed_modules": list(self.allowed_modules),
            },
        }

    def _check_and_install_dependencies(
        self,
        dependencies: List[str],
        auto_install: bool = False,
        require_confirmation: bool = True,
    ) -> Dict[str, Any]:
        """Check and optionally install missing dependencies with user confirmation."""
        if not dependencies:
            return {"success": True, "message": "No dependencies to check"}

        missing_packages = []
        installed_packages = []

        print(f"📦 Checking dependencies: {dependencies}")

        for package in dependencies:
            # Dependencies are distribution names passed to pip, not necessarily
            # import-package names. Checking imports conflates distributions that
            # expose the same module (for example onnxruntime and
            # onnxruntime-gpu), so consult installed distribution metadata.
            try:
                importlib_metadata.version(package)
                print(f"   ✅ {package} distribution is installed")
            except importlib_metadata.PackageNotFoundError:
                print(f"   ❌ {package} is not installed")
                missing_packages.append(package)

        if not missing_packages:
            return {"success": True, "message": "All dependencies are available"}

        print(f"\n⚠️  Missing packages: {missing_packages}")

        # Preserve exact distribution identities and caller order. Distribution
        # names may legitimately contain dots, so they must not be truncated as
        # though they were import submodules.
        packages_to_install = list(dict.fromkeys(missing_packages))

        # Handle missing packages
        if not auto_install:
            if require_confirmation:
                print("\n🔐 Security Notice:")
                print(
                    f"   The following packages need to be installed: {packages_to_install}"
                )
                print(f"   This will run: pip install {' '.join(packages_to_install)}")
                print("   ⚠️  Only install packages from trusted sources!")

                # In a real implementation, this would prompt the user
                # For now, we'll return a message asking for confirmation
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "missing_packages": missing_packages,
                    "packages_to_install": packages_to_install,
                    "install_command": f"pip install {' '.join(packages_to_install)}",
                    "message": "User confirmation required for package installation",
                }
            else:
                return {
                    "success": False,
                    "missing_packages": missing_packages,
                    "packages_to_install": packages_to_install,
                    "message": "Missing dependencies detected, auto-install disabled",
                }

        # Auto-install missing packages
        print("💿 Installing missing packages...")

        for package_to_install in packages_to_install:
            try:
                print(f"   📥 Installing {package_to_install}...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", package_to_install],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode == 0:
                    print(f"   ✅ Successfully installed {package_to_install}")
                    installed_packages.append(package_to_install)

                    # Verify installation
                    try:
                        importlib_metadata.version(package_to_install)
                        print(f"   ✅ {package_to_install} installation verified")
                    except importlib_metadata.PackageNotFoundError:
                        print(
                            f"   ⚠️ {package_to_install} installed but distribution metadata was not found"
                        )
                else:
                    print(
                        f"   ❌ Failed to install {package_to_install}: {result.stderr}"
                    )
                    return {
                        "success": False,
                        "error": f"Failed to install {package_to_install}: {result.stderr}",
                        "installed_packages": installed_packages,
                    }

            except Exception as e:
                print(f"   ❌ Error installing {package_to_install}: {e}")
                return {
                    "success": False,
                    "error": f"Error installing {package_to_install}: {e}",
                    "installed_packages": installed_packages,
                }

        print("✅ All dependencies installed successfully")
        return {
            "success": True,
            "installed_packages": installed_packages,
            "message": f"Successfully installed {len(installed_packages)} packages",
        }


@register_tool("PythonCodeExecutor")
class PythonCodeExecutor(BasePythonExecutor, BaseTool):
    """Execute Python code snippets safely in sandboxed environment."""

    def __init__(self, tool_config: Dict[str, Any]):
        BasePythonExecutor.__init__(self, tool_config)
        BaseTool.__init__(self, tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python code snippet with safety checks and timeout."""
        try:
            # Extract parameters
            code = arguments.get("code", "")
            if not code:
                error_response = self._format_error_response(
                    ValueError("Code parameter is required"),
                    "ValueError",
                    execution_time=0,
                )
                return {"status": "error", "data": error_response}

            timeout = arguments.get("timeout", 30)
            timeout = min(max(timeout, 1), 300)  # Clamp between 1-300 seconds

            return_variable = arguments.get("return_variable", "result")
            additional_vars = arguments.get("arguments", {})

            # SECURITY: The set of importable modules is a server-side trust
            # boundary configured via tool_config["allowed_imports"]. It must
            # NOT be widened by caller-supplied arguments, or a caller could
            # allowlist os/subprocess and disable the sandbox before it runs.
            if "allowed_imports" in arguments:
                error_response = self._format_error_response(
                    ValueError(
                        "allowed_imports cannot be set per call; import permissions "
                        "must be configured by the server administrator"
                    ),
                    "SecurityError",
                    execution_time=0,
                )
                return {"status": "error", "data": error_response}

            # Check AST safety
            is_safe, ast_warnings = self._check_ast_safety(code)
            if not is_safe:
                error_response = self._format_error_response(
                    ValueError(
                        f"Code contains forbidden operations: {', '.join(ast_warnings)}"
                    ),
                    "SecurityError",
                    execution_time=0,
                )
                return {"status": "error", "data": error_response}

            # Check dependencies if provided
            dependencies = arguments.get("dependencies", [])
            auto_install = arguments.get("auto_install_dependencies", False)
            require_confirmation = arguments.get("require_confirmation", True)

            if dependencies:
                dep_result = self._check_and_install_dependencies(
                    dependencies, auto_install, require_confirmation
                )

                if not dep_result["success"]:
                    if dep_result.get("requires_confirmation"):
                        return {
                            "success": False,
                            "data": {
                                "requires_confirmation": True,
                                "missing_packages": dep_result["missing_packages"],
                                "packages_to_install": dep_result.get(
                                    "packages_to_install", []
                                ),
                                "install_command": dep_result["install_command"],
                                "message": dep_result["message"],
                            },
                        }
                    else:
                        error_response = self._format_error_response(
                            RuntimeError(
                                dep_result.get("error", dep_result["message"])
                            ),
                            "DependencyError",
                            execution_time=0,
                        )
                        return {"status": "error", "data": error_response}

            # Create safe execution environment
            safe_globals = self._create_safe_globals(additional_vars)
            safe_locals = {}

            # Execute with timeout and output capture
            start_time = time.time()

            def execute_code():
                return self._capture_output(exec, code, safe_globals, safe_locals)

            try:
                result, stdout, stderr = self._execute_with_timeout(
                    execute_code, timeout
                )
                execution_time = time.time() - start_time

                # Extract result from locals
                final_result = safe_locals.get(return_variable, None)

                # Count code lines
                code_lines = len(code.splitlines())

                success_response = self._format_success_response(
                    final_result,
                    stdout,
                    stderr,
                    execution_time,
                    code_lines,
                    ast_warnings,
                )
                return {"status": "success", "data": success_response}

            except TimeoutError:
                execution_time = time.time() - start_time
                error_response = self._format_error_response(
                    TimeoutError(f"Code execution timed out after {timeout} seconds"),
                    "TimeoutError",
                    execution_time=execution_time,
                )
                return {"status": "error", "data": error_response}

        except Exception as e:
            error_response = self._format_error_response(
                e, type(e).__name__, execution_time=0
            )
            return {"status": "error", "data": error_response}


@register_tool("PythonScriptRunner")
class PythonScriptRunner(BasePythonExecutor, BaseTool):
    """Run Python script files in isolated subprocess with resource limits."""

    def __init__(self, tool_config: Dict[str, Any]):
        BasePythonExecutor.__init__(self, tool_config)
        BaseTool.__init__(self, tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run Python script file in subprocess with safety limits."""
        try:
            # Extract parameters
            script_path = arguments.get("script_path", "")
            if not script_path:
                error_response = self._format_error_response(
                    ValueError("script_path parameter is required"),
                    "ValueError",
                    execution_time=0,
                )
                return {"status": "error", "data": error_response}

            if not os.path.exists(script_path):
                error_response = self._format_error_response(
                    FileNotFoundError(f"Script file not found: {script_path}"),
                    "FileNotFoundError",
                    execution_time=0,
                )
                return {"status": "error", "data": error_response}

            script_args = arguments.get("script_args", [])
            timeout = arguments.get("timeout", 60)
            working_dir = arguments.get("working_directory", os.getcwd())
            env_vars = arguments.get("env_vars", {})

            # Check dependencies if provided
            dependencies = arguments.get("dependencies", [])
            auto_install = arguments.get("auto_install_dependencies", False)
            require_confirmation = arguments.get("require_confirmation", True)

            if dependencies:
                dep_result = self._check_and_install_dependencies(
                    dependencies, auto_install, require_confirmation
                )

                if not dep_result["success"]:
                    if dep_result.get("requires_confirmation"):
                        return {
                            "success": False,
                            "data": {
                                "requires_confirmation": True,
                                "missing_packages": dep_result["missing_packages"],
                                "packages_to_install": dep_result.get(
                                    "packages_to_install", []
                                ),
                                "install_command": dep_result["install_command"],
                                "message": dep_result["message"],
                            },
                        }
                    else:
                        error_response = self._format_error_response(
                            RuntimeError(
                                dep_result.get("error", dep_result["message"])
                            ),
                            "DependencyError",
                            execution_time=0,
                        )
                        return {"status": "error", "data": error_response}

            # Create restricted environment
            restricted_env = os.environ.copy()
            restricted_env.update(env_vars)
            # Remove potentially dangerous environment variables
            dangerous_vars = ["PYTHONPATH", "PATH"]
            for var in dangerous_vars:
                if var in restricted_env:
                    del restricted_env[var]

            # Prepare command
            cmd = [sys.executable, script_path] + script_args

            # Execute in subprocess
            start_time = time.time()

            # File-backed output avoids waiting for pipe EOF after the child
            # has exited. That can hang on Windows when another process
            # inherits a duplicate pipe writer. It also lets us return output
            # already written when the process times out.
            with (
                tempfile.TemporaryFile() as stdout_file,
                tempfile.TemporaryFile() as stderr_file,
            ):
                try:
                    result = subprocess.run(
                        cmd,
                        cwd=working_dir,
                        env=restricted_env,
                        stdin=subprocess.DEVNULL,
                        stdout=stdout_file,
                        stderr=stderr_file,
                        close_fds=True,
                        timeout=timeout,
                    )
                except subprocess.TimeoutExpired:
                    execution_time = time.time() - start_time
                    stdout = self._read_subprocess_output(stdout_file)
                    stderr = self._read_subprocess_output(stderr_file)
                    error_response = self._format_error_response(
                        TimeoutError(
                            f"Script execution timed out after {timeout} seconds"
                        ),
                        "TimeoutError",
                        stdout,
                        stderr,
                        execution_time,
                    )
                    return {"status": "error", "data": error_response}

                stdout = self._read_subprocess_output(stdout_file)
                stderr = self._read_subprocess_output(stderr_file)

            execution_time = time.time() - start_time

            if result.returncode == 0:
                success_response = self._format_success_response(
                    f"Script executed successfully (exit code: {result.returncode})",
                    stdout,
                    stderr,
                    execution_time,
                    code_lines=0,  # Not easily measurable for external scripts
                )
                return {"status": "success", "data": success_response}
            else:
                error_response = self._format_error_response(
                    RuntimeError(f"Script failed with exit code {result.returncode}"),
                    "RuntimeError",
                    stdout,
                    stderr,
                    execution_time,
                )
                return {"status": "error", "data": error_response}

        except Exception as e:
            error_response = self._format_error_response(
                e, type(e).__name__, execution_time=0
            )
            return {"status": "error", "data": error_response}

    @staticmethod
    def _read_subprocess_output(output_file) -> str:
        """Read binary subprocess output with ``text=True`` newline semantics."""
        output_file.flush()
        output_file.seek(0)
        output = output_file.read().decode(
            locale.getpreferredencoding(False), errors="replace"
        )
        return output.replace("\r\n", "\n").replace("\r", "\n")
