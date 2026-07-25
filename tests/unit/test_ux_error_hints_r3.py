"""
Regression tests for the round-3 user-experience fixes.

Each test pins one behaviour a real user hits when they make an ordinary
mistake (a typo, a missing key) or simply import the coding API:

* ``BaseTool.validate_parameters`` names the misspelled parameter, not just
  the missing one (Feature-R3-01).
* ``tu run <typo>`` offers "Did you mean?" the same way ``tu info`` does
  (Fix-R3-02).
* A not-found / API-key-gated tool reports actionable next steps instead of
  network-troubleshooting advice (Fix-R3-03).
* A key-gated tool is not reported as a spelling problem (Fix-R3-05).
* Generated coding-API wrappers never emit a ``SyntaxWarning`` because a
  docstring was truncated in the middle of an escaped backslash (Fix-R3-04).
* Union-typed parameters (``["integer", "null"]``) are type-coerced, so the
  documented ``tu run <tool> limit=10`` shorthand works (Fix-R3-06).
* ClinVar accepts standard coding HGVS such as ``c.1905+1G>A`` (Fix-R3-07).
* UniProt search reports the true match total, not the page size (Fix-R3-08).
* The PDB taxonomy tool returns the source organism's scientific name rather
  than its kingdom (Fix-R3-09).
"""

import argparse
import json
import pathlib
import warnings

import pytest

from tooluniverse.base_tool import BaseTool


