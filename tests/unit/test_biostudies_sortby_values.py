"""biostudies_search offered sortBy values BioStudies does not support.

``sortBy=accession`` (and ``title``) return zero hits with no error, so the documented
"accession" option silently emptied the result. The API's working values are relevance,
release_date, views, files and links (each reorders the results).
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _sort_by():
    tools = json.loads((DATA / "biostudies_tools.json").read_text(encoding="utf-8"))
    tool = next(t for t in tools if t["name"] == "biostudies_search")
    return tool["parameter"]["properties"]["sortBy"]


def test_only_supported_sort_values_are_offered():
    assert _sort_by()["enum"] == [
        "relevance",
        "release_date",
        "views",
        "files",
        "links",
    ]


def test_unsupported_values_are_explained_in_the_description():
    description = _sort_by()["description"]
    assert "'accession'" in description and "not supported" in description
