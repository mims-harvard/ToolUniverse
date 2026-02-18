"""
AdverseEventICDMapper

Extracts adverse events from narrative clinical or pharmacovigilance text and maps each event to ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AdverseEventICDMapper(
    source_text: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    Extracts adverse events from narrative clinical or pharmacovigilance text and maps each event to ...

    Parameters
    ----------
    source_text : str
        Unstructured narrative text that may mention adverse events.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    str
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {"name": "AdverseEventICDMapper", "arguments": {"source_text": source_text}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AdverseEventICDMapper"]
