"""
FAERS_search_reports_by_drug_and_reaction

Search and retrieve detailed adverse event reports for a specific drug and reaction type. Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_search_reports_by_drug_and_reaction(
    medicinalproduct: str,
    reactionmeddrapt: str,
    limit: Optional[int] = 10,
    skip: Optional[int] = 0,
    patientsex: Optional[str] = None,
    patientagegroup: Optional[str] = None,
    serious: Optional[str] = None,
    rxcui: Optional[list[Any] | str] = None,
    unii: Optional[list[Any] | str] = None,
    openfda_generic_name: Optional[list[Any] | str] = None,
    openfda_brand_name: Optional[list[Any] | str] = None,
    openfda_substance_name: Optional[list[Any] | str] = None,
    pharm_class_epc: Optional[list[Any] | str] = None,
    pharm_class_moa: Optional[list[Any] | str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search and retrieve detailed adverse event reports for a specific drug and reaction type. Returns...

    Parameters
    ----------
    medicinalproduct : str
        Drug name (required).
    reactionmeddrapt : str
        MedDRA preferred term for the adverse reaction (required). Example: 'INFUSION...
    limit : int
        Maximum number of reports to return. Must be between 1 and 100.
    skip : int
        Number of reports to skip for pagination. Must be non-negative.
    patientsex : str
        Optional: Filter by patient sex. Omit this parameter if you don't want to fil...
    patientagegroup : str
        Optional: Filter by patient age group. Omit this parameter if you don't want ...
    serious : str
        Optional: Filter by event seriousness. Omit this parameter if you don't want ...
    rxcui : list[Any] | str
        The RxNorm concept. `medicinalproduct` is free text the reporter typed -- "TY...
    unii : list[Any] | str

    openfda_generic_name : list[Any] | str

    openfda_brand_name : list[Any] | str

    openfda_substance_name : list[Any] | str

    pharm_class_epc : list[Any] | str
        Established pharmacologic class, so a class effect can be seen across reports
    pharm_class_moa : list[Any] | str

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
            "medicinalproduct": medicinalproduct,
            "reactionmeddrapt": reactionmeddrapt,
            "limit": limit,
            "skip": skip,
            "patientsex": patientsex,
            "patientagegroup": patientagegroup,
            "serious": serious,
            "rxcui": rxcui,
            "unii": unii,
            "openfda_generic_name": openfda_generic_name,
            "openfda_brand_name": openfda_brand_name,
            "openfda_substance_name": openfda_substance_name,
            "pharm_class_epc": pharm_class_epc,
            "pharm_class_moa": pharm_class_moa,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_search_reports_by_drug_and_reaction",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_search_reports_by_drug_and_reaction"]
