"""
MetabolomicsWorkbench_find_studies_by_phenotype

Discover Metabolomics Workbench studies matching a phenotype/experimental profile via the METSTAT...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetabolomicsWorkbench_find_studies_by_phenotype(
    analysis: Optional[str] = None,
    polarity: Optional[str] = None,
    chromatography: Optional[str] = None,
    species: Optional[str] = None,
    source: Optional[str] = None,
    disease: Optional[str] = None,
    kegg_id: Optional[str] = None,
    refmet_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Discover Metabolomics Workbench studies matching a phenotype/experimental profile via the METSTAT...

    Parameters
    ----------
    analysis : str
        Analysis type filter (e.g. 'MS', 'NMR', 'LC-MS').
    polarity : str
        Ionization polarity filter ('POSITIVE' or 'NEGATIVE').
    chromatography : str
        Chromatography type filter (e.g. 'HILIC', 'Reverse phase').
    species : str
        Subject species filter (e.g. 'Human', 'Mouse', 'Rat').
    source : str
        Sample source / specimen filter (e.g. 'Blood', 'Urine', 'Liver', 'Feces').
    disease : str
        Disease / condition filter (e.g. 'Diabetes', 'Cancer', 'Obesity').
    kegg_id : str
        KEGG compound id filter (e.g. 'C00031').
    refmet_name : str
        RefMet standardized metabolite name filter (e.g. 'Glucose', 'Cholic acid').
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
            "analysis": analysis,
            "polarity": polarity,
            "chromatography": chromatography,
            "species": species,
            "source": source,
            "disease": disease,
            "kegg_id": kegg_id,
            "refmet_name": refmet_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MetabolomicsWorkbench_find_studies_by_phenotype",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetabolomicsWorkbench_find_studies_by_phenotype"]
