"""Regression guard for #683: ClinGen_get_variant_classifications reported
curated variants as "genuinely uncurated" when queried by CAid.

The `classifications` endpoint stores an empty `caid` on some records
(CA015543, APC c.847C>T, Pathogenic), matches `caid` / `variationId` on
substring, and can lag the current document version. CAid and ClinVar
VariationID lookups now match exactly on `summary/classifications`, and a CAid
with no match is retried through the ClinGen Allele Registry's ClinVar IDs.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.clingen_tool import ClinGenTool

pytestmark = pytest.mark.unit

SUMMARY_URL = "https://erepo.clinicalgenome.org/evrepo/api/summary/classifications"
CLASSIFICATIONS_URL = "https://erepo.clinicalgenome.org/evrepo/api/classifications"
REGISTRY_URL = "https://reg.genome.network/allele/"


def _row(uuid, caid, cvid, gene, classification, ep, hgvs_title):
    return {
        "uuid": uuid,
        "caId": caid,
        "cvId": cvid,
        "gene": gene,
        "condition": "some condition",
        "mondoId": "MONDO:0000001",
        "classification": classification,
        "ep": ep,
        "hgvs": [hgvs_title.split("(")[0] + ":c.1A>G", hgvs_title],
    }


APC = _row(
    "u-apc",
    "CA015543",
    "184999",
    "APC",
    "Pathogenic",
    "InSiGHT Hereditary Colorectal Cancer/Polyposis VCEP",
    "NM_000038.6(APC):c.847C>T (p.Arg283Ter)",
)
RYR1_MYOPATHY = _row(
    "u-ryr1-a",
    "CA024187",
    "12982",
    "RYR1",
    "Pathogenic",
    "Congenital Myopathies VCEP",
    "NM_000540.3(RYR1):c.14582G>A (p.Arg4861His)",
)
RYR1_MHS = _row(
    "u-ryr1-b",
    "CA024187",
    "12982",
    "RYR1",
    "Uncertain Significance",
    "Malignant Hyperthermia Susceptibility VCEP",
    "NM_000540.3(RYR1):c.14582G>A (p.Arg4861His)",
)
# Stored without a CAid in either endpoint; reachable only by ClinVar ID.
VWF_NO_CAID = dict(
    _row(
        "u-vwf",
        None,
        "440410",
        "VWF",
        "Benign",
        "von Willebrand Disease VCEP",
        "NM_000552.5(VWF):c.1A>G (p.Met1Val)",
    ),
    caId=None,
)
NEAR_MISS_CV = _row(
    "u-near",
    "CA119132",
    "18041",
    "ABCA4",
    "Pathogenic",
    "x",
    "NM_000350.3(ABCA4):c.1A>G (p.Met1Val)",
)


def _response(status, payload):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    if status >= 400:
        err = requests.exceptions.HTTPError(f"{status}")
        err.response = MagicMock(status_code=status, text=str(payload))
        r.raise_for_status.side_effect = err
    return r


NO_RECORDS = {"status": {"code": 404, "msg": "No records were found for given query"}}


def _fake_get(summary_rows=(), registry=None, classifications=(), summary_error=None):
    """Route requests.get by URL like the live services do."""
    registry = registry or {}

    def get(url, params=None, timeout=None, **_):
        if url == SUMMARY_URL:
            if summary_error:
                return _response(summary_error, {"status": {"msg": "Server Error"}})
            column, value = params["columns"], params["values"]
            # The real endpoint matches exactly; NEAR_MISS_CV checks the
            # client re-checks anyway.
            rows = [r for r in summary_rows if r.get(column) == value]
            if column == "cvId" and value == "804":
                rows = [NEAR_MISS_CV]
            return (
                _response(200, {"data": rows}) if rows else _response(404, NO_RECORDS)
            )
        if url.startswith(REGISTRY_URL):
            caid = url[len(REGISTRY_URL) :]
            if isinstance(registry, Exception):
                raise registry
            if caid not in registry:
                return _response(404, {"errorType": "NotFound"})
            records = [{"variationId": int(v)} for v in registry[caid]]
            return _response(200, {"externalRecords": {"ClinVarVariations": records}})
        if url == CLASSIFICATIONS_URL:
            return _response(200, {"variantInterpretations": list(classifications)})
        raise AssertionError(f"unexpected URL {url}")

    return get


def _run(arguments, **fake):
    tool = ClinGenTool(
        {"fields": {"operation": "get_variant_classifications"}, "parameter": {}}
    )
    with patch(
        "tooluniverse.clingen_tool.requests.get", side_effect=_fake_get(**fake)
    ) as mock_get:
        result = tool.run(arguments)
    return result, [c.args[0] for c in mock_get.call_args_list]


class TestCaidLookup:
    def test_caid_missing_from_classifications_is_found(self):
        result, urls = _run({"variant": "CA015543"}, summary_rows=[APC])

        assert result["status"] == "success"
        assert result["total"] == 1
        row = result["data"][0]
        assert row["Assertion"] == "Pathogenic"
        assert row["Variation"] == "NM_000038.6(APC):c.847C>T (p.Arg283Ter)"
        assert row["ClinVar Variation Id"] == "184999"
        assert row["Expert Panel"].startswith("InSiGHT")
        assert CLASSIFICATIONS_URL not in urls
        assert "note" not in result

    def test_every_classification_of_the_allele_is_returned(self):
        result, _ = _run(
            {"variant": "CA024187"}, summary_rows=[RYR1_MYOPATHY, RYR1_MHS]
        )

        assert sorted(r["Expert Panel"] for r in result["data"]) == [
            "Congenital Myopathies VCEP",
            "Malignant Hyperthermia Susceptibility VCEP",
        ]

    def test_lowercase_and_prefixed_caid_are_normalised(self):
        for variant in ("ca015543", "CAR:CA015543"):
            result, _ = _run({"variant": variant}, summary_rows=[APC])
            assert result["total"] == 1

    def test_record_without_caid_is_reached_through_clinvar_id(self):
        result, urls = _run(
            {"variant": "CA645509542"},
            summary_rows=[VWF_NO_CAID],
            registry={"CA645509542": ["440410"]},
        )

        assert result["total"] == 1
        assert result["data"][0]["Assertion"] == "Benign"
        assert any(u.startswith(REGISTRY_URL) for u in urls)
        assert "440410" in result["note"]

    def test_registry_is_not_called_when_the_caid_matches(self):
        _, urls = _run({"variant": "CA015543"}, summary_rows=[APC])
        assert not any(u.startswith(REGISTRY_URL) for u in urls)


class TestEmptyResultsSayWhatWasChecked:
    def test_unknown_caid(self):
        result, _ = _run({"variant": "CA9999999999"})

        assert result["status"] == "success"
        assert result["total"] == 0
        note = result["note"]
        assert "CA9999999999" in note
        assert "genuinely uncurated" not in note

    def test_caid_with_clinvar_ids_but_no_classification(self):
        result, _ = _run(
            {"variant": "CA181077"}, registry={"CA181077": ["181077", "99"]}
        )

        assert result["total"] == 0
        assert "181077, 99" in result["note"]

    def test_registry_failure_is_flagged_not_reported_as_absence(self):
        result, _ = _run(
            {"variant": "CA015543"},
            registry=requests.exceptions.ConnectionError("reset"),
        )

        assert result["status"] == "success"
        assert result["total"] == 0
        assert "could not be reached" in result["note"]

    def test_summary_server_error_is_an_error(self):
        result, _ = _run({"variant": "CA015543"}, summary_error=500)
        assert result["status"] == "error"

    def test_hgvs_miss_points_at_notation(self):
        result, _ = _run({"variant": "NM_000527.5:c.654_656del"})

        assert result["total"] == 0
        assert "notation" in result["note"]
        assert "genuinely uncurated" not in result["note"]


class TestExactMatching:
    def test_clinvar_id_is_not_a_substring_match(self):
        result, urls = _run({"variant": "804"})

        assert urls[0] == SUMMARY_URL
        assert result["total"] == 0

    def test_clinvar_id_lookup(self):
        result, _ = _run({"variant": "184999"}, summary_rows=[APC])
        assert result["data"][0]["Variation"].startswith("NM_000038.6(APC)")

    def test_gene_listing_drops_substring_genes(self):
        atm = {
            "gene": {"label": "ATM"},
            "hgvs": ["NM_000051.4(ATM):c.1A>G (p.Met1Val)"],
            "guidelines": [],
        }
        gatm = {
            "gene": {"label": "GATM"},
            "hgvs": ["NM_001482.3(GATM):c.1A>G (p.Met1Val)"],
            "guidelines": [],
        }
        result, _ = _run({"gene": "ATM"}, classifications=[atm, gatm, atm])

        assert result["total"] == 2
        assert {r["HGNC Gene Symbol"] for r in result["data"]} == {"ATM"}

    def test_gene_also_scopes_an_identifier_lookup(self):
        result, _ = _run({"variant": "CA015543", "gene": "BRCA1"}, summary_rows=[APC])

        assert result["total"] == 0
        assert "BRCA1" in result["note"]
        assert "CA015543" in result["note"]
