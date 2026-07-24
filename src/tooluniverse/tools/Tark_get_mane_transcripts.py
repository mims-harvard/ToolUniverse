"""
Tark_get_mane_transcripts

Look up the MANE (Matched Annotation from NCBI and EMBL-EBI) transcript(s) for a gene, mapping th...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Tark_get_mane_transcripts(
    gene: Optional[str] = None,
    ensembl_id: Optional[str] = None,
    refseq_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up the MANE (Matched Annotation from NCBI and EMBL-EBI) transcript(s) for a gene, mapping th...

    Parameters
    ----------
    gene : str
        HGNC gene symbol, e.g. 'BRCA2', 'CFTR'.
    ensembl_id : str
        Ensembl transcript id, e.g. 'ENST00000380152' (version optional).
    refseq_id : str
        RefSeq transcript id, e.g. 'NM_000059' (version optional).
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
        for k, v in {
            "gene": gene,
            "ensembl_id": ensembl_id,
            "refseq_id": refseq_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Tark_get_mane_transcripts",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Tark_get_mane_transcripts"]
