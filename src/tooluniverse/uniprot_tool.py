import re
import time
import requests
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse
from .base_tool import BaseTool, ToolError
from .tool_registry import register_tool


# Common-name / scientific-name shortcuts for the handful of model organisms
# callers name in prose. Anything not listed here still works -- it is routed
# to UniProt's organism_name field rather than being rejected.
_ORGANISM_TAXIDS = {
    "human": "9606",
    "homo sapiens": "9606",
    "mouse": "10090",
    "mus musculus": "10090",
    "rat": "10116",
    "rattus norvegicus": "10116",
    "yeast": "559292",
    "saccharomyces cerevisiae": "559292",
    "zebrafish": "7955",
    "danio rerio": "7955",
    "fruitfly": "7227",
    "drosophila melanogaster": "7227",
    "c. elegans": "6239",
    "caenorhabditis elegans": "6239",
    "arabidopsis": "3702",
    "arabidopsis thaliana": "3702",
    "pig": "9823",
    "sus scrofa": "9823",
    "cow": "9913",
    "bos taurus": "9913",
    "rabbit": "9986",
    "oryctolagus cuniculus": "9986",
}


# Rewrite an explicit, caller-written `organism_id:<taxid>` clause. See
# _uniprot_organism_filter for why the numeric path must use `taxonomy_id`.
_ORGANISM_ID_CLAUSE = re.compile(r"\borganism_id:\"?(\d+)\"?")

_TAXONOMY_WIDENING_NOTE = (
    "Query scope widened: 'organism_id:<taxid>' was rewritten to "
    "'taxonomy_id:<taxid>'. UniProt's organism_id field (labelled "
    "'Organism [OS]') matches only an entry's own organism node, while "
    "taxonomy_id ('Taxonomy [OC]') matches anywhere in the entry's lineage. "
    "Most bacterial entries are annotated at strain level, so a species-level "
    "organism_id silently returns 0 or an undercount (e.g. "
    "'gene:gyrA AND organism_id:1423 AND reviewed:true' -> 0 hits vs 1 for "
    "taxonomy_id; gene:recA + E. coli 562 -> 9 vs 30). Results therefore "
    "include descendant strains of the taxid you supplied. To match the "
    "exact organism node only, write 'organism_id:<taxid>' yourself against "
    "the UniProt REST API, or use organism_name with the exact strain name."
)


def _uniprot_organism_filter(organism: str) -> str:
    """Build the UniProt query clause for an organism the caller named.

    Numeric taxonomy IDs are emitted as ``taxonomy_id:<taxid>``, NOT
    ``organism_id:<taxid>``. UniProt's field configuration
    (https://rest.uniprot.org/configure/uniprotkb/search-fields) documents
    these as two different fields:

    * ``organism_name`` / ``organism_id`` -- label "Organism [OS]" -- matches
      the entry's OWN organism node, exactly.
    * ``taxonomy_name`` / ``taxonomy_id`` -- label "Taxonomy [OC]" -- matches
      anywhere in the entry's taxonomic LINEAGE, i.e. includes descendant
      strains.

    Almost every bacterial UniProtKB entry is annotated at STRAIN level rather
    than species level, so scoping by a species-level taxid with
    ``organism_id`` silently returns 0 hits or a large undercount. Measured
    live against rest.uniprot.org (``size=0``, X-Total-Results header):

    ==========================================  ===========  ===========
    query                                       organism_id  taxonomy_id
    ==========================================  ===========  ===========
    gene:gyrA AND <f>:1423 AND reviewed:true              0            1
    gene:recA AND <f>:562                                 9           30
    gene:katG AND <f>:1773                              105          157
    gene:TP53 AND <f>:9606                              114          114
    ==========================================  ===========  ===========

    Human (and other single-node model organisms) are identical either way, so
    the switch is strictly an increase in correctness.

    Names are still routed to ``organism_name:"..."``: ``organism_id`` accepts
    numeric taxonomy IDs only, and passing a species name to it makes the whole
    search fail with HTTP 400 rather than returning zero hits. ``organism_name``
    accepts free text and covers the long tail of species (pathogens, plants,
    non-model organisms) that no shortcut table can enumerate. Confirmed live
    that ``organism_name:"Escherichia coli"`` returns 30 -- matching
    ``taxonomy_id:562`` -- so the name path already had lineage semantics and
    needs no change.
    """
    name = str(organism).strip()
    resolved = _ORGANISM_TAXIDS.get(name.lower(), name)
    if resolved.isdigit():
        return f"taxonomy_id:{resolved}"
    return f'organism_name:"{resolved}"'


