"""Regression guard: CPIC_get_alleles discarded the per-ancestry frequencies.

The tool's PostgREST `select` clause listed only
``name,functionalstatus,activityvalue,clinicalfunctionalstatus``, so every row
came back as e.g.::

    {"name": "*2", "functionalstatus": null, "activityvalue": null,
     "clinicalfunctionalstatus": "No function"}

CPIC actually publishes a `frequency` object on the same row -- allele
frequency per biogeographic group -- plus `strength` (its evidence level),
`citations` and `inferredfrequency`. Confirmed live::

    GET /v1/allele?genesymbol=eq.CYP2C19&name=eq.*2
      "strength": "Definitve"
      "frequency": {"European": 0.14685704, "East Asian": 0.28352264,
                    "Oceanian": 0.6095202, "Sub-Saharan African": 0.15684253,
                    "Latino": 0.104187496, "American": 0.121365316,
                    "African American/Afro-Caribbean": 0.18149492,
                    "Near Eastern": 0.11984708, "Central/South Asian": 0.269916}

Coverage measured across whole genes: CYP2C19 has 49 alleles with frequency on
36 and strength on 36; CYP2D6 has 208 alleles with frequency on 183. So the
tool dropped a populated, clinically central field on 74-88% of rows, and
per-ancestry star-allele frequency is the one thing a pharmacogenomics
counselling note needs -- there is no other route to it in this tool.

Two things the fix must not do:

  * collapse a missing frequency to zero. CPIC returns an explicit null (never
    ``{}``) where it publishes nothing, and a published 0.0 is real data: 16 of
    CYP2C19's 49 alleles and 97 of CYP2D6's 208 carry at least one 0.0.
  * relabel CPIC's biogeographic groups. The keys are CPIC's own labels
    ("Sub-Saharan African", "Central/South Asian", ...) and are passed through
    verbatim, never remapped onto gnomAD population codes.

Fully offline: ``requests.get`` is patched.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.cpic_search_pairs_tool import CPICGetAllelesTool

pytestmark = pytest.mark.unit


# Real CPIC rows for CYP2C19, trimmed to the fields under test. *2 is fully
# curated; *10 mixes published zeros with nulls inside one frequency map; *42
# is one of the 13 CYP2C19 alleles CPIC publishes no frequency for at all.
_CYP2C19_ROWS = [
    {
        "name": "*2",
        "functionalstatus": None,
        "activityvalue": None,
        "clinicalfunctionalstatus": "No function",
        "frequency": {
            "Latino": 0.104187496,
            "American": 0.121365316,
            "European": 0.14685704,
            "Oceanian": 0.6095202,
            "East Asian": 0.28352264,
            "Near Eastern": 0.11984708,
            "Central/South Asian": 0.269916,
            "Sub-Saharan African": 0.15684253,
            "African American/Afro-Caribbean": 0.18149492,
        },
        "inferredfrequency": False,
        "strength": "Definitve",
        "citations": ["8195181", "22027650"],
    },
    {
        "name": "*10",
        "functionalstatus": None,
        "activityvalue": None,
        "clinicalfunctionalstatus": "Decreased function",
        "frequency": {
            "Latino": 0.0012398496,
            "American": None,
            "European": 0.0,
            "Oceanian": None,
            "East Asian": 0.00010471204,
            "Near Eastern": 0.0,
            "Central/South Asian": None,
            "Sub-Saharan African": 0.0,
            "African American/Afro-Caribbean": 0.0032672414,
        },
        "inferredfrequency": False,
        "strength": "Limited",
        "citations": ["12464799", "19661214"],
    },
    {
        "name": "*42",
        "functionalstatus": None,
        "activityvalue": None,
        "clinicalfunctionalstatus": None,
        "frequency": None,
        "inferredfrequency": False,
        "strength": None,
        "citations": None,
    },
]

# CPIC's biogeographic-group labels, exactly as the API spells them.
_CPIC_GROUPS = {
    "Latino",
    "American",
    "European",
    "Oceanian",
    "East Asian",
    "Near Eastern",
    "Central/South Asian",
    "Sub-Saharan African",
    "African American/Afro-Caribbean",
}


class _FakeCPIC:
    """Stand-in for CPIC's PostgREST /allele endpoint.

    Honours the `select` clause the way PostgREST does -- a column the tool
    does not ask for is genuinely absent from the row -- so a mock cannot
    paper over a `select` that still drops `frequency`.
    """

    def __init__(self, rows, total=49):
        self.rows = rows
        self.total = total
        self.selects = []

    def __call__(self, url, params=None, headers=None, **kwargs):
        params = params or {}
        selected = (params.get("select") or "").split(",")
        self.selects.append(selected)
        rows = [{k: v for k, v in row.items() if k in selected} for row in self.rows]

        response = MagicMock()
        response.json.return_value = rows
        response.raise_for_status.return_value = None
        response.headers = {"Content-Range": f"0-{len(rows) - 1}/{self.total}"}
        response.url = "https://api.cpicpgx.org/v1/allele"
        return response


def _run(arguments=None, rows=None):
    fake = _FakeCPIC(rows if rows is not None else _CYP2C19_ROWS)
    with patch("tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake):
        result = CPICGetAllelesTool({"name": "CPIC_get_alleles"}).run(
            arguments or {"genesymbol": "CYP2C19"}
        )
    return result, fake


def _allele(name):
    """Return one star allele row from a default CYP2C19 run."""
    return next(r for r in _run()[0]["data"] if r["name"] == name)


class TestFrequencyIsRequestedAndReturned:
    def test_select_clause_asks_for_frequency(self):
        _, fake = _run()
        assert "frequency" in fake.selects[0]

    def test_rows_carry_the_frequency_object(self):
        star2 = _allele("*2")
        assert star2["frequency"]["East Asian"] == 0.28352264
        assert star2["frequency"]["Sub-Saharan African"] == 0.15684253

    def test_strength_accompanies_the_frequency(self):
        """CPIC's evidence level, so a frequency is never read ungraded."""
        assert _allele("*2")["strength"] == "Definitve"

    def test_citations_and_inferredfrequency_are_carried(self):
        star2 = _allele("*2")
        assert star2["citations"] == ["8195181", "22027650"]
        # False here means CPIC measured the frequency rather than inferring it.
        assert star2["inferredfrequency"] is False

    def test_narrative_findings_is_not_requested(self):
        """`findings` restates `strength` at ~78 KB across CYP2D6's 208 rows;
        `citations` grounds the same claim by PMID for ~9.6 KB."""
        _, fake = _run()
        assert "findings" not in fake.selects[0]


