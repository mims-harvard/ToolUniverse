"""Regression guard: gnomAD responses did not say which callset answered.

Two facts made that a silent wrong-answer generator rather than a cosmetic gap.

  (a) The defaults in this family deliberately differ. `gnomad_get_variant`,
      `gnomad_search_variants` and `gnomad_get_region` default to `gnomad_r3`;
      `gnomad_get_variant_populations` and `gnomad_get_constraint` default to
      `gnomad_r4`. Two sibling tools therefore disagree on the same variant by
      design, and nothing in either payload named its dataset.

  (b) gnomAD v3 is a GENOMES-ONLY callset -- it has no exome component at all --
      so under the r3 default `exome` is structurally null for *every* variant,
      indistinguishable from "not observed in exomes". Confirmed live on GJB2
      c.35delG (13-20189546-AC-A), the commonest non-syndromic-deafness carrier
      variant:

        dataset=gnomad_r3 (default)  genome an=151764   exome null
        dataset=gnomad_r4            genome an=151882   exome an=1461600, ac=10423

      A residual-carrier-risk calculation off an=151,764 that reads `exome:
      null` as "not seen in exomes" discards 10,423 allele observations out of
      1,461,600 alleles.

The fix is strictly additive disclosure -- no default was changed. Every
dataset-backed response now echoes `dataset` and `reference_genome`, plus a
`dataset_note` when the null callset is a property of the callset rather than
of the variant.

The dataset-to-assembly table was verified live against the API's own
`variant.reference_genome` field for all fourteen dataset ids, on
13-20189546-AC-A (GRCh38) and 13-20763685-AC-A (GRCh37).

Extended afterwards to the three tools in this family that have no dataset at
all -- `gnomad_get_gene`, `gnomad_get_transcript` and `gnomad_search_genes` --
which returned coordinates in an unnamed frame for the same reason and are
covered by `TestFeatureToolsDiscloseTheirAssembly` below.

Fully offline: `requests.Session.post` is patched.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.gnomad_tool import (
    gnomADGetVariantPopulations,
    gnomADGraphQLQueryTool,
    resolve_dataset_assembly,
)

pytestmark = pytest.mark.unit


def _resp(json_body):
    r = MagicMock()
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    r.status_code = 200
    r.url = "https://gnomad.broadinstitute.org/api"
    return r


class _FakeGnomAD:
    """Serves the real GJB2 c.35delG numbers, keyed on the requested dataset.

    The r3 branch returns `exome: null` exactly as gnomAD does, because v3 has
    no exome component -- a mock that always returned exome data would hide the
    very condition under test.
    """

    _BASE = {
        "variant_id": "13-20189546-AC-A",
        "chrom": "13",
        "pos": 20189546,
        "ref": "AC",
        "alt": "A",
        "rsid": "rs80338939",
    }
    _BY_DATASET = {
        "gnomad_r3": {
            "genome": {"af": 0.006272897393321209, "an": 151764, "ac": 952},
            "exome": None,
        },
        "gnomad_r4": {
            "genome": {"af": 0.006268023860628646, "an": 151882, "ac": 952},
            "exome": {"af": 0.007131226053639847, "an": 1461600, "ac": 10423},
        },
        "gnomad_r2_1": {
            "genome": {"af": 0.0067, "an": 31334, "ac": 210},
            "exome": {"af": 0.0069, "an": 249362, "ac": 1721},
        },
        # ExAC is the mirror image of v3: exomes only, `genome` always null.
        "exac": {
            "genome": None,
            "exome": {"af": 0.0069, "an": 121352, "ac": 837},
        },
    }

    def __init__(self):
        self.datasets_requested = []

    def __call__(self, url, json=None, **kwargs):
        dataset = (json or {}).get("variables", {}).get("dataset")
        self.datasets_requested.append(dataset)
        return _resp({"data": {"variant": {**self._BASE, **self._BY_DATASET[dataset]}}})


_GET_VARIANT_CONFIG = {
    "name": "gnomad_get_variant",
    "fields": {
        "query_schema": "query($variantId: String!, $dataset: DatasetId!) { variant }",
        "variable_map": {"variant_id": "variantId"},
        "default_variables": {"dataset": "gnomad_r3"},
    },
}

_POPULATIONS_CONFIG = {"name": "gnomad_get_variant_populations", "fields": {}}


def _run(tool_cls, config, arguments, responder=None):
    """Run a tool against a patched transport, returning (result, responder)."""
    responder = responder or _FakeGnomAD()
    with patch("requests.Session.post", side_effect=responder):
        return tool_cls(config).run(arguments), responder


def _run_get_variant(arguments):
    return _run(gnomADGraphQLQueryTool, _GET_VARIANT_CONFIG, arguments)


class TestDatasetIsEchoedEvenWhenDefaulted:
    """A caller must never have to guess which callset answered."""

    def test_omitted_dataset_still_reports_the_default_that_was_used(self):
        result, fake = _run_get_variant({"variant_id": "13-20189546-AC-A"})

        assert fake.datasets_requested == ["gnomad_r3"]
        assert result["status"] == "success"
        # The default was applied silently before; now it is stated.
        assert result["data"]["dataset"] == "gnomad_r3"

    def test_explicit_dataset_is_echoed_unchanged(self):
        result, _ = _run_get_variant(
            {"variant_id": "13-20189546-AC-A", "dataset": "gnomad_r4"}
        )
        assert result["data"]["dataset"] == "gnomad_r4"

    def test_default_dataset_is_not_changed_by_this_fix(self):
        """The whole value here is disclosure -- r3 must stay the r3 default."""
        _, fake = _run_get_variant({"variant_id": "13-20189546-AC-A"})
        assert fake.datasets_requested == ["gnomad_r3"]

    def test_the_variant_payload_itself_is_untouched(self):
        """Disclosure is additive: the pre-existing keys keep their values."""
        result, _ = _run_get_variant({"variant_id": "13-20189546-AC-A"})
        assert result["data"]["variant"] == {
            "variant_id": "13-20189546-AC-A",
            "chrom": "13",
            "pos": 20189546,
            "ref": "AC",
            "alt": "A",
            "rsid": "rs80338939",
            "genome": {"af": 0.006272897393321209, "an": 151764, "ac": 952},
            "exome": None,
        }


class TestAssemblyFollowsTheDataset:
    """gnomad_r2_1/exac are GRCh37; gnomad_r3/gnomad_r4 are GRCh38."""

    @pytest.mark.parametrize(
        "dataset,expected",
        [
            ("gnomad_r4", "GRCh38"),
            ("gnomad_r4_non_ukb", "GRCh38"),
            ("gnomad_r3", "GRCh38"),
            ("gnomad_r3_controls_and_biobanks", "GRCh38"),
            ("gnomad_r3_non_cancer", "GRCh38"),
            ("gnomad_r3_non_neuro", "GRCh38"),
            ("gnomad_r3_non_topmed", "GRCh38"),
            ("gnomad_r3_non_v2", "GRCh38"),
            ("gnomad_r2_1", "GRCh37"),
            ("gnomad_r2_1_controls", "GRCh37"),
            ("gnomad_r2_1_non_neuro", "GRCh37"),
            ("gnomad_r2_1_non_cancer", "GRCh37"),
            ("gnomad_r2_1_non_topmed", "GRCh37"),
            ("exac", "GRCh37"),
            # SV callsets follow the same version-to-assembly rule; round 34
            # routes them off `reference_genome`, so this must agree with it.
            ("gnomad_sv_r2_1", "GRCh37"),
            ("gnomad_sv_r2_1_controls", "GRCh37"),
            ("gnomad_sv_r4", "GRCh38"),
        ],
    )
    def test_assembly_mapping(self, dataset, expected):
        assert resolve_dataset_assembly(dataset) == expected

    def test_unknown_dataset_falls_back_to_grch38_not_an_error(self):
        """A dataset id we do not know must not turn a working call into one
        that fails -- gnomAD's current callsets are all GRCh38 but v2.1."""
        assert resolve_dataset_assembly("gnomad_r9_future") == "GRCh38"
        assert resolve_dataset_assembly(None) == "GRCh38"

    def test_assembly_is_reported_on_the_response(self):
        result, _ = _run_get_variant(
            {"variant_id": "13-20189546-AC-A", "dataset": "gnomad_r2_1"}
        )
        assert result["data"]["reference_genome"] == "GRCh37"
        # r2_1 carries both callsets, so no structural-null note applies.
        assert "dataset_note" not in result["data"]

    def test_an_assembly_the_query_actually_sent_beats_the_lookup(self):
        """gnomad_get_region takes its own `reference_genome`. Reporting an
        inference in preference to the value transmitted is exactly what this
        disclosure exists to prevent, so the sent value wins."""
        config = {
            "name": "gnomad_get_region",
            "fields": {
                "query_schema": "query { region }",
                "variable_map": {"reference_genome": "referenceGenome"},
                "default_variables": {
                    "dataset": "gnomad_r3",
                    "referenceGenome": "GRCh38",
                },
            },
        }
        responder = MagicMock(return_value=_resp({"data": {"region": {"chrom": "19"}}}))
        data = _run(
            gnomADGraphQLQueryTool,
            config,
            {"chrom": "19", "start": 1, "stop": 2, "reference_genome": "GRCh37"},
            responder,
        )[0]["data"]

        assert data["reference_genome"] == "GRCh37"
        assert data["dataset"] == "gnomad_r3"

    def test_constraint_tool_shares_this_mapping(self):
        """One table for the whole family, not a second copy."""
        from tooluniverse.gnomad_constraint_tool import GnomADConstraintTool

        assert GnomADConstraintTool._resolve_reference("exac") == "GRCh37"
        assert GnomADConstraintTool._resolve_reference("gnomad_r4") == "GRCh38"
        assert GnomADConstraintTool._resolve_reference(None) == "GRCh38"


