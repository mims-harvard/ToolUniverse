"""
ELIXIRTeSS_search_events

Search ELIXIR TeSS for upcoming and past bioinformatics training events, workshops, and courses. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ELIXIRTeSS_search_events(
    q: Optional[str] = None,
    country: Optional[str] = None,
    event_type: Optional[str] = None,
    online: Optional[bool] = None,
    page_size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ELIXIR TeSS for upcoming and past bioinformatics training events, workshops, and courses. ...

    Parameters
    ----------
    q : str
        Search query for events. Examples: 'metagenomics workshop', 'NGS training', '...
    country : str
        Filter by country. Examples: 'United Kingdom', 'Germany', 'Netherlands', 'Onl...
    event_type : str
        Filter by event type. Values: 'workshops_and_courses', 'conferences', 'webinars'
    online : bool
        Filter to online events only (true/false)
    page_size : int
        Number of results to return (default 10)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "q": q,
            "country": country,
            "event_type": event_type,
            "online": online,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ELIXIRTeSS_search_events",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ELIXIRTeSS_search_events"]
