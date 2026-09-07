# biothings_gateway_tool.py
"""
BioThings API gateway tool for ToolUniverse.

The BioThings platform hosts ~50 biomedical APIs behind one uniform
interface: every API answers /query, /metadata, and a typed annotation
route. ToolUniverse already wraps four of them individually (MyGene,
MyVariant, MyChem, MyDisease); this gateway reaches the rest without
needing a bespoke tool class per API.

The APIs it opens up that had no ToolUniverse coverage include DDInter
(drug-drug interactions), repoDB (drug repurposing), IDISK (dietary
supplements), TTD (Therapeutic Target Database), GMMAD2 (gut
microbiota-disease), denovo-db, BioMuta, PFOCR, SEMMEDDB, Disbiome,
InnateDB, CCLE, PheWAS, KAVIAR, and SuppKG.

Several hosted APIs duplicate dedicated ToolUniverse tools (ChEBI, GO,
HPO, MONDO, DOID, Rhea, DGIdb, BindingDB, PubTator3, FooDB). Those are
reachable here for uniformity, but the dedicated tools are richer and
should be preferred; BioThings_list_apis flags them.

API: https://biothings.transltr.io/{api}
No authentication required.
"""

import difflib

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

BIOTHINGS_BASE_URL = "https://biothings.transltr.io"


def quote(value: str) -> str:
    """Percent-encode an identifier for use in a URL path segment."""
    return requests.utils.quote(value, safe="")


# api slug -> (short description, name of a preferred dedicated TU tool or "")
BIOTHINGS_APIS: Dict[str, Any] = {
    # --- no dedicated ToolUniverse coverage ---
    "ddinter": ("Drug-drug interactions with severity level", ""),
    "repodb": ("Drug repurposing: approved/failed indications with trial status", ""),
    "idisk": ("Integrated Dietary Supplement Knowledgebase", ""),
    "ttd": ("Therapeutic Target Database associations", ""),
    "gmmad2": ("Gut microbiota-disease associations", ""),
    "disbiome": ("Microbiome composition changes in disease", ""),
    "denovodb": ("De novo variants from sequencing studies", ""),
    "biomuta": ("Cancer mutations mapped to protein positions", ""),
    "ccle": ("Cancer Cell Line Encyclopedia profiles", ""),
    "kaviar": ("Known VARiants: aggregated human variant catalog", ""),
    "phewas": ("Phenome-wide association study results", ""),
    "pfocr": ("Pathway figures mined from literature by OCR", ""),
    "semmeddb": ("SemMedDB: predications mined from PubMed abstracts", ""),
    "suppkg": ("Dietary supplement knowledge graph", ""),
    "mrcoc": ("MeSH co-occurrence counts across the literature", ""),
    "innatedb": ("Innate immunity interactions and pathways", ""),
    "gtrx": ("Genetic Testing Registry treatable rare disease evidence", ""),
    "mabs": ("Monoclonal antibody target associations", ""),
    "tissues": ("Tissue expression associations", ""),
    "agr": ("Alliance of Genome Resources model organism data", ""),
    "diseases": ("DISEASES: text-mined gene-disease associations", ""),
    "ebigene2phenotype": ("EBI gene-to-phenotype curated associations", ""),
    "mgigene2phenotype": ("MGI mouse gene-to-phenotype associations", ""),
    "rare_source": ("RARe-SOURCE rare disease gene annotations", ""),
    "pseudocap_go": ("Pseudomonas aeruginosa GO annotations", ""),
    "upheno_ontology": ("uPheno cross-species phenotype mappings", ""),
    "bioplanet_pathway_gene": ("BioPlanet pathway-gene memberships", ""),
    "bioplanet_pathway_disease": ("BioPlanet pathway-disease associations", ""),
    "text_mining_targeted_association": ("Text-mined targeted associations", ""),
    "biggim_drugresponse_kp": ("BigGIM drug response knowledge provider", ""),
    "multiomics_wellness_kp": ("Multiomics wellness knowledge provider", ""),
    "multiomics_ehr_risk_kp": ("Multiomics EHR risk knowledge provider", ""),
    # --- duplicates of dedicated ToolUniverse tools; prefer those ---
    "chebi": ("Chemical entities of biological interest", "ChEBI_* tools"),
    "go": ("Gene Ontology terms", "GO_* / QuickGO_* tools"),
    "go_bp": ("GO biological process branch", "GO_* / QuickGO_* tools"),
    "go_cc": ("GO cellular component branch", "GO_* / QuickGO_* tools"),
    "go_mf": ("GO molecular function branch", "GO_* / QuickGO_* tools"),
    "hpo": ("Human Phenotype Ontology terms", "HPO_* tools"),
    "mondo": ("MONDO disease ontology", "MONDO_* tools"),
    "doid": ("Human Disease Ontology", "DiseaseOntology_* tools"),
    "ncit": ("NCI Thesaurus concepts", "NCIThesaurus_* tools"),
    "uberon": ("UBERON anatomy ontology", "ols_* tools"),
    "cell_ontology": ("Cell Ontology terms", "ols_* tools"),
    "rhea": ("Rhea biochemical reactions", "Rhea_* tools"),
    "dgidb": ("Drug-gene interactions", "DGIdb_* tools"),
    "bindingdb": ("Binding affinity measurements", "BindingDB_* tools"),
    "fda_drugs": ("FDA drug product records", "OpenFDA_* / FDA_* tools"),
    "foodb": ("FooDB food constituent records", "FooDB_* tools"),
    "fooddata": ("USDA FoodData Central", "FoodDataCentral_* tools"),
    "pubtator3": ("PubTator3 literature annotations", "PubTator_* tools"),
}


