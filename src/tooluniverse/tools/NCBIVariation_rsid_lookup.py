"""
NCBIVariation_rsid_lookup

Look up a dbSNP rsID and retrieve variant details including GRCh38 genomic coordinates, associate...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBIVariation_rsid_lookup(
    rsid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Look up a dbSNP rsID and retrieve variant details including GRCh38 genomic coordinates, associate...

    Parameters
    ----------
    rsid : str
        dbSNP reference SNP ID. Examples: 'rs429358' (APOE epsilon-4 allele), 'rs7412...
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
    _args = {k: v for k, v in {"rsid": rsid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NCBIVariation_rsid_lookup",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBIVariation_rsid_lookup"]
