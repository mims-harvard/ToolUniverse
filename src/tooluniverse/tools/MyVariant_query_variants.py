"""
MyVariant_query_variants

Search for genetic variants by various criteria including rsID, gene, chromosome position, or cli...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MyVariant_query_variants(
    query: str,
    fields: Optional[
        str
    ] = "dbsnp.rsid,clinvar.rcv.clinical_significance,cadd.phred,gnomad_genome.af.af",
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for genetic variants by various criteria including rsID, gene, chromosome position, or cli...

    Parameters
    ----------
    query : str
        Search query. Examples: 'rs58991260' (rsID), 'chr7:g.55249071G>A' (HGVS), 'cl...
    fields : str
        Comma-separated fields to return. Common: dbsnp, clinvar, cadd, gnomad_genome...
    size : int
        Maximum number of results (1-100).
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
        for k, v in {"query": query, "fields": fields, "size": size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MyVariant_query_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MyVariant_query_variants"]