def _tool(properties, required):
    """Build a bare BaseTool with the given parameter schema."""
    return BaseTool(
        {
            "name": "DemoTool",
            "parameter": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
    )


ACCESSION_TOOL_PROPS = {
    "accession": {"type": "string"},
    "gene_name": {"type": "string"},
    "limit": {"type": "integer"},
}


class TestMisspelledParameterHint:
    """Feature-R3-01: widen the 'did you mean?' hint beyond case variants."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "wrong_key",
        [
            "Accession",  # case variant - the only form matched before
            "ACCESSION",
            "acession",  # ordinary typo (dropped letter)
            "accesion",
            "accession_id",  # near-miss with an extra suffix
        ],
    )
    def test_misspelled_required_param_is_named(self, wrong_key):
        """The error names both the key the user passed and the correct one."""
        tool = _tool(ACCESSION_TOOL_PROPS, ["accession"])
        err = tool.validate_parameters({wrong_key: "P12345"})
        assert err is not None
        msg = str(err)
        assert "did you mean" in msg.lower()
        assert wrong_key in msg
        assert "accession" in msg

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "wrong_key", ["geneName", "GeneName", "gene-name", "genename"]
    )
    def test_separator_and_camelcase_drift_is_matched(self, wrong_key):
        """camelCase / hyphen drift resolves to the snake_case schema name."""
        tool = _tool(ACCESSION_TOOL_PROPS, ["gene_name"])
        err = tool.validate_parameters({wrong_key: "TP53"})
        assert err is not None
        msg = str(err)
        assert "did you mean" in msg.lower()
        assert wrong_key in msg
        assert "gene_name" in msg

    @pytest.mark.unit
    def test_unrelated_key_is_reported_as_unrecognized(self):
        """With no near-match, the error still names the ignored parameter."""
        tool = _tool(ACCESSION_TOOL_PROPS, ["accession"])
        err = tool.validate_parameters({"totally_unrelated": "x"})
        assert err is not None
        msg = str(err)
        assert "unrecognized parameter" in msg.lower()
        assert "totally_unrelated" in msg
        # It is not a spelling of 'accession', so do not claim it is.
        assert "did you mean" not in msg.lower()

    @pytest.mark.unit
    def test_valid_sibling_param_is_not_flagged_as_a_typo(self):
        """A legitimate other parameter must never be reported as misspelled."""
        tool = _tool(ACCESSION_TOOL_PROPS, ["accession"])
        err = tool.validate_parameters({"gene_name": "TP53"})
        assert err is not None
        msg = str(err)
        assert "did you mean" not in msg.lower()
        assert "unrecognized parameter" not in msg.lower()

    @pytest.mark.unit
    def test_no_hint_noise_when_nothing_was_passed(self):
        """Empty arguments produce the plain required-property error."""
        tool = _tool(ACCESSION_TOOL_PROPS, ["accession"])
        msg = str(tool.validate_parameters({}))
        assert "did you mean" not in msg.lower()
        assert "unrecognized parameter" not in msg.lower()

    @pytest.mark.unit
    def test_valid_arguments_still_pass(self):
        """The added hint logic must not reject valid input."""
        tool = _tool(ACCESSION_TOOL_PROPS, ["accession"])
        assert tool.validate_parameters({"accession": "P12345", "limit": 5}) is None


class TestRunCommandSuggestsToolNames:
    """Fix-R3-02: `tu run <typo>` gains the "Did you mean?" hint."""

    @staticmethod
    def _not_found(name):
        """Fresh payload per call - cmd_run injects into the dict in place."""
        return {
            "status": "error",
            "error": f"Tool '{name}' not found even after loading tools",
            "error_details": {
                "type": "ToolUnavailableError",
                "retriable": False,
                "next_steps": ["Check tool name spelling"],
            },
        }

    class _FakeTU:
        def __init__(self, result, names):
            self._result = result
            self.all_tool_dict = {n: {"name": n} for n in names}

        def run_one_function(self, _payload):
            return self._result

    def _invoke(self, monkeypatch, capsys, tool_name, result, names):
        import tooluniverse.cli as cli

        monkeypatch.setattr(cli, "_get_tu", lambda: self._FakeTU(result, names))
        ns = argparse.Namespace(
            tool_name=tool_name, arguments=["{}"], json=False, raw=False, output=None
        )
        with pytest.raises(SystemExit):
            cli.cmd_run(ns)
        cap = capsys.readouterr()
        return cap.out + cap.err

    @pytest.mark.unit
    def test_typo_gets_did_you_mean(self, monkeypatch, capsys):
        text = self._invoke(
            monkeypatch,
            capsys,
            "UniProt_get_entry_by_accesion",
            self._not_found("UniProt_get_entry_by_accesion"),
            [
                "UniProt_get_entry_by_accession",
                "UniProt_get_sequence_by_accession",
                "ChEMBL_search",
            ],
        )
        assert "Did you mean" in text
        assert "UniProt_get_entry_by_accession" in text

    @pytest.mark.unit
    def test_nonsense_name_gets_no_spurious_suggestion(self, monkeypatch, capsys):
        text = self._invoke(
            monkeypatch,
            capsys,
            "ZZZQQQ_not_a_tool",
            self._not_found("ZZZQQQ_not_a_tool"),
            ["UniProt_get_entry_by_accession", "ChEMBL_search"],
        )
        assert "Did you mean" not in text

    @pytest.mark.unit
    def test_api_key_gated_tool_keeps_key_guidance(self, monkeypatch, capsys):
        result = {
            "status": "error",
            "error": (
                "Tool 'DisGeNET_get_vda' requires API key(s) not set: "
                "DISGENET_API_KEY. Set them as environment variables and retry."
            ),
            "error_details": {"type": "ToolUnavailableError", "retriable": False},
        }
        text = self._invoke(
            monkeypatch, capsys, "DisGeNET_get_vda", result, ["DisGeNET_get_gda"]
        )
        # The name is already correct; near-miss siblings would be noise.
        assert "Did you mean" not in text
        assert "DISGENET_API_KEY" in text


class TestUnavailableToolNextSteps:
    """Fix-R3-03: actionable next steps instead of network-troubleshooting."""

    def _tu(self, excluded=None):
        from tooluniverse import ToolUniverse

        tu = ToolUniverse.__new__(ToolUniverse)  # skip __init__ / tool loading
        tu.all_tool_dict = {"RealTool": {"name": "RealTool"}}
        tu._excluded_api_key_tools = excluded or {}
        tu._auto_load_tools_if_empty = lambda *a, **k: True
        return tu

    @pytest.mark.unit
    def test_unknown_tool_name_gets_discovery_steps(self):
        err = self._tu()._validate_parameters("NoSuchTool", {})
        assert err is not None
        steps = " ".join(err.next_steps)
        assert "spelling" in steps.lower()
        assert "network" not in steps.lower()
        assert "service status" not in steps.lower()

    @pytest.mark.unit
    def test_gated_tool_gets_api_key_steps(self):
        tu = self._tu(excluded={"GatedTool": ["MY_KEY"]})
        err = tu._validate_parameters("GatedTool", {})
        assert err is not None
        steps = " ".join(err.next_steps)
        assert "MY_KEY" in steps
        assert "network" not in steps.lower()

    @pytest.mark.unit
    def test_gated_tool_lookup_warning_names_the_key(self, caplog):
        """Fix-R3-05: a key-gated tool is not reported as a spelling problem."""
        tu = self._tu(excluded={"GatedTool": ["MY_KEY"]})
        with caplog.at_level("WARNING"):
            assert tu.tool_specification("GatedTool") is None
        text = caplog.text
        assert "MY_KEY" in text
        assert "not found" not in text

    @pytest.mark.unit
    def test_genuinely_missing_tool_still_says_not_found(self, caplog):
        tu = self._tu()
        with caplog.at_level("WARNING"):
            assert tu.tool_specification("ZZZQQQ_not_a_tool") is None
        assert "not found" in caplog.text


class TestGeneratedWrapperDocstrings:
    """Fix-R3-04: docstring truncation must not create an invalid escape."""

    @pytest.mark.unit
    def test_truncation_at_a_backslash_is_still_valid_python(self, tmp_path):
        from tooluniverse.generate_tools import generate_tool_file

        # Position the truncation boundary (77 chars) directly after a
        # backslash, which is what a FASTA "\n" example in a long parameter
        # description does in practice.
        description = "A" * 76 + "\\n" + "B" * 30
        assert description[76] == "\\"
        config = {
            "name": "DemoBackslashTool",
            "description": "Demo tool with a backslash in a parameter description",
            "parameter": {
                "type": "object",
                "properties": {
                    "sequences": {"type": "string", "description": description}
                },
                "required": ["sequences"],
            },
        }
        path = generate_tool_file("DemoBackslashTool", config, tmp_path)
        source = pathlib.Path(path).read_text()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            compile(source, str(path), "exec")
        assert not [w for w in caught if issubclass(w.category, SyntaxWarning)], (
            f"generated wrapper emits SyntaxWarning: {[str(w.message) for w in caught]}"
        )

    @pytest.mark.unit
    def test_shipped_wrappers_compile_without_warnings(self):
        """Every checked-in coding-API wrapper imports cleanly."""
        import tooluniverse.tools as tools_pkg

        root = pathlib.Path(tools_pkg.__file__).parent
        offenders = []
        for py in sorted(root.glob("*.py")):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                try:
                    compile(py.read_text(), str(py), "exec")
                except SyntaxError as exc:  # pragma: no cover - would be a hard break
                    offenders.append(f"{py.name}: SyntaxError {exc}")
                    continue
            offenders += [
                f"{py.name}: {w.message}"
                for w in caught
                if issubclass(w.category, SyntaxWarning)
            ]
        assert not offenders, f"wrappers with syntax warnings: {offenders}"


class TestUnionTypeCoercion:
    """Fix-R3-06: ["integer", "null"] is the repo's optional-parameter idiom."""

    def _tu(self):
        from tooluniverse import ToolUniverse

        return ToolUniverse.__new__(ToolUniverse)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "value,schema,expected",
        [
            ("10", {"type": "integer"}, 10),  # unchanged behaviour
            ("10", {"type": ["integer", "null"]}, 10),
            ("10", {"type": ["null", "integer"]}, 10),  # order must not matter
            ("1.5", {"type": ["number", "null"]}, 1.5),
            ("true", {"type": ["boolean", "null"]}, True),
            ("false", {"type": ["boolean", "null"]}, False),
        ],
    )
    def test_union_types_are_coerced(self, value, schema, expected):
        got = self._tu()._coerce_value_to_type(value, schema)
        assert got == expected and isinstance(got, type(expected))

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "value,schema",
        [
            ("10", {"type": ["string", "null"]}),  # string acceptable -> keep as-is
            ("9606", {"type": "string"}),  # Feature-27A-02 must not regress
            ("abc", {"type": ["integer", "null"]}),  # uncoercible
            ("1.5", {"type": ["integer", "null"]}),  # float is not an integer
        ],
    )
    def test_values_that_must_stay_strings(self, value, schema):
        assert self._tu()._coerce_value_to_type(value, schema) == value
        assert isinstance(self._tu()._coerce_value_to_type(value, schema), str)


