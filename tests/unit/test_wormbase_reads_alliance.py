"""WormBase's own API is unreachable; Alliance carries the same records.

rest.wormbase.org answers 403 with cf-mitigated: challenge to every client,
and downloads.wormbase.org does too, so there is no bulk route. The Alliance
of Genome Resources redistributes the curated records and WormBase is one of
its member databases -- a gene fetched there carries dataProvider
{"abbreviation": "WB", "fullName": "WormBase"} and its interactions carry
interactionSource "wormbase". That attribution is what makes this the same
data rather than a nearby answer, which is the distinction that ruled out
STRING for STITCH in #711.

This module already called Alliance to turn a symbol into a WBGene ID, since
WormBase's own search was unreachable too. The data follows now.

Routes verified live against WB:WBGene00000912 (daf-16) on 2026-10-03, and
recorded below as fixtures. The two POST endpoints answer 405 to GET, which is
how they were found, and reject {"geneIDs": [...]} -- they want a bare list.
"""

import json
from pathlib import Path

import pytest

import tooluniverse.wormbase_tool as wormbase

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"

GENE = {
    "gene": {
        "primaryExternalId": "WB:WBGene00000912",
        "geneSymbol": {"displayText": "daf-16", "formatText": "daf-16"},
        "geneSystematicName": {"displayText": "R13H8.1"},
        "geneFullName": {"displayText": "abnormal DAuer Formation 16"},
        "taxon": {"species": {"fullName": "Caenorhabditis elegans"}},
        "geneType": {"curie": "SO:0001217", "name": "protein_coding_gene"},
        "relatedNotes": [{"freeText": "daf-16 encodes a FOXO transcription factor."}],
        "dataProvider": {"abbreviation": "WB", "fullName": "WormBase"},
    }
}
PHENOTYPES = {
    "total": 28,
    "results": [
        {
            "phenotypeStatement": "autophagy variant",
            "relation": {"name": "is_implicated_in"},
            "subject": {"geneSymbol": {"displayText": "daf-16"}},
            "references": [{"curie": "AGRKB:101000000624359"}],
        }
    ],
}
ORTHOLOGS = {
    "total": 23,
    "results": [
        {
            "geneToGeneOrthologyGenerated": {
                "objectGene": {
                    "geneSymbol": {"displayText": "foxo"},
                    "primaryExternalId": "FB:FBgn0038197",
                    "taxon": {"name": "Drosophila melanogaster"},
                }
            }
        }
    ],
}
PARALOGS = {"total": 1, "results": [
    {"geneToGeneParalogy": {"objectGene": {
        "geneSymbol": {"displayText": "daf-16b"},
        "primaryExternalId": "WB:WBGene00000913"}}}
]}
MOLECULAR = {
    "total": 267,
    "results": [
        {
            "geneMolecularInteraction": {
                "geneAssociationSubject": {
                    "primaryExternalId": "WB:WBGene00000912",
                    "geneSymbol": {"displayText": "daf-16"},
                },
                "geneGeneAssociationObject": {
                    "primaryExternalId": "WB:WBGene00020142",
                    "geneSymbol": {"displayText": "ftt-2"},
                },
                "interactionType": {"curie": "MI:0914", "name": "association"},
                "interactionSource": {"curie": "MI:0487", "name": "wormbase"},
            }
        }
    ],
}
GENETIC = {"total": 379, "results": [
    {"geneGeneticInteraction": {
        "geneAssociationSubject": {"primaryExternalId": "WB:WBGene00000912",
                                   "geneSymbol": {"displayText": "daf-16"}},
        "geneGeneAssociationObject": {"primaryExternalId": "WB:WBGene00000898",
                                      "geneSymbol": {"displayText": "daf-2"}},
        "interactionType": {"name": "suppression"},
        "interactionSource": {"name": "wormbase"}}}
]}
DISEASES = {
    "categories": [
        {"id": "DOID:0050117", "label": "Infection"},
        {"id": "DOID:0080015", "label": "physical disorder"},
    ],
    "subjects": [],
}
EXPRESSION = {
    "total": 111,
    "results": [
        {
            "termIds": ["UBERON:0001016", "UBERON:0001062"],
            "geneExpressionAnnotation": {
                "whereExpressedStatement": "AIYL",
                "whenExpressedStageName": "Nematoda Life Stage",
                "expressionAssayUsed": {"name": "in situ reporter"},
                "expressionAnnotationSubject": {
                    "geneSymbol": {"displayText": "daf-16"}
                },
            },
        }
    ],
}