def _protein_name(protein_desc: Dict[str, Any]) -> str:
    """Extract a display name from a UniProtKB entry's proteinDescription.

    Reviewed (Swiss-Prot) entries have a single `recommendedName`, but
    unreviewed (TrEMBL) entries -- over 99% of UniProtKB -- have no
    `recommendedName` at all; their name lives in `submissionNames` (a
    list) instead. Confirmed live for Q53707/MecA PBP2': recommendedName
    is absent, and the actual name ("MecA PBP2' (penicillin binding
    protein 2')") is submissionNames[0].fullName.value.
    """
    name = protein_desc.get("recommendedName", {}).get("fullName", {}).get("value", "")
    if name:
        return name
    submission_names = protein_desc.get("submissionNames") or []
    if submission_names:
        return submission_names[0].get("fullName", {}).get("value", "")
    return ""


@register_tool("UniProtRESTTool")
class UniProtRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.endpoint = tool_config["fields"]["endpoint"]
        self.extract_path = tool_config["fields"].get("extract_path")
        self.timeout = 15  # Increase timeout for large entries

    def validate_parameters(self, arguments: Dict[str, Any]) -> Optional[ToolError]:
        """
        Validate parameters with automatic type coercion for limit.
        """
        # Coerce limit to integer if passed as string
        if "limit" in arguments and isinstance(arguments["limit"], str):
            try:
                arguments["limit"] = int(arguments["limit"])
            except (ValueError, TypeError):
                # Let schema validation handle the error
                pass

        # Call parent validation
        return super().validate_parameters(arguments)

    def _build_url(self, args: Dict[str, Any]) -> str:
        url = self.endpoint
        for k, v in args.items():
            url = url.replace(f"{{{k}}}", str(v))
        return url

    def _compact_entry(
        self, data: Dict[str, Any], arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Return an explicitly pageable summary of a UniProtKB entry."""
        arguments = arguments or {}
        protein_desc = data.get("proteinDescription", {})
        protein_name = _protein_name(protein_desc)
        gene_names = []
        for gene in data.get("genes", []):
            gene_name = gene.get("geneName", {}).get("value")
            if gene_name:
                gene_names.append(gene_name)

        comment_limit = min(max(int(arguments.get("comment_limit", 25)), 1), 100)
        comment_offset = max(int(arguments.get("comment_offset", 0)), 0)
        feature_limit = min(max(int(arguments.get("feature_limit", 100)), 1), 500)
        feature_offset = max(int(arguments.get("feature_offset", 0)), 0)
        reference_limit = min(max(int(arguments.get("reference_limit", 25)), 1), 100)
        reference_offset = max(int(arguments.get("reference_offset", 0)), 0)

        all_comments = data.get("comments", [])
        comment_page = all_comments[comment_offset : comment_offset + comment_limit]
        comment_summaries = []
        for comment in comment_page:
            comment_type = comment.get("commentType", "")
            text_values = [
                text["value"]
                for text in comment.get("texts", [])
                if isinstance(text, dict) and text.get("value")
            ]
            # Some biologically important comment types carry no top-level
            # `texts` array, so keying only on text_values silently dropped them.
            # COFACTOR stores its data under `cofactors[].name` (+ an optional
            # `note.texts`); confirmed live that P00439's Fe(2+) cofactor -- a
            # clinically relevant field -- vanished from the compact summary.
            if comment_type == "COFACTOR":
                cofactor_names = [
                    cf["name"]
                    for cf in comment.get("cofactors", [])
                    if isinstance(cf, dict) and cf.get("name")
                ]
                note_texts = [
                    t["value"]
                    for t in (comment.get("note", {}) or {}).get("texts", [])
                    if isinstance(t, dict) and t.get("value")
                ]
                text_values = cofactor_names + note_texts + text_values
            # Keep structured fields for comment types whose meaning is not
            # represented by top-level text (INTERACTION, ALTERNATIVE PRODUCTS,
            # WEB RESOURCE, etc.).  Omitting them made a present comment look
            # absent even within the documented compact view.
            details = {
                key: value
                for key, value in comment.items()
                if key not in {"commentType", "texts"}
            }
            comment_summaries.append(
                {
                    "commentType": comment_type,
                    "texts": text_values,
                    **({"details": details} if details else {}),
                }
            )

        all_features = data.get("features", [])
        # A page is bounded, but each returned feature remains intact.  This
        # preserves ECO evidence, ligand data, alternative sequences and other
        # fields that the previous three-field projection silently discarded.
        feature_summaries = all_features[
            feature_offset : feature_offset + feature_limit
        ]

        all_references = data.get("references", [])
        reference_summaries = all_references[
            reference_offset : reference_offset + reference_limit
        ]

        def paging(
            total: int, returned: int, offset: int, limit: int
        ) -> Dict[str, Any]:
            has_more = offset + returned < total
            return {
                "returned": returned,
                "total": total,
                "limit": limit,
                "offset": offset,
                "truncated": returned < total,
                "has_more": has_more,
                "next_offset": offset + returned if has_more else None,
            }

        comment_paging = paging(
            len(all_comments), len(comment_summaries), comment_offset, comment_limit
        )
        feature_paging = paging(
            len(all_features), len(feature_summaries), feature_offset, feature_limit
        )
        reference_paging = paging(
            len(all_references),
            len(reference_summaries),
            reference_offset,
            reference_limit,
        )

        return {
            "status": "success",
            "data": {
                "entryType": data.get("entryType", ""),
                "primaryAccession": data.get("primaryAccession", ""),
                "uniProtkbId": data.get("uniProtkbId", ""),
                "protein_name": protein_name,
                "gene_names": gene_names,
                "organism": data.get("organism", {}),
                "sequence": data.get("sequence", {}),
                "annotationScore": data.get("annotationScore"),
                "proteinExistence": data.get("proteinExistence", ""),
                "keywords": data.get("keywords", []),
                "comments": comment_summaries,
                "features": feature_summaries,
                "references": reference_summaries,
                "xref_count": len(data.get("uniProtKBCrossReferences", [])),
            },
            "metadata": {
                "compact": True,
                **{f"comments_{key}": value for key, value in comment_paging.items()},
                **{f"features_{key}": value for key, value in feature_paging.items()},
                **{
                    f"references_{key}": value
                    for key, value in reference_paging.items()
                },
                # Backward-compatible total aliases used by existing callers.
                "total_comments": len(all_comments),
                "total_features": len(all_features),
                "total_references": len(all_references),
            },
        }

    def _get_entry_publications(
        self, accession: str, arguments: Dict[str, Any]
    ) -> tuple[list, Dict[str, Any]]:
        """Fetch the publications view, including mapped bibliography.

        UniProtKB entry JSON only contains entry-curation references. The web
        Publications tab uses a separate per-entry endpoint that also exposes
        computationally mapped and community-curated literature.
        """
        source = arguments.get("publication_source", "computational")
        source_facets = {
            "computational": '(types:"1")',
            "curated": '(types:"2")',
            "community": '(types:"0")',
        }
        size = min(max(int(arguments.get("publication_limit", 25)), 1), 100)
        params: Dict[str, Any] = {"size": size}
        if source in source_facets:
            params["facetFilter"] = source_facets[source]
        if arguments.get("publication_cursor"):
            params["cursor"] = arguments["publication_cursor"]

        url = f"https://rest.uniprot.org/uniprotkb/{accession}/publications"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        publications = payload.get("results", [])

        try:
            total = int(response.headers.get("x-total-results", len(publications)))
        except (TypeError, ValueError):
            total = len(publications)

        next_url = None
        link = response.headers.get("Link", "")
        match = re.search(r'<([^>]+)>;\s*rel="next"', link)
        if match:
            next_url = match.group(1)
        next_cursor = (
            parse_qs(urlparse(next_url).query).get("cursor", [None])[0]
            if next_url
            else None
        )
        return publications, {
            "publication_source": source,
            "total_publications": total,
            "publications_returned": len(publications),
            "publications_truncated": bool(next_cursor),
            "has_more_publications": bool(next_cursor),
            "next_publication_cursor": next_cursor,
        }

    def _extract_data(
        self,
        data: Dict,
        extract_path: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Custom data extraction with support for filtering"""

        # Annotation extractors default to the structured form so evidence and
        # qualifiers stop being dropped, but callers written against the
        # historical flat string list can ask for it back with format="values".
        response_format = (arguments or {}).get("format") or "structured"
        legacy_values = response_format == "values"

        # Handle specific UniProt extraction patterns
        if extract_path == "function_annotations":
            # Preserve evidence attached to each FUNCTION text rather than
            # flattening annotations to strings and losing ECO/PubMed support.
            result = []
            for comment in data.get("comments", []):
                if comment.get("commentType") == "FUNCTION":
                    for text in comment.get("texts", []):
                        if "value" in text:
                            result.append(
                                text["value"]
                                if legacy_values
                                else {
                                    "value": text["value"],
                                    "evidences": text.get("evidences", []),
                                }
                            )
            return result

        elif extract_path == "subcellular_location_annotations":
            # Preserve the qualifiers that make a localization interpretable.
            # Flattening this field to location.value silently discarded
            # evidence, isoform/molecule specificity, topology, and notes.
            result = []
            for comment in data.get("comments", []):
                if comment.get("commentType") == "SUBCELLULAR LOCATION":
                    molecule = comment.get("molecule")
                    note = comment.get("note")
                    for annotation in comment.get("subcellularLocations", []):
                        location = annotation.get("location", {})
                        if not location.get("value"):
                            continue
                        result.append(
                            location["value"]
                            if legacy_values
                            else {
                                "location": location.get("value"),
                                "location_id": location.get("id"),
                                "evidences": location.get("evidences", []),
                                "molecule": molecule,
                                "topology": annotation.get("topology"),
                                "orientation": annotation.get("orientation"),
                                "note": note,
                            }
                        )
            return result

        elif extract_path == "features[?(@.type=='VARIANT')]":
            # Extract variant features
            result = []
            for feature in data.get("features", []):
                if feature.get("type") == "Natural variant":
                    result.append(feature)
            return result

        elif extract_path == "ptm_and_processing_features":
            # UniProt models both PTMs and chain-processing annotations as
            # feature records. Returning only Modified residue and Signal
            # omitted other documented members of those two groups.
            supported_types = {
                "Modified residue",
                "Glycosylation",
                "Lipidation",
                "Disulfide bond",
                "Cross-link",
                "Signal",
                "Transit peptide",
                "Propeptide",
                "Peptide",
                "Chain",
                "Initiator methionine",
            }
            return [
                feature
                for feature in data.get("features", [])
                if feature.get("type") in supported_types
            ]

        elif extract_path == (
            "comments[?(@.commentType=="
            "'ALTERNATIVE PRODUCTS')].isoforms[*].isoformIds[*]"
        ):
            # Extract isoform IDs
            result = []
            for comment in data.get("comments", []):
                if comment.get("commentType") == "ALTERNATIVE PRODUCTS":
                    for isoform in comment.get("isoforms", []):
                        for isoform_id in isoform.get("isoformIds", []):
                            result.append(isoform_id)
            return result

        # For simple paths, use jsonpath_ng
        try:
            from jsonpath_ng import parse

            expr = parse(extract_path)
            matches = expr.find(data)
            extracted_data = [m.value for m in matches]

            # Return single item if only one match, otherwise return list
            if len(extracted_data) == 0:
                return {
                    "status": "error",
                    "error": f"No data found for JSONPath: {extract_path}",
                }
            elif len(extracted_data) == 1:
                return extracted_data[0]
            else:
                return extracted_data

        except ImportError:
            return {
                "status": "error",
                "error": "jsonpath_ng library is required for data extraction",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": (
                    f"Failed to extract UniProt fields using "
                    f"JSONPath '{extract_path}': {e}"
                ),
            }

    @staticmethod
    def _total_results(resp, data: Dict[str, Any], results: list) -> int:
        """Resolve the true number of matches for a UniProt search response.

        Fix-R3-08: UniProt reports the match total in the ``x-total-results``
        response HEADER, not in the JSON body -- there is no ``resultsFound``
        key. Reading only the body meant the fallback always won, so a field
        named ``total_results`` silently reported the page size: a search for
        "beta-lactamase" in UniRef returned ``total_results: 2`` for ``limit:
        2`` when the real total is 395446. Prefer the header, and keep the
        body/page-size fallbacks for any endpoint that does supply them.
        """
        header = UniProtRESTTool._header_total(resp)
        if header is not None:
            return header
        return data.get("resultsFound", len(results))

    @staticmethod
    def _header_total(resp):
        """The ``x-total-results`` figure, or None when it is absent/unusable."""
        try:
            header = getattr(resp, "headers", {}).get("x-total-results")
        except (AttributeError, TypeError):
            return None
        try:
            return int(header)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _next_cursor(resp) -> Optional[str]:
        """Extract UniProt's opaque next-page cursor from the Link header."""
        link = getattr(resp, "headers", {}).get("Link", "")
        if not isinstance(link, str):
            return None
        match = re.search(r'<([^>]+)>;\s*rel="next"', link)
        if not match:
            return None
        return parse_qs(urlparse(match.group(1)).query).get("cursor", [None])[0]

    def _search_paging(self, resp, total: int, returned: int) -> Dict[str, Any]:
        next_cursor = self._next_cursor(resp)
        return {
            "has_more": bool(next_cursor),
            "truncated": bool(next_cursor),
            "next_cursor": next_cursor,
            "total_results": total,
            "returned": returned,
        }

    def _handle_search(self, arguments: Dict[str, Any]) -> Any:
        """Handle search queries with flexible parameters"""
        query = arguments.get("query", "")
        organism = arguments.get("organism", "")
        fields = arguments.get("fields")
        min_length = arguments.get("min_length")
        max_length = arguments.get("max_length")

        # Coerce limit to integer if passed as string
        limit_value = arguments.get("limit", 25)
        if isinstance(limit_value, str):
            limit_value = int(limit_value)
        limit = min(limit_value, 500)

        # Normalize query: UniProt has no bare 'organism' field. Numeric values
        # belong in a taxonomy field, everything else in organism_name --
        # rewriting a species name into a numeric-only field makes UniProt
        # reject the whole request with HTTP 400 (confirmed live:
        # 'organism_id:Klebsiella pneumoniae').
        query = re.sub(
            r"\borganism:(\"[^\"]+\"|\S+)",
            lambda m: _uniprot_organism_filter(m.group(1).strip('"')),
            query,
        )

        # The tool's own description used to tell callers to write
        # 'organism_id:9606' directly, so plenty of queries arrive with an
        # explicit organism_id clause. That field is exact-node-only ("Organism
        # [OS]") and undercounts strain-level entries, so rewrite it to the
        # lineage field ("Taxonomy [OC]") -- but DISCLOSE the rewrite in the
        # response rather than mutating the caller's query silently.
        query, organism_id_rewrites = _ORGANISM_ID_CLAUSE.subn(r"taxonomy_id:\1", query)
        normalization_note = _TAXONOMY_WIDENING_NOTE if organism_id_rewrites else None

        # Build query string
        query_parts = [query]
        if organism:
            # Skip when the caller already scoped the query themselves, so we
            # don't AND two conflicting organism clauses together. Both the
            # exact-node fields and the lineage fields count as "already
            # scoped" -- otherwise a caller-supplied taxonomy_id: clause (or
            # one we just rewrote from organism_id:) would be ANDed with a
            # second, conflicting organism clause.
            lowered = query.lower()
            if not any(
                field in lowered
                for field in (
                    "organism_id:",
                    "organism_name:",
                    "taxonomy_id:",
                    "taxonomy_name:",
                )
            ):
                query_parts.append(_uniprot_organism_filter(organism))

        # Auto-convert length parameters to range syntax
        if min_length or max_length:
            min_val = min_length if min_length else "*"
            max_val = max_length if max_length else "*"
            query_parts.append(f"length:[{min_val} TO {max_val}]")

        full_query = " AND ".join(query_parts)

        # Build parameters
        params = {"query": full_query, "size": str(limit), "format": "json"}
        if arguments.get("cursor"):
            params["cursor"] = arguments["cursor"]

        # Add fields parameter if specified
        if fields and isinstance(fields, list):
            params["fields"] = ",".join(fields)

        url = "https://rest.uniprot.org/uniprotkb/search"

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            # Extract results
            results = data.get("results", [])
            total = self._total_results(resp, data, results)
            paging = self._search_paging(resp, total, len(results))

            # If custom fields requested, return raw API response for flexibility
            if fields and isinstance(fields, list):
                payload = {
                    **paging,
                    "results": results,
                }
                if normalization_note:
                    payload["normalization_note"] = normalization_note
                return {"status": "success", "data": payload}

            # Otherwise, use formatted extraction logic
            formatted_results = []

            for entry in results:
                formatted_entry = {
                    "accession": entry.get("primaryAccession", ""),
                    "id": entry.get("uniProtkbId", ""),
                    "protein_name": "",
                    "gene_names": [],
                    "organism": "",
                    "length": 0,
                }

                # Extract protein name
                protein_desc = entry.get("proteinDescription", {})
                formatted_entry["protein_name"] = _protein_name(protein_desc)

                # Extract gene names
                genes = entry.get("genes", [])
                for gene in genes:
                    gene_name = gene.get("geneName", {})
                    if gene_name:
                        formatted_entry["gene_names"].append(gene_name.get("value", ""))

                # Extract organism
                organism_info = entry.get("organism", {})
                formatted_entry["organism"] = organism_info.get("scientificName", "")

                # Extract sequence length
                sequence = entry.get("sequence", {})
                formatted_entry["length"] = sequence.get("length", 0)

                formatted_results.append(formatted_entry)

            payload = {
                **paging,
                "results": formatted_results,
            }
            if normalization_note:
                payload["normalization_note"] = normalization_note
            return {"status": "success", "data": payload}

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request to UniProt API timed out"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request to UniProt API failed: {e}"}
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Failed to parse JSON response: {e}",
                "retryable": True,
            }

    def _handle_id_mapping(self, arguments: Dict[str, Any]) -> Any:
        """Handle ID mapping requests"""

        ids = arguments.get("ids", [])
        from_db = arguments.get("from_db", "")
        to_db = arguments.get("to_db", "UniProtKB")
        # UniProt mapping jobs can take >30s even for small inputs.
        max_wait_time = arguments.get("max_wait_time", 120)

        # Normalize IDs to list
        if isinstance(ids, str):
            ids = [ids]

        # Normalize database names
        # Map user-friendly names to UniProt ID mapping database names.
        # Important: do NOT map target UniProtKB to UniProtKB_AC-ID.
        db_mapping = {
            "Ensembl": "Ensembl",
            "Gene_Name": "Gene_Name",
            "RefSeq_Protein": "RefSeq_Protein_ID",
            "EMBL": "EMBL_ID",
            "UniProtKB": "UniProtKB",
            "UniProtKB_AC-ID": "UniProtKB_AC-ID",
        }
        from_db_normalized = db_mapping.get(from_db, from_db)
        to_db_normalized = db_mapping.get(to_db, to_db)

        # Step 1: Submit mapping job
        submit_url = "https://rest.uniprot.org/idmapping/run"
        # UniProt ID mapping API expects application/x-www-form-urlencoded,
        # not JSON.
        payload = {
            "ids": ",".join(ids),
            "from": from_db_normalized,
            "to": to_db_normalized,
        }

        try:
            resp = requests.post(submit_url, data=payload, timeout=self.timeout)
            resp.raise_for_status()
            job_data = resp.json()
            job_id = job_data.get("jobId")

            if not job_id:
                return {
                    "status": "error",
                    "data": {"error": "Failed to get job ID from UniProt ID mapping"},
                }

            # Step 2: Poll for job completion
            status_url = f"https://rest.uniprot.org/idmapping/status/{job_id}"
            results_url = f"https://rest.uniprot.org/idmapping/results/{job_id}"

            # UniProt pages ID-mapping results, reports the unpaged total in
            # the `x-total-results` header, and lists unmappable inputs under
            # `failedIds`. All three were ignored here, so P04637 -> PDB came
            # back `mapped_count: 25, failed_ids: []` -- 25 being a page size
            # against a real 295 -- and a typo'd accession vanished silently.
            #
            # Feature-26A-13 noted the status endpoint 303-redirects to a
            # results page once the job finishes. Both figures are already on
            # that response, so only rows beyond its short default page need
            # a second request. Re-fetch through the URL the redirect landed
            # on rather than the generic one: for `to_db=UniProtKB` the
            # redirect targets /idmapping/uniprotkb/results/, which streams
            # full entries, while /idmapping/results/ returns bare accession
            # strings -- fetching the latter silently replaced each
            # {accession, id, gene_name} object with a plain string.
            job_done = False
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                status_resp = requests.get(status_url, timeout=self.timeout)
                status_resp.raise_for_status()
                status_data = status_resp.json()

                job_status = status_data.get("jobStatus") or status_data.get("status")

                if (
                    job_status == "FINISHED"
                    or "results" in status_data
                    or "failedIds" in status_data
                ):
                    job_done = True
                    break
                elif job_status in ("FAILED", "ERROR"):
                    return {
                        "status": "error",
                        "error": "ID mapping job failed",
                    }

                time.sleep(1)  # Wait 1 second before next poll

            if not job_done:
                return {
                    "status": "error",
                    "error": (
                        f"UniProt ID mapping job did not complete within "
                        f"{max_wait_time}s. Try again or reduce the number of IDs."
                    ),
                }

            carried = status_data.get("results")
            total = self._header_total(status_resp)
            raw_results = []
            failed_ids = []
            total_results = None
            if carried is not None and total is not None and total <= len(carried):
                raw_results = carried
                failed_ids = list(status_data.get("failedIds") or [])
                total_results = total
            else:
                # Follow every `rel="next"` page so the preview (or one 500-row
                # page) cannot become the answer.
                landed = str(getattr(status_resp, "url", "") or "")
                next_url = landed if "/results/" in landed else results_url
                params = {"size": 500}
                while next_url:
                    results_resp = requests.get(
                        next_url, params=params, timeout=self.timeout
                    )
                    results_resp.raise_for_status()
                    page_data = results_resp.json()
                    if "results" not in page_data:
                        break
                    if total_results is None:
                        total_results = self._total_results(
                            results_resp, page_data, page_data["results"]
                        )
                    raw_results.extend(page_data["results"])
                    for failed_id in page_data.get("failedIds") or []:
                        if failed_id not in failed_ids:
                            failed_ids.append(failed_id)
                    link = getattr(results_resp, "headers", {}).get("Link", "")
                    match = (
                        re.search(r'<([^>]+)>;\s*rel="next"', link)
                        if isinstance(link, str)
                        else None
                    )
                    next_url = match.group(1) if match else None
                    params = None
                if total_results is None:
                    # Losing the answer would be worse than returning the
                    # status page's short preview.
                    raw_results = carried or []
                    failed_ids = list(status_data.get("failedIds") or [])
                    total_results = self._total_results(
                        status_resp, status_data, raw_results
                    )

            # Step 3: Parse results
            # UniProt returns `to` as a plain string (for simple DB mappings like
            # PDB) or as a full UniProtKB entry dict. Flatten both into a simple
            # from/to pair.
            formatted_results = []
            for result in raw_results:
                from_value = result.get("from", "")
                to_value = result.get("to")
                if isinstance(to_value, dict):
                    # UniProtKB entry: extract accession and gene name
                    gene_names = to_value.get("geneNames", [])
                    gene_name = gene_names[0].get("value", "") if gene_names else ""
                    formatted_results.append(
                        {
                            "from": from_value,
                            "to": {
                                "accession": to_value.get("primaryAccession", ""),
                                "id": to_value.get("uniProtkbId", ""),
                                "gene_name": gene_name,
                            },
                        }
                    )
                elif to_value is not None:
                    # Simple string mapping (PDB, Ensembl, etc.)
                    formatted_results.append({"from": from_value, "to": str(to_value)})

            result_offset = max(int(arguments.get("result_offset", 0)), 0)
            result_limit = min(max(int(arguments.get("result_limit", 500)), 1), 5000)
            visible_results = formatted_results[
                result_offset : result_offset + result_limit
            ]
            has_more = result_offset + len(visible_results) < len(formatted_results)
            result_data = {
                "mapped_count": len(formatted_results),
                "returned": len(visible_results),
                "result_offset": result_offset,
                "result_limit": result_limit,
                "has_more": has_more,
                "next_result_offset": (
                    result_offset + len(visible_results) if has_more else None
                ),
                "results": visible_results,
                "failed_ids": failed_ids,
                "total_results": total_results,
            }
            if total_results is not None and len(formatted_results) < total_results:
                result_data["truncated"] = True
                result_data["truncation_note"] = (
                    f"Returned {len(formatted_results)} of {total_results} mappings "
                    f"UniProt holds for these IDs. `mapped_count` counts the rows "
                    f"below, not the matches; an identifier absent here may still "
                    f"map. Narrow the request to fewer input IDs to see the rest."
                )
            else:
                result_data["truncated"] = has_more
            return {"status": "success", "data": result_data}

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "data": {"error": "Request to UniProt API timed out"},
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "data": {"error": f"Request to UniProt API failed: {e}"},
            }
        except ValueError as e:
            return {
                "status": "error",
                "data": {"error": f"Failed to parse JSON response: {e}"},
            }

    def _handle_uniref_search(self, arguments: Dict[str, Any]) -> Any:
        """Handle UniRef search queries"""
        query = arguments.get("query", "")
        declared_cluster_type_default = (
            self.tool_config.get("parameter", {})
            .get("properties", {})
            .get("cluster_type", {})
            .get("default", "")
        )
        cluster_type = arguments.get("cluster_type", declared_cluster_type_default)
        limit_value = arguments.get("limit", 25)
        if isinstance(limit_value, str):
            limit_value = int(limit_value)
        limit = min(limit_value, 500)

        # Build query - if cluster_type specified and not in query, add it
        # Note: UniRef search accepts queries like "P04637" or "id:UniRef50_P04637"
        # cluster_type is applied via UniProt's `identity:` query filter
        # (0.5/0.9/1.0 for UniRef50/90/100 -- confirmed live against
        # rest.uniprot.org/uniref/search). Skip it when the query already
        # names a UniRef cluster directly (e.g. "UniRef50_P04637") or
        # already carries its own identity filter, so we don't override an
        # explicit caller choice.
        full_query = query
        cluster_identity = {
            "UniRef100": "1.0",
            "UniRef90": "0.9",
            "UniRef50": "0.5",
        }.get(cluster_type)
        if (
            cluster_identity
            and "uniref" not in query.lower()
            and "identity:" not in query.lower()
        ):
            full_query = (
                f"({query}) AND identity:{cluster_identity}"
                if query
                else f"identity:{cluster_identity}"
            )

        params = {"query": full_query, "size": str(limit), "format": "json"}
        if arguments.get("cursor"):
            params["cursor"] = arguments["cursor"]
        url = "https://rest.uniprot.org/uniref/search"

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            total = self._total_results(resp, data, results)
            return {
                "status": "success",
                "data": {
                    **self._search_paging(resp, total, len(results)),
                    "results": results,
                },
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request to UniProt API timed out"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request to UniProt API failed: {e}"}
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Failed to parse JSON response: {e}",
                "retryable": True,
            }

    def _handle_uniparc_search(self, arguments: Dict[str, Any]) -> Any:
        """Handle UniParc search queries"""
        query = arguments.get("query", "")
        limit_value = arguments.get("limit", 25)
        if isinstance(limit_value, str):
            limit_value = int(limit_value)
        limit = min(limit_value, 500)

        params = {"query": query, "size": str(limit), "format": "json"}
        if arguments.get("cursor"):
            params["cursor"] = arguments["cursor"]
        url = "https://rest.uniprot.org/uniparc/search"

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            total = self._total_results(resp, data, results)
            return {
                "status": "success",
                "data": {
                    **self._search_paging(resp, total, len(results)),
                    "results": results,
                },
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request to UniProt API timed out"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request to UniProt API failed: {e}"}
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Failed to parse JSON response: {e}",
                "retryable": True,
            }

    def run(self, arguments: Dict[str, Any]) -> Any:
        # Check if this is a search request
        search_type = self.tool_config.get("fields", {}).get("search_type")
        mapping_type = self.tool_config.get("fields", {}).get("mapping_type")

        if search_type == "search":
            return self._handle_search(arguments)
        elif search_type == "uniref_search":
            return self._handle_uniref_search(arguments)
        elif search_type == "uniparc_search":
            return self._handle_uniparc_search(arguments)
        elif mapping_type == "async":
            return self._handle_id_mapping(arguments)

        # Build URL for standard accession-based queries
        local_only_args = {
            "compact",
            "include_publications",
            "publication_source",
            "publication_limit",
            "publication_cursor",
            "comment_limit",
            "comment_offset",
            "feature_limit",
            "feature_offset",
            "reference_limit",
            "reference_offset",
        }
        request_args = {k: v for k, v in arguments.items() if k not in local_only_args}
        url = self._build_url(request_args)
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": (f"UniProt API returned status code: {resp.status_code}"),
                    "detail": resp.text,
                }
            data = resp.json()
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request to UniProt API timed out"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request to UniProt API failed: {e}"}
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Failed to parse JSON response: {e}",
                "retryable": True,
            }

        # If extract_path is configured, extract the corresponding subset.
        # Inactive/deleted entries (confirmed live for Q9ZZZ9: entryType
        # "Inactive") carry none of the normal fields a JSONPath extractor
        # looks for, which previously surfaced as a confusing raw
        # "No data found for JSONPath: ..." error instead of explaining
        # *why* -- give the same clear reason _compact_entry already does.
        if self.extract_path:
            if str(data.get("entryType", "")).lower().startswith("inactive"):
                reason = data.get("inactiveReason", {}) or {}
                detail = (
                    reason.get("deletedReason")
                    or reason.get("mergeDemergeTo", [None])[0]
                )
                reason_type = reason.get("inactiveReasonType", "unknown reason")
                reason_text = f"{reason_type}: {detail}" if detail else reason_type
                return {
                    "status": "error",
                    "error": (
                        f"UniProt entry {arguments.get('accession', '')} is "
                        f"inactive/deleted ({reason_text})."
                    ),
                }
            result = self._extract_data(data, self.extract_path, arguments)

            # Handle empty results
            if isinstance(result, list) and len(result) == 0:
                return {
                    "status": "error",
                    "error": f"No data found for path: {self.extract_path}",
                }
            elif isinstance(result, dict) and "error" in result:
                return result

            return result

        publication_metadata: Dict[str, Any] = {}
        publications = None
        include_publications_default = (
            self.tool_config.get("parameter", {})
            .get("properties", {})
            .get("include_publications", {})
            .get("default", False)
        )
        if arguments.get("include_publications", include_publications_default):
            try:
                publications, publication_metadata = self._get_entry_publications(
                    arguments.get("accession", ""), arguments
                )
            except (requests.exceptions.RequestException, ValueError) as exc:
                publication_metadata = {
                    "publications_complete": False,
                    "publications_error": str(exc),
                    "warning": (
                        "The UniProtKB entry was retrieved, but its separate "
                        "publications endpoint could not be retrieved."
                    ),
                }

        compact_default = (
            self.tool_config.get("parameter", {})
            .get("properties", {})
            .get("compact", {})
            .get("default", False)
        )
        if arguments.get("compact", compact_default) is True:
            result = self._compact_entry(data, arguments)
            if publications is not None:
                result["data"]["additional_publications"] = publications
            result["metadata"].update(publication_metadata)
            return result

        if publications is not None or publication_metadata:
            data = dict(data)
            if publications is not None:
                data["additionalPublications"] = publications
            data["_tooluniverseMetadata"] = publication_metadata
        return data

    # Method bindings for backward compatibility
    def get_entry_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})

    def get_function_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})

    def get_names_taxonomy_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})

    def get_subcellular_location_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})

    def get_disease_variants_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})

    def get_ptm_processing_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})

    def get_sequence_isoforms_by_accession(self, accession: str) -> Any:
        return self.run({"accession": accession})
