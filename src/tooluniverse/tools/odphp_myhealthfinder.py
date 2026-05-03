"""
odphp_myhealthfinder

This tool provides personalized preventive-care recommendations and it is helpful for different a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def odphp_myhealthfinder(
    lang: str,
    age: int,
    sex: str,
    pregnant: str,
    strip_html: bool,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    This tool provides personalized preventive-care recommendations and it is helpful for different a...

    Parameters
    ----------
    lang : str
        Language code (en or es)
    age : int
        Age in years (0–120)
    sex : str
        Male or Female
    pregnant : str
        "Yes" or "No"
    strip_html : bool
        If true, also return PlainSections[] with HTML removed for each topic
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
            "lang": lang,
            "age": age,
            "sex": sex,
            "pregnant": pregnant,
            "strip_html": strip_html,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "odphp_myhealthfinder",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["odphp_myhealthfinder"]