class TestAbsentFrequencyIsNotZero:
    def test_unpublished_frequency_stays_null(self):
        """13 of CYP2C19's 49 alleles have no published frequency."""
        star42 = _allele("*42")
        assert star42["frequency"] is None
        assert star42["strength"] is None
        assert star42["citations"] is None

    def test_a_missing_frequency_is_never_an_empty_or_zeroed_map(self):
        """Absence must stay absence: not {}, and not a map of zeros."""
        result, _ = _run()
        for row in result["data"]:
            frequency = row["frequency"]
            assert frequency is None or isinstance(frequency, dict)
            assert frequency != {}
            if frequency:
                assert any(v is not None for v in frequency.values())

    def test_a_published_zero_survives_as_zero(self):
        """A group CPIC measured at 0.0 is real data and must not be dropped
        or turned into a null -- 16 of CYP2C19's 49 alleles carry one."""
        star10 = _allele("*10")
        assert star10["frequency"]["European"] == 0.0
        assert star10["frequency"]["Sub-Saharan African"] == 0.0

    def test_null_and_zero_coexist_within_one_frequency_map(self):
        """Per-group absence is distinguishable from per-group zero."""
        star10 = _allele("*10")
        assert star10["frequency"]["American"] is None
        assert star10["frequency"]["Near Eastern"] == 0.0


class TestBiogeographicGroupLabelsArePassedThroughVerbatim:
    def test_keys_are_cpics_own_labels_and_not_gnomad_population_codes(self):
        """Relabelling an ancestry group is exactly the class of defect this
        change exists to avoid, so pin the label set exactly and spell out the
        gnomAD codes that must never replace it."""
        frequency = _allele("*2")["frequency"]

        assert set(frequency) == _CPIC_GROUPS
        for gnomad_code in ("nfe", "eas", "afr", "amr", "sas", "asj", "fin", "mid"):
            assert gnomad_code not in frequency


class TestExistingBehaviourIsUnchanged:
    """Strictly additive: nothing already returned may move or disappear."""

    def test_previously_returned_keys_keep_their_values(self):
        star2 = _allele("*2")
        assert star2["clinicalfunctionalstatus"] == "No function"
        # activityvalue is null for CYP2C19 but real, gene-dependent data
        # elsewhere (non-null on 183 of CYP2D6's 208 alleles) -- untouched.
        assert star2["activityvalue"] is None
        assert star2["functionalstatus"] is None

    def test_select_still_asks_for_the_original_four_columns(self):
        """Order is PostgREST's business, not ours -- assert membership only."""
        _, fake = _run()
        assert set(fake.selects[0]) >= {
            "name",
            "functionalstatus",
            "activityvalue",
            "clinicalfunctionalstatus",
        }

    def test_paging_and_total_count_are_unaffected(self):
        result, _ = _run({"genesymbol": "CYP2C19", "limit": 3})
        assert result["status"] == "success"
        assert result["count"] == 3
        assert result["total_count"] == 49
        assert result["offset"] == 0
        assert "Re-run with offset=3" in result["note"]

    def test_missing_genesymbol_still_errors_the_same_way(self):
        tool = CPICGetAllelesTool({"name": "CPIC_get_alleles"})
        result = tool.run({})
        assert result["status"] == "error"
        assert "genesymbol is required" in result["error"]


class TestConfigDocumentsTheNewFields:
    def test_return_schema_and_description_cover_frequency(self):
        import json
        from pathlib import Path

        config_path = (
            Path(__file__).parent.parent.parent
            / "src/tooluniverse/data/cpic_tools.json"
        )
        config = next(
            c
            for c in json.loads(config_path.read_text())
            if c["name"] == "CPIC_get_alleles"
        )

        props = config["return_schema"]["oneOf"][0]["items"]["properties"]
        for field in ("frequency", "strength", "citations", "inferredfrequency"):
            assert field in props, field
        assert "null" in props["frequency"]["type"]
        assert "object" in props["frequency"]["type"]
        # Per-group values are nullable numbers, not a flat number.
        assert props["frequency"]["additionalProperties"]["type"] == ["null", "number"]

        description = config["description"]
        assert "frequency" in description
        # The description must warn that frequency is absent for some alleles.
        assert "null" in description
        assert "Sub-Saharan African" in description
