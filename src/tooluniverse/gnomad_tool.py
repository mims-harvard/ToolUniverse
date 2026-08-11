"""
gnomAD GraphQL API Tool

This tool provides access to the gnomAD (Genome Aggregation Database) for
population genetics data, variant frequencies, and gene constraint metrics
using GraphQL.
"""

import re
import requests
from typing import Dict, Any, Optional, Tuple
from .base_tool import BaseTool
from .tool_registry import register_tool


# --- Dataset provenance ------------------------------------------------------
#
# Every gnomAD response echoes the dataset that actually answered and the
# assembly its coordinates are in, because neither was previously recoverable
# from the payload. Two facts make that dangerous rather than merely untidy:
#
# 1. The defaults in this family deliberately differ. `gnomad_get_variant`,
#    `gnomad_search_variants` and `gnomad_get_region` default to `gnomad_r3`,
#    while `gnomad_get_variant_populations` and `gnomad_get_constraint` default
#    to `gnomad_r4`. Sibling calls on the same variant therefore disagree by
#    design, and nothing in the response said which callset produced which
#    number.
# 2. gnomAD v3 is a genomes-only callset -- it has no exome component at all --
#    so under the r3 default `exome` is structurally null for *every* variant,
#    which is indistinguishable from "not observed in exomes". On GJB2 c.35delG
#    (13-20189546-AC-A) that silently hid the 10,423 exome allele observations
#    out of 1,461,600 alleles that `gnomad_r4` reports. ExAC is the mirror
#    image: exomes only, `genome` always null.
#
# Verified live against the API's own `variant.reference_genome` field and the
# per-dataset allele numbers for 13-20189546-AC-A (GRCh38) and
# 13-20763685-AC-A (GRCh37):
#   gnomad_r4, gnomad_r4_non_ukb       GRCh38  genome an=151882, exome an=1461600
#   gnomad_r3 + its five subsets       GRCh38  genome an=151764, exome null
#   gnomad_r2_1 + its four subsets     GRCh37  genome an=31334,  exome an=249362
#   exac                               GRCh37  genome null,      exome an=121352
# Structural-variant callsets follow the same version-to-assembly rule and have
# no exome/genome split at all, hence `None` rather than an empty tuple.
#
# Matched by prefix so subsets released later resolve without a code change.
_DATASET_FAMILIES = (
    # (dataset id prefix, reference assembly, callsets the dataset contains).
    # `None` means the callset has no exome/genome split at all (SV callsets).
    ("gnomad_sv_r2_1", "GRCh37", None),
    ("gnomad_sv_r4", "GRCh38", None),
    ("gnomad_r2_1", "GRCh37", ("genome", "exome")),
    ("gnomad_r3", "GRCh38", ("genome",)),
    ("gnomad_r4", "GRCh38", ("genome", "exome")),
    ("exac", "GRCh37", ("exome",)),
)

_DEFAULT_ASSEMBLY = "GRCh38"

# Where to send a caller for the callset the selected dataset does not carry.
_CALLSET_ALTERNATIVES = {
    "exome": "dataset='gnomad_r4' (GRCh38) or dataset='gnomad_r2_1' (GRCh37)",
    "genome": "dataset='gnomad_r4' or dataset='gnomad_r3' (GRCh38)",
}


def _dataset_family(dataset: Optional[str]) -> Tuple[str, Optional[Tuple[str, ...]]]:
    """Return (reference assembly, callsets carried) for a gnomAD dataset id."""
    key = (dataset or "").lower()
    for prefix, assembly, callsets in _DATASET_FAMILIES:
        if key.startswith(prefix):
            return assembly, callsets
    return _DEFAULT_ASSEMBLY, None


def resolve_dataset_assembly(dataset: Optional[str]) -> str:
    """Map a gnomAD dataset id to the reference assembly it is built on."""
    return _dataset_family(dataset)[0]


def _reports_null(payload: Any, key: str) -> bool:
    """True when the payload sets `key` to null, at the root or one node down.

    gnomAD nests the record under its query field (``{"variant": {...}}``), so a
    single extra level is all that is ever needed.
    """
    if not isinstance(payload, dict):
        return False
    nodes = [payload, *(v for v in payload.values() if isinstance(v, dict))]
    return any(key in node and node[key] is None for node in nodes)


