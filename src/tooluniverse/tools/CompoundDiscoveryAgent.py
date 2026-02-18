"""
CompoundDiscoveryAgent

AI agent that analyzes potential drug compounds using multiple strategies and LLM reasoning
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CompoundDiscoveryAgent(
    disease_name: str,
    targets: str,
    context: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    AI agent that analyzes potential drug compounds using multiple strategies and LLM reasoning

    Parameters
    ----------
    disease_name : str
        Name of the disease
    targets : str
        List of therapeutic targets (comma-separated)
    context : str
        Additional context or specific requirements
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

    return get_shared_client().run_one_function(
        {
            "name": "CompoundDiscoveryAgent",
            "arguments": {
                "disease_name": disease_name,
                "targets": targets,
                "context": context,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CompoundDiscoveryAgent"]