ROUTES = {
    ("GET", "/gene/WB:WBGene00000912"): GENE,
    ("GET", "/gene/WB:WBGene00000912/phenotypes"): PHENOTYPES,
    ("GET", "/gene/WB:WBGene00000912/orthologs"): ORTHOLOGS,
    ("GET", "/gene/WB:WBGene00000912/paralogs"): PARALOGS,
    ("GET", "/gene/WB:WBGene00000912/molecular-interactions"): MOLECULAR,
    ("GET", "/gene/WB:WBGene00000912/genetic-interactions"): GENETIC,
    ("POST", "/gene/WB:WBGene00000912/disease-ribbon-summary"): DISEASES,
    ("POST", "/expression"): EXPRESSION,
}


class _Resp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


@pytest.fixture
def alliance(monkeypatch):
    seen = []

    def fake_request(session, method, url, **kwargs):
        path = url.split("/api", 1)[1].split("?")[0]
        key = (method, path)
        seen.append((method, path, kwargs.get("json")))
        assert key in ROUTES, f"unexpected call: {key}"
        return _Resp(ROUTES[key])

    monkeypatch.setattr(wormbase, "request_with_retry", fake_request)
    return seen


def _tool(name):
    config = {
        t["name"]: t
        for t in json.loads((DATA / "wormbase_tools.json").read_text("utf-8"))
    }[name]
    return wormbase.WormBaseTool(config)


def test_nothing_still_calls_rest_wormbase_org():
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "wormbase_tool.py"
    ).read_text("utf-8")
    body = source.split('"""', 2)[2]

    assert "rest.wormbase.org" not in body, (
        "a call left on the challenged host fails for every client"
    )
    assert "alliancegenome.org" in source


def test_the_curie_prefix_is_added_for_alliance():
    """WormBase's REST 500'd on a WB: prefix; Alliance requires it."""
    assert wormbase._alliance_curie("WBGene00000912") == "WB:WBGene00000912"
    assert wormbase._alliance_curie("WB:WBGene00000912") == "WB:WBGene00000912"
    # A symbol is left alone; _resolve_wbgene_id handles that first.
    assert wormbase._alliance_curie("unc-86") == "unc-86"


def test_gene_overview_maps_every_declared_field(alliance):
    result = _tool("WormBase_get_gene").run({"gene_id": "WBGene00000912"})

    data = result["data"]
    assert result["status"] == "success"
    assert data["wormbase_id"] == "WBGene00000912"
    assert data["gene_name"] == "daf-16"
    assert data["sequence_name"] == "R13H8.1"
    assert data["species"] == "Caenorhabditis elegans"
    assert "FOXO" in data["description"]
    assert data["gene_type"] == "protein_coding_gene"
    # No Alliance equivalent, and the response says so rather than guessing.
    assert data["status"] == ""
    assert "Live/Dead" in result["metadata"]["coverage_note"]


def test_phenotypes_keep_their_shape_and_say_what_is_missing(alliance):
    result = _tool("WormBase_get_phenotypes").run({"gene_id": "WBGene00000912"})

    data = result["data"]
    assert data["phenotype_count"] == 28
    assert data["phenotypes"][0]["phenotype_name"] == "autophagy variant"
    assert data["phenotypes"][0]["evidence_type"] == "is_implicated_in"
    assert data["phenotypes_not_observed"] == []
    assert "not observed" in result["metadata"]["coverage_note"]