class TestNullExomeIsSelfExplaining:
    """`exome: null` under a genomes-only callset must not read as absence."""

    def test_r3_response_says_the_callset_has_no_exomes(self):
        result, _ = _run_get_variant({"variant_id": "13-20189546-AC-A"})
        note = result["data"]["dataset_note"]

        assert "gnomad_r3" in note
        assert "no exome component" in note
        assert "NOT 'not observed'" in note
        # It must name the dataset that does carry exomes, without querying it.
        assert "gnomad_r4" in note

    def test_no_exome_numbers_are_fabricated_for_r3(self):
        """The note explains the null; it never invents a substitute value."""
        result, fake = _run_get_variant({"variant_id": "13-20189546-AC-A"})

        assert result["data"]["variant"]["exome"] is None
        # And no second dataset was auto-queried behind the caller's back.
        assert fake.datasets_requested == ["gnomad_r3"]

    def test_r4_carries_exomes_so_no_note_is_emitted(self):
        """Under a dataset that has exomes, a null exome would be a real
        absence -- the note must not fire and dilute that meaning."""
        result, _ = _run_get_variant(
            {"variant_id": "13-20189546-AC-A", "dataset": "gnomad_r4"}
        )
        assert "dataset_note" not in result["data"]
        assert result["data"]["variant"]["exome"]["ac"] == 10423

    def test_exac_null_genome_is_explained_the_same_way(self):
        """ExAC is exomes-only, the mirror image of v3."""
        result, _ = _run_get_variant(
            {"variant_id": "13-20189546-AC-A", "dataset": "exac"}
        )
        note = result["data"]["dataset_note"]
        assert "no genome component" in note
        assert result["data"]["reference_genome"] == "GRCh37"


