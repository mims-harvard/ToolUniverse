"""
KEGG_get_module

Retrieve a KEGG MODULE entry: a functional reaction-unit (a defined set of reaction steps) that i...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_get_module(
    module_id: Optional[str] = None,
    id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a KEGG MODULE entry: a functional reaction-unit (a defined set of reaction steps) that i...

    Parameters
    ----------
    module_id : str
        KEGG module identifier, e.g. 'M00001' (glycolysis EM pathway), 'M00002' (glyc...
    id : str
        Alias for module_id.
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
        k: v for k, v in {"module_id": module_id, "id": id}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_get_module",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_get_module"]
