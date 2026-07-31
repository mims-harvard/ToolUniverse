"""
ClassyFire_classify_by_inchikey

Classify a chemical structure into the ClassyFire ChemOnt chemical taxonomy by its InChIKey. Retu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClassyFire_classify_by_inchikey(
    inchikey: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Classify a chemical structure into the ClassyFire ChemOnt chemical taxonomy by its InChIKey. Retu...

    Parameters
    ----------
    inchikey : str
        Full 27-character InChIKey, e.g. 'BSYNRYMUTXBXSQ-UHFFFAOYSA-N' (aspirin).
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
    _args = {k: v for k, v in {"inchikey": inchikey}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ClassyFire_classify_by_inchikey",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClassyFire_classify_by_inchikey"]
