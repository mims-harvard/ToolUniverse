"""SABIO-RK kinetic constants come from each Solr doc's ``Json`` field.

The Solr index has no ``Parameter``/``ParameterUnit`` field, so
SABIO_RK_search_reactions always returned ``parameters: []`` and
BRENDA_get_enzyme_kinetics never produced a ``parameter_summary``. The
values (Km, kcat, ...) are inside ``Json`` under ``kineticlaw.parameter``;
the fixture below follows the live shape of EC 1.1.1.1 entry 4510.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.brenda_tool import BRENDATool
from tooluniverse.sabiork_tool import SABIORKTool

pytestmark = pytest.mark.unit

LAW = {
    "kineticlaw": {
        "parameter": [
            {
                "name": "kcat",
                "role": "Constant",
                "parameter_type": {"name": "kcat"},
                "species": {"species_ref_type": "species"},
                "start_value": 7200.0,
                "unit": {"name": "min^(-1)", "n_name": "s^(-1)"},
                "n_start_value": 120.0,
            },
            {
                "name": "Km",
                "role": "Constant",
                "parameter_type": {"name": "Km"},
                "species": {"species_key": "1 | Ethanol | Substrate"},
                "start_value": 1.02,
                "standard_deviation": 0.1,
                "unit": {"name": "mM", "n_name": "M"},
                "n_start_value": 0.00102,
            },
            {
                "name": "Vmax",
                "role": "Constant",
                "parameter_type": {"name": "Vmax"},
                "species": {},
                "start_value": 80.0,
                "unit": {"name": "U/mg", "n_name": "katal*g^(-1)"},
                "n_start_value": 0.00133336,
            },
            {
                "name": "Vmax",
                "role": "Constant",
                "parameter_type": {"name": "Vmax"},
                "species": {},
                "start_value": 40.0,
                "unit": {"name": "umol/(min*mg)", "n_name": "mol*s^(-1)*g^(-1)"},
                "n_start_value": 0.00066668,
            },
            # Assay concentration range: not a kinetic constant.
            {
                "name": "S",
                "role": "Variable",
                "parameter_type": {"name": "concentration"},
                "species": {"species_key": "1 | Ethanol | Substrate"},
                "start_value": 0.1,
                "end_value": 10.0,
                "unit": {"name": "mM", "n_name": "M"},
                "n_start_value": 0.0001,
            },
            # Placeholder SABIO-RK stores without a value.
            {
                "name": "kcat_Km",
                "role": "Constant",
                "parameter_type": {"name": "kcat/Km"},
                "species": {},
                "unit": {"name": "-"},
            },
        ]
    },
    "experimental_conditions": {
        "envvar_ph": {"start_value": 8.0},
        "envvar_temperature": {"start_value": 25.0, "unit": "°C"},
    },
}

DOC = {
    "EntryID": 4510,
    "ECNumber": ["1.1.1.1"],
    "EnzymeName": ["ADH"],
    "Organism": ["Kluyveromyces lactis"],
    "ParameterType": ["concentration", "kcat", "kcat/Km", "Km"],
    "Json": json.dumps(LAW),
}


def _solr(docs, num_found=768):
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    response.json.return_value = {"response": {"numFound": num_found, "docs": docs}}
    return response


def test_sabiork_search_returns_the_measured_constants():
    with patch("tooluniverse.sabiork_tool.requests.get") as get:
        get.return_value = _solr([DOC])
        result = SABIORKTool({"name": "SABIO_RK_search_reactions"}).run(
            {"operation": "search_reactions", "ec_number": "1.1.1.1", "limit": 1}
        )

    assert "Json" in get.call_args.kwargs["params"]["fl"].split(",")
    law = result["data"]["kinetic_laws"][0]
    by_type = {p["type"]: p for p in law["parameters"]}
    assert by_type["kcat"]["value"] == 7200.0
    assert by_type["kcat"]["unit"] == "min^(-1)"
    assert by_type["kcat"]["value_si"] == 120.0
    assert by_type["Km"]["species"] == "Ethanol"
    assert by_type["Km"]["standard_deviation"] == 0.1
    # Neither the assay variable nor the value-less placeholder is reported.
    assert {p["type"] for p in law["parameters"]} == {"kcat", "Km", "Vmax"}
    assert law["conditions"] == {
        "ph": 8.0,
        "temperature": 25.0,
        "temperature_unit": "°C",
    }


def test_brenda_kinetics_carries_values_and_a_summary():
    tool = BRENDATool({"name": "BRENDA_get_enzyme_kinetics"})
    with (
        patch("tooluniverse.brenda_tool.requests.get") as get,
        patch.object(BRENDATool, "_fetch_expasy_enzyme", return_value={}),
    ):
        get.return_value = _solr([DOC])
        result = tool._get_enzyme_kinetics({"ec_number": "1.1.1.1", "limit": 1})

    data = result["data"]
    km = [p for p in data["kinetic_parameters"][0]["parameters"] if p["type"] == "Km"]
    assert km[0]["value_si"] == 0.00102
    summary = data["parameter_summary"]
    assert summary["kcat"] == {
        "count": 1,
        "min": 120.0,
        "max": 120.0,
        "median": 120.0,
        "unit": "s^(-1)",
    }
    assert summary["Km"]["unit"] == "M"
    # katal*g^-1 and mol*s^-1*g^-1 are the same unit and are pooled.
    assert summary["Vmax"]["count"] == 2
    assert summary["Vmax"]["unit"] == "mol*s^(-1)*g^(-1)"
    assert "values_in_other_units" not in summary["Vmax"]


def test_values_in_a_minority_unit_are_counted_not_mixed():
    law = {
        "kineticlaw": {
            "parameter": [
                {
                    "name": "Km",
                    "role": "Constant",
                    "parameter_type": {"name": "Km"},
                    "start_value": v,
                    "unit": {"name": "mM", "n_name": unit},
                    "n_start_value": v,
                }
                for v, unit in ((0.1, "M"), (0.2, "M"), (5.0, "mg/ml"))
            ]
        }
    }
    tool = BRENDATool({"name": "BRENDA_get_enzyme_kinetics"})
    with (
        patch("tooluniverse.brenda_tool.requests.get") as get,
        patch.object(BRENDATool, "_fetch_expasy_enzyme", return_value={}),
    ):
        get.return_value = _solr([dict(DOC, Json=json.dumps(law))])
        result = tool._get_enzyme_kinetics({"ec_number": "1.1.1.1", "limit": 1})

    km = result["data"]["parameter_summary"]["Km"]
    assert (km["count"], km["max"], km["unit"]) == (2, 0.2, "M")
    assert km["values_in_other_units"] == 1


def test_a_doc_without_json_still_parses():
    with patch("tooluniverse.sabiork_tool.requests.get") as get:
        get.return_value = _solr([{"EntryID": 1, "Json": "not json"}, {"EntryID": 2}])
        result = SABIORKTool({"name": "SABIO_RK_search_reactions"}).run(
            {"operation": "search_reactions", "ec_number": "1.1.1.1"}
        )

    assert [law["parameters"] for law in result["data"]["kinetic_laws"]] == [[], []]