@register_tool("BioThingsGatewayTool")
class BioThingsGatewayTool(BaseTool):
    """
    Tool for querying any BioThings-hosted biomedical API.

    Supports listing the available APIs, full-text and fielded search,
    entity retrieval by identifier, and field/statistics introspection.

    No authentication required.
    """

    _biothing_types: Dict[str, str] = {}

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get("operation", "query")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the BioThings API call."""
        try:
            if self.operation == "list_apis":
                return self._list_apis(arguments)
            if self.operation == "query":
                return self._query(arguments)
            if self.operation == "get_entity":
                return self._get_entity(arguments)
            if self.operation == "get_metadata":
                return self._get_metadata(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"BioThings request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to BioThings. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"BioThings returned HTTP {code}"}
        except ValueError:
            return {
                "status": "error",
                "error": "BioThings returned a non-JSON response",
            }
        except Exception as e:
            return {"status": "error", "error": f"Error querying BioThings: {str(e)}"}

    def _validate_api(self, api: Any) -> Any:
        """Return an error dict if the api slug is missing or unknown."""
        if not api:
            return {
                "status": "error",
                "error": "api is required, e.g. 'ddinter'. "
                "Use BioThings_list_apis to see the available APIs.",
            }
        if api not in BIOTHINGS_APIS:
            # Substring first (partial names), then fuzzy (typos).
            close = [k for k in BIOTHINGS_APIS if api.lower() in k]
            if not close:
                close = difflib.get_close_matches(
                    api.lower(), BIOTHINGS_APIS, n=5, cutoff=0.6
                )
            hint = f" Did you mean: {', '.join(close[:5])}?" if close else ""
            return {
                "status": "error",
                "error": f"Unknown BioThings API '{api}'.{hint} "
                "Use BioThings_list_apis to see all available APIs.",
            }
        return None

    def _list_apis(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List the BioThings APIs reachable through this gateway."""
        keyword = arguments.get("keyword")
        only_unique = arguments.get("only_without_dedicated_tool")

        rows: List[Dict[str, Any]] = []
        for slug, (desc, dedicated) in sorted(BIOTHINGS_APIS.items()):
            if only_unique and dedicated:
                continue
            if keyword:
                kw = keyword.lower()
                if kw not in slug.lower() and kw not in desc.lower():
                    continue
            rows.append(
                {
                    "api": slug,
                    "description": desc,
                    "preferred_tooluniverse_tool": dedicated or None,
                }
            )

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "returned": len(rows),
                "total_apis": len(BIOTHINGS_APIS),
                "note": "APIs with preferred_tooluniverse_tool set are also covered "
                "by richer dedicated tools; prefer those.",
                "source": "BioThings (Su Lab / NCATS Translator)",
            },
        }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search one BioThings API with an Elasticsearch-style query."""
        api = arguments.get("api")
        invalid = self._validate_api(api)
        if invalid:
            return invalid

        q = arguments.get("q")
        if not q:
            return {
                "status": "error",
                "error": "q is required. Use '*' for everything, a bare term for "
                "full-text search, or a fielded query such as "
                "'subject.name:aspirin'. Use BioThings_get_metadata to see "
                "the available fields for an API.",
            }

        size = arguments.get("size")
        if not isinstance(size, int) or size <= 0:
            size = 10
        size = min(size, 100)

        params: Dict[str, Any] = {"q": q, "size": size}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]
        skip = arguments.get("skip")
        if isinstance(skip, int) and skip > 0:
            params["from"] = skip

        url = f"{BIOTHINGS_BASE_URL}/{api}/query"
        response = requests.get(url, params=params, timeout=self.timeout)
        if response.status_code == 400:
            return {
                "status": "error",
                "error": f"BioThings rejected the query '{q}' for API '{api}'. "
                "Check the field names with BioThings_get_metadata.",
            }
        response.raise_for_status()
        raw = response.json()

        hits = raw.get("hits") if isinstance(raw, dict) else None
        return {
            "status": "success",
            "data": hits if isinstance(hits, list) else [],
            "metadata": {
                "api": api,
                "query": q,
                "total_matching": raw.get("total") if isinstance(raw, dict) else None,
                "returned": len(hits) if isinstance(hits, list) else 0,
                "took_ms": raw.get("took") if isinstance(raw, dict) else None,
                "source": f"BioThings {api}",
            },
        }

    def _resolve_biothing_type(self, api: str) -> str:
        """Look up (and cache) the annotation route segment for an API."""
        if api in self._biothing_types:
            return self._biothing_types[api]
        response = requests.get(
            f"{BIOTHINGS_BASE_URL}/{api}/metadata", timeout=self.timeout
        )
        response.raise_for_status()
        meta = response.json()
        btype = meta.get("biothing_type") if isinstance(meta, dict) else ""
        self._biothing_types[api] = btype or ""
        return self._biothing_types[api]

    def _get_entity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one record by its BioThings _id."""
        api = arguments.get("api")
        invalid = self._validate_api(api)
        if invalid:
            return invalid

        entity_id = arguments.get("entity_id")
        if not entity_id:
            return {
                "status": "error",
                "error": "entity_id is required. IDs come from the _id field of "
                "BioThings_query results, e.g. 'MONDO:0010329'.",
            }

        entity_id = str(entity_id).strip()
        biothing_type = self._resolve_biothing_type(api)

        if biothing_type:
            url = f"{BIOTHINGS_BASE_URL}/{api}/{biothing_type}/{quote(entity_id)}"
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return {
                    "status": "success",
                    "data": response.json(),
                    "metadata": {
                        "api": api,
                        "entity_id": entity_id,
                        "biothing_type": biothing_type,
                        "source": f"BioThings {api}",
                    },
                }

        # Fall back to an _id query, which works regardless of route shape.
        response = requests.get(
            f"{BIOTHINGS_BASE_URL}/{api}/query",
            params={"q": f'_id:"{entity_id}"', "size": 1},
            timeout=self.timeout,
        )
        response.raise_for_status()
        hits = (response.json() or {}).get("hits") or []
        if not hits:
            return {
                "status": "error",
                "error": f"No record with _id '{entity_id}' in BioThings API "
                f"'{api}'. IDs come from the _id field of query results.",
            }

        return {
            "status": "success",
            "data": hits[0],
            "metadata": {
                "api": api,
                "entity_id": entity_id,
                "biothing_type": biothing_type or None,
                "retrieved_via": "_id query fallback",
                "source": f"BioThings {api}",
            },
        }

    def _get_metadata(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Describe an API: record counts, build date, and queryable fields."""
        api = arguments.get("api")
        invalid = self._validate_api(api)
        if invalid:
            return invalid

        meta_response = requests.get(
            f"{BIOTHINGS_BASE_URL}/{api}/metadata", timeout=self.timeout
        )
        meta_response.raise_for_status()
        meta = meta_response.json() or {}

        fields: List[str] = []
        if arguments.get("include_fields"):
            fields_response = requests.get(
                f"{BIOTHINGS_BASE_URL}/{api}/metadata/fields", timeout=self.timeout
            )
            if fields_response.status_code == 200:
                payload = fields_response.json()
                if isinstance(payload, dict):
                    fields = sorted(payload.keys())

        return {
            "status": "success",
            "data": {
                "api": api,
                "description": BIOTHINGS_APIS[api][0],
                "biothing_type": meta.get("biothing_type"),
                "build_date": meta.get("build_date"),
                "build_version": meta.get("build_version"),
                "stats": meta.get("stats"),
                "sources": list((meta.get("src") or {}).keys()),
                "queryable_fields": fields,
            },
            "metadata": {
                "api": api,
                "field_count": len(fields),
                "source": f"BioThings {api}",
            },
        }
