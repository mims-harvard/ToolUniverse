"""Regression guard for Fix-R30 in hgnc_tool.py: HGNC_fetch_gene_by_symbol
returned a *confident empty success* for any gene symbol that HGNC has since
retired.

The tool only ever called ``fetch/symbol/<X>``, which matches the *current*
approved symbol and nothing else. Genes get renamed constantly and the retired
string survives on the current record, so this silently blanked a large class
of real queries:

    curl -H 'Accept: application/json' \\
         https://rest.genenames.org/fetch/symbol/CYP2E
    -> {"response":{"numFound":0,"docs":[]}}

    curl -H 'Accept: application/json' \\
         https://rest.genenames.org/search/prev_symbol/CYP2E
    -> {"response":{"numFound":1,"docs":[
         {"hgnc_id":"HGNC:2631","symbol":"CYP2E1","score":4.48195}]}}

CYP2E1 was renamed from CYP2E on 2002-09-13 and its HGNC record carries
``"prev_symbol":["CYP2E"]``; likewise NQO1 carries
``"prev_symbol":["NMOR1","DIA4"]``, so ``{"symbol":"DIA4"}`` was equally dead.
The sibling HGNC_search_genes resolved both fine, which is exactly what masked
the dead path.

The fix uses ``fetch/prev_symbol/<X>`` then ``fetch/alias_symbol/<X>``. Both
were verified live: ``fetch`` is an exact, case-insensitive match on a stored
field and returns the *complete* record -- the doc from
``fetch/prev_symbol/CYP2E`` is byte-identical to the one from
``fetch/symbol/CYP2E1`` -- so the caller gets the same rich payload a direct
hit produces, not a thin search stub.

Ambiguity is real and must not be papered over: ``fetch/alias_symbol/p65``
returns numFound 3 (RELA HGNC:9955, SYT1 HGNC:11509, GORASP1 HGNC:16769, all
of which genuinely list P65 as an alias), so a multi-candidate resolution names
every candidate instead of picking the first.

No network: every test mocks ``tooluniverse.hgnc_tool.requests.get``.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.hgnc_tool import HGNCTool

pytestmark = pytest.mark.unit


def _symbol_tool():
    return HGNCTool(
        {
            "name": "HGNC_fetch_gene_by_symbol",
            "fields": {"endpoint": "fetch", "search_field": "symbol"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.return_value = payload
    return r


def _hgnc(num_found, docs):
    return {
        "responseHeader": {"status": 0, "QTime": 1},
        "response": {"numFound": num_found, "start": 0, "docs": docs},
    }


_EMPTY = _hgnc(0, [])

# Trimmed but structurally faithful copies of the real records.
_CYP2E1 = {
    "hgnc_id": "HGNC:2631",
    "symbol": "CYP2E1",
    "name": "cytochrome P450 family 2 subfamily E member 1",
    "status": "Approved",
    "locus_type": "gene with protein product",
    "location": "10q26.3",
    "prev_symbol": ["CYP2E"],
    "date_symbol_changed": "2002-09-13T00:00:00Z",
    "entrez_id": "1571",
    "ensembl_gene_id": "ENSG00000130649",
    "uniprot_ids": ["P05181"],
    "refseq_accession": ["NM_000773"],
    "omim_id": ["124040"],
}

_NQO1 = {
    "hgnc_id": "HGNC:2874",
    "symbol": "NQO1",
    "name": "NAD(P)H quinone dehydrogenase 1",
    "status": "Approved",
    "locus_type": "gene with protein product",
    "location": "16q22.1",
    "prev_symbol": ["NMOR1", "DIA4"],
    "entrez_id": "1728",
    "uniprot_ids": ["P15559"],
}

_TP53 = {
    "hgnc_id": "HGNC:11998",
    "symbol": "TP53",
    "name": "tumor protein p53",
    "status": "Approved",
    "locus_type": "gene with protein product",
    "location": "17p13.1",
    "entrez_id": "7157",
    "uniprot_ids": ["P04637"],
}

_P65_CANDIDATES = [
    {"hgnc_id": "HGNC:9955", "symbol": "RELA", "alias_symbol": ["p65"]},
    {"hgnc_id": "HGNC:11509", "symbol": "SYT1", "alias_symbol": ["P65"]},
    {
        "hgnc_id": "HGNC:16769",
        "symbol": "GORASP1",
        "alias_symbol": ["GRASP65", "P65", "FLJ23443"],
    },
]

_DISCLOSURE_KEYS = (
    "resolved_from",
    "resolved_symbol",
    "resolution_relation",
    "symbol_resolution_note",
)


def _router(routes):
    """Map a URL suffix -> HGNC payload; anything unmatched is an empty result."""
    calls = []

    def _get(url, **_kwargs):
        calls.append(url)
        for suffix, payload in routes.items():
            if url.endswith(suffix):
                return _resp(payload)
        return _resp(_EMPTY)

    return _get, calls


class TestPreviousSymbolResolves:
    """(a) A previous symbol resolves, and the substitution is disclosed."""

    def test_cyp2e_resolves_to_cyp2e1_with_full_record(self):
        get, calls = _router(
            {
                "/fetch/symbol/CYP2E": _EMPTY,
                "/fetch/prev_symbol/CYP2E": _hgnc(1, [_CYP2E1]),
            }
        )
        with patch("tooluniverse.hgnc_tool.requests.get", side_effect=get):
            result = _symbol_tool().run({"symbol": "CYP2E"})

        assert result["status"] == "success"
        # The full record, not a {hgnc_id, symbol, score} search stub.
        assert result["data"]["symbol"] == "CYP2E1"
        assert result["data"]["hgnc_id"] == "HGNC:2631"
        assert result["data"]["uniprot_ids"] == ["P05181"]
        assert result["data"]["location"] == "10q26.3"

        meta = result["metadata"]
        assert meta["num_found"] == 1
        assert meta["query_value"] == "CYP2E"  # what the caller actually asked for
        assert meta["resolved_from"] == "CYP2E"
        assert meta["resolved_symbol"] == "CYP2E1"
        assert meta["resolution_relation"] == "prev_symbol"
        note = meta["symbol_resolution_note"]
        assert "CYP2E" in note and "CYP2E1" in note
        assert "previous symbol" in note

        assert "/fetch/prev_symbol/CYP2E" in "".join(calls)

    def test_dia4_resolves_to_nqo1(self):
        get, _ = _router(
            {
                "/fetch/symbol/DIA4": _EMPTY,
                "/fetch/prev_symbol/DIA4": _hgnc(1, [_NQO1]),
            }
        )
        with patch("tooluniverse.hgnc_tool.requests.get", side_effect=get):
            result = _symbol_tool().run({"symbol": "DIA4"})

        assert result["status"] == "success"
        assert result["data"]["symbol"] == "NQO1"
        assert result["metadata"]["resolved_from"] == "DIA4"
        assert result["metadata"]["resolved_symbol"] == "NQO1"
        assert result["metadata"]["resolution_relation"] == "prev_symbol"

    def test_alias_symbol_is_used_when_prev_symbol_misses(self):
        gene = {"hgnc_id": "HGNC:12495", "symbol": "UBE2V2", "alias_symbol": ["MMS2"]}
        get, calls = _router(
            {
                "/fetch/alias_symbol/MMS2": _hgnc(1, [gene]),
            }
        )
        with patch("tooluniverse.hgnc_tool.requests.get", side_effect=get):
            result = _symbol_tool().run({"symbol": "MMS2"})

        assert result["status"] == "success"
        assert result["data"]["symbol"] == "UBE2V2"
        assert result["metadata"]["resolution_relation"] == "alias_symbol"
        assert "alias symbol" in result["metadata"]["symbol_resolution_note"]
        # prev_symbol is tried first: an official rename beats an informal alias.
        joined = " ".join(calls)
        assert joined.index("prev_symbol") < joined.index("alias_symbol")


class TestDirectHitUnchanged:
    """(b) A direct current-symbol hit is untouched and carries no disclosure."""

    def test_direct_hit_returns_record_without_disclosure_keys(self):
        get, calls = _router({"/fetch/symbol/TP53": _hgnc(1, [_TP53])})
        with patch("tooluniverse.hgnc_tool.requests.get", side_effect=get):
            result = _symbol_tool().run({"symbol": "TP53"})

        assert result["status"] == "success"
        assert result["data"] == _TP53
        meta = result["metadata"]
        assert meta["num_found"] == 1
        assert meta["query_value"] == "TP53"
        for key in _DISCLOSURE_KEYS:
            assert key not in meta, f"{key} must be absent on a direct hit"
        assert "no_results_note" not in meta
        # Exactly one request: no speculative fallback traffic on a hit.
        assert len(calls) == 1

    def test_current_symbol_wins_over_being_someone_elses_prev_symbol(self):
        """A string can be gene A's current symbol and gene B's prev symbol.

        The current-symbol hit must always win and the fallback must never run.
        """
        other = {"hgnc_id": "HGNC:99999", "symbol": "OTHER", "prev_symbol": ["TP53"]}
        get, calls = _router(
            {
                "/fetch/symbol/TP53": _hgnc(1, [_TP53]),
                "/fetch/prev_symbol/TP53": _hgnc(1, [other]),
            }
        )
        with patch("tooluniverse.hgnc_tool.requests.get", side_effect=get):
            result = _symbol_tool().run({"symbol": "TP53"})

        assert result["data"]["symbol"] == "TP53"
        assert "resolved_from" not in result["metadata"]
        assert not any("prev_symbol" in c for c in calls)


class TestUnknownSymbolIsNotABareEmptySuccess:
    """(c) A genuinely unknown symbol must not come back as a bare {}."""

    def test_unknown_symbol_carries_an_explanatory_note(self):
        get, calls = _router({})  # every endpoint returns numFound 0
        with patch("tooluniverse.hgnc_tool.requests.get", side_effect=get):
            result = _symbol_tool().run({"symbol": "NOTAGENEXYZ"})

        meta = result["metadata"]
        assert meta["num_found"] == 0
        note = meta["no_results_note"]
        assert "NOTAGENEXYZ" in note
        assert "HGNC_search_genes" in note
        # It must be explicit that all three relations were checked.
        assert "previous symbol" in note and "alias" in note
        for key in _DISCLOSURE_KEYS:
            assert key not in meta
        # symbol, prev_symbol, alias_symbol were all attempted.
        assert len(calls) == 3


class TestAmbiguousResolutionNamesCandidates:
    """(d) A multi-candidate resolution must not silently pick one."""

    def test_p65_lists_every_candidate_and_returns_no_single_gene(self):
        get, _ = _router({"/fetch/alias_symbol/p65": _hgnc(3, _P65_CANDIDATES)})
        with patch("tooluniverse.hgnc_tool.requests.get", side_effect=get):
            result = _symbol_tool().run({"symbol": "p65"})

        assert result["status"] == "error"
        # Crucially, no arbitrary gene record is handed back as the answer.
        assert "data" not in result

        message = result["error"]
        for symbol in ("RELA", "SYT1", "GORASP1"):
            assert symbol in message
        assert "HGNC:9955" in message

        meta = result["metadata"]
        assert meta["resolution_relation"] == "alias_symbol"
        assert meta["resolved_from"] == "p65"
        assert "resolved_symbol" not in meta
        assert [c["symbol"] for c in meta["ambiguous_candidates"]] == [
            "RELA",
            "SYT1",
            "GORASP1",
        ]


class TestSiblingsAlsoAvoidBareEmptySuccess:
    """The same shape existed on the other four HGNC tools in hgnc_tools.json."""

    def _tool(self, endpoint, search_field):
        return HGNCTool(
            {
                "fields": {"endpoint": endpoint, "search_field": search_field},
                "parameter": {"type": "object", "properties": {}},
            }
        )

    def test_fetch_by_id_miss_has_a_note(self):
        get, _ = _router({})
        with patch("tooluniverse.hgnc_tool.requests.get", side_effect=get):
            result = self._tool("fetch", "hgnc_id").run({"hgnc_id": "HGNC:99999999"})
        assert result["data"] == {}
        assert "no_results_note" in result["metadata"]
        # No prev/alias fallback is meaningful for an ID.
        assert "resolved_from" not in result["metadata"]

    def test_gene_family_miss_has_a_note(self):
        get, _ = _router({})
        with patch("tooluniverse.hgnc_tool.requests.get", side_effect=get):
            result = self._tool("fetch", "gene_group_id").run(
                {"gene_group_id": "99999999"}
            )
        assert result["data"] == []
        assert "no_results_note" in result["metadata"]

    def test_search_genes_miss_has_a_note(self):
        get, _ = _router({})
        with patch("tooluniverse.hgnc_tool.requests.get", side_effect=get):
            result = self._tool("search", None).run({"query": "zzzznotagene"})
        assert result["data"] == []
        assert "no_results_note" in result["metadata"]

    def test_search_by_location_miss_has_a_note(self):
        get, _ = _router({})
        with patch("tooluniverse.hgnc_tool.requests.get", side_effect=get):
            result = self._tool("search", "location").run({"location": "99z99.9"})
        assert result["data"] == []
        assert "location" in result["metadata"]["no_results_note"]

    def test_search_hit_carries_no_note(self):
        get, _ = _router(
            {"/search/BRCA1": _hgnc(1, [{"hgnc_id": "HGNC:1100", "symbol": "BRCA1"}])}
        )
        with patch("tooluniverse.hgnc_tool.requests.get", side_effect=get):
            result = self._tool("search", None).run({"query": "BRCA1"})
        assert result["data"][0]["symbol"] == "BRCA1"
        assert "no_results_note" not in result["metadata"]
