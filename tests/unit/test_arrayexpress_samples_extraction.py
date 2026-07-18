"""Regression guard for Fix-R14C-2: arrayexpress_get_experiment_samples
extracted the wrong level of a BioStudies study's section tree. Confirmed
live (raw curl to the BioStudies API for E-GEOD-33447) that the literal
"Samples" section is just a wrapper carrying aggregate summary attributes
("Sample count", one "Experimental Factors" attribute per factor -- which
the old dict-build collapsed to just the last one on name collision), not
per-sample data. The real per-sample-group records live one level deeper,
under a "Source Characteristics" subsection, as "Characteristics Table"
entries (one per distinct combination of characteristics, e.g. age/tissue).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.arrayexpress_tool import ArrayExpressRESTTool

pytestmark = pytest.mark.unit


# Trimmed version of the real BioStudies section tree for E-GEOD-33447,
# preserving the exact nesting shape that caused the bug.
STUDY_SECTION = {
    "accno": "s-E-GEOD-33447",
    "type": "Study",
    "attributes": [],
    "subsections": [
        {
            "accno": "s-samples-factors-E-GEOD-33447",
            "type": "Samples",
            "attributes": [
                {"name": "Sample count", "value": "16"},
                {"name": "Experimental Factors", "value": "TISSUE"},
                {"name": "Experimental Factors", "value": "AGE"},
            ],
            "subsections": [
                {
                    "accno": "source_chars-E-GEOD-33447",
                    "type": "Source Characteristics",
                    "subsections": [
                        [
                            {
                                "accno": "source_0",
                                "type": "Characteristics Table",
                                "attributes": [
                                    {"name": "age", "value": "39 years"},
                                    {"name": "tissue", "value": "normal breast"},
                                    {"name": "No. of Samples", "value": "1"},
                                ],
                            },
                            {
                                "accno": "source_1",
                                "type": "Characteristics Table",
                                "attributes": [
                                    {"name": "age", "value": "49 years"},
                                    {"name": "tissue", "value": "breast cancer"},
                                    {"name": "No. of Samples", "value": "2"},
                                ],
                            },
                        ]
                    ],
                }
            ],
        }
    ],
}


def _tool():
    return ArrayExpressRESTTool({"name": "arrayexpress_get_experiment_samples"})


def test_extracts_real_per_sample_group_records_not_the_wrapper():
    tool = _tool()
    samples = tool._extract_samples_from_section(STUDY_SECTION)

    assert samples == [
        {"age": "39 years", "tissue": "normal breast", "No. of Samples": "1"},
        {"age": "49 years", "tissue": "breast cancer", "No. of Samples": "2"},
    ]


def test_does_not_return_the_aggregate_samples_wrapper_record():
    tool = _tool()
    samples = tool._extract_samples_from_section(STUDY_SECTION)

    assert not any("Sample count" in s for s in samples)
    assert not any("Experimental Factors" in s for s in samples)
