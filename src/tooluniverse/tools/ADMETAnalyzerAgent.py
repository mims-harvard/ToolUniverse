"""
ADMETAnalyzerAgent

AI agent that analyzes ADMET data and provides insights on drug-likeness and safety profiles
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ADMETAnalyzerAgent(
    compounds: str,
    admet_data: str,
    disease_context: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    AI agent that analyzes ADMET data and provides insights on drug-likeness and safety profiles

    Parameters
    ----------
    compounds : str
        List of compounds to analyze (comma-separated)
    admet_data : str
        ADMET data from computational tools to analyze
    disease_context : str
        Disease context for ADMET evaluation
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
            "name": "ADMETAnalyzerAgent",
            "arguments": {
                "compounds": compounds,
                "admet_data": admet_data,
                "disease_context": disease_context,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ADMETAnalyzerAgent"]
