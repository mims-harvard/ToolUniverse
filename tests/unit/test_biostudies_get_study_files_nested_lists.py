"""biostudies_get_study_files returned 0 files for studies that have them.

BioStudies nests a subsection's file entries as a list of lists
("files": [[{...}, {...}]]); the tool only accepted dict entries and skipped
every file (same defect as arrayexpress_get_experiment_files). Shape below is
trimmed from the live record E-GEOD-26319, which lists 4 processed files.
"""

import pytest

pytestmark = pytest.mark.unit


def _file(name, size):
    return {
        "path": name,
        "size": size,
        "attributes": [{"name": "Description", "value": "Processed Data"}],
        "type": "file",
    }


STUDY = {
    "accno": "E-GEOD-26319",
    "section": {
        "type": "Study",
        "subsections": [
            {"accno": "s-protocols", "type": "Protocols"},
            {
                "type": "Assays and Data",
                "subsections": [
                    {
                        "type": "Processed Data",
                        "files": [
                            [
                                _file("GSM646313_sample_table.txt", 843671),
                                _file("GSM646312_sample_table.txt", 844851),
                            ]
                        ],
                    }
                ],
            },
        ],
    },
}


def _tool():
    from tooluniverse.biostudies_tool import BioStudiesRESTTool

    return BioStudiesRESTTool({"name": "biostudies_get_study_files"})


def test_files_nested_as_list_of_lists_are_extracted():
    files = _tool()._extract_files(STUDY)
    assert [f["path"] for f in files] == [
        "GSM646313_sample_table.txt",
        "GSM646312_sample_table.txt",
    ]
    assert files[0]["size"] == 843671
    assert files[0]["attributes"] == [
        {"name": "Description", "value": "Processed Data"}
    ]


def test_flat_dict_file_entries_still_work():
    section = {"type": "Study", "files": [_file("a.txt", 1), _file("b.txt", 2)]}
    files = _tool()._extract_files({"section": section})
    assert [f["path"] for f in files] == ["a.txt", "b.txt"]


def test_top_level_nested_files_array_is_flattened():
    files = _tool()._extract_files({"files": [[_file("a.txt", 1)], _file("b.txt", 2)]})
    assert [f["path"] for f in files] == ["a.txt", "b.txt"]
