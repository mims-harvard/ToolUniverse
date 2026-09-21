"""BRENDA tools raised UnboundLocalError when ``zeep`` is not installed.

Each SOAP method did ``from zeep.exceptions import Fault`` inside its ``try`` and then
``except Fault``. With zeep missing the import raised ImportError, the handler
expression ``Fault`` was evaluated while unbound, and an UnboundLocalError escaped
``run()`` instead of ``_get_client()``'s "pip install zeep" message. ``Fault`` is now
imported once at module level (with a placeholder class when zeep is absent).
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse import brenda_tool
from tooluniverse.brenda_tool import BRENDATool

pytestmark = pytest.mark.unit

OPERATIONS = [
    ("get_km", {"ec_number": "1.1.1.1"}),
    ("get_kcat", {"ec_number": "1.1.1.1"}),
    ("get_inhibitors", {"ec_number": "1.1.1.1"}),
    ("get_enzyme_info", {"ec_number": "1.1.1.1"}),
]


@pytest.fixture
def brenda_credentials(monkeypatch):
    monkeypatch.setenv("BRENDA_EMAIL", "user@example.org")
    monkeypatch.setenv("BRENDA_PASSWORD", "secret")


@pytest.mark.parametrize("operation,arguments", OPERATIONS)
def test_missing_zeep_gives_an_install_hint_not_an_unbound_local_error(
    monkeypatch, brenda_credentials, operation, arguments
):
    monkeypatch.setitem(sys.modules, "zeep", None)  # `from zeep import ...` fails
    result = BRENDATool({"name": "BRENDA_" + operation}).run(
        {"operation": operation, **arguments}
    )
    assert result["status"] == "error"
    assert "pip install zeep" in result["error"]


def test_soap_fault_about_credentials_is_still_translated(brenda_credentials):
    client = MagicMock()
    client.service.getKmValue.side_effect = brenda_tool.Fault("Wrong password")
    with patch.object(brenda_tool, "_get_client", return_value=client):
        result = BRENDATool({"name": "BRENDA_get_km"}).run(
            {"operation": "get_km", "ec_number": "1.1.1.1"}
        )
    assert result["status"] == "error"
    assert "Invalid BRENDA credentials" in result["error"]


def test_fault_is_an_exception_class_whether_or_not_zeep_is_installed():
    assert issubclass(brenda_tool.Fault, Exception)
