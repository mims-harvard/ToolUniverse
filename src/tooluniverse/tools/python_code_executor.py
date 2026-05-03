"""
python_code_executor

Execute Python code snippets safely in sandboxed environment with timeout and resource limits. Su...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def python_code_executor(
    code: str,
    arguments: Optional[dict[str, Any]] = None,
    timeout: Optional[int] = 30,
    return_variable: Optional[str] = "result",
    allowed_imports: Optional[list[str]] = None,
    dependencies: Optional[list[str]] = None,
    auto_install_dependencies: Optional[bool] = False,
    require_confirmation: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Execute Python code snippets safely in sandboxed environment with timeout and resource limits. Su...

    Parameters
    ----------
    code : str
        Python code to execute. Can use variables from 'arguments' parameter. Use 're...
    arguments : dict[str, Any]
        Variables to pass into execution environment as dictionary. Keys become varia...
    timeout : int
        Execution timeout in seconds
    return_variable : str
        Variable name to extract as result from the executed code
    allowed_imports : list[str]
        Additional allowed modules beyond the default safe set (math, json, datetime,...
    dependencies : list[str]
        List of Python packages that the code depends on. Will be checked and optiona...
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
            "code": code,
            "arguments": arguments,
            "timeout": timeout,
            "return_variable": return_variable,
            "allowed_imports": allowed_imports,
            "dependencies": dependencies,
            "auto_install_dependencies": auto_install_dependencies,
            "require_confirmation": require_confirmation,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "python_code_executor",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["python_code_executor"]
