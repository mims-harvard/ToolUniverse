"""Regression guard for Fix-R28-4: PubChem_get_compound_2D_image_by_CID
returned raw `bytes` for its "PNG"/"SVG" return_format instead of a
JSON-serializable envelope. Confirmed live this crashed the CLI outright:
`TypeError: Object of type bytes is not JSON serializable` in both
`--json` and default rendering modes. Fixed by base64-encoding the image
into {status, data: {image_base64, encoding, format}}.
"""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.pubchem_tool import PubChemRESTTool

pytestmark = pytest.mark.unit

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"fake-png-bytes"


def _tool():
    return PubChemRESTTool(
        {
            "name": "PubChem_get_compound_2D_image_by_CID",
            "type": "PubChemRESTTool",
            "fields": {
                "endpoint": "/compound/cid/{cid}/PNG?image_size={image_size}",
                "return_format": "PNG",
            },
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _png_response():
    r = MagicMock()
    r.status_code = 200
    r.content = _PNG_MAGIC
    return r


class TestImageEnvelope:
    def test_returns_json_serializable_envelope_not_raw_bytes(self):
        tool = _tool()
        with patch(
            "tooluniverse.pubchem_tool.requests.get", return_value=_png_response()
        ):
            result = tool.run({"cid": 9554, "image_size": "300x300"})

        assert result["status"] == "success"
        assert isinstance(result["data"]["image_base64"], str)
        # Must not raise -- this is exactly what crashed the CLI before the fix.
        json.dumps(result)

    def test_base64_round_trips_to_original_bytes(self):
        tool = _tool()
        with patch(
            "tooluniverse.pubchem_tool.requests.get", return_value=_png_response()
        ):
            result = tool.run({"cid": 9554, "image_size": "300x300"})

        decoded = base64.b64decode(result["data"]["image_base64"])
        assert decoded == _PNG_MAGIC
        assert result["data"]["format"] == "png"
