"""A 404 from Expression Atlas must not be reported as a successful lookup.

Found while measuring the Expression Atlas claim of arXiv 2609.26836. The
paper's own claim -- that accession aliases are not resolved -- is not this
layer's: E-MTAB-5214 is absent from the API and absent from the
4,562-experiment listing, so there is no object to alias. Probing it turned
up something that is ours. Measured live 2026-11-12:

    ExpressionAtlas_get_experiment {"accession": "E-MTAB-5214"}
      -> {"status": "success", "data": null}
    GxA_get_experiment_info        {"accession": "E-MTAB-5214"}
      -> {"status": "error", ...}

Two tools over one resource, disagreeing about one accession, and the one
saying success was the wrong one. An accession can 404 because it does not
exist, because it is mistyped, or because it has been RETIRED from Expression
Atlas while still resolving in ArrayExpress/BioStudies -- none of which is a
successful lookup, and a caller that checks `status` was told all three had
worked.
"""

import json
from pathlib import Path

import pytest
import requests

from tooluniverse.expression_atlas_tool import ExpressionAtlasTool

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "expression_atlas_tools.json"
)


def _config(name):
    for tool in json.loads(CONFIG.read_text()):
        if tool.get("name") == name:
            return tool
    raise AssertionError(name)


class _NotFound:
    status_code = 404

    def raise_for_status(self):
        error = requests.exceptions.HTTPError("404 Client Error")
        error.response = self
        raise error

    def json(self):  # pragma: no cover - never reached
        return {}


def test_a_missing_accession_is_an_error(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.expression_atlas_tool.requests.get", lambda *a, **k: _NotFound()
    )
    tool = ExpressionAtlasTool(_config("ExpressionAtlas_get_experiment"))
    result = tool.run({"operation": "get_experiment", "accession": "E-MTAB-5214"})
    assert result["status"] == "error"
    assert "E-MTAB-5214" in result["error"]
    assert result["error_details"]["type"] == "NotFound"
    assert result["error_details"]["http_status"] == 404
    # The error names what to do instead, and names retirement as a cause --
    # an id that resolves elsewhere is still absent here.
    assert "ExpressionAtlas_search_experiments" in result["error"]
    assert "retired" in result["error"].lower()


def test_the_schema_no_longer_promises_a_null_success(monkeypatch):
    schema = _config("ExpressionAtlas_get_experiment")["return_schema"]
    success = schema["oneOf"][0]
    assert success["type"] == "object", "the success branch must not be nullable"
    assert "null when the record does not exist" not in success.get("description", "")
    assert "error_details" in schema["oneOf"][1]["properties"]
