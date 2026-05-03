"""
Mutalyzer_back_translate

Convert a protein-level HGVS variant to possible DNA-level variant descriptions using Mutalyzer. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Mutalyzer_back_translate(
    variant: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Convert a protein-level HGVS variant to possible DNA-level variant descriptions using Mutalyzer. ...

    Parameters
    ----------
    variant : str
        Protein-level HGVS variant description. Examples: 'NP_002993.1:p.Asp92Tyr' (S...
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
    _args = {k: v for k, v in {"variant": variant}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Mutalyzer_back_translate",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Mutalyzer_back_translate"]
