"""``FAERS_search_serious_reports_by_drug`` had no way to ask for serious reports.

The tool's name and description promised "detailed reports of serious adverse
events", but its ``search_fields`` map carried only ``medicinalproduct`` and the
four optional ``seriousness*`` CRITERION flags. With none of those supplied
nothing constrained seriousness at all, and the tool returned byte-identical
output to its unfiltered sibling ``FAERS_search_adverse_event_reports`` for the
same arguments -- verified live 2026-08-12 for ibuprofen, limit 5.

The contamination is real and drug-dependent. Measured live over the first 100
reports returned, counting the openFDA ``serious`` field (1 = serious,
2 = non-serious):

    acamprosate      12% non-serious
    levetiracetam    24%
    ibuprofen        39%
    gadobutrol       79%

There was no parameter to fix it with: ``serious`` was absent from the schema
AND from the search-field map, while the sibling tool has exposed it all along.
This adds it -- ``HUMAN_TO_FDA_MAP["serious"]`` already knew how to render it --
so the change is config-only and additive: the default still returns both
classes, which is why the description now says so instead of implying otherwise.

Live check of the added parameter, gadobutrol at limit 100: omitted -> 21
serious / 79 non-serious; ``serious="Yes"`` -> 100 / 0; ``serious="No"`` ->
0 / 100.

Config-only assertions -- no network.
"""

import inspect
import json
from pathlib import Path

import pytest

import tooluniverse
from tooluniverse.openfda_adv_tool import HUMAN_TO_FDA_MAP

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"
TOOL = "FAERS_search_serious_reports_by_drug"
SIBLING = "FAERS_search_adverse_event_reports"


def _config(name):
    configs = json.loads(
        (DATA_DIR / "fda_drug_adverse_event_detail_tools.json").read_text()
    )
    return next(c for c in configs if c["name"] == name)


def test_the_tool_can_now_be_asked_for_serious_reports_at_all():
    config = _config(TOOL)

    assert "serious" in config["parameter"]["properties"]
    assert config["parameter"]["properties"]["serious"]["enum"] == ["Yes", "No"]
    # Declaring the parameter is not enough: it has to reach the query.
    assert config["fields"]["search_fields"]["serious"] == ["serious"]


def test_the_value_mapping_the_parameter_relies_on_exists():
    """'Yes'/'No' are rendered by the shared map, not by new code."""
    assert HUMAN_TO_FDA_MAP["serious"] == {"Yes": "1", "No": "2"}


def test_it_asks_the_same_seriousness_question_as_its_unfiltered_sibling():
    """The sibling has always had this parameter; the two now agree."""
    assert (
        _config(TOOL)["fields"]["search_fields"]["serious"]
        == _config(SIBLING)["fields"]["search_fields"]["serious"]
    )


def test_the_description_no_longer_promises_a_filter_that_is_off_by_default():
    description = _config(TOOL)["description"]

    assert "NOT restricted to serious reports" in description
    assert "serious='Yes'" in description
    # The claim is backed by a measurement, and names a drug it was measured on.
    assert "gadobutrol" in description


def test_the_generated_python_wrapper_exposes_the_parameter_too():
    """The config is one surface; the SDK function is another, and it ships.

    `src/tooluniverse/tools/*.py` is generated but tracked, so a config-only
    change leaves `FAERS_search_serious_reports_by_drug(medicinalproduct=...,
    serious="Yes")` raising TypeError for every Python-API caller.
    """
    from tooluniverse.tools.FAERS_search_serious_reports_by_drug import (
        FAERS_search_serious_reports_by_drug as fn,
    )

    parameters = inspect.signature(fn).parameters
    assert "serious" in parameters
    assert parameters["serious"].default is None
    # And it is actually forwarded, not just accepted and dropped.
    assert '"serious": serious' in inspect.getsource(fn)


def test_the_return_schema_no_longer_promises_a_serious_only_list():
    description = _config(TOOL)["return_schema"]["description"]

    assert "serious" in description
    assert "non-serious" in description


def test_a_test_example_actually_exercises_the_new_parameter():
    examples = _config(TOOL)["test_examples"]

    assert any(e.get("serious") == "Yes" for e in examples)
    # The pre-existing criterion examples are untouched.
    assert any(e.get("seriousnessdeath") == "Yes" for e in examples)
