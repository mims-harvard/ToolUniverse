"""
Progenetix_cnv_search

Search for cancer biosamples with copy number variations (CNVs) in a specific genomic region.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Progenetix_cnv_search(
    reference_name: str,
    start: int,
    end: int,
    variant_type: Optional[str] = None,
    filters: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for cancer biosamples with CNVs in a specific genomic region.

    Parameters
    ----------
    reference_name : str
        RefSeq chromosome accession (e.g., 'refseq:NC_000007.14' for chr7/GRCh38).
    start : int
        Start position (1-based, GRCh38).
    end : int
        End position (1-based, GRCh38).
    variant_type : str, optional
        CNV type: 'DUP' for amplification, 'DEL' for deletion.
    filters : str, optional
        NCIt ontology code to filter by cancer type (e.g., 'NCIT:C4017' for breast cancer).
    limit : int, optional
        Maximum number of biosamples to return (default 10).
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
