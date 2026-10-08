"""Europe PMC article IDs must keep PMC:/MED: prefixes case-insensitive."""

from unittest.mock import patch

import pytest

from tooluniverse.europepmc_annotations_tool import EuroPMCAnnotationsTool

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("PMC4353746", "PMC:PMC4353746"),
        ("pmc4353746", "PMC:PMC4353746"),
        ("PMC:PMC4353746", "PMC:PMC4353746"),
        ("pmc:PMC4353746", "PMC:PMC4353746"),
        ("pmc:pmc4353746", "PMC:PMC4353746"),
        ("25780448", "MED:25780448"),
        ("MED:25780448", "MED:25780448"),
        ("med:25780448", "MED:25780448"),
    ],
)
def test_normalize_article_id_is_case_insensitive(raw, expected):
    assert EuroPMCAnnotationsTool._normalize_article_id(raw) == expected


def test_lowercase_prefixed_id_is_sent_canonicalized():
    tool = EuroPMCAnnotationsTool({"name": "europepmc_annotations_by_article"})
    with patch.object(tool, "_fetch_annotations", return_value=[]) as fetch:
        result = tool.run({"article_id": "pmc:PMC4353746"})

    fetch.assert_called_once_with("PMC:PMC4353746", None)
    assert result["status"] == "success"
    assert result["data"]["article_id"] == "PMC:PMC4353746"
