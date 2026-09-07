"""
LOINC_get_answer_list

Get the answer lists published for a LOINC code -- the permissible coded values a list-type obser...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LOINC_get_answer_list(
    loinc_code: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the answer lists published for a LOINC code -- the permissible coded values a list-type obser...

    Parameters
    ----------
    loinc_code : str
        LOINC code whose answer lists you want (e.g. '883-9' for ABO group, '44250-9'...
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
    _args = {k: v for k, v in {"loinc_code": loinc_code}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "LOINC_get_answer_list",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LOINC_get_answer_list"]
