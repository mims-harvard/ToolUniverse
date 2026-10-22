"""Round 226: requested HOCOMOCO PWMs must never disappear silently."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.hocomoco_tool import HocomocoTool

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parents[2] / "src" / "tooluniverse" / "data" / "hocomoco_tools.json"
)


def _config():
    configs = json.loads(CONFIG_PATH.read_text())
    return next(c for c in configs if c["name"] == "HOCOMOCO_get_motif")


def _response(payload, status=200):
    response = MagicMock(status_code=status)
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _detail(full_name="CTCF.H14CORE.0.P.B", model_length=2):
    return {
        "full_name": full_name,
        "gene_name_human": "CTCF",
        "consensus": "AC",
        "model_length": model_length,
    }


def test_requested_pwm_is_validated_and_returned():
    """A valid matrix must match the declared motif length and alphabet width."""
    pwm = [[0.1, 0.2, 0.3, 0.4], [-1.0, 0.0, 1.0, 2.0]]
    with patch(
        "tooluniverse.hocomoco_tool.requests.get",
        side_effect=[_response(_detail()), _response(pwm)],
    ):
        result = HocomocoTool(_config()).run(
            {"motif_id": "CTCF.H14CORE.0.P.B", "include_pwm": True}
        )

    assert result["status"] == "success"
    assert result["data"]["pwm"] == pwm
    assert result["data"]["pwm_requested"] is True
    assert result["data"]["pwm_status"] == "available"


@pytest.mark.parametrize(
    "pwm_response,error_fragment",
    [
        (_response({}, status=503), "HTTP 503"),
        (_response([[0.1, 0.2, 0.3, 0.4]]), "malformed PWM"),
        (_response([[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]), "malformed PWM"),
    ],
)
def test_requested_pwm_failure_never_returns_metadata_only_success(
    pwm_response, error_fragment
):
    """Missing or malformed PWM evidence must fail the requested operation."""
    with patch(
        "tooluniverse.hocomoco_tool.requests.get",
        side_effect=[_response(_detail()), pwm_response],
    ):
        result = HocomocoTool(_config()).run(
            {"motif_id": "CTCF.H14CORE.0.P.B", "include_pwm": True}
        )

    assert result["status"] == "error"
    assert error_fragment in result["error"]
    assert result["pwm_requested"] is True
    assert result["pwm_retrieved"] is False
    assert "data" not in result


def test_motif_identity_mismatch_is_rejected():
    """A valid payload for another motif cannot masquerade as the requested record."""
    with patch(
        "tooluniverse.hocomoco_tool.requests.get",
        return_value=_response(_detail(full_name="CTCFL.H14CORE.0.P.B")),
    ):
        result = HocomocoTool(_config()).run(
            {"motif_id": "CTCF.H14CORE.0.P.B"}
        )
    assert result["status"] == "error"
    assert "identity mismatch" in result["error"]


def test_include_pwm_must_be_boolean_before_network():
    """Truth-like strings cannot silently alter the evidence requirement."""
    with patch("tooluniverse.hocomoco_tool.requests.get") as request:
        result = HocomocoTool(_config()).run(
            {"motif_id": "CTCF.H14CORE.0.P.B", "include_pwm": "true"}
        )
    assert result["status"] == "error"
    assert "boolean" in result["error"]
    request.assert_not_called()


def test_config_documents_pwm_guarantee_and_status_fields():
    """Public schema must describe the stronger requested-data contract."""
    config = _config()
    assert "mandatory" in config["description"]
    properties = config["return_schema"]["properties"]
    assert properties["pwm_status"]["enum"] == ["available", "not_requested"]
    assert properties["pwm_requested"]["type"] == "boolean"
