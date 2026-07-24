"""
KEGG_get_enzyme

Retrieve a KEGG ENZYME entry by EC number. Returns all NAMEs (accepted name plus synonyms), the C...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_get_enzyme(
    ec_number: Optional[str] = None,
    enzyme_id: Optional[str] = None,
    id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a KEGG ENZYME entry by EC number. Returns all NAMEs (accepted name plus synonyms), the C...

    Parameters
    ----------
    ec_number : str
        Enzyme Commission (EC) number, e.g. '2.7.1.1' (hexokinase), '1.1.1.1' (alcoho...
    enzyme_id : str
        Alias for ec_number.
    id : str
        Alias for ec_number.
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
        for k, v in {"ec_number": ec_number, "enzyme_id": enzyme_id, "id": id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_get_enzyme",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_get_enzyme"]
