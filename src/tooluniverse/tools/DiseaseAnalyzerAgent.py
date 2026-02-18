"""
DiseaseAnalyzerAgent

AI agent that analyzes disease characteristics and identifies potential therapeutic targets using...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DiseaseAnalyzerAgent(
    disease_name: str,
    context: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    AI agent that analyzes disease characteristics and identifies potential therapeutic targets using...

    Parameters
    ----------
    disease_name : str
        Name of the disease to analyze
    context : str
        Additional context or specific focus areas
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
            "name": "DiseaseAnalyzerAgent",
            "arguments": {"disease_name": disease_name, "context": context},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DiseaseAnalyzerAgent"]