class TestVariantPopulationsDisclosesTooDespiteDifferentDefault:
    """The r4-defaulting sibling: same disclosure, different default."""

    def _run(self, arguments):
        return _run(gnomADGetVariantPopulations, _POPULATIONS_CONFIG, arguments)

    def test_default_is_still_r4_and_is_reported(self):
        result, fake = self._run({"variant_id": "13-20189546-AC-A"})

        assert fake.datasets_requested == ["gnomad_r4"]
        assert result["data"]["dataset"] == "gnomad_r4"
        assert result["data"]["reference_genome"] == "GRCh38"
        assert "dataset_note" not in result["data"]

    def test_the_two_siblings_disagree_by_default_and_both_now_say_why(self):
        """gnomad_get_variant defaults to r3, this tool to r4. The divergence
        is intentional; what was missing is that each response names its own."""
        variant_result, _ = _run_get_variant({"variant_id": "13-20189546-AC-A"})
        populations_result, _ = self._run({"variant_id": "13-20189546-AC-A"})

        assert variant_result["data"]["dataset"] == "gnomad_r3"
        assert populations_result["data"]["dataset"] == "gnomad_r4"
        # Same variant, different allele numbers, now attributable.
        assert variant_result["data"]["variant"]["genome"]["an"] == 151764
        assert populations_result["data"]["genome"]["an"] == 151882

    def test_r3_here_also_explains_its_null_exome(self):
        result, _ = self._run(
            {"variant_id": "13-20189546-AC-A", "dataset": "gnomad_r3"}
        )
        assert result["data"]["exome"] is None
        assert "no exome component" in result["data"]["dataset_note"]