class TestClinVarHgvsQuery:
    """Fix-R3-07: coding HGVS (c.) must not silently return zero results."""

    def _search_tool(self):
        from tooluniverse.clinvar_tool import ClinVarSearchVariants

        return ClinVarSearchVariants(
            {"name": "ClinVar_search_variants", "fields": {"endpoint": "/esearch.fcgi"}}
        )

    def _term_for(self, monkeypatch, arguments):
        """Run the tool with the network stubbed; return the variant-search term.

        The tool also issues a gene-symbol validation request, so collect every
        term and pick the one that actually queries the variant index.
        """
        tool = self._search_tool()
        terms = []

        def fake_request(endpoint, params=None, max_retries=3):
            terms.append((params or {}).get("term", ""))
            return {
                "status": "success",
                "data": {"esearchresult": {"count": "0", "idlist": []}},
            }

        monkeypatch.setattr(tool, "_make_request", fake_request)
        tool.run(arguments)
        variant_terms = [t for t in terms if "[gene]" in t]
        assert variant_terms, f"no variant-search term issued; saw {terms}"
        return variant_terms[0]

    @pytest.mark.unit
    def test_coding_hgvs_keeps_the_c_prefix_quoted(self, monkeypatch):
        """'c.1905+1G>A' only matches with the prefix intact AND quoted."""
        term = self._term_for(
            monkeypatch, {"gene": "DPYD", "variant_name": "c.1905+1G>A"}
        )
        assert '"c.1905+1G>A"[Variant name]' in term

    @pytest.mark.unit
    def test_protein_hgvs_still_offers_the_stripped_spelling(self, monkeypatch):
        """'p.Glu342Lys' only matches with the prefix stripped - keep both."""
        term = self._term_for(
            monkeypatch, {"gene": "SERPINA1", "variant_name": "p.Glu342Lys"}
        )
        assert '"p.Glu342Lys"[Variant name]' in term
        assert '"Glu342Lys"[Variant name]' in term
        assert " OR " in term

    @pytest.mark.unit
    def test_prefixless_name_is_not_duplicated(self, monkeypatch):
        term = self._term_for(
            monkeypatch, {"gene": "SERPINA1", "variant_name": "Glu342Lys"}
        )
        assert term.count("[Variant name]") == 1
        assert " OR " not in term

    @pytest.mark.unit
    def test_rsid_is_still_routed_to_free_text(self, monkeypatch):
        term = self._term_for(
            monkeypatch, {"gene": "CYP2C19", "variant_name": "rs4244285"}
        )
        assert "rs4244285" in term
        assert "[Variant name]" not in term


