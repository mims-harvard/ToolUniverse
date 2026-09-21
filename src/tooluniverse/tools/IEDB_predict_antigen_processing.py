"""
IEDB_predict_antigen_processing

Predict MHC class I antigen processing using the IEDB next-generation tools API (https://api-next...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IEDB_predict_antigen_processing(
    sequence: str,
    sequence_text: Optional[str] = None,
    allele: Optional[str] = "HLA-A*02:01",
    method: Optional[str] = "netmhcpan",
    length: Optional[int] = 9,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict MHC class I antigen processing using the IEDB next-generation tools API (https://api-next...

    Parameters
    ----------
    sequence : str
        Protein sequence (single-letter amino acids), e.g. 'SLYNTVATLYCVHQRIDVKQNTLKL...
    sequence_text : str
        Alias for sequence.
    allele : str
        MHC class I allele, validated upstream against the MHC Restriction Ontology. ...
    method : str
        MHC-I binding method used in the chain: 'netmhcpan' (default), 'netmhcpan_ba'...
    length : int
        Peptide length (8-15 for MHC-I, typically 9).
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
            "sequence": sequence,
            "sequence_text": sequence_text,
            "allele": allele,
            "method": method,
            "length": length,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IEDB_predict_antigen_processing",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IEDB_predict_antigen_processing"]
