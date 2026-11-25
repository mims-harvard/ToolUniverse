# depmap_tool.py
"""
DepMap (Dependency Map) API tool for ToolUniverse.

DepMap provides cancer cell line dependency data from CRISPR knockout screens,
drug sensitivity data, and multi-omics characterization of cancer cell lines.

Data includes:
- CRISPR gene effect scores (gene essentiality)
- Drug sensitivity data
- Cell line metadata (lineage, mutations)
- Gene expression data

API Documentation: https://depmap.sanger.ac.uk/documentation/api/
Base URL: https://api.cellmodelpassports.sanger.ac.uk
"""

import re

import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for Sanger Cell Model Passports API
DEPMAP_BASE_URL = "https://api.cellmodelpassports.sanger.ac.uk"

# One request returns every CRISPR knockout record of a gene at this page
# size. _CRISPR_MAX_PAGES stops the loop if the API ever pages without end.
_CRISPR_PAGE_SIZE = 2000
_CRISPR_MAX_PAGES = 10


def _model_key(name: Any) -> str:
    """A model id or name without case and punctuation ('HCT-116' -> 'hct116')."""
    return re.sub(r"[^0-9a-z]", "", str(name).lower())


def _gene_symbol(item: Dict[str, Any]) -> str:
    """Uppercased gene symbol used as the sort key of the /genes catalog."""
    return item.get("attributes", {}).get("symbol", "").upper()


