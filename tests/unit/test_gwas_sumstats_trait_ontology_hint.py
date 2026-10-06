"""Regression guard for Fix-R21E-2, carried across the v2 migration.

The original trap: GWASSumStats_get_trait_studies took an EFO id, and a
caller holding a MONDO id from a sibling database (PGS Catalog uses MONDO
for the same diseases) got a bare 404 with no hint about why. That was fixed
by naming the likely namespace mismatch.

The GWAS Catalog v2 API filters studies on the trait LABEL, so no ontology id
works any more -- and worse, an id returns zero studies rather than an error,
which reads as "this trait has no studies". The guard therefore widened: any
ontology id, MONDO or EFO, must produce an error that explains what to pass
instead. EFO_0000249, the id the old tool documented, is itself obsolete now
(OLS resolves it to "obsolete_Alzheimer's disease").
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.gwas_sumstats_tool import GWASSumStatsTool

pytestmark = pytest.mark.unit


def _tool():
    return GWASSumStatsTool(
        {"name": "gwas_sumstats_test", "fields": {"endpoint_type": "get_trait_studies"}}
    )


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.raise_for_status = MagicMock()
    r.json.return_value = json_body or {}
    return r


@pytest.mark.parametrize("trait_id", ["MONDO_0004975", "EFO_0000249", "EFO_9999999"])
def test_any_ontology_id_is_explained(trait_id):
    """Zero studies for an id is indistinguishable from a trait with none."""
    with patch("tooluniverse.gwas_sumstats_tool.requests.get") as get:
        result = _tool().run({"trait_id": trait_id})

    assert result["status"] == "error"
    assert trait_id in result["error"]
    assert "label" in result["error"]
    # No request is worth making: the API would answer 200 with nothing.
    get.assert_not_called()


def test_a_label_succeeds():
    body = {
        "_embedded": {
            "studies": [
                {
                    "accessionId": "GCST002245",
                    "reportedTrait": "Alzheimer's disease",
                    "efoTraits": [{"key": "EFO_0000249", "label": "Alzheimer disease"}],
                }
            ]
        },
        "page": {"totalElements": 1},
    }
    with patch(
        "tooluniverse.gwas_sumstats_tool.requests.get", return_value=_resp(200, body)
    ):
        result = _tool().run({"trait": "Alzheimer disease"})

    assert result["status"] == "success"
    assert result["data"][0]["study_accession"] == "GCST002245"
