"""Regression guard for Fix-R23D-2: GTDB_get_species's species/search
endpoint is case-sensitive on binomial capitalization (confirmed live:
lowercase "akkermansia muciniphila" 404s with a misleading "no genomes
found" error while "Akkermansia muciniphila" succeeds), unlike the sibling
GTDB_search_genomes endpoint which matches case-insensitively. Fixed by
normalizing input to Genus-capitalized/species-lowercase before querying.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.gtdb_tool import GTDBTool

pytestmark = pytest.mark.unit

_SPECIES_RESPONSE = {
    "name": "Akkermansia muciniphila",
    "genomes": [
        {"accession": "GCA_000723745.2", "ncbi_org_name": "Akkermansia muciniphila"}
    ],
}


def _tool():
    return GTDBTool({"name": "gtdb_test", "parameter": {}})


def _resp(status_code, json_body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    r.headers = {"content-type": "application/json"}
    return r


class TestSpeciesCaseNormalization:
    def test_lowercase_input_still_resolves(self):
        tool = _tool()
        resp = _resp(200, _SPECIES_RESPONSE)

        with patch.object(tool.session, "get", return_value=resp) as mock_get:
            result = tool.run(
                {"operation": "get_species", "species": "akkermansia muciniphila"}
            )

        assert result["status"] == "success"
        assert result["data"]["species_name"] == "Akkermansia muciniphila"
        called_url = mock_get.call_args[0][0]
        assert (
            "Akkermansia%20muciniphila" in called_url
            or "Akkermansia muciniphila" in called_url
        )

    def test_already_proper_case_unaffected(self):
        tool = _tool()
        resp = _resp(200, _SPECIES_RESPONSE)

        with patch.object(tool.session, "get", return_value=resp):
            result = tool.run(
                {"operation": "get_species", "species": "Akkermansia muciniphila"}
            )

        assert result["status"] == "success"
        assert result["data"]["total_genomes"] == 1

    def test_all_uppercase_input_normalized(self):
        tool = _tool()
        resp = _resp(200, _SPECIES_RESPONSE)

        with patch.object(tool.session, "get", return_value=resp) as mock_get:
            tool.run({"operation": "get_species", "species": "AKKERMANSIA MUCINIPHILA"})

        called_url = mock_get.call_args[0][0]
        assert "MUCINIPHILA" not in called_url