def _missing_callset_note(dataset: Optional[str], payload: Any) -> Optional[str]:
    """Explain a null callset that is structural rather than an observation.

    Only the single-component callsets can reach a note: v3 carries genomes and
    ExAC carries exomes, while v2.1 and v4 carry both and so never have a
    structurally absent one.
    """
    callsets = _dataset_family(dataset)[1]
    if not callsets:
        return None
    absent = next((k for k in _CALLSET_ALTERNATIVES if k not in callsets), None)
    if absent is None or not _reports_null(payload, absent):
        return None
    return (
        f"Dataset '{dataset}' is a {callsets[0]}-only callset with no {absent} "
        f"component, so `{absent}` is null for every variant in it. That means "
        f"'not present in this callset', NOT 'not observed'. For {absent} allele "
        f"counts query {_CALLSET_ALTERNATIVES[absent]}."
    )


def describe_dataset(
    dataset: Optional[str], payload: Any = None, assembly: Optional[str] = None
) -> Dict[str, Any]:
    """Build the provenance block echoed on every dataset-backed response.

    Always reports `dataset` and `reference_genome` -- including when the caller
    omitted `dataset` and silently received the tool's default -- plus a
    `dataset_note` whenever the payload's null callset is a property of the
    callset rather than of the variant.

    `assembly` is the reference genome the query actually sent, for the queries
    that carry one of their own (gnomad_get_region does). It wins over the
    lookup table: reporting an inference in preference to the value that was
    transmitted is the very thing this disclosure exists to prevent. gnomAD
    rejects a mismatched pair with HTTP 500 (confirmed live: dataset=gnomad_r2_1
    with reference_genome=GRCh38, and gnomad_r3 with GRCh37, both 500 while the
    matching pairs succeed), so the two agree on every response that gets here.
    """
    block: Dict[str, Any] = {
        "dataset": dataset,
        "reference_genome": assembly or resolve_dataset_assembly(dataset),
    }
    note = _missing_callset_note(dataset, payload)
    if note:
        block["dataset_note"] = note
    return block


def payload_reference_genome(payload: Any) -> Optional[str]:
    """Return gnomAD's own `reference_genome`, if the payload carries one.

    The dataset-scoped queries infer the assembly from the callset id, but the
    feature queries have no dataset at all -- they take a `reference_genome`
    argument directly. For those, the assembly does not have to be inferred or
    hard-coded: the API states it itself. Introspecting the live schema
    (``{__type(name: "Gene"){fields{name}}}``) shows `reference_genome` as the
    first field of both `Gene` and `Transcript`, so the query asks for it and
    this reads it back. `GeneSearchResult` exposes only `ensembl_id`,
    `ensembl_version` and `symbol`, so a gene search has to fall back to the
    value the request transmitted -- still the value in play, not a guess.

    gnomAD nests each record under its query field (``{"gene": {...}}``), so one
    level down is all that is ever needed.
    """
    if not isinstance(payload, dict):
        return None
    for node in payload.values():
        if isinstance(node, dict) and isinstance(node.get("reference_genome"), str):
            return node["reference_genome"]
    return None


class gnomADGraphQLTool(BaseTool):
    """Base class for gnomAD GraphQL API tools."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint_url = "https://gnomad.broadinstitute.org/api"
        # Prefer JSON-driven query definitions. Support both legacy top-level
        # `query_schema` and `fields.query_schema`.
        fields_cfg = tool_config.get("fields", {}) or {}
        self.query_schema = tool_config.get("query_schema") or fields_cfg.get(
            "query_schema", ""
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "ToolUniverse/1.0",
            }
        )
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute GraphQL query with given arguments."""
        try:
            response = self.session.post(
                self.endpoint_url,
                json={"query": self.query_schema, "variables": arguments},
                timeout=self.timeout,
            )
            status_code = getattr(response, "status_code", None)
            response.raise_for_status()
            result = response.json()

            # GraphQL errors are returned with HTTP 200; surface them to users.
            errors = result.get("errors")
            if errors:
                first = errors[0] if isinstance(errors, list) and errors else None
                msg = first.get("message") if isinstance(first, dict) else None
                msg = msg or "gnomAD GraphQL query returned errors"
                return {
                    "status": "error",
                    "error": msg,
                    "url": getattr(response, "url", self.endpoint_url),
                    "status_code": status_code,
                    "detail": errors[:3],
                    "data": None,
                }

            data = result.get("data")
            if not data or all(not v for v in data.values()):
                return {
                    "status": "error",
                    "error": "No data returned from gnomAD API",
                    "url": getattr(response, "url", self.endpoint_url),
                    "status_code": status_code,
                    "data": None,
                }

            return {
                "status": "success",
                "data": data,
                "url": getattr(response, "url", self.endpoint_url),
            }

        except requests.exceptions.HTTPError as e:
            resp = getattr(e, "response", None)
            return {
                "status": "error",
                "error": (
                    f"gnomAD API returned HTTP {getattr(resp, 'status_code', None)}"
                ),
                "url": getattr(resp, "url", self.endpoint_url),
                "status_code": getattr(resp, "status_code", None),
                "detail": (getattr(resp, "text", "") or "")[:500] or None,
                "data": None,
            }
        except (requests.exceptions.RequestException, ValueError) as e:
            return {
                "status": "error",
                "error": f"gnomAD GraphQL request failed: {str(e)}",
                "url": self.endpoint_url,
                "status_code": None,
                "detail": None,
                "data": None,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"gnomAD GraphQL request failed: {str(e)}",
                "url": self.endpoint_url,
                "status_code": None,
                "detail": None,
                "data": None,
            }


