"""
SwissModel_download_pdb

Download the actual 3D atomic coordinates (PDB format) of SWISS-MODEL Repository structures for a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SwissModel_download_pdb(
    uniprot_id: str,
    sort: Optional[str] = None,
    provider: Optional[str] = None,
    template: Optional[str] = None,
    range: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Download the actual 3D atomic coordinates (PDB format) of SWISS-MODEL Repository structures for a...

    Parameters
    ----------
    uniprot_id : str
        UniProt accession identifier. Examples: 'P04637' (human p53), 'P00533' (human...
    sort : str
        Optional ordering for the bundled models. 'seqid' sorts by sequence identity ...
    provider : str
        Optional model-provider filter. 'swissmodel' = SWISS-MODEL homology models on...
    template : str
        Optional template filter; download only models built from this template (PDB ...
    range : str
        Optional residue range filter ('from-to', e.g. '94-312'); download only model...
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
            "uniprot_id": uniprot_id,
            "sort": sort,
            "provider": provider,
            "template": template,
            "range": range,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SwissModel_download_pdb",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SwissModel_download_pdb"]
