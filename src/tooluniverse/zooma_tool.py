"""
ZOOMA tool for ToolUniverse.

ZOOMA (https://www.ebi.ac.uk/spot/zooma) is an EBI/SPOT service that maps free
text (e.g. a sample attribute, phenotype description, organism name, or disease
label) to ontology terms. It returns ontology cross-references (semantic tags as
OBO/EFO IRIs) together with a confidence rating (HIGH/GOOD/MEDIUM/LOW) and
provenance, drawing on curated annotations plus OLS text tagging.

This fills the gap left by the retired OxO service and complements OLS: instead
of looking up a known term, ZOOMA annotates arbitrary free text to the most
likely ontology term(s).

Operations (dispatched by tool_config["fields"]["operation"]):
  - annotate         : map free text to ranked ontology annotations (default)
  - list_datasources : list ZOOMA curated annotation datasources

API: https://www.ebi.ac.uk/spot/zooma/v2/api/
No authentication required. Public access.
"""

import requests
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool

ZOOMA_BASE = "https://www.ebi.ac.uk/spot/zooma/v2/api"

# Confidence ranking used for the optional min_confidence filter.
_CONFIDENCE_RANK = {"LOW": 0, "MEDIUM": 1, "GOOD": 2, "HIGH": 3}


@register_tool("ZoomaTool")
class ZoomaTool(BaseTool):
    """
    Tool for ZOOMA - EBI free-text-to-ontology annotation service.

    Maps a free-text property value (optionally with a property type and an
    ontology source filter) to ontology terms, returning their IRIs, CURIEs,
    confidence, and provenance. Also lists ZOOMA datasources.

    No authentication required. run() never raises.
    """

    def __init__(self, tool_config: dict):
        super().__init__(tool_config)
        self.timeout = 30
        fields = tool_config.get("fields", {}) or {}
        self.operation = fields.get("operation", "annotate")

    def run(self, arguments: dict) -> dict:
        """Execute the requested ZOOMA call. Never raises."""
        try:
            if self.operation == "list_datasources":
                return self._list_datasources()
            return self._annotate(arguments or {})
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ZOOMA request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to ZOOMA service."}
        except requests.exceptions.HTTPError as e:
            code = getattr(e.response, "status_code", "unknown")
            return {"status": "error", "error": f"ZOOMA HTTP error: {code}"}
        except Exception as e:  # noqa: BLE001 - defensive: run() must never raise
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    # ----------------------------------------------------------- annotate
    def _annotate(self, arguments: dict) -> dict:
        property_value = (arguments.get("property_value") or "").strip()
        if not property_value:
            return {
                "status": "error",
                "error": "Parameter 'property_value' is required (free text to annotate).",
            }

        params = {"propertyValue": property_value}

        property_type = arguments.get("property_type")
        if property_type:
            params["propertyType"] = str(property_type).strip()

        # Optional ontology / source filter, e.g. "efo" or "efo,uberon".
        ontologies = arguments.get("ontologies")
        if ontologies:
            if isinstance(ontologies, (list, tuple)):
                onto_list = [str(o).strip() for o in ontologies if str(o).strip()]
            else:
                onto_list = [o.strip() for o in str(ontologies).split(",") if o.strip()]
            if onto_list:
                params["filter"] = (
                    "required:[none],ontologies:[" + ",".join(onto_list) + "]"
                )

        resp = requests.get(
            f"{ZOOMA_BASE}/services/annotate",
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        raw = resp.json()
        if not isinstance(raw, list):
            raw = []

        min_conf = arguments.get("min_confidence")
        min_rank = _CONFIDENCE_RANK.get(str(min_conf).upper()) if min_conf else None

        try:
            max_results = int(arguments.get("max_results", 10))
        except (TypeError, ValueError):
            max_results = 10
        if max_results < 1:
            max_results = 1

        annotations = []
        for item in raw:
            conf = item.get("confidence")
            if min_rank is not None:
                rank = _CONFIDENCE_RANK.get(str(conf).upper())
                if rank is None or rank < min_rank:
                    continue
            annotations.append(self._format(item))
            if len(annotations) >= max_results:
                break

        return {"status": "success", "data": annotations}

    @staticmethod
    def _format(item: dict) -> dict:
        prop = item.get("annotatedProperty") or {}
        prov = item.get("provenance") or {}
        source = prov.get("source") or {}
        olslinks = (item.get("_links") or {}).get("olslinks") or []
        ols_urls = [
            link.get("href")
            for link in olslinks
            if isinstance(link, dict) and link.get("href")
        ]
        tags = item.get("semanticTags") or []
        curies = [c for c in (_iri_to_curie(t) for t in tags) if c]
        return {
            "property_value": prop.get("propertyValue"),
            "property_type": prop.get("propertyType"),
            "semantic_tags": tags,
            "curies": curies,
            "confidence": item.get("confidence"),
            "source": source.get("name"),
            "source_type": source.get("type"),
            "evidence": prov.get("evidence"),
            "ols_links": ols_urls,
        }

    # ------------------------------------------------------- datasources
    def _list_datasources(self) -> dict:
        resp = requests.get(
            f"{ZOOMA_BASE}/sources",
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        raw = resp.json()
        if not isinstance(raw, list):
            raw = []
        data = [
            {
                "name": s.get("name"),
                "type": s.get("type"),
                "uri": s.get("uri"),
            }
            for s in raw
            if isinstance(s, dict)
        ]
        return {"status": "success", "data": data}


def _iri_to_curie(iri: Any) -> str | None:
    """Derive a CURIE (e.g. MONDO:0004979) from an ontology IRI/PURL."""
    if not iri or not isinstance(iri, str):
        return None
    short = iri.rstrip("/").split("/")[-1].split("#")[-1]
    if "_" in short:
        prefix, _, local = short.partition("_")
        if prefix and local:
            return f"{prefix}:{local}"
    return short or None
