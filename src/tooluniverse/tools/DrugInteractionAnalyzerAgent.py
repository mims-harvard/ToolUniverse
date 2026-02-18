"""
DrugInteractionAnalyzerAgent

AI agent that analyzes drug-drug interactions and provides clinical recommendations
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DrugInteractionAnalyzerAgent(
    compounds: str,
    patient_context: Optional[str] = "General adult population",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    AI agent that analyzes drug-drug interactions and provides clinical recommendations

    Parameters
    ----------
    compounds : str
        List of compounds to analyze for interactions (comma-separated)
    patient_context : str
        Patient context (age, comorbidities, medications, etc.)
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
            "name": "DrugInteractionAnalyzerAgent",
            "arguments": {"compounds": compounds, "patient_context": patient_context},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DrugInteractionAnalyzerAgent"]