class TestUniProtTotalResults:
    """Fix-R3-08: total_results must be the match count, not the page size."""

    class _Resp:
        def __init__(self, headers):
            self.headers = headers

    def _tool(self):
        from tooluniverse.uniprot_tool import UniProtRESTTool

        return UniProtRESTTool(
            {"name": "UniProt_search", "fields": {"endpoint": "/uniprotkb/search"}}
        )

    @pytest.mark.unit
    def test_header_total_wins_over_page_size(self):
        tool = self._tool()
        resp = self._Resp({"x-total-results": "395446"})
        assert tool._total_results(resp, {}, [1, 2]) == 395446

    @pytest.mark.unit
    def test_falls_back_to_body_then_page_size(self):
        tool = self._tool()
        assert tool._total_results(self._Resp({}), {"resultsFound": 62}, [1]) == 62
        assert tool._total_results(self._Resp({}), {}, [1, 2, 3]) == 3

    @pytest.mark.unit
    def test_non_numeric_header_falls_back(self):
        tool = self._tool()
        resp = self._Resp({"x-total-results": "not-a-number"})
        assert tool._total_results(resp, {}, [1, 2]) == 2


class TestPdbTaxonomyReturnsScientificName:
    """Fix-R3-09: the tool promises a scientific name; ask RCSB for one."""

    @pytest.mark.unit
    def test_source_organism_scientific_name_is_requested(self):
        import tooluniverse

        data_dir = pathlib.Path(tooluniverse.__file__).parent / "data"
        configs = json.loads((data_dir / "rcsb_pdb_tools.json").read_text())
        tool = next(c for c in configs if c["name"] == "get_taxonomy_by_pdb_id")
        fields = tool["fields"]["return_fields"]
        assert (
            "polymer_entities.rcsb_entity_source_organism.ncbi_scientific_name"
            in fields
        ), "must request the source organism's own name, not only its parent taxon"
        # The expression host is a different organism and must stay
        # distinguishable from the source.
        assert any("rcsb_entity_host_organism" in f for f in fields)