def test_expression_uses_the_declared_term_object_shape(alliance):
    """The schema declares {term_id, term_name}; Alliance gives strings."""
    result = _tool("WormBase_get_expression").run({"gene_id": "WBGene00000912"})

    data = result["data"]
    assert data["expressed_in"] == [
        {"term_id": "UBERON:0001016", "term_name": "AIYL"}
    ]
    # A stage has no term id in the row, so it is null rather than invented.
    assert data["expressed_during"] == [
        {"term_id": None, "term_name": "Nematoda Life Stage"}
    ]
    assert data["expression_assays"] == ["in situ reporter"]
    assert data["gene_name"] == "daf-16"


def test_orthologs_and_paralogs_come_from_two_endpoints(alliance):
    result = _tool("WormBase_get_orthologs").run({"gene_id": "WBGene00000912"})

    data = result["data"]
    assert data["cross_species_ortholog_count"] == 23
    ortholog = data["cross_species_orthologs"][0]
    # Field names follow the declared schema, not Alliance's own spelling.
    assert ortholog["ortholog_id"] == "FB:FBgn0038197"
    assert ortholog["ortholog_label"] == "foxo"
    assert ortholog["species"] == "Drosophila melanogaster"
    assert data["paralogs"][0]["ortholog_label"] == "daf-16b"
    assert data["nematode_orthologs"] == []
    assert "six model organisms" in result["metadata"]["coverage_note"]

    paths = [path for _method, path, _body in alliance]
    assert "/gene/WB:WBGene00000912/orthologs" in paths
    assert "/gene/WB:WBGene00000912/paralogs" in paths


def test_interactions_merge_molecular_and_genetic(alliance):
    result = _tool("WormBase_get_interactions").run({"gene_id": "WBGene00000912"})

    data = result["data"]
    assert data["total_physical_interactions"] == 267
    assert data["total_genetic_interactions"] == 379
    assert data["total_interactions"] == 267 + 379
    physical = data["physical_interactions"][0]
    assert physical["interactor_1"] == "daf-16"
    assert physical["interactor_2_id"] == "WBGene00020142"
    assert physical["interaction_type"] == "association"
    # The source is WormBase's own, which is the point of using Alliance.
    assert physical["citation"] == "wormbase"


def test_diseases_come_from_the_ribbon_as_a_post(alliance):
    result = _tool("WormBase_get_human_diseases").run({"gene_id": "WBGene00000912"})

    data = result["data"]
    assert data["disease_count"] == 2
    assert data["diseases"][0] == {
        "disease_id": "DOID:0050117",
        "disease_name": "Infection",
        "evidence": [],
        "model_type": "",
    }
    assert data["human_gene_ids"] == []

    posts = [(m, p, b) for m, p, b in alliance if m == "POST"]
    assert posts == [
        ("POST", "/gene/WB:WBGene00000912/disease-ribbon-summary",
         ["WB:WBGene00000912"])
    ], "the body is a bare list; a dict is rejected upstream"


def test_a_missing_gene_id_is_still_an_error(alliance):
    for name in ("WormBase_get_gene", "WormBase_get_phenotypes"):
        result = _tool(name).run({})
        assert result["status"] == "error"
        assert "gene_id" in result["error"]


def test_every_response_names_alliance_as_the_route(alliance):
    for name in (
        "WormBase_get_gene",
        "WormBase_get_phenotypes",
        "WormBase_get_orthologs",
        "WormBase_get_human_diseases",
    ):
        result = _tool(name).run({"gene_id": "WBGene00000912"})
        assert result["metadata"]["source"] == (
            "WormBase via the Alliance of Genome Resources"
        )
        assert result["metadata"]["query"] == "WBGene00000912"
