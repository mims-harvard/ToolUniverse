"""
LOVD_search_variants

Search variants in LOVD by DBID or HGVS DNA notation. Use variant_dbid for exact LOVD variant IDs...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LOVD_search_variants(
    gene_symbol: str,
    variant_dbid: Optional[str] = None,
    dna_notation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search variants in LOVD by DBID or HGVS DNA notation. Use variant_dbid for exact LOVD variant IDs...

    Parameters
    ----------
    gene_symbol : str
        HGNC gene symbol (e.g., 'TP53', 'BRCA1').
    variant_dbid : str
        LOVD variant DBID (e.g., 'TP53_010464'). Unique identifier assigned by LOVD.
    dna_notation : str
        HGVS DNA notation without RefSeq prefix (e.g., 'c.*2609C>A', 'c.742C>T'). Use...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "gene_symbol": gene_symbol,
            "variant_dbid": variant_dbid,
            "dna_notation": dna_notation,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LOVD_search_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LOVD_search_variants"]
