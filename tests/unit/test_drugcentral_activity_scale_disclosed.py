"""Round 31: DrugCentral_get_targets emitted a p-scale potency under a bare
"IC50" label with no units.

DrugCentral (via MyChem.info) stores bioactivity potency in ``act_value`` on
the pChEMBL scale -- ``-log10`` of the molar potency -- not as a nM/uM
concentration. The tool renamed that field to ``activity_value`` and paired it
with ``activity_type: "IC50"``, so a caller reading
``{"activity_type": "IC50", "activity_value": "4.01"}`` naturally reads it as
an IC50 of 4.01 nM (or uM). The real IC50 is 10^-4.01 M = ~96800 nM (96.8 uM)
-- verified against ChEMBL for praziquantel/ABCB11 (CHEMBL976/CHEMBL6020:
IC50 96800 nM, pchembl 4.01) and for miltefosine/AKT1 (IC50 9600 nM,
pchembl 5.02). That is a ~5-order-of-magnitude misstatement.

The fix is purely additive: ``activity_value`` and ``activity_type`` keep
their exact upstream values, and new sibling keys
(``activity_type_reported``, ``activity_value_scale``, ``activity_value_nM``)
make the scale unambiguous.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.drugcentral_tool import DrugCentralTool

pytestmark = pytest.mark.unit


# Shape copied from the live response for
# https://mychem.info/v1/query?q=drugcentral.xrefs.chembl_id:CHEMBL976&fields=drugcentral.bioactivity
_PRAZIQUANTEL_TARGETS_RESPONSE = {
    "_id": "FSVJFNAIGNNGKK-UHFFFAOYSA-N",
    "drugcentral": {
        "_license": "http://bit.ly/2SeEhUy",
        "structures": {"inn": "praziquantel"},
        "bioactivity": {
            "act_source": "CHEMBL",
            "act_type": "IC50",
            "act_value": "4.01",
            "organism": "Homo sapiens",
            "target_class": "Transporter",
            "target_name": "Bile salt export pump",
            "uniprot": [
                {
                    "gene_symbol": "ABCB11",
                    "swissprot_entry": "ABCBB_HUMAN",
                    "uniprot_id": "O95342",
                }
            ],
        },
    },
}

# Upstream legitimately omits act_type/act_value for many rows (34 of 143 in a
# live sample), and MoA-only rows carry an action_type but no potency at all.
_MISSING_AND_JUNK_VALUES_RESPONSE = {
    "_id": "XZWYZXLIPXDOLR-UHFFFAOYSA-N",
    "drugcentral": {
        "structures": {"inn": "metformin"},
        "bioactivity": [
            {
                "act_source": "DRUG LABEL",
                "action_type": "INHIBITOR",
                "moa": "1",
                "organism": "Homo sapiens",
                "target_name": "Solute carrier family 22 member 1",
                "uniprot": [{"gene_symbol": "SLC22A1", "uniprot_id": "O15245"}],
            },
            {
                "act_source": "WOMBAT-PK",
                "act_type": "Ki",
                "act_value": "",
                "target_name": "Empty string value",
            },
            {
                "act_source": "CHEMBL",
                "act_type": "IC50",
                "act_value": "not-a-number",
                "target_name": "Unparseable value",
            },
            {
                "act_source": "CHEMBL",
                "act_type": "Kd",
                "act_value": None,
                "target_name": "Explicit null value",
            },
        ],
    },
}


def _tool(operation="get_targets"):
    return DrugCentralTool(
        {"name": "drugcentral_test", "fields": {"operation": operation}}
    )


def _resp(json_body):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = json_body
    r.raise_for_status = MagicMock()
    return r


def _run(payload, arguments):
    tool = _tool()
    with patch("tooluniverse.drugcentral_tool.requests.get", return_value=_resp(payload)):
        return tool.run(arguments)


class TestPScaleDisclosed:
    def test_activity_value_is_unchanged(self):
        """Additive fix: existing callers must still see the exact old value."""
        result = _run(_PRAZIQUANTEL_TARGETS_RESPONSE, {"chem_id": "CHEMBL976"})

        assert result["status"] == "success"
        target = result["data"]["targets"][0]
        assert target["activity_value"] == "4.01"
        assert target["activity_type"] == "IC50"

    def test_scale_and_units_keys_present(self):
        result = _run(_PRAZIQUANTEL_TARGETS_RESPONSE, {"chem_id": "CHEMBL976"})
        target = result["data"]["targets"][0]

        assert target["activity_type_reported"] == "pIC50"

        scale = target["activity_value_scale"]
        assert isinstance(scale, str) and scale
        # Must say -log10 / molar and must say it is not a concentration.
        assert "-log10" in scale
        assert "not a concentration" in scale.lower()

    def test_derived_nanomolar_matches_chembl(self):
        """pIC50 4.01 -> ~96800 nM, per ChEMBL activity CHEMBL976/CHEMBL6020."""
        result = _run(_PRAZIQUANTEL_TARGETS_RESPONSE, {"chem_id": "CHEMBL976"})
        nanomolar = result["data"]["targets"][0]["activity_value_nM"]

        assert nanomolar == pytest.approx(96800, rel=0.05)
        # Sanity: the old bare number would have been read as ~4 nM.
        assert nanomolar > 10000

    def test_derived_nanomolar_for_miltefosine_akt1(self):
        """Second verified point: pIC50 5.02 -> ~9600 nM (ChEMBL AKT1)."""
        payload = {
            "drugcentral": {
                "structures": {"inn": "miltefosine"},
                "bioactivity": {
                    "act_source": "CHEMBL",
                    "act_type": "IC50",
                    "act_value": "5.02",
                    "target_name": "Serine/threonine-protein kinase AKT",
                    "uniprot": [{"gene_symbol": "AKT1", "uniprot_id": "P31749"}],
                },
            }
        }
        result = _run(payload, {"chem_id": "CHEMBL1200365"})
        target = result["data"]["targets"][0]

        assert target["activity_value"] == "5.02"
        assert target["activity_type_reported"] == "pIC50"
        assert target["activity_value_nM"] == pytest.approx(9600, rel=0.05)


class TestNonNumericAndMissingValues:
    def test_no_crash_and_no_fabricated_concentration(self):
        result = _run(_MISSING_AND_JUNK_VALUES_RESPONSE, {"chem_id": "CHEMBL1431"})

        assert result["status"] == "success"
        targets = result["data"]["targets"]
        assert len(targets) == 4

        for target in targets:
            # Key may be absent or null, but must never be a made-up number.
            assert target.get("activity_value_nM") is None

    def test_missing_activity_type_yields_null_reported_type(self):
        result = _run(_MISSING_AND_JUNK_VALUES_RESPONSE, {"chem_id": "CHEMBL1431"})
        moa_only = result["data"]["targets"][0]

        assert moa_only["activity_type"] is None
        assert moa_only.get("activity_type_reported") is None
        assert moa_only["is_moa"] is True

    def test_present_activity_type_still_gets_p_prefix(self):
        result = _run(_MISSING_AND_JUNK_VALUES_RESPONSE, {"chem_id": "CHEMBL1431"})
        by_name = {t["target_name"]: t for t in result["data"]["targets"]}

        assert by_name["Empty string value"]["activity_type_reported"] == "pKi"
        assert by_name["Explicit null value"]["activity_type_reported"] == "pKd"
