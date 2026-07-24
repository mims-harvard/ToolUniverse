"""
AMPSphere_search_amps

Filter/search the AMPSphere catalogue (863,498 prokaryotic smORF antimicrobial peptides from the ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AMPSphere_search_amps(
    list_options: Optional[bool] = None,
    habitat: Optional[str] = None,
    family: Optional[str] = None,
    microbial_source: Optional[str] = None,
    exp_evidence: Optional[str] = None,
    antifam: Optional[str] = None,
    RNAcode: Optional[str] = None,
    coordinates: Optional[str] = None,
    pep_length_interval: Optional[str] = None,
    mw_interval: Optional[str] = None,
    pI_interval: Optional[str] = None,
    charge_interval: Optional[str] = None,
    page_size: Optional[int | str] = None,
    page: Optional[int | str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Filter/search the AMPSphere catalogue (863,498 prokaryotic smORF antimicrobial peptides from the ...

    Parameters
    ----------
    list_options : bool
        If true, ignore all other filters and return the valid filter enumerations fr...
    habitat : str
        Environmental habitat filter, e.g. 'human gut', 'soil', 'marine'. Must match ...
    family : str
        SPHERE family accession filter, e.g. 'SPHERE-III.001_396'. Returns the AMPs i...
    microbial_source : str
        Microbial taxonomic source filter (GTDB-style name), e.g. 'Faecalibacterium'....
    exp_evidence : str
        Experimental-evidence quality flag filter: 'Passed', 'Failed', or 'Not tested'.
    antifam : str
        Antifam quality flag filter: 'Passed', 'Failed', or 'Not tested' (Antifam = n...
    RNAcode : str
        RNAcode coding-potential quality flag filter: 'Passed', 'Failed', or 'Not tes...
    coordinates : str
        Genomic-coordinates quality flag filter: 'Passed', 'Failed', or 'Not tested'.
    pep_length_interval : str
        Peptide-length range as 'min,max' (residues), e.g. '8,20'. Catalogue range is...
    mw_interval : str
        Molecular-weight range as 'min,max' (Da), e.g. '800,3000'. Catalogue range is...
    pI_interval : str
        Isoelectric-point range as 'min,max', e.g. '9,12'. Catalogue range is ~4-12.
    charge_interval : str
        Net-charge-at-pH-7 range as 'min,max', e.g. '0,10'. Catalogue range is ~-57 t...
    page_size : int | str
        Results per page (default 20).
    page : int | str
        Zero-based page index (default 0).
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
            "list_options": list_options,
            "habitat": habitat,
            "family": family,
            "microbial_source": microbial_source,
            "exp_evidence": exp_evidence,
            "antifam": antifam,
            "RNAcode": RNAcode,
            "coordinates": coordinates,
            "pep_length_interval": pep_length_interval,
            "mw_interval": mw_interval,
            "pI_interval": pI_interval,
            "charge_interval": charge_interval,
            "page_size": page_size,
            "page": page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AMPSphere_search_amps",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AMPSphere_search_amps"]