@register_tool("DepMapTool")
class DepMapTool(BaseTool):
    """
    Tool for querying DepMap/Sanger Cell Model Passports API.

    Provides access to:
    - Cancer cell line dependency data (CRISPR screens)
    - Drug sensitivity profiles
    - Cell line metadata and annotations
    - Gene effect scores for target validation

    No authentication required for non-commercial use.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_cell_lines"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DepMap API call."""
        operation = self.operation

        if operation == "get_cell_lines":
            return self._get_cell_lines(arguments)
        elif operation == "get_cell_line":
            return self._get_cell_line(arguments)
        elif operation == "search_cell_lines":
            return self._search_cell_lines(arguments)
        elif operation == "get_gene_dependencies":
            return self._get_gene_dependencies(arguments)
        elif operation == "get_drug_response":
            return self._get_drug_response(arguments)
        elif operation == "search_genes":
            return self._search_genes(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    @staticmethod
    def _parse_model_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Map a JSON:API /models response's ``data`` array to model rows.

        The row was {model_id, model_name}. A /models list item carries 24
        attributes, and the ones that were dropped are what the tool's own
        description means by "for target validation studies": whether the
        line has CRISPR knockout data at all, and expression, mutation,
        RNA-seq, CNV, methylation, proteomics, fusion and drug-response
        data. PK-59 is crispr_ko_available false and mutations_available
        true, and a caller planning a knockout screen could not see either.

        Its measured characteristics went too: mutations_per_mb 24.79 is the
        tumour mutational burden, ploidy_wes 3.51 the ploidy, model_type
        says cell line against organoid, and growth_properties adherent
        against suspension.

        tissue and cancer_type genuinely are not on this resource -- they
        live on related sample/patient resources, one request per model --
        which is why they are absent here and why DepMap_get_cell_line
        exists.
        """
        availability_keys = (
            "crispr_ko",
            "expression",
            "mutations",
            "rnaseq",
            "cnv",
            "methylation",
            "proteomics",
            "fusions",
            "drugs",
        )
        models = []
        for item in data.get("data", []):
            attributes = item.get("attributes", {}) or {}
            names = attributes.get("names")
            models.append(
                {
                    "model_id": item.get("id"),
                    "model_name": names[0] if names else None,
                    "model_names": [n for n in (names or []) if n],
                    "model_type": attributes.get("model_type"),
                    "growth_properties": attributes.get("growth_properties"),
                    "model_treatment": attributes.get("model_treatment"),
                    "mutations_per_mb": attributes.get("mutations_per_mb"),
                    "ploidy_wes": attributes.get("ploidy_wes"),
                    "ploidy_wgs": attributes.get("ploidy_wgs"),
                    "ploidy": attributes.get("ploidy"),
                    "pubmed_id": attributes.get("pmed"),
                    "doi": attributes.get("doi"),
                    "comment": attributes.get("comment"),
                    "commercially_available": attributes.get("commercial_available"),
                    # Which assays exist for the line, which is the question a
                    # target-validation screen starts from.
                    "data_available": {
                        key: attributes.get(f"{key}_available")
                        for key in availability_keys
                    },
                }
            )
        return models

    def _get_cell_lines(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get list of cancer cell lines with metadata.

        Filter by tissue type or cancer type.
        """
        tissue = arguments.get("tissue")
        cancer_type = arguments.get("cancer_type")
        page_size = arguments.get("page_size", 20)

        try:
            # Fix-R19C-3: `filter[model]` on this endpoint doesn't
            # actually filter (confirmed live across multiple syntax
            # variants -- filtered and unfiltered requests return
            # identical results and the identical total count), and
            # `model_name`/`tissue`/`cancer_type`/`sample_site`/`gender`/
            # `ethnicity` aren't real attributes on the model resource at
            # all (only `names`, a list; the rest live on related sample/
            # tissue/cancer_type/patient resources, reachable per-model
            # via `include=`, which isn't practical for a whole page of
            # results without an N+1 request per row). Rather than
            # silently accepting a tissue/cancer_type filter and
            # returning unfiltered results, warn that filtering isn't
            # currently supported by the upstream API; model_name is
            # fixed since it's cheap (no extra request needed).
            url = f"{DEPMAP_BASE_URL}/models"
            params = {"page[size]": min(page_size, 100)}
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Parse cell line data. tissue/cancer_type/sample_site/gender/
            # ethnicity are not attributes on /models list items at all
            # (they live on each item's related sample/patient resources,
            # only resolvable one model at a time via DepMap_get_cell_line)
            # -- left unset here rather than reading nonexistent keys.
            cell_lines = self._parse_model_list(data)

            result = {
                "status": "success",
                "data": {
                    "cell_lines": cell_lines,
                    "count": len(cell_lines),
                    "total": data.get("meta", {}).get("count", len(cell_lines)),
                },
            }
            # The Cell Model Passports /models endpoint does not support
            # server-side tissue/cancer_type filtering (confirmed live:
            # every filter[...] syntax tried -- filter[model], filter[
            # tissue.name], filter[sample.tissue.name], bare tissue=/
            # cancer_type= -- returned the identical unfiltered page).
            # Say so explicitly instead of silently ignoring the filter.
            if tissue or cancer_type:
                result["metadata"] = {
                    "note": (
                        "The upstream API does not support server-side "
                        "tissue/cancer_type filtering on this endpoint; "
                        "results above are unfiltered. Use "
                        "DepMap_search_cell_lines by name, or "
                        "DepMap_get_cell_line per model_id to check its "
                        "tissue/cancer_type."
                    )
                }
            return result
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_cell_line(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed information for a specific cell line.

        Returns metadata, mutations, and available data types.
        """
        model_id = arguments.get("model_id")
        model_name = arguments.get("model_name")

        if not model_id and not model_name:
            return {
                "status": "error",
                "error": "Either model_id or model_name is required",
            }

        try:
            if model_id:
                url = f"{DEPMAP_BASE_URL}/models/{model_id}"
            else:
                # Search by name first
                search_result = self._search_cell_lines({"query": model_name})
                if (
                    search_result["status"] != "success"
                    or not search_result["data"]["cell_lines"]
                ):
                    return {
                        "status": "success",
                        "data": None,
                        "message": f"Cell line '{model_name}' not found",
                    }
                model_id = search_result["data"]["cell_lines"][0]["model_id"]
                url = f"{DEPMAP_BASE_URL}/models/{model_id}"

            # tissue/cancer_type/sample_site/tissue_status/age_at_sampling/
            # gender/ethnicity/msi_status are not attributes on the model
            # resource itself -- they live on related sample/patient/
            # model_msi_status resources (confirmed live via the API's own
            # /models/{id} response, which has none of these fields).
            # `include` pulls all of them in with this one request instead
            # of a separate round-trip per relationship.
            params = {
                "include": "sample,sample.tissue,sample.cancer_type,sample.patient,model_msi_status"
            }
            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"Cell line not found: {model_id or model_name}",
                }

            response.raise_for_status()
            data = response.json()

            item = data.get("data", {})
            attrs = item.get("attributes", {})
            # `id` comes back as a string for most included types (e.g.
            # sample, patient) but as an int for lookup-table types like
            # tissue/cancer_type (confirmed live) -- normalize to str so
            # the two sides of the (type, id) key always match.
            included_by_key = {
                (inc.get("type"), str(inc.get("id"))): inc
                for inc in data.get("included", [])
                if isinstance(inc, dict)
            }

            def _resolve(node: Dict[str, Any], rel_name: str) -> Dict[str, Any]:
                """Follow a to-one relationship from a JSON:API resource
                object to its included resource object (or {} if absent)."""
                rel = (node.get("relationships") or {}).get(rel_name, {}).get("data")
                if isinstance(rel, list):
                    rel = rel[0] if rel else None
                if not isinstance(rel, dict):
                    return {}
                return included_by_key.get((rel.get("type"), str(rel.get("id"))), {})

            sample = _resolve(item, "sample")
            sample_attrs = sample.get("attributes", {})
            tissue_attrs = _resolve(sample, "tissue").get("attributes", {})
            cancer_type_attrs = _resolve(sample, "cancer_type").get("attributes", {})
            patient_attrs = _resolve(sample, "patient").get("attributes", {})
            msi_attrs = _resolve(item, "model_msi_status").get("attributes", {})
            names = attrs.get("names")

            return {
                "status": "success",
                "data": {
                    "model_id": item.get("id"),
                    "model_name": names[0] if names else None,
                    "tissue": tissue_attrs.get("name"),
                    "cancer_type": cancer_type_attrs.get("name"),
                    "tissue_status": sample_attrs.get("tissue_status"),
                    "sample_site": sample_attrs.get("sample_site"),
                    "gender": patient_attrs.get("gender"),
                    "ethnicity": patient_attrs.get("ethnicity"),
                    "age_at_sampling": sample_attrs.get("age_at_sampling"),
                    "growth_properties": attrs.get("growth_properties"),
                    "msi_status": msi_attrs.get("msi_status"),
                    "ploidy": attrs.get("ploidy"),
                    "mutational_burden": attrs.get("mutations_per_mb"),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _find_catalog_page(
        self,
        url: str,
        params: Dict[str, Any],
        query_upper: str,
        symbol_of,
        request_timeout: int,
    ) -> tuple[List[Dict[str, Any]], int | None, int]:
        """Binary-search a symbol-sorted, paginated JSON:API catalog for the
        single page that could contain ``query_upper``.

        ``params`` must already request page 1 (``page[number]=1``) with the
        desired ``sort`` and ``page[size]``; it is mutated in place as pages
        are visited. ``symbol_of(item)`` returns an item's uppercased sort
        symbol. Returns that page's list of resource items, or ``[]`` if the
        query sorts outside the whole catalog.

        Comparing the query against each page's first/last symbol (rather
        than scanning linearly from page 1) keeps the cost to
        ~log2(total_pages) round-trips over the full catalog. ``fetched_page``
        is tracked so re-examining the current page reuses the data already in
        hand instead of refetching (which would also risk stale data).
        """
        page_size = params["page[size]"]
        response = requests.get(url, params=params, timeout=request_timeout)
        response.raise_for_status()
        first_data = response.json()
        total_count = first_data.get("meta", {}).get("count", 0)
        total_pages = max(1, -(-total_count // page_size))  # ceil division

        page_items = first_data.get("data", [])
        fetched_page = 1
        lo, hi = 1, total_pages
        while lo <= hi:
            mid = (lo + hi) // 2
            if mid != fetched_page:
                params["page[number]"] = mid
                response = requests.get(url, params=params, timeout=request_timeout)
                response.raise_for_status()
                page_items = response.json().get("data", [])
                fetched_page = mid
            if not page_items:
                hi = mid - 1
                continue
            if query_upper < symbol_of(page_items[0]):
                hi = mid - 1
            elif query_upper > symbol_of(page_items[-1]):
                lo = mid + 1
            else:
                return page_items, fetched_page, total_pages
        return [], None, total_pages

    def _search_cell_lines(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search cell lines by name or identifier.
        """
        query = arguments.get("query")

        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            # The Cell Model Passports API silently ignores filter[model]
            # on /models (confirmed live: any query, including nonsense
            # strings, returned the same unfiltered first page). The real
            # name-search endpoint is /search/models?q=... . Confirmed live
            # this endpoint's own result order is NOT exact-match-first
            # (e.g. q=HCC38 returns "HCC38-BL" before the exact "HCC38"
            # match) -- DepMap_get_cell_line's by-name lookup relies on
            # cell_lines[0], so re-sort client-side with exact matches
            # first rather than trusting upstream order.
            url = f"{DEPMAP_BASE_URL}/search/models"
            params = {"q": query, "page[size]": 20}

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            query_upper = query.upper()
            cell_lines = []
            for item in data.get("data", []):
                names = item.get("attributes", {}).get("names") or []
                name = names[0] if names else None
                if name:
                    cell_lines.append(
                        {
                            "model_id": item.get("id"),
                            "model_name": name,
                            "exact_match": name.upper() == query_upper,
                        }
                    )
            cell_lines.sort(key=lambda c: (not c["exact_match"], c["model_name"]))

            return {
                "status": "success",
                "data": {
                    "query": query,
                    "cell_lines": cell_lines,
                    "count": len(cell_lines),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _fetch_crispr_ko(self, gene_id: str) -> Dict[str, Any]:
        """All CRISPR knockout records of one gene, with their models.

        ``/genes/{id}/datasets/crispr_ko`` holds one record per screen of a
        model (cell line or organoid). The model name, tissue and cancer type
        come in the same response through ``include``. One page of 2000
        covers every gene today (KRAS has 1,269 records); the loop reads
        further pages if a gene ever has more, and ``reported`` lets the
        caller see a short read.
        """
        url = f"{DEPMAP_BASE_URL}/genes/{gene_id}/datasets/crispr_ko"
        params: Dict[str, Any] = {
            "page[size]": _CRISPR_PAGE_SIZE,
            "page[number]": 1,
            "include": "model,model.sample.tissue,model.sample.cancer_type",
            "fields[model]": "names,model_type,sample",
            "fields[sample]": "tissue,cancer_type",
            "fields[tissue]": "name",
            "fields[cancer_type]": "name",
        }
        records: List[Dict[str, Any]] = []
        included: Dict[tuple, Dict[str, Any]] = {}
        reported: Optional[int] = None
        while True:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            page = payload.get("data") or []
            records.extend(page)
            for inc in payload.get("included") or []:
                included[(inc.get("type"), str(inc.get("id")))] = inc
            count = (payload.get("meta") or {}).get("count")
            if isinstance(count, int):
                reported = count
            if reported is not None:
                complete = len(records) >= reported
            else:
                complete = len(page) < _CRISPR_PAGE_SIZE
            if not page or complete or params["page[number]"] >= _CRISPR_MAX_PAGES:
                break
            params["page[number]"] += 1
        return {"records": records, "included": included, "reported": reported}

    @staticmethod
    def _crispr_rows(fetched: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Flatten CRISPR knockout records into rows, most dependent first."""
        included = fetched["included"]

        def _linked(node: Dict[str, Any], rel_name: str) -> Dict[str, Any]:
            rel = ((node.get("relationships") or {}).get(rel_name) or {}).get("data")
            if not isinstance(rel, dict):
                return {}
            return included.get((rel.get("type"), str(rel.get("id"))), {})

        rows = []
        for record in fetched["records"]:
            attrs = record.get("attributes") or {}
            model_ref = ((record.get("relationships") or {}).get("model") or {}).get(
                "data"
            ) or {}
            model = _linked(record, "model")
            sample = _linked(model, "sample")
            names = (model.get("attributes") or {}).get("names") or []
            bf_scaled = attrs.get("bf_scaled")
            rows.append(
                {
                    "model_id": model_ref.get("id"),
                    "model_name": names[0] if names else None,
                    "model_names": names,
                    "model_type": (model.get("attributes") or {}).get("model_type"),
                    "tissue": (_linked(sample, "tissue").get("attributes") or {}).get(
                        "name"
                    ),
                    "cancer_type": (
                        _linked(sample, "cancer_type").get("attributes") or {}
                    ).get("name"),
                    "source": attrs.get("source"),
                    "bf_scaled": bf_scaled,
                    "bf": attrs.get("bf"),
                    "fc_clean_qn": attrs.get("fc_clean_qn"),
                    "qc_pass": attrs.get("qc_pass"),
                    "loss_of_fitness": (bf_scaled < 0)
                    if isinstance(bf_scaled, (int, float))
                    else None,
                }
            )
        rows.sort(
            key=lambda r: (
                r["bf_scaled"] is None,
                r["bf_scaled"] if r["bf_scaled"] is not None else 0,
                str(r["model_id"]),
                str(r["source"]),
            )
        )
        return rows

    @staticmethod
    def _crispr_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Counts over every screen of the gene, before any model filter."""

        def _count(part: List[Dict[str, Any]]) -> Dict[str, Any]:
            scored = [r for r in part if r["loss_of_fitness"] is not None]
            hits = sum(1 for r in scored if r["loss_of_fitness"])
            return {
                "screens": len(part),
                "loss_of_fitness_screens": hits,
                "loss_of_fitness_fraction": round(hits / len(scored), 3)
                if scored
                else None,
            }

        summary = _count(rows)
        summary["models"] = len({r["model_id"] for r in rows})
        summary["by_source"] = {
            source: _count([r for r in rows if r["source"] == source])
            for source in sorted({str(r["source"]) for r in rows})
        }
        return summary

    def _get_gene_dependencies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the CRISPR knockout fitness scores of a gene, one row per screen.

        The scores come from /genes/{id}/datasets/crispr_ko: Sanger (Project
        Score) and Broad screens processed by the Sanger pipeline. bf_scaled
        is the scaled Bayes factor of the screen; below 0 the knockout causes
        a significant loss of fitness in that model. This is not the Chronos
        gene effect of depmap.org, and -0.5 is not its threshold.
        """
        gene_symbol = arguments.get("gene_symbol")
        model_filter = str(arguments.get("model_id") or "").strip()

        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol parameter is required"}

        try:
            limit = arguments.get("limit")
            limit = 50 if limit is None else int(limit)
            offset = int(arguments.get("offset") or 0)
        except (TypeError, ValueError):
            return {"status": "error", "error": "limit and offset must be integers"}
        if not 1 <= limit <= 500:
            return {"status": "error", "error": "limit must be between 1 and 500"}
        if offset < 0:
            return {"status": "error", "error": "offset must be 0 or more"}

        try:
            # Use DepMap_search_genes internally for reliable matching
            search_result = self._search_genes({"query": gene_symbol})

            if search_result.get("status") != "success":
                return search_result

            genes = search_result.get("data", {}).get("genes", [])
            exact_matches = [g for g in genes if g.get("exact_match")]
            matched_gene = exact_matches[0] if exact_matches else None

            if matched_gene is None and genes:
                # No exact match — report candidates
                return {
                    "status": "success",
                    "data": {
                        "gene_symbol": gene_symbol,
                        "exact_match": None,
                        "candidates": genes[:5],
                        "warning": (
                            f"No exact match for '{gene_symbol}'. "
                            f"Similar: {[g['symbol'] for g in genes[:5]]}. "
                            "Use DepMap_search_genes for disambiguation."
                        ),
                    },
                }

            if matched_gene is None:
                return {
                    "status": "success",
                    "data": {
                        "gene_symbol": gene_symbol,
                        "exact_match": None,
                        "message": (
                            f"Gene '{gene_symbol}' not found in DepMap. "
                            "The Sanger Cell Model Passports API has "
                            "limited gene search capabilities."
                        ),
                    },
                }

            fetched = self._fetch_crispr_ko(matched_gene["gene_id"])
            rows = self._crispr_rows(fetched)
            symbol = matched_gene.get("symbol") or gene_symbol
            data: Dict[str, Any] = {
                "gene_symbol": gene_symbol,
                "matched_gene": matched_gene,
                "summary": self._crispr_summary(rows),
            }

            reported = fetched["reported"]
            if reported is not None and reported != len(rows):
                data["warning"] = (
                    f"The API reported {reported} CRISPR knockout records for "
                    f"{symbol} and returned {len(rows)}. The summary and the "
                    "scores cover only the returned records."
                )

            matched = rows
            if model_filter:
                # Case and punctuation are ignored: 'HCT116' finds 'HCT-116'.
                wanted = _model_key(model_filter)
                matched = [
                    r
                    for r in rows
                    if _model_key(r["model_id"]) == wanted
                    or wanted in [_model_key(n) for n in r["model_names"]]
                ]
                if rows and not matched:
                    return self._no_screen_for_model(model_filter, symbol, len(rows))

            page = matched[offset : offset + limit]
            has_more = offset + len(page) < len(matched)
            if not rows:
                note = (
                    f"{symbol} is in the gene catalog and has no CRISPR knockout "
                    "record. A gene that the screening libraries do not target "
                    "has none. This is not a measurement, so it does not show "
                    "that the gene is non-essential."
                )
            else:
                note = (
                    "One row per screen of a model, most dependent first. "
                    "bf_scaled is the scaled Bayes factor: below 0 the knockout "
                    "causes a significant loss of fitness in that model "
                    "(loss_of_fitness true), 0 or above it does not. fc_clean_qn "
                    "is the corrected log fold change of the guides: more "
                    "negative is stronger depletion. These are Sanger-pipeline "
                    "scores, not the Chronos gene effect of depmap.org, so the "
                    "-0.5 Chronos threshold does not apply. A model screened by "
                    "both Sanger and Broad has two rows."
                )
            data.update(
                {
                    "model_filter": model_filter or None,
                    "scores": [
                        {k: v for k, v in r.items() if k != "model_names"} for r in page
                    ],
                    "count": len(page),
                    "total_scores": len(matched),
                    "offset": offset,
                    "limit": limit,
                    "returned": len(page),
                    "has_more": has_more,
                    "next_offset": offset + len(page) if has_more else None,
                    "note": note,
                }
            )
            return {"status": "success", "data": data}
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _no_screen_for_model(
        self, model_filter: str, symbol: str, screens: int
    ) -> Dict[str, Any]:
        """Explain a model filter that matches none of the gene's screens.

        An unknown model and a real model without a screen would both give an
        empty list. A model id is looked up, so the two get different answers.
        """
        hint = "DepMap_search_cell_lines finds the model_id of a cell line."
        if re.fullmatch(r"SIDM\d+", model_filter, flags=re.IGNORECASE):
            model_id = model_filter.upper()
            response = requests.get(
                f"{DEPMAP_BASE_URL}/models/{model_id}",
                params={"fields[model]": "names,crispr_ko_available"},
                timeout=self.timeout,
            )
            # An unknown model id answers HTTP 200 with {"data": null}.
            model = None
            if response.status_code != 404:
                response.raise_for_status()
                model = response.json().get("data")
            if not isinstance(model, dict):
                return {
                    "status": "error",
                    "error": f"DepMap has no model with the id {model_id}. {hint}",
                }
            attrs = model.get("attributes") or {}
            names = attrs.get("names") or []
            return {
                "status": "success",
                "data": {
                    "gene_symbol": symbol,
                    "model_filter": model_id,
                    "scores": [],
                    "count": 0,
                    "total_scores": 0,
                    "returned": 0,
                    "has_more": False,
                    "next_offset": None,
                    "note": (
                        f"Model {model_id}"
                        + (f" ({names[0]})" if names else "")
                        + f" has no CRISPR knockout record for {symbol}. "
                        f"crispr_ko_available for this model is "
                        f"{attrs.get('crispr_ko_available')}. {screens} screens "
                        f"of other models have a score for {symbol}."
                    ),
                },
            }
        return {
            "status": "error",
            "error": (
                f"No CRISPR knockout record of {symbol} is for a model named "
                f"'{model_filter}'. The model was not screened, or this is not "
                f"a DepMap model name. {hint}"
            ),
        }

    def _search_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for genes in DepMap by symbol.

        The Sanger Cell Model Passports API gene filter is limited,
        so this method fetches sorted gene batches and filters client-side.
        """
        query = arguments.get("query")

        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            # Fix-R19C-1: the Sanger API's filter[gene] param doesn't work
            # for exact symbol matching (confirmed live: it silently
            # returns an unrelated, seemingly-arbitrary page of genes
            # regardless of the filter value). The catalog has ~45,751
            # genes; the previous "scan up to 5 pages of 100" approach only
            # ever covered the first ~1% alphabetically, so any gene not
            # starting with A/B (e.g. KRAS, TP53, EGFR) was always
            # reported "not found" -- confirmed live for all three.
            # Results are sorted by symbol, so binary-search the pages by
            # comparing the query against each page's first/last symbol
            # instead of scanning linearly from page 1.
            url = f"{DEPMAP_BASE_URL}/genes"
            params = {"sort": "symbol", "page[size]": 1000, "page[number]": 1}
            query_upper = query.upper()
            # Binary search makes several sequential round-trips (~6 for the
            # full 45k-gene catalog); this API is occasionally slow on an
            # individual request (confirmed live, one page took 22s), so
            # give each request more headroom than the tool's default.
            page_items, catalog_page, total_pages = self._find_catalog_page(
                url, params, query_upper, _gene_symbol, max(self.timeout, 45)
            )

            # An exact symbol lookup is complete on the located page. For a
            # prefix-only query (for example "C"), matching symbols can span
            # multiple subsequent 1000-record pages; continue until the
            # sorted catalog has moved beyond the prefix.
            exact_on_page = any(
                _gene_symbol(item) == query_upper for item in page_items
            )
            if page_items and not exact_on_page and catalog_page is not None:
                next_page = catalog_page + 1
                while next_page <= total_pages:
                    params["page[number]"] = next_page
                    response = requests.get(
                        url, params=params, timeout=max(self.timeout, 45)
                    )
                    response.raise_for_status()
                    next_items = response.json().get("data", [])
                    matching = [
                        item
                        for item in next_items
                        if _gene_symbol(item).startswith(query_upper)
                    ]
                    page_items.extend(matching)
                    if not matching or len(matching) < len(next_items):
                        break
                    next_page += 1

            genes = []
            for item in page_items:
                attrs = item.get("attributes", {})
                symbol = attrs.get("symbol", "")
                # Check for exact or prefix match
                if symbol.upper() == query_upper or symbol.upper().startswith(
                    query_upper
                ):
                    genes.append(
                        {
                            "gene_id": item.get("id"),
                            "symbol": symbol,
                            "name": attrs.get("name"),
                            "hgnc_id": attrs.get("hgnc_id"),
                            "ensembl_id": attrs.get("ensembl_gene_id"),
                            "exact_match": (symbol.upper() == query_upper),
                            # The tool's description says it returns "gene IDs
                            # and annotations" and returned the ids alone.
                            # hgnc_status is the one that can mislead: a
                            # withdrawn or merged symbol resolves silently,
                            # and the caller has no way to see that the
                            # symbol they searched is no longer the current
                            # one. location is the cytogenetic locus, and
                            # method_of_action is what a target-validation
                            # question asks after essentiality.
                            "hgnc_status": attrs.get("hgnc_status"),
                            "location": attrs.get("location"),
                            "method_of_action": attrs.get("method_of_action"),
                            "hgnc_merge_comment": attrs.get("hgnc_merge_comment"),
                        }
                    )

            # Sort: exact matches first
            genes.sort(
                key=lambda g: (
                    not g["exact_match"],
                    g.get("symbol", ""),
                )
            )

            if not genes:
                return {
                    "status": "success",
                    "data": {
                        "query": query,
                        "genes": [],
                        "count": 0,
                        "note": (
                            f"Gene '{query}' not found in DepMap "
                            "gene catalog. The Sanger Cell Model "
                            "Passports API has limited gene search. "
                            "Try using an Ensembl ID or check "
                            "depmap.org directly."
                        ),
                    },
                }

            total_matches = len(genes)
            limit = max(1, min(int(arguments.get("limit", 20)), 500))
            offset = max(0, int(arguments.get("offset", 0)))
            page_genes = genes[offset : offset + limit]
            has_more = offset + len(page_genes) < total_matches

            return {
                "status": "success",
                "data": {
                    "query": query,
                    "genes": page_genes,
                    "count": len(page_genes),
                    "total_genes": total_matches,
                    "offset": offset,
                    "limit": limit,
                    "returned": len(page_genes),
                    "has_more": has_more,
                    "next_offset": offset + len(page_genes) if has_more else None,
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"DepMap API request failed: {str(e)}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
            }

    def _get_drug_response(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get drug sensitivity data for cell lines.

        Returns IC50/AUC values for drug-cell line combinations.
        """
        drug_name = arguments.get("drug_name")
        model_id = arguments.get("model_id")

        if not drug_name and not model_id:
            return {
                "status": "error",
                "error": "Either drug_name or model_id is required",
            }

        try:
            # Query drugs endpoint
            url = f"{DEPMAP_BASE_URL}/drugs"
            params = {"page[size]": 20}

            if drug_name:
                params["filter[drug]"] = f"drug_name:{drug_name}"

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            drugs = []
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                drugs.append(
                    {
                        "drug_id": item.get("id"),
                        "drug_name": attrs.get("drug_name"),
                        "synonyms": attrs.get("synonyms"),
                        "targets": attrs.get("targets"),
                        "target_pathway": attrs.get("target_pathway"),
                    }
                )

            return {
                "status": "success",
                "data": {
                    "query": drug_name or model_id,
                    "drugs": drugs,
                    "count": len(drugs),
                    "note": "Drug sensitivity data (IC50, AUC) available through DepMap portal.",
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
