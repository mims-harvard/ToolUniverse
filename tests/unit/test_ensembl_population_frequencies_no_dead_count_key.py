"""EnsemblVar_get_population_frequencies must not emit a `count` key.

Regression for Fix-R33. Each population entry carried
`"count": pop.get("count")`, but Ensembl's variation records have no such
field, so the key was null on 100% of rows forever. Sitting beside a populated
`allele_count`, that null invited the reading "this population was measured but
the sample size is unknown" -- a claim Ensembl never makes.

Verified live against
https://rest.ensembl.org/variation/human/rs4244285?pops=1&content-type=application/json
-- 148 population entries, key sets counted:
  146 x ('allele', 'allele_count', 'frequency', 'population')
    2 x ('allele', 'frequency', 'population')   [TOPMed]
`count` appeared ZERO times.

The two TOPMed entries are the reason `allele_count` must KEEP its None: there
the null is real missing data reported by the source, unlike `count`, which
never existed.

All assertions run against a synthetic Ensembl payload -- no network.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import tooluniverse
from tooluniverse.ensembl_variation_ext_tool import EnsemblVariationExtTool

pytestmark = pytest.mark.unit

CONFIG = next(
    c
    for c in json.loads(
        (
            Path(tooluniverse.__file__).parent
            / "data"
            / "ensembl_variation_ext_tools.json"
        ).read_text()
    )
    if c["name"] == "EnsemblVar_get_population_frequencies"
)

# Mirrors the real rs4244285 payload shape: gnomAD entries carry allele_count,
# TOPMed entries carry only population/allele/frequency.
WITH_ALLELE_COUNT = [
    {
        "population": "gnomADe:fin",
        "allele": "A",
        "frequency": 0.1726,
        "allele_count": 8799,
    },
    {
        "population": "gnomADe:mid",
        "allele": "A",
        "frequency": 0.1102,
        "allele_count": 586,
    },
]
WITHOUT_ALLELE_COUNT = [
    {"population": "TOPMed", "allele": "A", "frequency": 0.167311735},
    {"population": "TOPMed", "allele": "G", "frequency": 0.832688265},
]


def _payload(populations=None):
    return {
        "name": "rs4244285",
        "most_severe_consequence": "synonymous_variant",
        "source": "Variants (including SNPs and indels) imported from dbSNP",
        "mappings": [
            {
                "seq_region_name": "10",
                "start": 94781859,
                "allele_string": "G/A/C/T",
                "assembly_name": "GRCh38",
            }
        ],
        "populations": (
            WITH_ALLELE_COUNT + WITHOUT_ALLELE_COUNT
            if populations is None
            else populations
        ),
    }


def _run(payload):
    tool = EnsemblVariationExtTool(
        {
            "name": "EnsemblVar_get_population_frequencies",
            "fields": {"endpoint": "population_frequencies"},
        }
    )

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    with patch(
        "tooluniverse.ensembl_variation_ext_tool.requests.get",
        return_value=_Response(),
    ):
        result = tool.run({"variant_id": "rs4244285"})
    assert result["status"] == "success"
    return result["data"]


def test_dead_count_key_is_absent_from_every_population_entry():
    populations = _run(_payload())["populations"]

    assert len(populations) == 4
    assert all("count" not in entry for entry in populations)


def test_allele_count_keeps_its_none_when_the_source_omits_it():
    """Unlike `count`, a null allele_count is real missing data from Ensembl."""
    populations = _run(_payload())["populations"]

    topmed = [e for e in populations if e["population"] == "TOPMed"]
    assert len(topmed) == 2
    assert all("allele_count" in e for e in topmed)
    assert all(e["allele_count"] is None for e in topmed)
    assert {e["frequency"] for e in topmed} == {0.167311735, 0.832688265}


def test_populated_allele_counts_are_unchanged():
    """Additive-safe: the keys that carried real data still carry it."""
    populations = _run(_payload())["populations"]

    gnomad = {
        e["population"]: e["allele_count"]
        for e in populations
        if e["population"].startswith("gnomADe")
    }
    assert gnomad == {"gnomADe:fin": 8799, "gnomADe:mid": 586}


def test_entry_key_set_is_exactly_the_four_fields_ensembl_publishes():
    for entry in _run(_payload())["populations"]:
        assert set(entry) == {"population", "allele", "frequency", "allele_count"}


def test_config_no_longer_advertises_a_count_field():
    entry_props = None
    for branch in CONFIG["return_schema"]["oneOf"]:
        populations = branch.get("properties", {}).get("populations")
        if populations:
            entry_props = populations["items"]["properties"]
    assert entry_props is not None
    assert "count" not in entry_props
    assert set(entry_props) == {"population", "allele", "frequency", "allele_count"}
    # allele_count stays nullable: the TOPMed rows above genuinely lack it.
    assert entry_props["allele_count"]["type"] == ["integer", "null"]


def test_description_does_not_promise_a_sample_size():
    assert "no sample size" in CONFIG["description"].lower()
