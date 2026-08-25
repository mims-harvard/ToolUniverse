"""ClinGen allele coordinates must arrive with their frame attached.

Regression for Fix-R36. `ClinGenAllele_lookup_hgvs` / `_get_allele` emitted
genomic coordinates with no statement of the coordinate convention and dropped
the upstream `referenceSequence`, leaving two silent failure modes.

(1) Off-by-one. The registry reports interbase (0-based, half-open) coordinates.
Verified live:
  python -m tooluniverse.cli run ClinGenAllele_lookup_hgvs \
      '{"hgvs":"NM_000059.3:c.1234C>G"}'
    -> genomic_alleles[0] = {"chromosome":"13","start":32332711,
                             "end":32332712,"allele":"G",
                             "reference_allele":"C","reference_genome":"GRCh38"}
while the SAME record's own cross-references say the variant is at the 1-based
position 32,332,712:
    external_records.MyVariantInfo_hg38 = ["chr13:g.32332712C>G"]
    external_records.gnomAD_4           = ["13-32332712-C-G"]
    communityStandardTitle              = "NM_000059.4(BRCA2):c.1234C>G"
A caller who read `start` as a genomic position was off by one, silently, with
nothing anywhere in the output or the description saying so.

(2) Unidentifiable reference frame. Upstream
  curl 'https://reg.genome.network/allele?hgvs=NM_000059.3%3Ac.1234C%3EG'
returns a fourth genomicAlleles entry with NO referenceGenome and NO chromosome:
    {"coordinates":[{"allele":"G","end":22233,"referenceAllele":"C",
                     "start":22232}],
     "hgvs":["NG_012772.3:g.22233C>G","LRG_293:g.22233C>G"],
     "referenceSequence":"http://reg.genome.network/refseq/RS002532"}
`referenceSequence` was the only field identifying which sequence 22232/22233
counts against, and the tool discarded it -- so that row surfaced as
`chromosome: null, reference_genome: null` plus two numbers in no stated frame.

The fix is strictly additive: `reference_sequence` and `coordinate_system` are
added to every genomic row, `reference_sequence` to every transcript row. These
tests pin all three properties against mocked HTTP, no network.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.clingen_allele_tool import COORDINATE_SYSTEM, ClinGenAlleleTool

pytestmark = pytest.mark.unit

# Verbatim shape of the upstream reply for NM_000059.3:c.1234C>G (trimmed to the
# fields the tool reads). Note the fourth genomic row: no referenceGenome, no
# chromosome, referenceSequence only.
UPSTREAM_RESPONSE = {
    "@id": "http://reg.genome.network/allele/CA387762202",
    "communityStandardTitle": ["NM_000059.4(BRCA2):c.1234C>G (p.Pro412Ala)"],
    "externalRecords": {
        "MyVariantInfo_hg38": [{"id": "chr13:g.32332712C>G"}],
        "gnomAD_4": [{"id": "13-32332712-C-G"}],
    },
    "genomicAlleles": [
        {
            "chromosome": "13",
            "coordinates": [
                {
                    "allele": "G",
                    "end": 32332712,
                    "referenceAllele": "C",
                    "start": 32332711,
                }
            ],
            "hgvs": ["NC_000013.11:g.32332712C>G"],
            "referenceGenome": "GRCh38",
            "referenceSequence": "http://reg.genome.network/refseq/RS000061",
        },
        {
            "chromosome": "13",
            "coordinates": [
                {
                    "allele": "G",
                    "end": 32906849,
                    "referenceAllele": "C",
                    "start": 32906848,
                }
            ],
            "hgvs": ["NC_000013.10:g.32906849C>G"],
            "referenceGenome": "GRCh37",
            "referenceSequence": "http://reg.genome.network/refseq/RS000037",
        },
        {
            "chromosome": "13",
            "coordinates": [
                {
                    "allele": "G",
                    "end": 31804849,
                    "referenceAllele": "C",
                    "start": 31804848,
                }
            ],
            "hgvs": ["NC_000013.9:g.31804849C>G"],
            "referenceGenome": "NCBI36",
            "referenceSequence": "http://reg.genome.network/refseq/RS000013",
        },
        {
            # RefSeqGene/LRG row: no assembly, no chromosome upstream.
            "coordinates": [
                {"allele": "G", "end": 22233, "referenceAllele": "C", "start": 22232}
            ],
            "hgvs": ["NG_012772.3:g.22233C>G", "LRG_293:g.22233C>G"],
            "referenceSequence": "http://reg.genome.network/refseq/RS002532",
        },
    ],
    "transcriptAlleles": [
        {
            "coordinates": [
                {"allele": "G", "end": 1433, "referenceAllele": "C", "start": 1432}
            ],
            "geneSymbol": "BRCA2",
            "hgvs": ["ENST00000470094.2:c.1234C>G"],
            "proteinEffect": {"hgvs": "ENSP00000434898.2:p.Pro412Ala"},
            "referenceSequence": "http://reg.genome.network/refseq/RS914116",
        }
    ],
}

# The 1-based positions the same record advertises through its own
# cross-references, keyed by assembly. start+1 must reproduce each of them.
ONE_BASED_FROM_CROSS_REFERENCES = {
    "GRCh38": 32332712,  # MyVariantInfo_hg38 / gnomAD_4
    "GRCh37": 32906849,  # MyVariantInfo_hg19
    "NCBI36": 31804849,  # NC_000013.9:g.31804849C>G
}


def _tool(operation="lookup_hgvs"):
    return ClinGenAlleleTool(
        {"name": "ClinGenAllele_test", "fields": {"operation": operation}}
    )


def _resp(payload, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.text = str(payload)
    r.json = MagicMock(return_value=payload)
    return r


def _genomic(operation="lookup_hgvs", args=None):
    tool = _tool(operation)
    with patch.object(tool.session, "get", return_value=_resp(UPSTREAM_RESPONSE)):
        result = tool.run(args or {"hgvs": "NM_000059.3:c.1234C>G"})
    assert result["status"] == "success"
    return result["data"]


def test_every_genomic_row_states_its_coordinate_system():
    """The convention must ride along with the numbers, not live only in docs."""
    genomic = _genomic()["genomic_alleles"]
    assert len(genomic) == 4

    for row in genomic:
        assert row["coordinate_system"] == COORDINATE_SYSTEM
        # Machine-readable enough to branch on, and unambiguous to a human.
        assert "0-based" in row["coordinate_system"]
        assert "start+1" in row["coordinate_system"]


def test_start_plus_one_reproduces_the_positions_the_record_cross_references():
    """This is the off-by-one the label exists to prevent."""
    genomic = _genomic()["genomic_alleles"]
    by_assembly = {row["reference_genome"]: row for row in genomic}

    for assembly, one_based in ONE_BASED_FROM_CROSS_REFERENCES.items():
        row = by_assembly[assembly]
        assert row["start"] + 1 == one_based, assembly
        # start stays interbase -- the fix documents it, it does not renumber it.
        assert row["start"] == one_based - 1, assembly


def test_reference_sequence_is_surfaced_on_every_genomic_row():
    genomic = _genomic()["genomic_alleles"]
    assert [row["reference_sequence"] for row in genomic] == [
        "http://reg.genome.network/refseq/RS000061",
        "http://reg.genome.network/refseq/RS000037",
        "http://reg.genome.network/refseq/RS000013",
        "http://reg.genome.network/refseq/RS002532",
    ]


def test_the_assembly_less_row_is_still_identifiable_via_reference_sequence():
    """The row with no chromosome and no assembly used to be uninterpretable."""
    genomic = _genomic()["genomic_alleles"]
    row = next(r for r in genomic if r["start"] == 22232)

    assert row["chromosome"] is None
    assert row["reference_genome"] is None
    # ...but the frame is no longer a mystery.
    assert row["reference_sequence"] == "http://reg.genome.network/refseq/RS002532"
    assert row["coordinate_system"] == COORDINATE_SYSTEM


def test_reference_sequence_is_absent_safe():
    """Upstream may omit referenceSequence; that must be None, not a KeyError."""
    payload = {
        "@id": "http://reg.genome.network/allele/CA1",
        "genomicAlleles": [
            {
                "chromosome": "1",
                "referenceGenome": "GRCh38",
                "coordinates": [
                    {"start": 100, "end": 101, "allele": "T", "referenceAllele": "A"}
                ],
            }
        ],
        "transcriptAlleles": [{"geneSymbol": "X", "hgvs": ["NM_1.1:c.1A>T"]}],
    }
    tool = _tool("lookup_hgvs")
    with patch.object(tool.session, "get", return_value=_resp(payload)):
        result = tool.run({"hgvs": "NC_000001.11:g.101A>T"})

    assert result["status"] == "success"
    row = result["data"]["genomic_alleles"][0]
    assert row["reference_sequence"] is None
    assert row["coordinate_system"] == COORDINATE_SYSTEM
    assert result["data"]["transcript_alleles"][0]["reference_sequence"] is None


def test_transcript_rows_carry_their_reference_sequence():
    transcripts = _genomic()["transcript_alleles"]
    assert transcripts[0]["reference_sequence"] == (
        "http://reg.genome.network/refseq/RS914116"
    )


def test_get_allele_gets_the_same_treatment_via_format_allele():
    """Both operations share _format_allele(), so neither path can drift."""
    data = _genomic("get_allele", {"ca_id": "CA387762202"})
    genomic = data["genomic_alleles"]

    assert all(row["coordinate_system"] == COORDINATE_SYSTEM for row in genomic)
    assert all(row["reference_sequence"] for row in genomic)


def test_the_change_is_purely_additive():
    """No pre-existing field or value may have moved."""
    genomic = _genomic()["genomic_alleles"]
    row = genomic[0]

    assert {
        "chromosome": row["chromosome"],
        "start": row["start"],
        "end": row["end"],
        "allele": row["allele"],
        "reference_allele": row["reference_allele"],
        "reference_genome": row["reference_genome"],
    } == {
        "chromosome": "13",
        "start": 32332711,
        "end": 32332712,
        "allele": "G",
        "reference_allele": "C",
        "reference_genome": "GRCh38",
    }
