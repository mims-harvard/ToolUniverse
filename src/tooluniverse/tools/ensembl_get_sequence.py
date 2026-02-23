"""
ensembl_get_sequence

Get DNA or protein sequence for a gene, transcript, or genomic region. Returns sequence in JSON f...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_sequence(
    id: str,
    type_: Optional[str] = "genomic",
    species: Optional[str] = None,
    multiple_sequences: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get DNA or protein sequence for a gene, transcript, or genomic region. Returns sequence in JSON f...

    Parameters
    ----------
    id : str
        Ensembl gene/transcript ID (e.g., 'ENSG00000139618' or 'ENST00000380152')
    type_ : str
        Sequence type: 'genomic' (genomic DNA), 'cds' (coding sequence), 'cdna' (cDNA...
    species : str
        Species name (optional, defaults to human)
    multiple_sequences : bool
        Return multiple sequences if available (e.g., all transcripts)
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

    return get_shared_client().run_one_function(
        {
            "name": "ensembl_get_sequence",
            "arguments": {
                "id": id,
                "type": type_,
                "species": species,
                "multiple_sequences": multiple_sequences,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_sequence"]
