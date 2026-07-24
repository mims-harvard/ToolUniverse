"""
OpenNeuro_advanced_search

Faceted search across all OpenNeuro datasets plus the archive-wide total participant count. Retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenNeuro_advanced_search(
    species: Optional[str] = None,
    sex: Optional[str] = None,
    diagnosis: Optional[str] = None,
    modality: Optional[str] = None,
    tasks: Optional[str] = None,
    keywords: Optional[list[str]] = None,
    scannerManufacturers: Optional[str] = None,
    tracerNames: Optional[str] = None,
    tracerRadionuclides: Optional[str] = None,
    studyDomains: Optional[str] = None,
    bodyParts: Optional[str] = None,
    authors: Optional[str] = None,
    bidsDatasetType: Optional[str] = None,
    ageRange: Optional[list[Any]] = None,
    subjectCountRange: Optional[list[Any]] = None,
    first: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Faceted search across all OpenNeuro datasets plus the archive-wide total participant count. Retur...

    Parameters
    ----------
    species : str
        Species facet (e.g., 'human')
    sex : str
        Participant sex facet (e.g., 'Male', 'Female')
    diagnosis : str
        Clinical diagnosis facet
    modality : str
        Imaging modality facet (e.g., 'MRI', 'EEG', 'PET')
    tasks : str
        Task name facet
    keywords : list[str]
        Keyword facets (list of strings)
    scannerManufacturers : str
        Scanner manufacturer facet (e.g., 'Siemens')
    tracerNames : str
        PET tracer name facet
    tracerRadionuclides : str
        PET tracer radionuclide facet
    studyDomains : str
        Study domain facet
    bodyParts : str
        Body part facet
    authors : str
        Author name facet
    bidsDatasetType : str
        BIDS dataset type facet (e.g., 'raw', 'derivative')
    ageRange : list[Any]
        Participant age range as [min, max]
    subjectCountRange : list[Any]
        Subject-count range as [min, max]
    first : int
        Number of matching datasets to return (default 10, max 25)
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
            "species": species,
            "sex": sex,
            "diagnosis": diagnosis,
            "modality": modality,
            "tasks": tasks,
            "keywords": keywords,
            "scannerManufacturers": scannerManufacturers,
            "tracerNames": tracerNames,
            "tracerRadionuclides": tracerRadionuclides,
            "studyDomains": studyDomains,
            "bodyParts": bodyParts,
            "authors": authors,
            "bidsDatasetType": bidsDatasetType,
            "ageRange": ageRange,
            "subjectCountRange": subjectCountRange,
            "first": first,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenNeuro_advanced_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenNeuro_advanced_search"]
