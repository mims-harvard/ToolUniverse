"""Regression guard for Fix-R77B-1: three return_schema fields declared a
single strict type (string/array) when the underlying API can legitimately
return null for that field, so a genuinely-empty value failed schema
validation even though the tool itself handled it correctly.

Each of these already has a sibling field in the same schema that already
permits null (e.g. DailyMed's previous_page/next_page, OmicsDI's organisms),
confirming these are schema-definition gaps rather than deliberate strictness.

- OmicsDI_search_datasets: dataset.description / dataset.publicationDate
  (OmicsDI aggregates multiple repositories; not all of them populate these).
- DailyMed_search_spls: metadata.previous_page_url / metadata.next_page_url
  (already normalized to None by SearchSPLTool on the first/last page --
  see tests/unit/test_dailymed_null_and_headers.py).
- PDBe_get_compound_details: <compound>[].cross_links (a compound with no
  cross-references to external databases).
"""

import json

import jsonschema
import pytest

pytestmark = pytest.mark.unit


def _dataset_item_schema():
    with open("src/tooluniverse/data/omicsdi_tools.json") as f:
        tools = json.load(f)
    tool = next(t for t in tools if t["name"] == "OmicsDI_search_datasets")
    branch = tool["return_schema"]["oneOf"][0]
    return branch["properties"]["datasets"]["items"]


def _dailymed_metadata_schema():
    with open("src/tooluniverse/data/dailymed_tools.json") as f:
        tools = json.load(f)
    tool = next(t for t in tools if t["name"] == "DailyMed_search_spls")
    return tool["return_schema"]["properties"]["metadata"]


def _pdbe_compound_item_schema():
    with open("src/tooluniverse/data/pdbe_graph_tools.json") as f:
        tools = json.load(f)
    tool = next(t for t in tools if t["name"] == "PDBe_get_compound_details")
    branch = tool["return_schema"]["oneOf"][0]
    return branch["additionalProperties"]["items"]


def test_omicsdi_dataset_allows_null_description_and_publication_date():
    schema = _dataset_item_schema()
    jsonschema.validate(
        instance={
            "id": "PXD000001",
            "source": "PRIDE",
            "title": "A dataset",
            "description": None,
            "organisms": None,
            "publicationDate": None,
            "omicsType": [],
            "citationsCount": 0,
            "viewsCount": 0,
            "downloadCount": 0,
        },
        schema=schema,
    )


def test_omicsdi_dataset_still_requires_description_to_be_string_or_null():
    schema = _dataset_item_schema()
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={"description": 12345}, schema=schema)


def test_dailymed_metadata_allows_null_page_urls():
    schema = _dailymed_metadata_schema()
    jsonschema.validate(
        instance={
            "current_url": "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json",
            "next_page_url": None,
            "total_elements": 1,
            "total_pages": 1,
            "current_page": 1,
            "previous_page": None,
            "previous_page_url": None,
            "next_page": None,
        },
        schema=schema,
    )


def test_pdbe_compound_allows_null_cross_links():
    schema = _pdbe_compound_item_schema()
    jsonschema.validate(
        instance={
            "name": "heme",
            "formula": "C34 H32 Fe N4 O4",
            "compound_type": "NON-POLYMER",
            "cross_links": None,
        },
        schema=schema,
    )