@register_tool("gnomADGraphQLQueryTool")
class gnomADGraphQLQueryTool(gnomADGraphQLTool):
    """
    Generic gnomAD GraphQL tool driven by JSON config.

    Config fields supported:
    - fields.query_schema: GraphQL query string
    - fields.variable_map: map tool argument names -> GraphQL variable names
    - fields.default_variables: default GraphQL variable values
    - fields.derived_variables: GraphQL variables computed from another
      variable via a lookup table, e.g.::

          {"svDataset": {"from": "reference_genome",
                         "map": {"GRCh37": "gnomad_sv_r2_1",
                                 "GRCh38": "gnomad_sv_r4"},
                         "default": "gnomad_sv_r4"}}

      When the source value is free-form rather than an enum, `patterns`
      matches it against regular expressions in order instead, e.g.::

          {"svDataset": {"from": "variant_id",
                         "patterns": [{"match": "^[A-Za-z]+_[0-9XY]+_[0-9]+$",
                                       "value": "gnomad_sv_r2_1"}],
                         "default": "gnomad_sv_r4"}}

      `map` is consulted first, then `patterns`, then `default`.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        fields_cfg = tool_config.get("fields", {}) or {}
        self.variable_map = fields_cfg.get("variable_map", {}) or {}
        self.default_variables = fields_cfg.get("default_variables", {}) or {}
        self.derived_variables = fields_cfg.get("derived_variables", {}) or {}

    @staticmethod
    def _match_patterns(patterns: Any, source_value: Any) -> Any:
        """Return the value of the first regex rule matching `source_value`."""
        if not isinstance(patterns, list) or not isinstance(source_value, str):
            return None
        for rule in patterns:
            if not isinstance(rule, dict):
                continue
            expression = rule.get("match")
            if expression and re.search(expression, source_value):
                return rule.get("value")
        return None

    def _apply_derived_variables(self, variables: Dict[str, Any]) -> None:
        """Fill in variables computed from another variable's value.

        A derived variable is only applied when the caller did not supply it
        explicitly, so an explicit value always wins over the lookup table.
        """
        for name, rule in self.derived_variables.items():
            if name in variables or not isinstance(rule, dict):
                continue
            source = rule.get("from")
            source_value = variables.get(self.variable_map.get(source, source))
            value = (rule.get("map") or {}).get(source_value)
            if value is None:
                value = self._match_patterns(rule.get("patterns"), source_value)
            if value is None:
                value = rule.get("default")
            if value is not None:
                variables[name] = value

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Merge defaults + map argument names to GraphQL variables
        variables: Dict[str, Any] = dict(self.default_variables)
        for k, v in (arguments or {}).items():
            if v is None:
                continue
            variables[self.variable_map.get(k, k)] = v
        self._apply_derived_variables(variables)
        result = super().run(variables)
        # Disclose the callset that answered. `svDataset` is covered too because
        # the SV tools derive it rather than taking it from the caller, so it is
        # the least visible dataset choice in the family.
        dataset = variables.get("dataset") or variables.get("svDataset")
        data = result.get("data")
        if dataset and isinstance(data, dict):
            data.update(
                describe_dataset(dataset, data, variables.get("referenceGenome"))
            )
        elif isinstance(data, dict):
            # `gnomad_get_gene`, `gnomad_get_transcript` and `gnomad_search_genes`
            # are the family's only queries with no dataset, so the disclosure
            # above never reached them -- yet they return `chrom`/`start`/`stop`
            # and said nothing about the frame those are in. The gap is not
            # cosmetic: BRCA2 comes back as 13:32,315,086-32,400,268 under the
            # GRCh38 default and 13:32,889,611-32,973,805 under GRCh37, a 574 kb
            # shift, and a gene search returns ensembl_version 17 vs 10 for the
            # same accession. Reported here as `reference_genome`, the same key
            # and the same top-of-`data` placement the dataset-scoped siblings
            # use, so one reading habit works across the family.
            assembly = payload_reference_genome(data) or variables.get(
                "referenceGenome"
            )
            if assembly:
                data["reference_genome"] = assembly
        return result


@register_tool("gnomADGetVariantPopulations")
class gnomADGetVariantPopulations(gnomADGraphQLTool):
    """
    Get per-ancestry (population-stratified) allele frequencies for a variant.

    The gnomAD API returns per-population `ac` and `an` only; this tool computes
    `af = ac / an` (guarding `an == 0` -> `af = None`) and separates the rows by
    genome vs exome callset.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        if not self.query_schema:
            self.query_schema = (
                "query($variantId: String!, $dataset: DatasetId!) { "
                "variant(variantId: $variantId, dataset: $dataset) { "
                "variant_id chrom pos ref alt rsid "
                "genome { ac an populations { id ac an } } "
                "exome { ac an populations { id ac an } } } }"
            )

    @staticmethod
    def _compute_af(ac, an):
        """Return ac/an, or None when an is missing/zero."""
        if not an:  # covers None and 0
            return None
        return ac / an

    def _build_callset(self, callset):
        """Build a callset summary (overall af + per-population rows)."""
        if not callset:
            return None
        populations = []
        for pop in callset.get("populations") or []:
            ac = pop.get("ac")
            an = pop.get("an")
            populations.append(
                {
                    "id": pop.get("id"),
                    "ac": ac,
                    "an": an,
                    "af": self._compute_af(ac, an),
                }
            )
        return {
            "ac": callset.get("ac"),
            "an": callset.get("an"),
            "af": self._compute_af(callset.get("ac"), callset.get("an")),
            "populations": populations,
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch a variant's per-ancestry allele frequencies."""
        arguments = arguments or {}
        variant_id = arguments.get("variant_id")
        if not variant_id:
            return {"status": "error", "error": "variant_id is required", "data": None}

        dataset = arguments.get("dataset") or "gnomad_r4"
        graphql_args = {"variantId": variant_id, "dataset": dataset}

        result = super().run(graphql_args)
        if result.get("status") != "success":
            return result

        variant = (result.get("data") or {}).get("variant")
        if not variant:
            return {
                "status": "error",
                "error": f"No variant found for variant_id '{variant_id}' in dataset '{dataset}'",
                "url": result.get("url"),
                "data": None,
            }

        data = {
            "variant_id": variant.get("variant_id"),
            "chrom": variant.get("chrom"),
            "pos": variant.get("pos"),
            "ref": variant.get("ref"),
            "alt": variant.get("alt"),
            "rsid": variant.get("rsid"),
            "genome": self._build_callset(variant.get("genome")),
            "exome": self._build_callset(variant.get("exome")),
        }
        # This tool defaults to gnomad_r4 while gnomad_get_variant defaults to
        # gnomad_r3, so the two disagree on the same variant by design. The
        # dataset id was always reported here; the assembly and the structural
        # null now come with it.
        data.update(describe_dataset(dataset, data))

        return {
            "status": "success",
            "data": data,
            "url": result.get("url"),
        }


@register_tool("gnomADGetGeneConstraints")
class gnomADGetGeneConstraints(gnomADGraphQLTool):
    """Get gene constraint metrics from gnomAD."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Set default query schema if not provided in config
        if not self.query_schema:
            self.query_schema = """
query GeneConstraints(
  $geneSymbol: String!,
  $referenceGenome: ReferenceGenomeId!
) {
  gene(gene_symbol: $geneSymbol, reference_genome: $referenceGenome) {
    symbol
    gene_id
    exac_constraint {
      exp_lof
      obs_lof
      pLI
      exp_mis
      obs_mis
      exp_syn
      obs_syn
    }
    gnomad_constraint {
      exp_lof
      obs_lof
      oe_lof
      pLI
      exp_mis
      obs_mis
      oe_mis
      exp_syn
      obs_syn
      oe_syn
    }
  }
}
"""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene constraints."""
        gene_symbol = arguments.get("gene_symbol", "")
        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol is required"}

        reference_genome = arguments.get("reference_genome") or "GRCh38"

        # Convert tool args to GraphQL variables
        graphql_args = {
            "geneSymbol": gene_symbol,
            "referenceGenome": reference_genome,
        }

        result = super().run(graphql_args)

        # Add gene_symbol to result for reference
        if result.get("status") == "success":
            result["gene_symbol"] = gene_symbol

        return result
