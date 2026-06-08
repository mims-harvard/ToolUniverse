"""
Unit tests for gnomad_get_variant_populations (gnomADGetVariantPopulations).

Covers per-ancestry allele-frequency (af = ac/an) computation, the an==0 guard,
genome vs exome callset separation, and an error path. HTTP is mocked so the
tests run offline.
"""

import pytest

from tooluniverse.gnomad_tool import gnomADGetVariantPopulations

pytestmark = pytest.mark.unit


TOOL_CONFIG = {
    "type": "gnomADGetVariantPopulations",
    "name": "gnomad_get_variant_populations",
    "parameter": {
        "type": "object",
        "properties": {
            "variant_id": {"type": "string"},
            "dataset": {"type": "string"},
        },
        "required": ["variant_id"],
    },
}


class _FakeResponse:
    """Minimal stand-in for a requests.Response."""

    def __init__(
        self, payload, status_code=200, url="https://gnomad.broadinstitute.org/api"
    ):
        self._payload = payload
        self.status_code = status_code
        self.url = url
        self.text = ""

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _make_tool(payload):
    """Build the tool with its session.post patched to return `payload`."""
    tool = gnomADGetVariantPopulations(TOOL_CONFIG)
    tool.session.post = lambda *args, **kwargs: _FakeResponse(payload)
    return tool


def _variant_payload(genome=None, exome=None):
    return {
        "data": {
            "variant": {
                "variant_id": "1-55051215-G-GA",
                "chrom": "1",
                "pos": 55051215,
                "ref": "G",
                "alt": "GA",
                "rsid": "rs527413419",
                "genome": genome,
                "exome": exome,
            }
        }
    }


def test_af_computation_per_population():
    payload = _variant_payload(
        genome={
            "ac": 30,
            "an": 1000,
            "populations": [
                {"id": "amr", "ac": 10, "an": 200},
                {"id": "nfe", "ac": 5, "an": 500},
            ],
        }
    )
    result = _make_tool(payload).run({"variant_id": "1-55051215-G-GA"})

    assert result["status"] == "success"
    data = result["data"]
    assert data["variant_id"] == "1-55051215-G-GA"
    assert data["dataset"] == "gnomad_r4"  # default applied

    genome = data["genome"]
    assert genome["af"] == 30 / 1000
    pops = {p["id"]: p for p in genome["populations"]}
    assert pops["amr"]["af"] == 10 / 200
    assert pops["nfe"]["af"] == 5 / 500
    assert pops["amr"]["ac"] == 10 and pops["amr"]["an"] == 200


def test_an_zero_guard_yields_null_af():
    payload = _variant_payload(
        genome={
            "ac": 0,
            "an": 0,
            "populations": [
                {"id": "mid", "ac": 0, "an": 0},
                {"id": "fin", "ac": 0, "an": None},
            ],
        }
    )
    result = _make_tool(payload).run({"variant_id": "1-55051215-G-GA"})

    genome = result["data"]["genome"]
    assert genome["af"] is None
    pops = {p["id"]: p for p in genome["populations"]}
    assert pops["mid"]["af"] is None  # an == 0
    assert pops["fin"]["af"] is None  # an is None


def test_genome_and_exome_split():
    payload = _variant_payload(
        genome={
            "ac": 4,
            "an": 100,
            "populations": [{"id": "afr", "ac": 4, "an": 100}],
        },
        exome={
            "ac": 9,
            "an": 300,
            "populations": [{"id": "eas", "ac": 9, "an": 300}],
        },
    )
    result = _make_tool(payload).run(
        {"variant_id": "1-55051215-G-GA", "dataset": "gnomad_r4"}
    )

    data = result["data"]
    assert data["genome"]["af"] == 4 / 100
    assert data["exome"]["af"] == 9 / 300
    assert data["genome"]["populations"][0]["id"] == "afr"
    assert data["exome"]["populations"][0]["id"] == "eas"


def test_exome_null_callset_passes_through():
    payload = _variant_payload(
        genome={"ac": 1, "an": 50, "populations": [{"id": "sas", "ac": 1, "an": 50}]},
        exome=None,
    )
    result = _make_tool(payload).run({"variant_id": "1-55051215-G-GA"})

    assert result["status"] == "success"
    assert result["data"]["exome"] is None
    assert result["data"]["genome"]["populations"][0]["af"] == 1 / 50


def test_missing_variant_id_returns_error():
    """A missing variant_id returns an error envelope without an HTTP call."""
    tool = gnomADGetVariantPopulations(TOOL_CONFIG)
    result = tool.run({})
    assert result["status"] == "error"
    assert "variant_id" in result["error"]


def test_variant_not_found_returns_error():
    """A null variant in the response yields an error envelope, never raises."""
    payload = {"data": {"variant": None}}
    result = _make_tool(payload).run({"variant_id": "1-1-A-T"})
    assert result["status"] == "error"
    assert result["data"] is None
    assert "error" in result


def test_graphql_error_path_propagates():
    """GraphQL-level errors (HTTP 200) surface as an error envelope."""
    payload = {"errors": [{"message": "Variant not found"}]}
    result = _make_tool(payload).run({"variant_id": "bad-id"})
    assert result["status"] == "error"
    assert "Variant not found" in result["error"]
