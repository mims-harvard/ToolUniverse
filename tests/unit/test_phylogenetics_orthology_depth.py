"""Phylogenetics / orthology depth tools: parse + error-path coverage (mocked HTTP).

Covers five new tools that close confirmed capability gaps in the
phylogenetics-orthology cluster. Each tool reuses an existing registered
tool class (no new @register_tool), dispatching on the JSON ``fields.endpoint``:

* ``OMA_resolve_xref`` (OMATool, endpoint ``xref``) — resolve a gene symbol /
  UniProt name / cross-reference to OMA entries via ``/xref/?search=``.
* ``OMA_get_genome_pair_orthologs`` (OMATool, endpoint ``genome_pairs``) —
  all pairwise orthologs between two whole genomes via ``/pairs/{g1}/{g2}/``.
* ``OMA_get_protein_go`` (OMATool, endpoint ``protein_ontology``) — per-protein
  GO annotations via ``/protein/{id}/ontology/``.
* ``EnsemblCompara_get_cafe_tree`` (EnsemblComparaTool, endpoint ``cafe_tree``)
  — CAFE gene-family gain/loss tree via ``/cafe/genetree/...``.
* ``OrthoDB_get_group_fasta`` (OrthoDBTool, endpoint ``fasta``) — member
  protein FASTA for an orthogroup via ``/fasta?id=...``.

All network calls are mocked; these tests never touch the live APIs.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


def _json_response(payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def _text_response(text, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# OMA_resolve_xref  (OMATool / endpoint "xref")
# ---------------------------------------------------------------------------

_OMA_XREF_FAKE = [
    {
        "xref": "MED4_HUMAN",
        "source": "UniProtKB/SwissProt",
        "seq_match": "exact",
        "entry_nr": 24423700,
        "omaid": "HUMAN17018",
        "genome": {
            "code": "HUMAN",
            "taxon_id": 9606,
            "species": "Homo sapiens",
        },
    },
    {
        "xref": "TMED4_HUMAN",
        "source": "UniProtKB/SwissProt",
        "seq_match": "exact",
        "entry_nr": 24495488,
        "omaid": "HUMAN88806",
        "genome": {"code": "HUMAN", "taxon_id": 9606, "species": "Homo sapiens"},
    },
]


def _oma_tool(endpoint):
    from tooluniverse.oma_tool import OMATool

    return OMATool({"fields": {"endpoint": endpoint}, "timeout": 30})


class TestOMAResolveXref(unittest.TestCase):
    def test_parses_xref_matches(self):
        """Cross-reference matches are parsed into oma_id/entry_nr/genome fields."""
        tool = _oma_tool("xref")
        with patch("tooluniverse.oma_tool.requests.get") as get:
            get.return_value = _json_response(_OMA_XREF_FAKE)
            result = tool.run({"search": "MED4_HUMAN"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 2)
        first = result["data"][0]
        self.assertEqual(first["oma_id"], "HUMAN17018")
        self.assertEqual(first["entry_nr"], 24423700)
        self.assertEqual(first["species_code"], "HUMAN")
        self.assertEqual(first["taxon_id"], 9606)
        self.assertEqual(result["metadata"]["total_matches"], 2)

    def test_respects_limit(self):
        """The limit argument caps the number of returned records."""
        tool = _oma_tool("xref")
        with patch("tooluniverse.oma_tool.requests.get") as get:
            get.return_value = _json_response(_OMA_XREF_FAKE)
            result = tool.run({"search": "MED4_HUMAN", "limit": 1})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)

    def test_missing_search_is_error(self):
        """Missing 'search' returns a status=error envelope, no raise."""
        tool = _oma_tool("xref")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("search", result["error"])

    def test_http_error_does_not_raise(self):
        """Upstream HTTP error is caught and returned as status=error."""
        import requests

        tool = _oma_tool("xref")
        with patch("tooluniverse.oma_tool.requests.get") as get:
            err = requests.exceptions.HTTPError()
            err.response = MagicMock(status_code=502)
            get.return_value.raise_for_status.side_effect = err
            result = tool.run({"search": "BRCA2"})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# OMA_get_genome_pair_orthologs  (OMATool / endpoint "genome_pairs")
# ---------------------------------------------------------------------------

_OMA_PAIRS_FAKE = [
    {
        "entry_1": {
            "entry_nr": 24408118,
            "omaid": "HUMAN01436",
            "canonicalid": "NK2R_HUMAN",
            "sequence_length": 398,
            "species": {"code": "HUMAN", "taxon_id": 9606, "species": "Homo sapiens"},
            "oma_group": 1117505,
            "oma_hog_id": "HOG:F0800563.1b",
            "chromosome": "10",
        },
        "entry_2": {
            "entry_nr": 24806063,
            "omaid": "MOUSE00001",
            "canonicalid": "NK2R_MOUSE",
            "sequence_length": 384,
            "species": {"code": "MOUSE", "taxon_id": 10090, "species": "Mus musculus"},
            "oma_group": 1117505,
            "oma_hog_id": "HOG:F0800563.1b",
            "chromosome": "10",
        },
        "rel_type": "1:1",
        "distance": 14.0382,
        "score": 3660.8,
        "oma_group": 1117505,
    }
]


class TestOMAGenomePairOrthologs(unittest.TestCase):
    def test_parses_pair(self):
        """A genome-vs-genome ortholog pair is parsed into entry_1/entry_2."""
        tool = _oma_tool("genome_pairs")
        with patch("tooluniverse.oma_tool.requests.get") as get:
            get.return_value = _json_response(_OMA_PAIRS_FAKE)
            result = tool.run({"genome1": "HUMAN", "genome2": "MOUSE", "per_page": 1})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        pair = result["data"][0]
        self.assertEqual(pair["entry_1"]["oma_id"], "HUMAN01436")
        self.assertEqual(pair["entry_1"]["canonical_id"], "NK2R_HUMAN")
        self.assertEqual(pair["entry_2"]["oma_id"], "MOUSE00001")
        self.assertEqual(pair["entry_2"]["species_code"], "MOUSE")
        self.assertEqual(pair["rel_type"], "1:1")
        self.assertEqual(result["metadata"]["genome1"], "HUMAN")

    def test_missing_genome_is_error(self):
        """Missing genome2 returns a status=error envelope, no raise."""
        tool = _oma_tool("genome_pairs")
        result = tool.run({"genome1": "HUMAN"})
        self.assertEqual(result["status"], "error")
        self.assertIn("genome2", result["error"])

    def test_connection_error_does_not_raise(self):
        """Connection error is caught and returned as status=error."""
        import requests

        tool = _oma_tool("genome_pairs")
        with patch("tooluniverse.oma_tool.requests.get") as get:
            get.side_effect = requests.exceptions.ConnectionError()
            result = tool.run({"genome1": "HUMAN", "genome2": "MOUSE"})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# OMA_get_protein_go  (OMATool / endpoint "protein_ontology")
# ---------------------------------------------------------------------------

_OMA_GO_FAKE = [
    {
        "id": "HUMAN17018",
        "GO_term": "GO:0060261",
        "name": "positive regulation of transcription initiation by RNA polymerase II",
        "aspect": "biological_process",
        "ic": 8.271075269496553,
        "evidence": "IDA",
        "reference": "PMID:12218053",
    },
    {
        "id": "HUMAN17018",
        "GO_term": "GO:0005634",
        "name": "nucleus",
        "aspect": "cellular_component",
        "ic": 2.5,
        "evidence": "IEA",
        "reference": None,
    },
]


class TestOMAProteinGO(unittest.TestCase):
    def test_parses_go_annotations(self):
        """Per-protein GO annotations parsed with aspect/evidence/reference."""
        tool = _oma_tool("protein_ontology")
        with patch("tooluniverse.oma_tool.requests.get") as get:
            get.return_value = _json_response(_OMA_GO_FAKE)
            result = tool.run({"protein_id": "HUMAN17018"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 2)
        first = result["data"][0]
        self.assertEqual(first["go_term"], "GO:0060261")
        self.assertEqual(first["aspect"], "biological_process")
        self.assertEqual(first["evidence"], "IDA")
        self.assertEqual(first["reference"], "PMID:12218053")
        self.assertAlmostEqual(first["information_content"], 8.27107, places=3)

    def test_aspect_filter(self):
        """The aspect filter restricts annotations to the requested GO aspect."""
        tool = _oma_tool("protein_ontology")
        with patch("tooluniverse.oma_tool.requests.get") as get:
            get.return_value = _json_response(_OMA_GO_FAKE)
            result = tool.run(
                {"protein_id": "HUMAN17018", "aspect": "cellular_component"}
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["go_term"], "GO:0005634")

    def test_missing_protein_id_is_error(self):
        """Missing protein_id returns a status=error envelope, no raise."""
        tool = _oma_tool("protein_ontology")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("protein_id", result["error"])


# ---------------------------------------------------------------------------
# EnsemblCompara_get_cafe_tree  (EnsemblComparaTool / endpoint "cafe_tree")
# ---------------------------------------------------------------------------

_CAFE_FAKE = {
    "type": "cafe tree",
    "rooted": 1,
    "pvalue_avg": 0,
    "tree": {
        "id": 4018200342,
        "n_members": 0,
        "p_value_lim": 0.01,
        "lambda": 5.08187e-08,
        "name": "Bilateria",
        "tax": {"id": 33213, "scientific_name": "Bilateria"},
        "children": [
            {
                "id": 4018200344,
                "n_members": 1,
                "p_value_lim": 0.01,
                "pvalue": 0.5076,
                "lambda": 5.08187e-08,
                "name": "Gnathostomata",
                "tax": {"id": 7776, "scientific_name": "Gnathostomata"},
                "children": [],
            }
        ],
    },
}


def _compara_tool():
    from tooluniverse.ensembl_compara_tool import EnsemblComparaTool

    return EnsemblComparaTool({"fields": {"endpoint": "cafe_tree"}, "timeout": 30})


class TestEnsemblComparaCafeTree(unittest.TestCase):
    def test_parses_cafe_tree_by_id(self):
        """CAFE tree by gene_tree_id parses lambda and per-node n_members/pvalue."""
        tool = _compara_tool()
        with patch("tooluniverse.ensembl_compara_tool.requests.get") as get:
            get.return_value = _json_response(_CAFE_FAKE)
            result = tool.run({"gene_tree_id": "ENSGT00390000003602"})
        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["type"], "cafe tree")
        self.assertEqual(data["rooted"], 1)
        self.assertAlmostEqual(data["lambda"], 5.08187e-08)
        # root + one child collected
        self.assertEqual(data["total_nodes"], 2)
        names = {n["name"] for n in data["nodes"]}
        self.assertIn("Gnathostomata", names)
        child = next(n for n in data["nodes"] if n["name"] == "Gnathostomata")
        self.assertEqual(child["n_members"], 1)
        self.assertAlmostEqual(child["pvalue"], 0.5076)

    def test_parses_cafe_tree_by_symbol(self):
        """Gene-symbol lookup builds the member/symbol CAFE URL."""
        tool = _compara_tool()
        with patch("tooluniverse.ensembl_compara_tool.requests.get") as get:
            get.return_value = _json_response(_CAFE_FAKE)
            result = tool.run({"gene": "BRCA2", "species": "homo_sapiens"})
        self.assertEqual(result["status"], "success")
        # Ensure the symbol path builds the member/symbol URL.
        called_url = get.call_args[0][0]
        self.assertIn("/cafe/genetree/member/symbol/homo_sapiens/BRCA2", called_url)

    def test_missing_args_is_error(self):
        """Neither gene_tree_id nor gene returns a status=error envelope."""
        tool = _compara_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("gene_tree_id", result["error"])

    def test_http_error_does_not_raise(self):
        """Upstream HTTP error is caught and returned as status=error."""
        import requests

        tool = _compara_tool()
        with patch("tooluniverse.ensembl_compara_tool.requests.get") as get:
            err = requests.exceptions.HTTPError()
            err.response = MagicMock(status_code=400)
            get.return_value.raise_for_status.side_effect = err
            result = tool.run({"gene_tree_id": "BAD"})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# OrthoDB_get_group_fasta  (OrthoDBTool / endpoint "fasta")
# ---------------------------------------------------------------------------

_ORTHODB_FASTA_FAKE = (
    '>9606_0:003066 {"pub_og_id":"794361at2759",'
    '"og_name":"Breast cancer 2 susceptibility protein","level_taxid":2759,'
    '"organism_taxid":"9606_0","organism_name":"Homo sapiens",'
    '"pub_gene_id":"BRCA2","description":"Breast cancer type 2 helical domain"}\n'
    "MPIGSKERPTFF\n"
    "EIFKTRCNK\n"
    '>9606_1:00357e {"pub_og_id":"794361at2759",'
    '"og_name":"Breast cancer 2 susceptibility protein","level_taxid":2759,'
    '"organism_taxid":"9606_1","organism_name":"Homo sapiens",'
    '"pub_gene_id":"675","description":"Breast cancer type 2 susceptibility protein"}\n'
    "MPIGSKERPT\n"
)


def _orthodb_tool():
    from tooluniverse.orthodb_tool import OrthoDBTool

    return OrthoDBTool({"fields": {"endpoint": "fasta"}, "timeout": 30})


class TestOrthoDBGroupFasta(unittest.TestCase):
    def test_parses_fasta_records(self):
        """FASTA records parse JSON header metadata and concatenate sequence lines."""
        tool = _orthodb_tool()
        with patch("tooluniverse.orthodb_tool.requests.get") as get:
            get.return_value = _text_response(_ORTHODB_FASTA_FAKE)
            result = tool.run({"group_id": "794361at2759", "species": "9606"})
        self.assertEqual(result["status"], "success")
        seqs = result["data"]["sequences"]
        self.assertEqual(len(seqs), 2)
        first = seqs[0]
        self.assertEqual(first["id"], "9606_0:003066")
        self.assertEqual(first["pub_gene_id"], "BRCA2")
        self.assertEqual(first["og_name"], "Breast cancer 2 susceptibility protein")
        self.assertEqual(first["organism_name"], "Homo sapiens")
        self.assertEqual(first["pub_og_id"], "794361at2759")
        # Multi-line sequence is concatenated.
        self.assertEqual(first["sequence"], "MPIGSKERPTFFEIFKTRCNK")
        self.assertEqual(first["length"], len("MPIGSKERPTFFEIFKTRCNK"))
        self.assertEqual(result["data"]["total_sequences"], 2)
        self.assertIn(">9606_0:003066", result["data"]["fasta"])

    def test_respects_limit(self):
        """The limit argument caps the number of returned records."""
        tool = _orthodb_tool()
        with patch("tooluniverse.orthodb_tool.requests.get") as get:
            get.return_value = _text_response(_ORTHODB_FASTA_FAKE)
            result = tool.run({"group_id": "794361at2759", "limit": 1})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]["sequences"]), 1)

    def test_missing_group_id_is_error(self):
        """Missing group_id returns a status=error envelope, no raise."""
        tool = _orthodb_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("group_id", result["error"])

    def test_empty_body_is_error(self):
        """An empty FASTA body returns a status=error envelope."""
        tool = _orthodb_tool()
        with patch("tooluniverse.orthodb_tool.requests.get") as get:
            get.return_value = _text_response("")
            result = tool.run({"group_id": "nonexistent"})
        self.assertEqual(result["status"], "error")

    def test_timeout_does_not_raise(self):
        """Request timeout is caught and returned as status=error."""
        import requests

        tool = _orthodb_tool()
        with patch("tooluniverse.orthodb_tool.requests.get") as get:
            get.side_effect = requests.exceptions.Timeout()
            result = tool.run({"group_id": "794361at2759"})
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
