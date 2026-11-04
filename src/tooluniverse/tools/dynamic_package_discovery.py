"""
dynamic_package_discovery

Dynamically searches PyPI and evaluates packages based on requirements
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def dynamic_package_discovery(
    requirements: str,
    functionality: Optional[str] = None,
    constraints: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Dynamically searches PyPI and evaluates packages based on requirements

    Parameters
    ----------
    requirements : str
        Description of what the package should do
    functionality : str
        Specific functionality needed
    constraints : dict[str, Any]
        Constraints (python version, license, etc.)
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
            "requirements": requirements,
            "functionality": functionality,
            "constraints": constraints,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "dynamic_package_discovery",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["dynamic_package_discovery"]
