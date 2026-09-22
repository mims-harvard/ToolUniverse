"""arrayexpress_get_experiment_files returned 0 files for experiments that have them.

BioStudies nests a subsection's file entries one level deeper as a list of lists
("files": [[{...}, {...}]]). The extractor only accepted dict entries, so it
silently skipped every file. Shape below is trimmed from the real study record
E-GEOD-26319 (Assays and Data -> Processed Data), which the API reports as 4 files.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.arrayexpress_tool import ArrayExpressRESTTool

pytestmark = pytest.mark.unit


def _tool():
    return ArrayExpressRESTTool({"name": "arrayexpress_get_experiment_files"})


def _file(name, size):
    return {
        "path": name,
        "size": size,
        "attributes": [{"name": "Description", "value": "Processed Data"}],
        "type": "file",
    }


NESTED_SECTION = {
    "accno": "E-GEOD-26319",
    "type": "Study",
    "subsections": [
        {"accno": "s-protocols", "type": "Protocols"},
        {
            "accno": "s-assays-data-E-GEOD-26319",
            "type": "Assays and Data",
            "subsections": [
                {
                    "accno": "processed-data",
                    "type": "Processed Data",
                    "files": [
                        [
                            _file("GSM646313_sample_table.txt", 843671),
                            _file("GSM646312_sample_table.txt", 844851),
                        ]
                    ],
                },
                {
                    "accno": "mage-tab",
                    "type": "MAGE-TAB Files",
                    "files": [[_file("E-GEOD-26319.idf.txt", 5000)]],
                },
            ],
        },
    ],
}


def test_files_nested_as_list_of_lists_are_extracted():
    files = _tool()._extract_files_from_section(NESTED_SECTION)
    assert [f["name"] for f in files] == [
        "GSM646313_sample_table.txt",
        "GSM646312_sample_table.txt",
        "E-GEOD-26319.idf.txt",
    ]
    assert files[0] == {
        "name": "GSM646313_sample_table.txt",
        "size": 843671,
        "type": "file",
    }


def test_flat_dict_file_entries_still_work():
    section = {"type": "Study", "files": [_file("a.txt", 1), _file("b.txt", 2)]}
    files = _tool()._extract_files_from_section(section)
    assert [f["name"] for f in files] == ["a.txt", "b.txt"]


def test_mixed_nesting_depths_are_flattened():
    section = {
        "type": "Study",
        "files": [_file("a.txt", 1), [_file("b.txt", 2), [_file("c.txt", 3)]]],
    }
    files = _tool()._extract_files_from_section(section)
    assert [f["name"] for f in files] == ["a.txt", "b.txt", "c.txt"]


def test_section_without_files_returns_empty_list():
    assert _tool()._extract_files_from_section({"type": "Study"}) == []
