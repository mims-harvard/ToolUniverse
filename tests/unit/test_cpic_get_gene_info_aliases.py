"""Regression guard for Fix-R31B-3: CPIC_get_gene_info only accepted a
`symbol` parameter, unlike its sibling tool CPIC_search_gene_drug_pairs
which already documents `gene`/`gene_symbol` as aliases -- confirmed live
that the natural-language guess `{"gene": "CYP2D6"}` failed schema
validation on this tool while working fine on the sibling. Added the same
aliases via `fields.path_aliases` (mapped to the canonical `symbol` before
the URL is built) plus an `anyOf` schema so any one of the three names
satisfies validation.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config():
    configs = json.loads((_DATA_DIR / "cpic_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == "CPIC_get_gene_info":
            return cfg
    raise AssertionError("CPIC_get_gene_info not found")


def _tool():
    return BaseRESTTool(_tool_config())


class TestSchemaAcceptsAllAliases:
    def test_symbol_alone_is_valid(self):
        assert _tool().validate_parameters({"symbol": "CYP2D6"}) is None

    def test_gene_alone_is_valid(self):
        assert _tool().validate_parameters({"gene": "CYP2D6"}) is None

    def test_gene_symbol_alone_is_valid(self):
        assert _tool().validate_parameters({"gene_symbol": "CYP2D6"}) is None

    def test_none_of_the_three_is_invalid(self):
        assert _tool().validate_parameters({}) is not None


class TestAliasResolvesToCanonicalUrlParam:
    def test_gene_alias_builds_symbol_url_without_leaking_gene_param(self):
        tool = _tool()
        args = {"gene": "CYP2D6"}
        url = tool._build_url(args)
        params = tool._build_params(args)

        assert "symbol=eq.CYP2D6" in url
        assert "gene" not in params

    def test_gene_symbol_alias_resolves_to_symbol_in_url(self):
        tool = _tool()
        args = {"gene_symbol": "CYP2C19"}
        url = tool._build_url(args)

        assert "symbol=eq.CYP2C19" in url

    def test_run_uppercases_a_lowercase_gene_alias(self):
        # End-to-end: run()'s uppercase_params step (Fix-R30E-3) must apply
        # regardless of which alias name the caller used.
        tool = _tool()
        import unittest.mock as mock

        captured = {}

        def fake_request(session, method, url, **kwargs):
            captured["url"] = url
            resp = mock.MagicMock()
            resp.status_code = 200
            resp.json.return_value = []
            resp.headers = {"content-type": "application/json"}
            resp.text = "[]"
            return resp

        with mock.patch(
            "tooluniverse.base_rest_tool.request_with_retry", side_effect=fake_request
        ):
            tool.run({"gene": "cyp2d6"})

        assert "symbol=eq.CYP2D6" in captured["url"]
