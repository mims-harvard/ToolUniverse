# wormbase_tool.py
"""
WormBase gene tools for ToolUniverse, served through the Alliance API.

WormBase curates Caenorhabditis elegans: gene information, phenotypes,
expression, orthologs, interactions and human disease models.

rest.wormbase.org is unreachable from any HTTP client. It answers 403 with
cf-mitigated: challenge and a "Just a moment... Enable JavaScript and cookies"
page, and so does downloads.wormbase.org, so there is no bulk route either.
See data/broken_apis/wormbase_rest.json.

The Alliance of Genome Resources redistributes the same curated records, and
WormBase is one of its member databases -- a gene fetched there carries
dataProvider {"abbreviation": "WB", "fullName": "WormBase"} and its
interactions carry interactionSource "wormbase". So this is the same data with
attribution, not a substitute that answers a nearby question.

This module already depended on Alliance to turn a gene symbol into a WBGene
ID, since WormBase's own search was unreachable too; now the data follows.

Three fields have no Alliance equivalent and come back empty rather than
guessed. Each says so in its own metadata:

  status                    WormBase's Live/Dead gene status
  phenotypes_not_observed   WormBase's "not observed" annotations
  nematode_orthologs        Alliance covers the six model organisms, not
                            other nematodes

API: https://www.alliancegenome.org/api
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .http_utils import cloudflare_challenge, request_with_retry
from .tool_registry import register_tool

ALLIANCE_API_BASE = "https://www.alliancegenome.org/api"
ALLIANCE_AUTOCOMPLETE_URL = f"{ALLIANCE_API_BASE}/search_autocomplete"

# Verified 2026-10-03 against WB:WBGene00000912 (daf-16):
#   GET  /gene/{curie}                        200   31696 B
#   GET  /gene/{curie}/phenotypes             200   28 records
#   GET  /gene/{curie}/orthologs              200   23 records
#   GET  /gene/{curie}/paralogs               200   26463 B
#   GET  /gene/{curie}/molecular-interactions 200   267 records
#   GET  /gene/{curie}/genetic-interactions   200   379 records
#   POST /gene/{curie}/disease-ribbon-summary 200   8661 B   body: [curie]
#   POST /expression                          200   111 records, body: [curie]
# The two POST endpoints answer 405 to GET, which is how they were found; they
# want a bare JSON list, and reject {"geneIDs": [...]} with
# "Not able to deserialize data provided."
_ROW_LIMIT = 50

# Module-level cache: gene name (lower) -> WBGene ID, avoids repeated lookups
_WBGENE_CACHE: dict = {}


def _resolve_wbgene_id(gene_input: str) -> str:
    """Resolve a gene name (e.g. 'unc-86') to a WBGene ID via the Alliance API.

    If the input already looks like a WBGene ID (with or without a "WB:"
    CURIE prefix -- exactly what a sibling tool like Alliance_search_genes
    returns for the same gene), return it with the prefix stripped.
    Returns the resolved WBGene ID or the original input if resolution fails.
    """
    # Fix-R13B-1: WormBase's own REST API 500s on a "WB:"-prefixed ID
    # because the old check below didn't strip it, so the colon-containing
    # string was passed straight into the URL path unchanged.
    unprefixed = gene_input.split(":", 1)[-1]
    if unprefixed.upper().startswith("WBGENE"):
        return unprefixed

    cache_key = gene_input.lower()
    if cache_key in _WBGENE_CACHE:
        return _WBGENE_CACHE[cache_key]

    try:
        # Fix-R13B-2: /api/search with `category`/`species` params returns
        # zero results for any real gene symbol (confirmed live) -- Alliance
        # no longer honours those params on that endpoint. The endpoint that
        # actually resolves symbols is /api/search_autocomplete, which mixes
        # gene/disease/dataset hits and has no `id` field, so gene hits must
        # be filtered client-side by category and the gene id read from
        # `curie` (e.g. "WB:WBGene00006746").
        params = {"q": gene_input, "limit": 25}
        resp = requests.get(ALLIANCE_AUTOCOMPLETE_URL, params=params, timeout=10)
        if resp.status_code != 200:
            return gene_input
        results = resp.json().get("results", [])
        for r in results:
            if r.get("category") != "gene_search_result":
                continue
            raw_id = r.get("curie", "")
            if r.get("symbol", "").lower() == cache_key and raw_id.startswith("WB:"):
                resolved = raw_id.split(":", 1)[-1]
                _WBGENE_CACHE[cache_key] = resolved
                return resolved
        return gene_input
    except Exception:
        return gene_input


def _alliance_curie(gene_id: str) -> str:
    """Alliance wants the CURIE form; WormBase's REST needed it stripped."""
    bare = gene_id.split(":", 1)[-1]
    return f"WB:{bare}" if bare.upper().startswith("WBGENE") else gene_id


