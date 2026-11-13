"""A coordinate string must not be answered with an empty success.

arXiv 2609.26836 reports ClinGen_search_gene_validity not accepting genomic
coordinates. Measured live 2026-11-12:

    ClinGen_search_gene_validity {"gene": "BRCA1"}
      -> 2 Definitive curations

    ClinGen_search_gene_validity {"gene": "chr17:43044295-43125483"}
      -> {"status": "success", "data": [], "total": 0}

The same locus. ClinGen's curation files are CSVs keyed by HGNC symbol with
no coordinate, transcript or ontology index, so any other identifier filters
to nothing -- and an empty success is exactly what a curated gene with no
classifications returns. The capability gap is small; the silence is the
defect, and it is the one that makes an agent conclude the region is
uncurated.

The refusal must not swing the other way: measured 2026-11-13 against every
token in the live gene-validity download (6,161 candidates), none is refused.
A bare "T", "X" or "M" is deliberately accepted -- T was HGNC's symbol for
brachyury before TBXT -- so only `chr`-prefixed chromosome names are caught.
"""

import pytest

from tooluniverse.clingen_tool import _not_a_gene_symbol

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "value,looks_like",
    [
        ("chr17:43044295-43125483", "a genomic coordinate or range"),
        ("17:43044295-43125483", "a genomic coordinate or range"),
        ("chr17", "a chromosome name"),
        ("ENSG00000012048", "an Ensembl identifier"),
        ("ENST00000357654.9", "an Ensembl identifier"),
        ("NM_007294.4", "a RefSeq accession"),
        ("NM_007294.4:c.68_69del", "a RefSeq accession"),
        ("NC_000017.11:g.43044295A>G", "a RefSeq accession"),
        ("MONDO:0007254", "a disease or phenotype identifier"),
        ("1100", "a bare number"),
    ],
)
def test_an_identifier_the_file_is_not_keyed_by_is_refused(value, looks_like):
    refusal = _not_a_gene_symbol(value)
    assert refusal is not None, value
    assert refusal["status"] == "error"
    assert refusal["error_details"]["submitted_looks_like"] == looks_like
    assert refusal["error_details"]["parameter_accepts"] == "HGNC gene symbol"
    # The error must name the way out, not only the refusal.
    assert "Ensembl_get_region_features" in refusal["error"]


@pytest.mark.parametrize(
    "symbol",
    [
        "BRCA1",
        "TP53",
        "C11orf65",
        "NKX2-5",
        "HLA-B",
        "MT-ND1",
        "T",
        "X",
        "M",
        "MT1A",
        "H19",
        "A1BG",
        "SLC25A4",
        "KCNQ1OT1",
    ],
)
def test_a_real_gene_symbol_is_never_refused(symbol):
    # Refusing a real symbol would be the same defect pointed the other way.
    assert _not_a_gene_symbol(symbol) is None, symbol


def test_every_gene_keyed_handler_refuses(monkeypatch):
    import json
    from pathlib import Path

    from tooluniverse.clingen_tool import ClinGenTool

    configs = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "src"
            / "tooluniverse"
            / "data"
            / "clingen_tools.json"
        ).read_text()
    )

    def no_network(*args, **kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("the refusal must happen before the download")

    monkeypatch.setattr("tooluniverse.clingen_tool.requests.get", no_network)

    checked = 0
    for config in configs:
        if "gene" not in config.get("parameter", {}).get("properties", {}):
            continue
        result = ClinGenTool(config).run({"gene": "chr17:43044295-43125483"})
        assert result["status"] == "error", config["name"]
        assert "HGNC gene symbol" in result["error"], config["name"]
        checked += 1
    assert checked >= 5, checked


def test_an_unknown_symbol_says_it_is_a_coverage_statement(monkeypatch):
    import json
    from pathlib import Path

    from tooluniverse.clingen_tool import ClinGenTool

    configs = {
        c["name"]: c
        for c in json.loads(
            (
                Path(__file__).resolve().parents[2]
                / "src"
                / "tooluniverse"
                / "data"
                / "clingen_tools.json"
            ).read_text()
        )
    }

    class _Response:
        status_code = 200
        text = (
            "GENE SYMBOL,GENE ID (HGNC),DISEASE LABEL,CLASSIFICATION\n"
            "BRCA1,HGNC:1100,hereditary breast ovarian cancer,Definitive\n"
            "TP53,HGNC:11998,Li-Fraumeni syndrome,Definitive\n"
        )

        def raise_for_status(self):
            return None

    monkeypatch.setattr(
        "tooluniverse.clingen_tool.requests.get", lambda *a, **k: _Response()
    )
    tool = ClinGenTool(configs["ClinGen_search_gene_validity"])
    result = tool.run({"gene": "ZZZNOTAGENE"})
    assert result["status"] == "success"
    assert result["total"] == 0
    # A zero that does not say what it is a zero of is the defect next door.
    assert "curation coverage" in result["note"]
    assert result["curated_genes_in_file"] == 2
