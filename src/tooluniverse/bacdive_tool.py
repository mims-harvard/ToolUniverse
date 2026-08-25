# bacdive_tool.py
"""
BacDive REST API tool for ToolUniverse.

BacDive (DSMZ) is the Global Core Biodata Resource for bacterial and archaeal
strain-level phenotype data: morphology, growth conditions, physiology,
isolation source, and culture collection numbers for 100k+ strains.

ToolUniverse already covers prokaryotic taxonomy (GTDB) and metagenomes
(MGnify), but nothing describes how an organism actually grows or behaves.
BacDive fills that gap, and pairs with the culture media recipes in MediaDive.

API: https://api.bacdive.dsmz.de
No authentication required for the routes used here.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

BACDIVE_BASE_URL = "https://api.bacdive.dsmz.de"


def _first(value: Any) -> Any:
    """BacDive returns either a dict or a list of dicts per section."""
    if isinstance(value, list):
        return value[0] if value else {}
    return value if isinstance(value, dict) else {}


def _collect(value: Any) -> List[Dict[str, Any]]:
    """Normalize a section into a list of dicts."""
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    return [value] if isinstance(value, dict) else []


@register_tool("BacDiveTool")
class BacDiveTool(BaseTool):
    """
    Tool for querying BacDive bacterial strain phenotype records.

    Supports listing the strains described for a species, and retrieving one
    strain's curated phenotype: taxonomy, morphology, growth temperature and
    pH, oxygen tolerance, isolation source, and risk group.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_by_taxon"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the BacDive API call."""
        try:
            if self.operation == "search_by_taxon":
                return self._search_by_taxon(arguments)
            elif self.operation == "get_strain":
                return self._get_strain(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"BacDive request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to BacDive. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"BacDive returned HTTP {code}"}
        except ValueError:
            return {
                "status": "error",
                "error": "BacDive returned a non-JSON response",
            }
        except Exception as e:
            return {"status": "error", "error": f"Error querying BacDive: {str(e)}"}

    def _search_by_taxon(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List BacDive strain IDs described for a genus or species."""
        genus = arguments.get("genus")
        if not genus:
            return {
                "status": "error",
                "error": "genus is required, e.g. 'Bacillus'. "
                "Optionally add species, e.g. species='subtilis'.",
            }

        species = arguments.get("species")
        path = f"{genus.strip()}/{species.strip()}" if species else genus.strip()
        url = f"{BACDIVE_BASE_URL}/taxon/{path}"

        response = requests.get(url, timeout=self.timeout)
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No BacDive entries for taxon '{path}'. "
                "Check spelling and capitalization (genus is capitalized).",
            }
        response.raise_for_status()
        raw = response.json()

        results = raw.get("results")
        strain_ids: List[Any] = []
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    strain_ids.extend(item.values())
                else:
                    strain_ids.append(item)
        elif isinstance(results, dict):
            strain_ids = list(results.values())

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        def _sid(v: Any) -> Any:
            if isinstance(v, str) and "/" in v:
                return v.rstrip("/").rsplit("/", 1)[-1]
            return v

        ids = [_sid(v) for v in strain_ids][:limit]

        return {
            "status": "success",
            "data": [{"bacdive_id": i} for i in ids],
            "metadata": {
                "taxon": path,
                "total_matching": raw.get("count"),
                "returned": len(ids),
                "next_page": raw.get("next"),
                "note": "Pass a bacdive_id to BacDive_get_strain for phenotype detail.",
                "source": "BacDive (DSMZ)",
            },
        }

    def _get_strain(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve one strain's curated phenotype record."""
        bacdive_id = arguments.get("bacdive_id")
        if bacdive_id is None or str(bacdive_id).strip() == "":
            return {
                "status": "error",
                "error": "bacdive_id is required, e.g. 24493. "
                "Use BacDive_search_by_taxon to find IDs for a species.",
            }

        url = f"{BACDIVE_BASE_URL}/fetch/{str(bacdive_id).strip()}"
        response = requests.get(url, timeout=self.timeout)
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No BacDive strain with ID '{bacdive_id}'.",
            }
        response.raise_for_status()
        raw = response.json()

        results = raw.get("results") or {}
        record = _first(list(results.values())) if results else {}
        if not record:
            return {
                "status": "error",
                "error": f"BacDive returned no record body for ID '{bacdive_id}'.",
            }

        general = _first(record.get("General"))
        taxonomy = _first(record.get("Name and taxonomic classification"))
        lpsn = _first(taxonomy.get("LPSN")) if taxonomy else {}
        morphology = _first(record.get("Morphology"))
        culture = record.get("Culture and growth conditions") or {}
        physiology = record.get("Physiology and metabolism") or {}
        isolation = (
            record.get("Isolation, sampling and environmental information") or {}
        )
        safety = _first(record.get("Safety information"))

        temperatures = [
            {
                "temperature": t.get("temperature"),
                "growth": t.get("growth"),
                "type": t.get("type"),
            }
            for t in _collect(culture.get("culture temp"))
        ]
        media = [
            {"name": m.get("name"), "growth": m.get("growth")}
            for m in _collect(culture.get("culture medium"))
        ]
        oxygen = [
            o.get("oxygen tolerance")
            for o in _collect(physiology.get("oxygen tolerance"))
        ]

        return {
            "status": "success",
            "data": {
                "bacdive_id": general.get("BacDive-ID"),
                "description": general.get("description"),
                "keywords": general.get("keywords") or [],
                "dsm_number": general.get("DSM-Number"),
                "domain": lpsn.get("domain"),
                "phylum": lpsn.get("phylum"),
                "class": lpsn.get("class"),
                "order": lpsn.get("order"),
                "family": lpsn.get("family"),
                "genus": taxonomy.get("genus"),
                "species": taxonomy.get("species"),
                "strain_designation": taxonomy.get("strain designation"),
                "type_strain": taxonomy.get("type strain"),
                "cell_morphology": _first(morphology.get("cell morphology")),
                "gram_stain": _first(morphology.get("cell morphology")).get(
                    "gram stain"
                ),
                "culture_temperatures": temperatures,
                "culture_media": media,
                "oxygen_tolerance": [o for o in oxygen if o],
                "isolation_source": _first(isolation.get("isolation")).get(
                    "sample type"
                ),
                "risk_group": safety.get("biosafety level")
                or safety.get("Risk group"),
            },
            "metadata": {
                "bacdive_id": bacdive_id,
                "sections_available": sorted(record.keys()),
                "source": "BacDive (DSMZ) — Global Core Biodata Resource",
            },
        }