class TestDerivedSvDatasetIsDisclosed:
    """The SV tools pick their callset from `reference_genome` (round 34), so
    it is the least visible dataset choice in the family."""

    _SV_CONFIG = {
        "name": "gnomad_get_sv_by_gene",
        "fields": {
            "query_schema": "query { gene }",
            "variable_map": {"reference_genome": "referenceGenome"},
            "default_variables": {"referenceGenome": "GRCh38"},
            "derived_variables": {
                "svDataset": {
                    "from": "reference_genome",
                    "map": {"GRCh37": "gnomad_sv_r2_1", "GRCh38": "gnomad_sv_r4"},
                    "default": "gnomad_sv_r4",
                }
            },
        },
    }

    def _run(self, arguments):
        responder = MagicMock(return_value=_resp({"data": {"gene": {"symbol": "RHD"}}}))
        return _run(gnomADGraphQLQueryTool, self._SV_CONFIG, arguments, responder)[0]

    @pytest.mark.parametrize(
        "reference_genome,dataset,assembly",
        [
            ("GRCh37", "gnomad_sv_r2_1", "GRCh37"),
            ("GRCh38", "gnomad_sv_r4", "GRCh38"),
            (None, "gnomad_sv_r4", "GRCh38"),
        ],
    )
    def test_auto_selected_sv_callset_is_named(
        self, reference_genome, dataset, assembly
    ):
        arguments = {"gene_symbol": "RHD"}
        if reference_genome:
            arguments["reference_genome"] = reference_genome
        data = self._run(arguments)["data"]

        assert data["dataset"] == dataset
        assert data["reference_genome"] == assembly
        # SV callsets have no exome/genome split, so no callset note applies.
        assert "dataset_note" not in data


