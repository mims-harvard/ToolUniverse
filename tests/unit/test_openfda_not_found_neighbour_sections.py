"""A section missing only because of the label format returns the label's matching sections.

``FDA_get_teratogenic_effects_by_drug_name`` for glatiramer acetate returned
NOT_FOUND. Glatiramer labels are in PLR format, which has no
``teratogenic_effects`` field: the pregnancy content lives in ``pregnancy`` and
``use_in_specific_populations``. The NOT_FOUND branch already re-runs the query
without the ``_exists_:<section>`` guard; those records now supply the
corresponding sections, under their own names, instead of an empty result.

Everything mocks the HTTP layer -- no network.
"""

import sys
import types
import urllib.parse
from unittest.mock import patch

import pytest

from tooluniverse.openfda_tool import (
    NEIGHBOUR_SECTIONS,
    FDADrugLabelTool,
    _redirect_to_neighbour_sections,
)

NOT_FOUND = {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}
_DRUG_LIST_MODULE = "tooluniverse.data.fda_drugs_with_brand_generic_names_for_tool"


def _plr_label(**extra):
    row = {
        "risks": None,
        "abuse": ["..."],
        "animal_pharmacology_and_or_toxicology": ["..."],
        "carcinogenesis_and_mutagenesis_and_impairment_of_fertility": ["..."],
        "boxed_warning": ["WARNING: ..."],
        "warnings_and_cautions": ["5.1 Serious ..."],
        "use_in_specific_populations": ["8.1 Pregnancy ..."],
        "openfda": {"brand_name": ["B"], "generic_name": ["g"], "route": ["ORAL"]},
    }
    row.update(extra)
    return row


def _probe(*rows):
    return {"results": list(rows) or [_plr_label()]}


def test_a_missing_section_returns_the_label_s_corresponding_sections():
    out = _redirect_to_neighbour_sections("risks", _probe(), {"limit": 3})
    assert out["status"] == "redirected"
    assert out["requested_section"] == "risks"
    assert out["returned_sections"] == [
        "warnings_and_cautions",
        "boxed_warning",
        "use_in_specific_populations",
    ]


def test_the_most_relevant_section_comes_first_and_unrelated_ones_never_come():
    out = _redirect_to_neighbour_sections("risks", _probe(), {})
    assert out["returned_sections"][0] == "warnings_and_cautions"
    for unrelated in (
        "abuse",
        "animal_pharmacology_and_or_toxicology",
        "carcinogenesis_and_mutagenesis_and_impairment_of_fertility",
    ):
        assert unrelated not in out["returned_sections"]
        assert unrelated not in out["results"][0]


def test_nothing_is_relabelled_as_the_requested_section():
    out = _redirect_to_neighbour_sections("risks", _probe(), {})
    assert "risks" not in out["results"][0]
    assert "These are NOT the 'risks' section" in out["note"]


def test_each_record_says_which_product_and_route_it_is():
    record = _redirect_to_neighbour_sections("risks", _probe(), {})["results"][0]
    assert record["openfda.brand_name"] == ["B"]
    assert record["openfda.generic_name"] == ["g"]
    assert record["openfda.route"] == ["ORAL"]


def test_empty_or_null_neighbours_keep_the_original_not_found():
    probe = _probe(
        {
            "risks": None,
            "warnings_and_cautions": [],
            "boxed_warning": None,
            "abuse": ["present but not a neighbour"],
        }
    )
    assert _redirect_to_neighbour_sections("risks", probe, {}) is None


@pytest.mark.parametrize(
    "section, probe",
    [
        ("not_a_section", _probe()),
        ("pharmacogenomics", _probe()),
        ("risks", {"error": {"code": "X"}}),
        ("risks", None),
        ("risks", {"results": "x"}),
        ("risks", {"results": [None, 3]}),
    ],
)
def test_unmapped_sections_and_odd_input_return_none(section, probe):
    assert _redirect_to_neighbour_sections(section, probe, {}) is None


