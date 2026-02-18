"""
HypothesisGenerator

Generates research hypotheses based on provided background context, domain, and desired format. U...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HypothesisGenerator(
    context: str,
    domain: str,
    number_of_hypotheses: str,
    hypothesis_format: Optional[str] = "concise declarative sentences",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Generates research hypotheses based on provided background context, domain, and desired format. U...

    Parameters
    ----------
    context : str
        Background information, observations, or data description from which to deriv...
    domain : str
        Field of study or research area (e.g., 'neuroscience', 'ecology', 'materials ...
    number_of_hypotheses : str
        Number of hypotheses to generate (e.g., '3', '5').
    hypothesis_format : str
        Optional directive on how to structure each hypothesis. Choose from one of th...
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
            "name": "HypothesisGenerator",
            "arguments": {
                "context": context,
                "domain": domain,
                "number_of_hypotheses": number_of_hypotheses,
                "hypothesis_format": hypothesis_format,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HypothesisGenerator"]
