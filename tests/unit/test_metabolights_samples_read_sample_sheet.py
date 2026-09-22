"""metabolights_get_study_samples reported "success, 0 samples" for every study.

The upstream /samples endpoint answers HTTP 400 for all studies and the study
record has no sample rows, so the old fallback always produced an empty
success. The tool now reads the study's public ISA-Tab sample sheet
(s_<id>.txt) and returns an error, not an empty list, when that is missing.
"""

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

SHEET = (
    "Source Name\tCharacteristics[Organism]\tCharacteristics[Organism part]\tSample Name\n"
    "ADG10003u\tHomo sapiens\turine\tADG10003u_1\n"
    "ADG10008u\tHomo sapiens\turine\tADG10008u_1\n"
)


def _tool(sheet_status=200, sheet_text=SHEET):
    from tooluniverse.metabolights_tool import MetaboLightsRESTTool

    tool = MetaboLightsRESTTool(
        {
            "name": "metabolights_get_study_samples",
            "fields": {
                "endpoint": "https://www.ebi.ac.uk/metabolights/ws/studies/{study_id}/samples"
            },
        }
    )
    requested = []

    def fake_get(url, params=None, timeout=None):
        requested.append(url)
        response = MagicMock()
        if url.endswith("/samples"):
            response.status_code = 400
            response.url = url
            return response
        response.status_code = sheet_status
        response.text = sheet_text
        if sheet_status >= 400:
            response.raise_for_status.side_effect = RuntimeError(
                f"{sheet_status} Client Error"
            )
        return response

    tool.session = MagicMock()
    tool.session.get.side_effect = fake_get
    return tool, requested


def test_samples_come_from_the_public_sample_sheet():
    tool, requested = _tool()
    result = tool.run({"study_id": "MTBLS1"})
    assert result["status"] == "success"
    assert result["count"] == result["total_count"] == 2
    assert result["truncated"] is False
    assert result["data"][0] == {
        "Source Name": "ADG10003u",
        "Characteristics[Organism]": "Homo sapiens",
        "Characteristics[Organism part]": "urine",
        "Sample Name": "ADG10003u_1",
    }
    assert requested[-1].endswith("/studies/public/MTBLS1/s_MTBLS1.txt")


def test_missing_sample_sheet_is_an_error_not_an_empty_success():
    tool, _ = _tool(sheet_status=404, sheet_text="")
    result = tool.run({"study_id": "MTBLS99999"})
    assert result["status"] == "error"
    assert "MTBLS99999" in result["error"]


def test_study_id_is_validated_before_building_the_archive_url():
    tool, requested = _tool()
    result = tool.run({"study_id": "../../etc/passwd"})
    assert result["status"] == "error"
    assert not any("etc/passwd" in u and "ftp.ebi.ac.uk" in u for u in requested)


def test_large_sheets_are_capped_and_flagged(monkeypatch):
    import tooluniverse.metabolights_tool as mod

    monkeypatch.setattr(mod, "MAX_SAMPLE_ROWS", 1)
    tool, _ = _tool()
    result = tool.run({"study_id": "MTBLS1"})
    assert result["count"] == 1
    assert result["total_count"] == 2
    assert result["truncated"] is True
