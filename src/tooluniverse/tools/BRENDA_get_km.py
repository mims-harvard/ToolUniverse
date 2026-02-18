"""
BRENDA_get_km

Get Km (Michaelis constant) values from BRENDA enzyme database. Km indicates substrate affinity -...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BRENDA_get_km(
    operation: str,
    ec_number: str,
    organism: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get Km (Michaelis constant) values from BRENDA enzyme database. Km indicates substrate affinity -...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_km)
    ec_number : str
        EC number (e.g., 1.1.1.1 for alcohol dehydrogenase, 2.7.1.1 for hexokinase)
    organism : str
        Optional organism filter (e.g., 'Homo sapiens', 'Escherichia coli')
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
            "name": "BRENDA_get_km",
            "arguments": {
                "operation": operation,
                "ec_number": ec_number,
                "organism": organism,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BRENDA_get_km"]
