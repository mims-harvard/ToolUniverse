"""
python_script_runner

Run Python script files in isolated subprocess with resource limits and timeout. Supports command...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def python_script_runner(
    script_path: str,
    script_args: Optional[list[str]] = None,
    timeout: Optional[int] = 60,
    working_directory: Optional[str] = None,
    env_vars: Optional[dict[str, Any]] = None,
    dependencies: Optional[list[str]] = None,
    auto_install_dependencies: Optional[bool] = False,
    require_confirmation: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Run Python script files in isolated subprocess with resource limits and timeout. Supports command...

    Parameters
    ----------
    script_path : str
        Path to Python script file (.py) to execute
    script_args : list[str]
        Command-line arguments to pass to the script
    timeout : int
        Execution timeout in seconds
    working_directory : str
        Working directory for script execution (defaults to script directory)
    env_vars : dict[str, Any]
        Environment variables to set for script execution
    dependencies : list[str]
        List of Python packages that the script depends on. Will be checked and optio...
    auto_install_dependencies : bool
        Whether to automatically install missing dependencies without user confirmation
    require_confirmation : bool
        Whether to require user confirmation before installing packages
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "script_path": script_path,
            "script_args": script_args,
            "timeout": timeout,
            "working_directory": working_directory,
            "env_vars": env_vars,
            "dependencies": dependencies,
            "auto_install_dependencies": auto_install_dependencies,
            "require_confirmation": require_confirmation,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "python_script_runner",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["python_script_runner"]
