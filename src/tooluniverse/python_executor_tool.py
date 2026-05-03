"""
Python Code Execution Tools for ToolUniverse

This module provides two specialized tools for executing Python code:
1. python_code_executor - Execute Python code snippets safely in sandboxed environment
2. python_script_runner - Run Python script files in isolated subprocess
"""

import ast
import io
import os
import signal
import subprocess
import sys
import time
import traceback
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
        "getattr",
        "setattr",
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

    def __init__(self, tool_config: Dict[str, Any]):
        """Initialize the executor with tool configuration."""
        self.tool_config = tool_config
        self.allowed_modules = set(self.DEFAULT_ALLOWED_MODULES)

        # Add custom allowed modules if specified
        if "allowed_imports" in tool_config:
            self.allowed_modules.update(tool_config["allowed_imports"])

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

            # Check for forbidden function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.FORBIDDEN_AST_NODES["Call"]:
                        warnings.append(f"Forbidden function call: {node.func.id}")
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in self.FORBIDDEN_AST_NODES["Call"]:
                        warnings.append(f"Forbidden method call: {node.func.attr}")

            # Check for forbidden attribute access
            elif isinstance(node, ast.Attribute):
                if node.attr in self.FORBIDDEN_AST_NODES["Attribute"]:
                    warnings.append(f"Forbidden attribute access: {node.attr}")

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
            if name in self.allowed_modules:
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

    def _get_package_to_install(self, package: str) -> str:
        """Get the actual package name to install (parent package for submodules)"""
        if "." in package:
            # For submodules like 'keggtools.keggrest', install the parent package 'keggtools'
            return package.split(".")[0]
        return package

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
            # Try multiple import strategies
            import_success = False

            # Strategy 1: Direct package name
            try:
                __import__(package.replace("-", "_"))
                print(f"   ✅ {package} is installed (direct import)")
                import_success = True
            except ImportError:
                pass

            # Strategy 2: Try common submodule patterns
            if not import_success:
                patterns = [
                    package.replace("-", "_"),
                    package.replace("-", ""),
                    package.split("-")[0],  # For packages like 'keggtools' -> 'kegg'
                ]

                for pattern in patterns:
                    try:
                        __import__(pattern)
                        print(f"   ✅ {package} is installed (as {pattern})")
                        import_success = True
                        break
                    except ImportError:
                        continue

            # Strategy 3: Check if it's a submodule (e.g., keggtools.api)
            if not import_success and "." in package:
                try:
                    __import__(package)
                    print(f"   ✅ {package} is installed (submodule)")
                    import_success = True
                except ImportError:
                    pass

            # Strategy 4: Check parent package for submodules
            if not import_success and "." in package:
                parent_package = package.split(".")[0]
                try:
                    parent_module = __import__(parent_package)
                    # Try to access the submodule
                    submodule_name = package.split(".")[1]
                    if hasattr(parent_module, submodule_name):
                        print(
                            f"   ✅ {package} is available (submodule of {parent_package})"
                        )
                        import_success = True
                    else:
                        # Try importing the submodule directly
                        __import__(package)
                        print(f"   ✅ {package} is installed (submodule)")
                        import_success = True
                except ImportError:
                    pass

            if not import_success:
                print(f"   ❌ {package} is not installed")
                missing_packages.append(package)

        if not missing_packages:
            return {"success": True, "message": "All dependencies are available"}

        print(f"\n⚠️  Missing packages: {missing_packages}")

        # Get packages to actually install (parent packages for submodules)
        packages_to_install = [
            self._get_package_to_install(pkg) for pkg in missing_packages
        ]
        packages_to_install = list(set(packages_to_install))  # Remove duplicates

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
                        __import__(package_to_install.replace("-", "_"))
                        print(f"   ✅ {package_to_install} import verified")
                    except ImportError:
                        print(
                            f"   ⚠️ {package_to_install} installed but import may need different name"
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

            # Update allowed modules if specified
            if "allowed_imports" in arguments:
                self.allowed_modules.update(arguments["allowed_imports"])

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

            try:
                result = subprocess.run(
                    cmd,
                    cwd=working_dir,
                    env=restricted_env,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                execution_time = time.time() - start_time

                if result.returncode == 0:
                    success_response = self._format_success_response(
                        f"Script executed successfully "
                        f"(exit code: {result.returncode})",
                        result.stdout,
                        result.stderr,
                        execution_time,
                        code_lines=0,  # Not easily measurable for external scripts
                    )
                    return {"status": "success", "data": success_response}
                else:
                    error_response = self._format_error_response(
                        RuntimeError(
                            f"Script failed with exit code {result.returncode}"
                        ),
                        "RuntimeError",
                        result.stdout,
                        result.stderr,
                        execution_time,
                    )
                    return {"status": "error", "data": error_response}

            except subprocess.TimeoutExpired:
                execution_time = time.time() - start_time
                error_response = self._format_error_response(
                    TimeoutError(f"Script execution timed out after {timeout} seconds"),
                    "TimeoutError",
                    execution_time=execution_time,
                )
                return {"status": "error", "data": error_response}

        except Exception as e:
            error_response = self._format_error_response(
                e, type(e).__name__, execution_time=0
            )
            return {"status": "error", "data": error_response}
