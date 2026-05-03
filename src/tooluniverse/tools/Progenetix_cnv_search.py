"""
Progenetix_cnv_search

Search for cancer biosamples with copy number variations (CNVs) in a specific genomic region. Com...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Progenetix_cnv_search(
    reference_name: str,
    start: int,
    end: int,
    variant_type: Optional[str] = "",
    filters: Optional[str] = "",
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for cancer biosamples with copy number variations (CNVs) in a specific genomic region. Com...

    Parameters
    ----------
    reference_name : str
        RefSeq chromosome accession. Examples: 'refseq:NC_000007.14' (chr7/GRCh38), '...
    start : int
        Start position (1-based, GRCh38). Example: 55019017 for EGFR start.
    end : int
        End position (1-based, GRCh38). Example: 55211628 for EGFR end.
    variant_type : str
        CNV type: 'DUP' for amplification/duplication, 'DEL' for deletion. Leave empt...
    filters : str
        Optional NCIt ontology code to filter by cancer type. Example: 'NCIT:C4017' f...
    limit : int
        Maximum number of biosamples to return (default: 10).
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
        for k, v in {
            "reference_name": reference_name,
            "start": start,
            "end": end,
            "variant_type": variant_type,
            "filters": filters,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Progenetix_cnv_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Progenetix_cnv_search"]