def _wb_id(curie: str) -> str:
    """The WBGene form the previous responses used."""
    return (curie or "").split(":", 1)[-1]


def _text(value: Any) -> str:
    """Alliance wraps display strings as {formatText, displayText}."""
    if isinstance(value, dict):
        return value.get("displayText") or value.get("formatText") or ""
    return value or ""


def _named(value: Any) -> str:
    """An ontology term's label."""
    if isinstance(value, dict):
        return value.get("name") or value.get("label") or ""
    return value or ""


@register_tool("WormBaseTool")
class WormBaseTool(BaseTool):
    """
    Tool for querying WormBase, the C. elegans genome database.

    Provides detailed gene information for C. elegans and other
    nematodes including phenotypes, expression data, orthologs,
    and functional annotations.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "gene_overview"
        )
        self.session = requests.Session()

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the WormBase API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"WormBase API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to WormBase API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            challenge = cloudflare_challenge(getattr(e, "response", None))
            if challenge:
                return {
                    "status": "error",
                    "error": f"WormBase is unreachable: {challenge}.",
                }
            return {
                "status": "error",
                "error": f"WormBase API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying WormBase: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "gene_overview":
            return self._gene_overview(arguments)
        elif self.endpoint_type == "gene_phenotypes":
            return self._gene_phenotypes(arguments)
        elif self.endpoint_type == "gene_expression":
            return self._gene_expression(arguments)
        elif self.endpoint_type == "gene_orthologs":
            return self._gene_orthologs(arguments)
        elif self.endpoint_type == "gene_interactions":
            return self._gene_interactions(arguments)
        elif self.endpoint_type == "gene_human_diseases":
            return self._gene_human_diseases(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    # ------------------------------------------------------------------ #
    # Alliance transport
    # ------------------------------------------------------------------ #
    def _alliance(self, path: str, params=None, body=None) -> Any:
        """GET or POST an Alliance endpoint and return the parsed JSON.

        Goes through request_with_retry so the shared User-Agent and backoff
        apply. Raises for a non-2xx; run() turns that into an envelope.
        """
        url = f"{ALLIANCE_API_BASE}{path}"
        method = "POST" if body is not None else "GET"
        response = request_with_retry(
            self.session,
            method,
            url,
            params=params,
            headers={"Accept": "application/json"},
            json=body,
            timeout=self.timeout,
            max_attempts=3,
        )
        response.raise_for_status()
        return response.json()

    def _gene_required(self, arguments: Dict[str, Any]):
        gene_input = arguments.get("gene_id", "")
        if not gene_input:
            return None, {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'WBGene00006763' or 'unc-86')",
            }
        return _alliance_curie(_resolve_wbgene_id(gene_input)), None

    @staticmethod
    def _envelope(endpoint: str, curie: str, data: Dict[str, Any], note=None):
        metadata = {
            "source": "WormBase via the Alliance of Genome Resources",
            "query": _wb_id(curie),
            "endpoint": endpoint,
        }
        if note:
            metadata["coverage_note"] = note
        return {"status": "success", "data": data, "metadata": metadata}

    # ------------------------------------------------------------------ #
    # The six aspects
    # ------------------------------------------------------------------ #
    def _gene_overview(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Gene identity, type and description."""
        curie, error = self._gene_required(arguments)
        if error:
            return error

        gene = (self._alliance(f"/gene/{curie}") or {}).get("gene") or {}
        notes = [
            n.get("freeText", "")
            for n in (gene.get("relatedNotes") or [])
            if isinstance(n, dict) and n.get("freeText")
        ]
        data = {
            "wormbase_id": _wb_id(gene.get("primaryExternalId") or curie),
            "gene_name": _text(gene.get("geneSymbol")),
            "sequence_name": _text(gene.get("geneSystematicName")),
            "species": ((gene.get("taxon") or {}).get("species") or {}).get(
                "fullName", ""
            ),
            "description": notes[0] if notes else _text(gene.get("geneFullName")),
            "gene_type": _named(gene.get("geneType")),
            # WormBase's Live/Dead status is not in the Alliance record.
            "status": "",
        }
        return self._envelope(
            "gene_overview",
            curie,
            data,
            "status is empty: WormBase's Live/Dead gene status has no Alliance "
            "equivalent. Every other field is the Alliance record, which "
            "attributes itself to WormBase.",
        )

    def _gene_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Phenotype annotations."""
        curie, error = self._gene_required(arguments)
        if error:
            return error

        payload = self._alliance(
            f"/gene/{curie}/phenotypes", params={"limit": _ROW_LIMIT}
        )
        results = payload.get("results") or []
        phenotypes = []
        for row in results:
            statement = row.get("phenotypeStatement") or ""
            references = [
                ref.get("curie", "")
                for ref in (row.get("references") or [])
                if isinstance(ref, dict)
            ]
            phenotypes.append(
                {
                    "phenotype_id": "",
                    "phenotype_name": statement,
                    # The declared field. Alliance's relation name is the
                    # closest thing it publishes: "is_implicated_in".
                    "evidence_type": _named(row.get("relation")),
                    "references": [r for r in references if r],
                }
            )
        subject = (results[0].get("subject") if results else {}) or {}
        data = {
            "wormbase_id": _wb_id(curie),
            "gene_name": _text(subject.get("geneSymbol")),
            "phenotype_count": payload.get("total", len(phenotypes)),
            "phenotypes": phenotypes,
            # Alliance carries the implicated-in annotations only.
            "not_observed_count": 0,
            "phenotypes_not_observed": [],
        }
        return self._envelope(
            "gene_phenotypes",
            curie,
            data,
            "phenotypes_not_observed is empty: Alliance publishes the "
            "implicated-in annotations and not WormBase's 'not observed' set. "
            "phenotype_id is empty for the same reason -- the annotation is "
            "identified by its statement here.",
        )

    def _gene_expression(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Expression annotations."""
        curie, error = self._gene_required(arguments)
        if error:
            return error

        payload = self._alliance(
            "/expression", params={"limit": _ROW_LIMIT}, body=[curie]
        )
        # The annotation names these whereExpressedStatement and
        # whenExpressedStageName -- plain strings, e.g. "AIYL" and
        # "Nematoda Life Stage" -- not the ontology objects I first looked for.
        # The declared shape is {term_id, term_name}, which is what the
        # WormBase widget gave. Alliance names the place and the stage as plain
        # strings (whereExpressedStatement "AIYL", whenExpressedStageName
        # "Nematoda Life Stage") and carries the anatomy term ids separately in
        # the row's termIds, so term_id is filled from there for a location and
        # left null for a stage rather than invented.
        expressed_in, during, assays = [], [], []
        seen_in, seen_during, gene_name = set(), set(), ""
        for row in payload.get("results") or []:
            annotation = row.get("geneExpressionAnnotation") or {}
            subject = annotation.get("expressionAnnotationSubject") or {}
            gene_name = gene_name or _text(subject.get("geneSymbol"))
            where = annotation.get("whereExpressedStatement") or ""
            when = annotation.get("whenExpressedStageName") or ""
            assay = _named(annotation.get("expressionAssayUsed"))
            term_ids = [
                term for term in (row.get("termIds") or []) if isinstance(term, str)
            ]
            if where and where not in seen_in:
                seen_in.add(where)
                expressed_in.append(
                    {"term_id": term_ids[0] if term_ids else None,
                     "term_name": where}
                )
            if when and when not in seen_during:
                seen_during.add(when)
                during.append({"term_id": None, "term_name": when})
            if assay and assay not in assays:
                assays.append(assay)
        data = {
            "wormbase_id": _wb_id(curie),
            "gene_name": gene_name,
            "expressed_in_count": len(expressed_in),
            "expressed_in": expressed_in,
            "expressed_during": during,
            # Alliance reports the assay, not a subcellular compartment.
            "subcellular_localization": [],
            "expression_assays": assays,
            "expression_clusters_count": 0,
            "expression_clusters": [],
        }
        return self._envelope(
            "gene_expression",
            curie,
            data,
            f"{payload.get('total', 0)} annotations upstream, "
            f"{len(payload.get('results') or [])} read. expression_clusters and "
            "subcellular_localization are empty: both are WormBase widget "
            "concepts with no Alliance equivalent. expression_assays is added "
            "in their place, since Alliance does report the assay used.",
        )

    def _gene_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Orthologs across the Alliance model organisms, plus paralogs."""
        curie, error = self._gene_required(arguments)
        if error:
            return error

        # Field names follow the declared schema -- ortholog_id,
        # ortholog_label, methods, species -- not Alliance's own spelling, so
        # a caller written against the WormBase responses keeps working.
        orthologs = []
        payload = self._alliance(f"/gene/{curie}/orthologs")
        for row in payload.get("results") or []:
            pair = row.get("geneToGeneOrthologyGenerated") or {}
            other = pair.get("objectGene") or {}
            methods = [
                _named(m)
                for m in (pair.get("predictionMethodsMatched") or [])
                if _named(m)
            ]
            orthologs.append(
                {
                    "ortholog_id": other.get("primaryExternalId", ""),
                    "ortholog_label": _text(other.get("geneSymbol")),
                    "species": (other.get("taxon") or {}).get("name", ""),
                    "methods": methods,
                }
            )

        paralogs = []
        paralog_payload = self._alliance(f"/gene/{curie}/paralogs")
        for row in paralog_payload.get("results") or []:
            pair = row.get("geneToGeneParalogy") or {}
            other = pair.get("objectGene") or {}
            paralogs.append(
                {
                    "ortholog_id": other.get("primaryExternalId", ""),
                    "ortholog_label": _text(other.get("geneSymbol")),
                }
            )

        data = {
            "wormbase_id": _wb_id(curie),
            "cross_species_ortholog_count": payload.get("total", len(orthologs)),
            "cross_species_orthologs": orthologs,
            # Alliance's set is the six model organisms.
            "nematode_ortholog_count": 0,
            "nematode_orthologs": [],
            "paralog_count": paralog_payload.get("total", len(paralogs)),
            "paralogs": paralogs,
        }
        return self._envelope(
            "gene_orthologs",
            curie,
            data,
            "nematode_orthologs is empty: Alliance publishes orthology across "
            "its six model organisms, so orthologs in other nematodes are not "
            "available here.",
        )

    def _gene_interactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Molecular and genetic interactions."""
        curie, error = self._gene_required(arguments)
        if error:
            return error

        def rows(path, inner_key):
            payload = self._alliance(
                f"/gene/{curie}/{path}", params={"limit": _ROW_LIMIT}
            )
            out = []
            for row in payload.get("results") or []:
                inner = row.get(inner_key) or {}
                subject = inner.get("geneAssociationSubject") or {}
                obj = inner.get("geneGeneAssociationObject") or {}
                out.append(
                    {
                        "interactor_1": _text(subject.get("geneSymbol")),
                        "interactor_1_id": _wb_id(
                            subject.get("primaryExternalId", "")
                        ),
                        "interactor_2": _text(obj.get("geneSymbol")),
                        "interactor_2_id": _wb_id(obj.get("primaryExternalId", "")),
                        "interaction_type": _named(inner.get("interactionType")),
                        "citation": _named(inner.get("interactionSource")),
                    }
                )
            return payload.get("total", len(out)), out

        physical_total, physical = rows(
            "molecular-interactions", "geneMolecularInteraction"
        )
        genetic_total, genetic = rows(
            "genetic-interactions", "geneGeneticInteraction"
        )
        data = {
            "wormbase_id": _wb_id(curie),
            "total_interactions": physical_total + genetic_total,
            "physical_count": len(physical),
            "total_physical_interactions": physical_total,
            "physical_interactions": physical,
            "genetic_count": len(genetic),
            "total_genetic_interactions": genetic_total,
            "genetic_interactions": genetic,
        }
        return self._envelope(
            "gene_interactions",
            curie,
            data,
            f"citation carries the aggregating source (interactionSource, e.g. "
            f"'wormbase') rather than a publication. At most {_ROW_LIMIT} rows "
            "of each kind are read; the totals are the upstream counts.",
        )

    def _gene_human_diseases(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Human disease associations, as Alliance's DO ribbon categories."""
        curie, error = self._gene_required(arguments)
        if error:
            return error

        payload = self._alliance(
            f"/gene/{curie}/disease-ribbon-summary", body=[curie]
        )
        diseases = []
        for category in payload.get("categories") or []:
            if not isinstance(category, dict):
                continue
            diseases.append(
                {
                    "disease_id": category.get("id", ""),
                    "disease_name": category.get("label", ""),
                    # The ribbon is a summary by disease term and carries
                    # neither the evidence codes nor the model type that
                    # WormBase's human_diseases field did.
                    "evidence": [],
                    "model_type": "",
                }
            )
        data = {
            "wormbase_id": _wb_id(curie),
            # The ribbon summarises by disease term, not by human gene.
            "human_gene_ids": [],
            "disease_count": len(diseases),
            "diseases": diseases,
        }
        return self._envelope(
            "gene_human_diseases",
            curie,
            data,
            "diseases are Disease Ontology categories from Alliance's disease "
            "ribbon (e.g. DOID:0050117 Infection), so evidence and model_type "
            "are empty -- the ribbon summarises by term and carries neither. "
            "human_gene_ids is empty too: it groups by disease rather than by "
            "the human ortholog, which WormBase_get_orthologs answers.",
        )