class TestFeatureToolsDiscloseTheirAssembly:
    """The three dataset-free tools returned coordinates in an unnamed frame.

    `gnomad_get_gene`, `gnomad_get_transcript` and `gnomad_search_genes` are the
    only queries in this family with no `dataset`, so the disclosure above never
    reached them -- yet they all return `chrom`/`start`/`stop` (or
    assembly-specific search hits) and named no assembly at all. Recorded live
    before the fix, `gnomad_get_gene {"gene_symbol": "BRCA2"}` answered:

        {"gene": {"gene_id": "ENSG00000139618", "symbol": "BRCA2",
                  "chrom": "13", "start": 32315086, "stop": 32400268, ...}}

    Nothing there says whether 32,315,086 should be compared against GRCh37 or
    GRCh38 data. It matters by 574 kb -- the same call with
    `reference_genome: GRCh37` returns 13:32,889,611-32,973,805 -- and a search
    is assembly-specific too: BRCA2 resolves to `ensembl_version` 17 on GRCh38
    and 10 on GRCh37.

    The assembly is not inferred. Introspecting the live schema
    (``{__type(name: "Gene"){fields{name}}}``) shows `reference_genome` on both
    `Gene` and `Transcript`, so the query now asks gnomAD for it and reports
    what gnomAD says. Confirmed live:

        gene(gene_symbol:"BRCA2", reference_genome: GRCh38)
            -> reference_genome "GRCh38", start 32315086
        gene(gene_symbol:"BRCA2", reference_genome: GRCh37)
            -> reference_genome "GRCh37", start 32889611
        transcript(transcript_id:"ENST00000380152", reference_genome: GRCh38)
            -> reference_genome "GRCh38", start 32315508

    `GeneSearchResult` exposes only `ensembl_id`, `ensembl_version` and
    `symbol`, so a gene search falls back to the assembly the request
    transmitted -- still the value in play rather than a hard-coded constant.
    """

    _GENE_CONFIG = {
        "name": "gnomad_get_gene",
        "fields": {
            "query_schema": "query { gene { reference_genome } }",
            "variable_map": {"reference_genome": "referenceGenome"},
            "default_variables": {"referenceGenome": "GRCh38"},
        },
    }
    _SEARCH_CONFIG = {
        "name": "gnomad_search_genes",
        "fields": {
            "query_schema": "query { gene_search }",
            "variable_map": {"reference_genome": "referenceGenome"},
            "default_variables": {"referenceGenome": "GRCh38"},
        },
    }
    # gnomAD's real GRCh38 answers, including the reference_genome the API
    # itself reports on the record.
    _GENE_38 = {
        "reference_genome": "GRCh38",
        "gene_id": "ENSG00000139618",
        "symbol": "BRCA2",
        "chrom": "13",
        "start": 32315086,
        "stop": 32400268,
        "strand": "+",
        "canonical_transcript_id": "ENST00000380152",
    }
    _GENE_37 = {
        **_GENE_38,
        "reference_genome": "GRCh37",
        "start": 32889611,
        "stop": 32973805,
        "canonical_transcript_id": "ENST00000544455",
    }
    _TRANSCRIPT_38 = {
        "reference_genome": "GRCh38",
        "transcript_id": "ENST00000380152",
        "gene_id": "ENSG00000139618",
        "gene": {"gene_id": "ENSG00000139618", "symbol": "BRCA2"},
        "chrom": "13",
        "start": 32315508,
        "stop": 32400268,
        "strand": "+",
    }

    @staticmethod
    def _run_feature(config, payload, arguments):
        responder = MagicMock(return_value=_resp({"data": payload}))
        return _run(gnomADGraphQLQueryTool, config, arguments, responder)[0]

    def test_gene_names_the_assembly_it_answered_in(self):
        result = self._run_feature(
            self._GENE_CONFIG, {"gene": self._GENE_38}, {"gene_symbol": "BRCA2"}
        )
        assert result["data"]["reference_genome"] == "GRCh38"
        # The coordinates the disclosure applies to are untouched.
        assert result["data"]["gene"]["start"] == 32315086

    def test_gene_reports_the_api_value_not_the_default(self):
        """gnomAD's own field wins, so the label can never drift from the frame
        the record is actually in."""
        result = self._run_feature(
            self._GENE_CONFIG,
            {"gene": self._GENE_37},
            {"gene_symbol": "BRCA2", "reference_genome": "GRCh37"},
        )
        assert result["data"]["reference_genome"] == "GRCh37"
        assert result["data"]["gene"]["start"] == 32889611

    def test_transcript_names_the_assembly_it_answered_in(self):
        config = dict(self._GENE_CONFIG, name="gnomad_get_transcript")
        result = self._run_feature(
            config,
            {"transcript": self._TRANSCRIPT_38},
            {"transcript_id": "ENST00000380152"},
        )
        assert result["data"]["reference_genome"] == "GRCh38"
        assert result["data"]["transcript"]["start"] == 32315508

    def test_gene_search_falls_back_to_the_assembly_it_requested(self):
        """GeneSearchResult carries no reference_genome field, so the sent
        value is the best available evidence -- and search hits really do
        differ: ensembl_version 17 on GRCh38, 10 on GRCh37."""
        result = self._run_feature(
            self._SEARCH_CONFIG,
            {
                "gene_search": [
                    {
                        "ensembl_id": "ENSG00000139618",
                        "ensembl_version": "10",
                        "symbol": "BRCA2",
                    }
                ]
            },
            {"query": "BRCA2", "reference_genome": "GRCh37"},
        )
        assert result["data"]["reference_genome"] == "GRCh37"

    def test_omitted_argument_still_reports_the_default_that_was_used(self):
        """The silent default is the whole point: a caller who passed nothing
        must still be told which frame they got."""
        result = self._run_feature(
            self._SEARCH_CONFIG,
            {"gene_search": [{"ensembl_id": "ENSG00000139618", "symbol": "BRCA2"}]},
            {"query": "BRCA2"},
        )
        assert result["data"]["reference_genome"] == "GRCh38"

    def test_no_dataset_keys_are_injected(self):
        """These queries are not dataset-scoped. Naming a callset that never
        answered would be a fabrication, so only the assembly is added."""
        result = self._run_feature(
            self._GENE_CONFIG, {"gene": self._GENE_38}, {"gene_symbol": "BRCA2"}
        )
        assert "dataset" not in result["data"]
        assert "dataset_note" not in result["data"]

    def test_disclosure_is_purely_additive(self):
        """Every pre-existing key keeps its exact value; one key is added."""
        payload_gene = dict(self._GENE_38)
        result = self._run_feature(
            self._GENE_CONFIG, {"gene": payload_gene}, {"gene_symbol": "BRCA2"}
        )
        assert result["data"]["gene"] == self._GENE_38
        assert set(result["data"]) == {"gene", "reference_genome"}

    def test_a_payload_with_no_assembly_anywhere_is_left_alone(self):
        """No transmitted value and no API field means nothing to disclose --
        inventing GRCh38 there would be exactly the guess this fix removes."""
        config = {
            "name": "gnomad_get_gene_constraints",
            "fields": {"query_schema": "query { gene }"},
        }
        result = self._run_feature(config, {"gene": {"symbol": "BRCA2"}}, {})
        assert result["data"] == {"gene": {"symbol": "BRCA2"}}


class TestErrorsAreNotAnnotated:
    """A failed call has no callset to disclose and must be left alone."""

    def test_graphql_error_response_is_unchanged(self):
        responder = MagicMock(
            return_value=_resp({"errors": [{"message": "Variant not found"}]})
        )
        result = _run(
            gnomADGraphQLQueryTool,
            _GET_VARIANT_CONFIG,
            {"variant_id": "nope"},
            responder,
        )[0]

        assert result["status"] == "error"
        assert result["data"] is None
        assert "dataset" not in result
