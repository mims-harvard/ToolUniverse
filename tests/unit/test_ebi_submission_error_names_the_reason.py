"""EBI Job Dispatcher submission errors give EBI's reason, and name its faults.

Run 37273817054 quoted 11 EBI failures as "... (HTTP 400): <?xml version=
'1.0' encoding='UTF-8'?>" -- the slice stopped before the reason. The reason
was a missing file on EBI's own disk, for every service at once.
"""

import pytest

from tooluniverse.ebi_alignment_tool import _submission_error

pytestmark = pytest.mark.unit

XML = "<?xml version='1.0' encoding='UTF-8'?>\n<error>\n<description>{}</description>\n</error>"


def test_a_server_side_file_error_is_named_as_ebis():
    body = XML.format(
        "/nfs/public/rw/es/projects/wp-jdispatcher/sources/prod-hl/jobs/clustalo/"
        "rest/20261005/0744/clustalo-R20261005-074427-0916-56309048-p1m.params "
        "(No such file or directory)"
    )

    message = _submission_error("clustalo", 400, body)

    assert "on EBI's side" in message
    assert "server fault" in message
    assert "<?xml" not in message


def test_a_request_error_quotes_ebis_description():
    body = XML.format("Invalid parameters: \\n Sequence -> Sequence is required")

    message = _submission_error("mafft", 400, body)

    assert message.startswith("mafft submission failed (HTTP 400): Invalid parameters")
    assert "EBI's side" not in message


def test_a_body_that_is_not_xml_is_quoted():
    assert _submission_error("phobius", 503, "Service Unavailable").endswith(
        "Service Unavailable"
    )
