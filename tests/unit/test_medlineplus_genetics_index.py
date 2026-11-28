"""MedlinePlus_get_genetics_index lists the genetics pages, not its four sections.

TopicIndex.xml nests every page one level down: four section topics
(Conditions, Genes, Chromosomes, Handbook), each holding its pages under
<topics><topic>, with the page name in <title>. The tool read only the four
section topics and looked for a <name> key that the index does not have, so
it returned 4 rows with an empty name (measured live 2026-11-23) where the
index lists 2,965 pages.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse import medlineplus_tool as M

pytestmark = pytest.mark.unit

# A slice of the real index (2026-11-23), same structure.
INDEX = """<?xml version="1.0" encoding="utf-8"?>
<genetics_home_reference_topic_list version="3.0">
<title>MedlinePlus Genetics</title>
<url>https://medlineplus.gov/</url>
<topic id="Conditions">
<title>Conditions</title>
<url>https://medlineplus.gov/genetics/condition/</url>
<topics>
<topic><url>https://medlineplus.gov/genetics/condition/alport-syndrome</url><title>Alport syndrome</title>
<other_names><other_name>Hematuric hereditary nephritis</other_name></other_names></topic>
<topic><url>https://medlineplus.gov/genetics/condition/marfan-syndrome</url><title>Marfan syndrome</title></topic>
</topics>
</topic>
<topic id="Genes">
<title>Genes</title>
<url>https://medlineplus.gov/genetics/gene/</url>
<topics>
<topic><url>https://medlineplus.gov/genetics/gene/fbn1</url><title>FBN1: fibrillin 1</title></topic>
</topics>
</topic>
<topic id="Handbook">
<title>Help Me Understand Genetics</title>
<url>https://medlineplus.gov/genetics/understanding/</url>
<topics>
<topic><title>Cells and DNA</title><url>https://medlineplus.gov/genetics/understanding/basics</url></topic>
</topics>
</topic>
</genetics_home_reference_topic_list>"""


def _tool():
    config_path = Path(M.__file__).parent / "data" / "medlineplus_tools.json"
    config = next(
        tool
        for tool in json.loads(config_path.read_text(encoding="utf-8"))
        if tool["name"] == "MedlinePlus_get_genetics_index"
    )
    return M.MedlinePlusRESTTool(config)


def _run(index_xml, arguments=None):
    response = MagicMock()
    response.status_code = 200
    response.text = index_xml
    with patch.object(M.requests, "get", return_value=response):
        return _tool().run(dict(arguments or {}))


def test_index_lists_every_page_with_its_title_and_section():
    # Genes and Handbook hold one page each, which xmltodict gives as a dict
    # rather than a list; those pages must not be dropped.
    result = _run(INDEX)

    assert result["topics"] == [
        {
            "name": "Alport syndrome",
            "url": "https://medlineplus.gov/genetics/condition/alport-syndrome",
            "category": "Conditions",
        },
        {
            "name": "Marfan syndrome",
            "url": "https://medlineplus.gov/genetics/condition/marfan-syndrome",
            "category": "Conditions",
        },
        {
            "name": "FBN1: fibrillin 1",
            "url": "https://medlineplus.gov/genetics/gene/fbn1",
            "category": "Genes",
        },
        {
            "name": "Cells and DNA",
            "url": "https://medlineplus.gov/genetics/understanding/basics",
            "category": "Handbook",
        },
    ]
    assert result["count"] == 4


def test_an_index_without_pages_is_an_error():
    empty = (
        '<?xml version="1.0" encoding="utf-8"?>'
        "<genetics_home_reference_topic_list version='3.0'>"
        "<title>MedlinePlus Genetics</title></genetics_home_reference_topic_list>"
    )

    assert _run(empty) == {"error": "No genetics topics found"}


def test_a_category_returns_one_section_and_says_what_it_left_out():
    # The whole index is 2,965 pages and about 400 KB of JSON, so a caller
    # after one section can ask for it -- but a short list has to state the
    # size of the index it came from, or it reads like the whole thing.
    result = _run(INDEX, {"category": "Conditions"})

    assert [topic["name"] for topic in result["topics"]] == [
        "Alport syndrome",
        "Marfan syndrome",
    ]
    assert result["count"] == 2
    assert result["category"] == "Conditions"
    assert result["total"] == 4


def test_the_category_is_the_section_id_not_its_title():
    # The Handbook section is <topic id="Handbook"> with the title "Help Me
    # Understand Genetics", so the two are not interchangeable.
    result = _run(INDEX, {"category": "handbook"})

    assert result["category"] == "Handbook"
    assert [topic["name"] for topic in result["topics"]] == ["Cells and DNA"]


def test_an_unknown_category_is_refused_not_ignored():
    # Returning all 2,965 pages for a typo, or an empty list, would both read
    # as an answer. Name the sections the index actually has instead.
    result = _run(INDEX, {"category": "Genes "})
    assert result["count"] == 1

    result = _run(INDEX, {"category": "Proteins"})
    assert "topics" not in result
    assert result["error"] == (
        "Unknown category 'Proteins'. The index has: Conditions, Genes, Handbook."
    )


def test_no_category_still_returns_the_whole_index():
    result = _run(INDEX)

    assert result["count"] == 4
    # Nothing was filtered, so there is nothing to disclose.
    assert "category" not in result
    assert "total" not in result


@pytest.mark.network
def test_live_index_lists_condition_and_gene_pages():
    result = _tool().run({})

    sections = {topic["category"] for topic in result["topics"]}
    assert {"Conditions", "Genes"} <= sections
    assert len(result["topics"]) > 2000
    assert all(topic["name"] and topic["url"] for topic in result["topics"])


@pytest.mark.network
def test_live_chromosomes_section_is_a_small_slice_of_the_index():
    result = _tool().run({"category": "Chromosomes"})

    assert result["category"] == "Chromosomes"
    assert {topic["category"] for topic in result["topics"]} == {"Chromosomes"}
    assert result["count"] == len(result["topics"])
    assert result["count"] < result["total"]
