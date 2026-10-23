"""
HLALigandAtlas_get_benign_peptides

Retrieve benign-tissue HLA-presented peptides from the complete HLA Ligand Atlas 2020.12 aggregat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HLALigandAtlas_get_benign_peptides(
    peptide: Optional[str] = None,
    hla_class: Optional[str] = None,
    allele: Optional[str] = None,
    tissue: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve benign-tissue HLA-presented peptides from the complete HLA Ligand Atlas 2020.12 aggregat...

    Parameters
    ----------
    peptide : str
        Exact peptide sequence (single-letter amino acids) to match, e.g. 'LLPKKTESHH...
    hla_class : str
        HLA class filter: 'HLA-I' or 'HLA-II'. Leave empty for both.
    allele : str
        Substring of a presenting allele to match within the donor_alleles list, e.g....
    tissue : str
        Tissue of origin substring to match, e.g. 'Lung', 'Brain', 'Spleen'. Case-ins...
    limit : int
        Maximum rows on this page, 1-500. Defaults to 50; invalid values are rejected.
    offset : int
        Zero-based offset into the exact filtered match set; continue with metadata.n...
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
            "peptide": peptide,
            "hla_class": hla_class,
            "allele": allele,
            "tissue": tissue,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HLALigandAtlas_get_benign_peptides",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HLALigandAtlas_get_benign_peptides"]
