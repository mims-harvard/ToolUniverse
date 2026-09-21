"""
DDBJ_get_entry

Retrieve a DNA Data Bank of Japan record by accession. DDBJ is the third INSDC member alongside N...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DDBJ_get_entry(
    accession: str,
    entry_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a DNA Data Bank of Japan record by accession. DDBJ is the third INSDC member alongside N...

    Parameters
    ----------
    accession : str
        DDBJ accession, e.g. 'DRP000001', 'PRJDB3490', 'JGAS000001', 'E-GEAD-1000', '...
    entry_type : str
        Override the inferred entry type. One of: bioproject, biosample, sra-study, s...
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
        for k, v in {"accession": accession, "entry_type": entry_type}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DDBJ_get_entry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DDBJ_get_entry"]