def test_a_bad_limit_is_ignored_and_a_good_one_caps_the_records():
    assert (
        _redirect_to_neighbour_sections("risks", _probe(), {"limit": "bad"})["status"]
        == "redirected"
    )
    out = _redirect_to_neighbour_sections(
        "risks", _probe(*[_plr_label() for _ in range(5)]), {"limit": 2}
    )
    assert out["result_count"] == 2
    assert len(out["results"]) == 2


def test_the_map_is_well_formed():
    for section, neighbours in NEIGHBOUR_SECTIONS.items():
        assert section not in neighbours, section
        assert len(neighbours) == len(set(neighbours)), section


# --- through the real tool --------------------------------------------------


@pytest.fixture
def tiny_drug_list(monkeypatch):
    """Stub the 6 MB closest-name table the spelling stage would otherwise scan."""
    stub = types.ModuleType(_DRUG_LIST_MODULE)
    stub.drug_list = [{"brand_name": "COPAXONE", "generic_name": "GLATIRAMER ACETATE"}]
    monkeypatch.setitem(sys.modules, _DRUG_LIST_MODULE, stub)
    return stub


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _config(name, return_fields):
    return {
        "name": name,
        "description": name,
        "type": "FDADrugLabel",
        "parameter": {
            "type": "object",
            "properties": {"drug_name": {"type": "string"}},
            "required": ["drug_name"],
        },
        "fields": {
            "search_fields": {
                "drug_name": ["openfda.brand_name", "openfda.generic_name"]
            },
            "return_fields": return_fields,
        },
    }


def _serve(section, record):
    """openFDA with a label that lacks `section`: the guard decides the answer."""
    seen = []

    def fake_get(url, *args, **kwargs):
        seen.append(urllib.parse.unquote(url))
        if f"_exists_:{section}" in seen[-1]:
            return _FakeResponse(NOT_FOUND)
        return _FakeResponse(
            {
                "meta": {"results": {"skip": 0, "limit": 5, "total": 1}},
                "results": [record],
            }
        )

    return fake_get, seen


def _glatiramer():
    return {
        "openfda": {
            "brand_name": ["COPAXONE"],
            "generic_name": ["GLATIRAMER ACETATE"],
            "route": ["SUBCUTANEOUS"],
        },
        "pregnancy": ["8.1 Pregnancy Risk Summary Available data ..."],
        "use_in_specific_populations": ["8 USE IN SPECIFIC POPULATIONS ..."],
        "warnings_and_cautions": ["5 WARNINGS AND PRECAUTIONS ..."],
        "spl_product_data_elements": ["COPAXONE glatiramer acetate"],
    }


def test_the_teratogenic_effects_tool_returns_the_plr_pregnancy_sections(
    tiny_drug_list,
):
    fake_get, seen = _serve("teratogenic_effects", _glatiramer())
    tool = FDADrugLabelTool(
        _config("FDA_get_teratogenic_effects_by_drug_name", ["teratogenic_effects"])
    )
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        out = tool.run({"drug_name": "glatiramer acetate", "limit": 3})
    assert out["status"] == "redirected"
    assert out["requested_section"] == "teratogenic_effects"
    assert out["returned_sections"] == [
        "pregnancy",
        "use_in_specific_populations",
        "warnings_and_cautions",
    ]
    assert out["results"][0]["openfda.brand_name"] == ["COPAXONE"]
    assert "teratogenic_effects" not in out["results"][0]
    # the records came from the probe the NOT_FOUND branch already ran
    assert any("_exists_:teratogenic_effects" not in url for url in seen)


def test_a_section_outside_the_map_still_gets_the_not_found_answer(tiny_drug_list):
    fake_get, _ = _serve("pharmacogenomics", _glatiramer())
    tool = FDADrugLabelTool(
        _config("FDA_get_pharmacogenomics_info_by_drug_name", ["pharmacogenomics"])
    )
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        out = tool.run({"drug_name": "glatiramer acetate", "limit": 3})
    assert out.get("status") != "redirected"
