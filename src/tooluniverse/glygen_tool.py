# glygen_tool.py
"""
GlyGen REST API tool for ToolUniverse.

GlyGen is a data integration and dissemination project for carbohydrate
and glycoconjugate related data. It integrates glycan structures, glycoproteins,
glycosylation sites, species, enzymes, and publications.

API: https://api.glygen.org
No authentication required. Free for academic/research use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

GLYGEN_BASE_URL = "https://api.glygen.org"

# A GlyGen detail record is wide: P14210 answers 375 publications, 105 SNVs
# and 202 cross-references. Lists are capped and every cap is disclosed with
# the full count beside it, so a short list is never mistaken for a short
# answer.
ROWS_PER_SECTION = 50


def _capped(rows, cap=ROWS_PER_SECTION):
    """`(rows[:cap], full count, was it cut)` for one section of a record."""
    rows = [row for row in (rows or []) if isinstance(row, dict)]
    return rows[:cap], len(rows), len(rows) > cap


def _first_number(row, *keys):
    """The first of `keys` the row actually carries, else None.

    None rather than 0, because a count the API never sent and a count of
    zero are different answers and only one of them is a measurement.
    """
    for key in keys:
        value = row.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
    return None


def _publications(rows, cap=ROWS_PER_SECTION):
    """The papers behind a record, which only ever reached the caller as a count.

    `publication_count: 375` says that evidence exists and not what it is.
    GlyGen answers the title, journal, date, authors and the PubMed reference
    for each one in the same response.
    """
    kept, total, cut = _capped(rows, cap)
    return (
        [
            {
                "title": row.get("title"),
                "journal": row.get("journal"),
                "date": row.get("date"),
                "authors": row.get("authors"),
                "reference": row.get("reference"),
                "evidence": row.get("evidence") or [],
            }
            for row in kept
        ],
        total,
        cut,
    )


@register_tool("GlyGenTool")
class GlyGenTool(BaseTool):
    """
    Tool for querying the GlyGen glycoinformatics database.

    GlyGen provides access to glycan structures, glycoproteins, glycosylation
    sites, biosynthetic enzymes, and related publications from integrated
    sources including GlyTouCan, GlyConnect, UniProt, and PubMed.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "glycan"
        )
        self.query_mode = tool_config.get("fields", {}).get("query_mode", "detail")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the GlyGen API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"GlyGen API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to GlyGen API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"GlyGen API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying GlyGen: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "glycan" and self.query_mode == "detail":
            return self._glycan_detail(arguments)
        elif self.endpoint_type == "glycan" and self.query_mode == "search":
            return self._glycan_search(arguments)
        elif self.endpoint_type == "protein" and self.query_mode == "detail":
            return self._protein_detail(arguments)
        elif self.endpoint_type == "protein" and self.query_mode == "search":
            return self._protein_search(arguments)
        elif self.endpoint_type == "site" and self.query_mode == "detail":
            return self._site_detail(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type/query_mode: {self.endpoint_type}/{self.query_mode}",
            }

    def _glycan_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific glycan by GlyTouCan accession."""
        glytoucan_ac = arguments.get("glytoucan_ac", "")
        if not glytoucan_ac:
            return {"status": "error", "error": "glytoucan_ac parameter is required"}

        url = f"{GLYGEN_BASE_URL}/glycan/detail/{glytoucan_ac}/"
        response = requests.post(
            url,
            json={},
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        raw = response.json()

        # Extract key fields for structured response
        result = {
            "glytoucan_ac": raw.get("glytoucan", {}).get("glytoucan_ac"),
            "mass": raw.get("mass"),
            "number_monosaccharides": raw.get("number_monosaccharides"),
            "glycan_type": raw.get("glycan_type"),
            "iupac": raw.get("iupac"),
            "wurcs": raw.get("wurcs"),
            "classification": raw.get("classification", []),
            "species": [dict(s) for s in raw.get("species", [])],
            "species_count": len(raw.get("species", [])),
            "glycoprotein_count": len(raw.get("glycoprotein", [])),
            "glycoproteins": [
                {**gp, "uniprot_ac": gp.get("uniprot_canonical_ac")}
                for gp in raw.get("glycoprotein", [])
            ],
            "returned_glycoprotein_count": len(raw.get("glycoprotein", [])),
            "publication_count": len(raw.get("publication", [])),
            "composition": raw.get("composition", []),
            "byonic": raw.get("byonic"),
        }

        # The biosynthetic enzymes. The class docstring names them among what
        # GlyGen provides and no tool in this family exposed them, so which
        # glycosyltransferases build a glycan was unreachable through
        # ToolUniverse while sitting in a response already fetched: G17689DH
        # answers 65 of them, with the gene, the UniProt accession, the
        # organism and the evidence for each.
        enzymes, enzyme_total, enzymes_cut = _capped(raw.get("enzyme"))
        result["enzymes"] = [
            {
                "uniprot_canonical_ac": e.get("uniprot_canonical_ac"),
                "gene": e.get("gene"),
                "protein_name": e.get("protein_name"),
                "tax_name": e.get("tax_name"),
                "tax_common_name": e.get("tax_common_name"),
                "tax_id": e.get("tax_id"),
                "gene_link": e.get("gene_link"),
                "xref_key": e.get("xref_key"),
                "xref_id": e.get("xref_id"),
                "evidence": e.get("evidence") or [],
            }
            for e in enzymes
        ]
        result["enzyme_count"] = enzyme_total
        result["enzymes_truncated"] = enzymes_cut

        # The structure as a graph. `number_monosaccharides: 12` was the only
        # thing said about a composition the response spells out residue by
        # residue, each with the residue it is attached to and the linkage.
        residues, residue_total, residues_cut = _capped(
            raw.get("residues"), cap=ROWS_PER_SECTION * 4
        )
        result["residues"] = [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "parent_id": r.get("parentid"),
                "attached_by": r.get("attachedby"),
            }
            for r in residues
        ]
        result["residue_count"] = residue_total
        result["residues_truncated"] = residues_cut

        # Which named motifs the structure contains, and which other
        # GlyTouCan accessions it subsumes or is subsumed by -- the topology
        # and base composition of the same structure, which is how a glycan
        # is matched at a coarser resolution.
        result["motifs"] = [
            {
                "id": m.get("id"),
                "name": m.get("name"),
                "synonym": m.get("synonym"),
                "keywords": m.get("keywords") or [],
            }
            for m in (raw.get("motifs") or [])
            if isinstance(m, dict)
        ]
        subsumption, subsumption_total, subsumption_cut = _capped(
            raw.get("subsumption"), cap=ROWS_PER_SECTION * 2
        )
        result["subsumption"] = [
            {
                "related_accession": x.get("related_accession"),
                "relationship": x.get("relationship"),
            }
            for x in subsumption
        ]
        result["subsumption_count"] = subsumption_total
        result["subsumption_truncated"] = subsumption_cut

        publications, publication_total, publications_cut = _publications(
            raw.get("publication")
        )
        result["publications"] = publications
        result["publication_count"] = publication_total
        result["publications_truncated"] = publications_cut

        # Where the glycan has been observed, and the other databases that
        # hold it. The expression rows name the tissue or cell line as an
        # UBERON/CLO record, which is what makes them joinable.
        expression, expression_total, expression_cut = _capped(raw.get("expression"))
        result["expression"] = [
            {
                "category": e.get("category"),
                "tissue": e.get("tissue"),
                "cell_line": e.get("cell_line"),
                "species": e.get("species"),
                "uniprot_canonical_ac": e.get("uniprot_canonical_ac"),
                "start_pos": e.get("start_pos"),
                "end_pos": e.get("end_pos"),
                "residue": e.get("residue"),
                "evidence": e.get("evidence") or [],
            }
            for e in expression
        ]
        result["expression_count"] = expression_total
        result["expression_truncated"] = expression_cut
        crossref, crossref_total, crossref_cut = _capped(raw.get("crossref"))
        result["crossref"] = [
            {
                "database": x.get("database"),
                "id": x.get("id"),
                "url": x.get("url"),
                "categories": x.get("categories") or [],
            }
            for x in crossref
        ]
        result["crossref_count"] = crossref_total
        result["crossref_truncated"] = crossref_cut

        # How the structure is built, one step at a time: the precursor
        # accession, the residue added and the enzyme that adds it. The
        # enzyme list above says which enzymes are involved; this says what
        # each one does, and it is GlyGen's own GlycoTree reconstruction.
        result["biosynthesis_steps"] = [
            {
                "source": step.get("source"),
                "target": step.get("target"),
                "residue_affected": step.get("residue_affected"),
                "enzymes": step.get("enzymes") or [],
            }
            for step in (raw.get("glycotree_pathways") or [])
            if isinstance(step, dict)
        ]

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "GlyGen",
                "query": glytoucan_ac,
                "endpoint": "glycan/detail",
            },
        }

    def _glycan_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for glycans by mass range, monosaccharide count, organism, etc."""
        # Build search query
        query = {}
        if "mass_min" in arguments or "mass_max" in arguments:
            mass = {}
            if "mass_min" in arguments:
                mass["min"] = arguments["mass_min"]
            if "mass_max" in arguments:
                mass["max"] = arguments["mass_max"]
            query["mass"] = mass

        if "monosaccharide_min" in arguments or "monosaccharide_max" in arguments:
            mono = {}
            if "monosaccharide_min" in arguments:
                mono["min"] = arguments["monosaccharide_min"]
            if "monosaccharide_max" in arguments:
                mono["max"] = arguments["monosaccharide_max"]
            query["number_monosaccharides"] = mono

        if "glycan_type" in arguments:
            query["glycan_type"] = arguments["glycan_type"]

        if not query:
            return {
                "status": "error",
                "error": "At least one search parameter required (mass_min/max, monosaccharide_min/max, glycan_type)",
            }

        pagination_args = self._validate_search_pagination(arguments)
        if isinstance(pagination_args, dict):
            return pagination_args
        offset, limit = pagination_args

        # Step 1: Submit search
        search_url = f"{GLYGEN_BASE_URL}/glycan/search/"
        search_resp = requests.post(
            search_url,
            json=query,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()
        list_id = search_data.get("list_id")

        if not list_id:
            return {
                "status": "success",
                "data": [],
                "metadata": self._search_pagination_metadata(
                    {}, [], offset, limit, {"list_id": None, "query": query}
                ),
            }

        # Step 2: Retrieve results
        list_url = f"{GLYGEN_BASE_URL}/glycan/list/"
        list_body = {
            "id": list_id,
            "offset": offset,
            "limit": limit,
            "sort": "hit_score",
            "order": "desc",
        }
        list_resp = requests.post(
            list_url,
            json=list_body,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        list_resp.raise_for_status()
        list_data = list_resp.json()

        results = []
        for item in list_data.get("results", []):
            results.append(
                {
                    "glytoucan_ac": item.get("glytoucan_ac"),
                    "mass": item.get("mass"),
                    "number_proteins": item.get("number_proteins"),
                    "number_enzymes": item.get("number_enzymes"),
                    "number_species": item.get("number_species"),
                    # The literature behind the glycan. The row reported
                    # three counts -- proteins, enzymes, species -- and not
                    # this one, while the response carried both the count and
                    # the PMIDs themselves. GlyGen joins them with "; " into
                    # one string, so a caller that took it whole would have
                    # a single 36-id "identifier".
                    "publication_count": item.get("publication_count"),
                    "pubmed_ids": [
                        pmid.strip()
                        for pmid in str(item.get("publication") or "").split(";")
                        if pmid.strip()
                    ],
                    # GlyGen renders every glycan; the link was in the row.
                    "image_url": item.get("image_url"),
                    "hit_score": item.get("hit_score"),
                    "byonic": item.get("byonic"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": self._search_pagination_metadata(
                list_data,
                results,
                offset,
                limit,
                {"list_id": list_id, "query": query},
            ),
        }

    @staticmethod
    def _validate_search_pagination(arguments: Dict[str, Any]):
        """Validate GlyGen's one-based list offset without silent clamping."""
        limit = arguments.get("limit", 20)
        offset = arguments.get("offset", 1)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 50
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 50",
                "parameter": "limit",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 1:
            return {
                "status": "error",
                "error": "offset must be a positive one-based integer",
                "parameter": "offset",
            }
        return offset, limit

    @staticmethod
    def _search_pagination_metadata(
        list_data: Dict[str, Any],
        results: list,
        requested_offset: int,
        requested_limit: int,
        extra: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build continuation metadata from GlyGen's list response."""
        pagination = list_data.get("pagination", {})
        offset = pagination.get("offset", requested_offset)
        limit = pagination.get("limit", requested_limit)
        total = pagination.get("total_length", len(results))
        try:
            offset = int(offset)
        except (TypeError, ValueError):
            offset = requested_offset
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = requested_limit
        try:
            total = int(total)
        except (TypeError, ValueError):
            total = len(results)
        returned_count = len(results)
        has_more = offset - 1 + returned_count < total
        metadata = {
            "total_results": total,
            "returned_count": returned_count,
            "offset": offset,
            "requested_offset": requested_offset,
            "limit": limit,
            "has_more": has_more,
            "next_offset": offset + returned_count
            if returned_count and has_more
            else None,
            "truncated": has_more,
            "result_set_complete": not has_more,
        }
        metadata.update(extra)
        return metadata

    def _protein_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get glycoprotein details including glycosylation sites."""
        uniprot_ac = arguments.get("uniprot_ac", "")
        if not uniprot_ac:
            return {"status": "error", "error": "uniprot_ac parameter is required"}

        url = f"{GLYGEN_BASE_URL}/protein/detail/{uniprot_ac}/"
        response = requests.post(
            url,
            json={},
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        raw = response.json()

        # Extract key fields
        protein_names = raw.get("protein_names", [])
        gene_names = raw.get("gene_names", [])
        glycosylation = raw.get("glycosylation", [])
        species = raw.get("species", [])

        result = {
            "protein_name": protein_names[0].get("name") if protein_names else None,
            "gene_names": [g.get("name") for g in gene_names],
            "gene_name_count": len(gene_names),
            "gene_name_details": [dict(g) for g in gene_names],
            "species": species[0].get("name") if species else None,
            "mass": raw.get("mass"),
            "sequence_length": len(raw.get("sequence", {}).get("sequence", "")),
            "glycosylation_count": len(glycosylation),
            "glycosylation_sites": [
                {
                    **g,
                    "position": g.get("start_pos"),
                    "residue": g.get("residue"),
                    "type": g.get("type"),
                    "glytoucan_ac": g.get("glytoucan_ac"),
                    "site_category": g.get("site_category"),
                }
                for g in glycosylation
            ],
            "returned_glycosylation_count": len(glycosylation),
            "function": raw.get("function", [{}])[0].get("annotation")
            if raw.get("function")
            else None,
        }

        # Four counts and none of the four lists. The description said it
        # "reports associated disease/pathway/SNV/publication counts", which
        # was true and still left a caller unable to name one of them from a
        # response that holds all four: P14210 answers 46 diseases with their
        # ids and evidence, 105 SNVs with position, substitution and the
        # glycosylation effect, 19 pathways with resource links and 375
        # papers. The counts stay, with the things beside them.
        diseases, disease_total, diseases_cut = _capped(raw.get("disease"))
        result["diseases"] = [
            {
                "disease_id": d.get("disease_id"),
                "name": (d.get("recommended_name") or {}).get("name"),
                "id": (d.get("recommended_name") or {}).get("id"),
                "resource": (d.get("recommended_name") or {}).get("resource"),
                "description": (d.get("recommended_name") or {}).get("description"),
                "evidence": d.get("evidence") or [],
            }
            for d in diseases
        ]
        result["disease_count"] = disease_total
        result["diseases_truncated"] = diseases_cut

        snvs, snv_total, snvs_cut = _capped(raw.get("snv"))
        result["snvs"] = [
            {
                "chr_id": v.get("chr_id"),
                "chr_pos": v.get("chr_pos"),
                "ref_nt": v.get("ref_nt"),
                "alt_nt": v.get("alt_nt"),
                "start_pos": v.get("start_pos"),
                "end_pos": v.get("end_pos"),
                "sequence_org": v.get("sequence_org"),
                "sequence_mut": v.get("sequence_mut"),
                # GlyGen's own reading: what the substitution does to the
                # glycosylation, which is the question this database answers
                # and no other source in the catalogue carries.
                "glycoeffect": v.get("glycoeffect"),
                "site_label": v.get("site_lbl"),
                "keywords": v.get("keywords") or [],
                "comment": v.get("comment"),
                "evidence": v.get("evidence") or [],
            }
            for v in snvs
        ]
        result["snv_count"] = snv_total
        result["snvs_truncated"] = snvs_cut

        pathways, pathway_total, pathways_cut = _capped(raw.get("pathway"))
        result["pathways"] = [
            {"id": x.get("id"), "resource": x.get("resource"), "url": x.get("url")}
            for x in pathways
        ]
        result["pathway_count"] = pathway_total
        result["pathways_truncated"] = pathways_cut

        publications, publication_total, publications_cut = _publications(
            raw.get("publication")
        )
        result["publications"] = publications
        result["publication_count"] = publication_total
        result["publications_truncated"] = publications_cut

        # Where the protein is expressed, with the score behind "present".
        result["expression_tissue"] = [
            {
                "tissue": t.get("tissue"),
                "present": t.get("present"),
                "score": t.get("score"),
                "evidence": t.get("evidence") or [],
            }
            for t in (raw.get("expression_tissue") or [])
            if isinstance(t, dict)
        ]
        # Deliberately not carried, because the catalogue answers them
        # elsewhere and whole: the sequence itself, the 202 cross-references,
        # the domain list and the structures, all of which the UniProt family
        # of tools returns for the same accession. What is carried here is
        # what is particular to GlyGen.

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "GlyGen",
                "query": uniprot_ac,
                "endpoint": "protein/detail",
            },
        }

    def _protein_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for glycoproteins by organism, glycosylation type, etc."""
        query = {}

        if "organism_id" in arguments:
            query["organism"] = {"id": arguments["organism_id"]}

        if "glycosylation_evidence" in arguments:
            query["glycosylation_evidence"] = arguments["glycosylation_evidence"]

        if "glycosylation_type" in arguments:
            query["glycosylation_type"] = arguments["glycosylation_type"]

        if "protein_name" in arguments:
            query["protein_name"] = arguments["protein_name"]

        if "gene_name" in arguments:
            query["gene_name"] = arguments["gene_name"]

        if not query:
            return {
                "status": "error",
                "error": "At least one search parameter required (organism_id, glycosylation_evidence, glycosylation_type, protein_name, gene_name)",
            }

        pagination_args = self._validate_search_pagination(arguments)
        if isinstance(pagination_args, dict):
            return pagination_args
        offset, limit = pagination_args

        # Step 1: Submit search
        search_url = f"{GLYGEN_BASE_URL}/protein/search/"
        search_resp = requests.post(
            search_url,
            json=query,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()
        list_id = search_data.get("list_id")

        if not list_id:
            return {
                "status": "success",
                "data": [],
                "metadata": self._search_pagination_metadata(
                    {}, [], offset, limit, {"list_id": None, "query": query}
                ),
            }

        # Step 2: Retrieve results
        list_url = f"{GLYGEN_BASE_URL}/protein/list/"
        list_body = {
            "id": list_id,
            "offset": offset,
            "limit": limit,
            "sort": "hit_score",
            "order": "desc",
        }
        list_resp = requests.post(
            list_url,
            json=list_body,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        list_resp.raise_for_status()
        list_data = list_resp.json()

        results = []
        for item in list_data.get("results", []):
            # `total_n_glycosites` and `total_o_glycosites` are not keys a
            # /protein/list row carries. With `or 0` around each, the sum came
            # out as 0 on every row of every search -- from a tool whose
            # description promises "glycosylation-site counts" -- and a zero
            # reads as a measurement, not as a field that was never there.
            # The row states `reported_n_glycosites` and
            # `reported_o_glycosites`, and separately how many of those sites
            # have a glycan identified on them.
            n_sites = _first_number(item, "reported_n_glycosites", "total_n_glycosites")
            o_sites = _first_number(item, "reported_o_glycosites", "total_o_glycosites")
            total = None
            if n_sites is not None or o_sites is not None:
                total = (n_sites or 0) + (o_sites or 0)
            results.append(
                {
                    "uniprot_canonical_ac": item.get("uniprot_canonical_ac"),
                    "protein_name": item.get("protein_name"),
                    "gene_name": item.get("gene_name"),
                    "organism": item.get("organism"),
                    # Null, not 0, when the row reports neither count: one
                    # means "no sites", the other "nothing said".
                    "glycosylation_count": total,
                    # N-linked and O-linked are different questions and the
                    # sum answered neither.
                    "n_linked_site_count": n_sites,
                    "o_linked_site_count": o_sites,
                    "n_linked_sites_with_glycan": _first_number(
                        item, "reported_n_glycosites_with_glycan"
                    ),
                    "o_linked_sites_with_glycan": _first_number(
                        item, "reported_o_glycosites_with_glycan"
                    ),
                    "predicted_glycosite_count": _first_number(
                        item, "predicted_glycosites"
                    ),
                    "fully_resolved_glycan_count": _first_number(
                        item, "reported_fully_resolved_glycans"
                    ),
                    "publication_count": _first_number(item, "publication_count"),
                    "mass": item.get("mass"),
                    "sequence_length": item.get("length"),
                    "uniprot_id": item.get("uniprot_id") or [],
                    "refseq_ac": item.get("refseq_ac") or [],
                    # RefSeq's names for the same protein and gene, which can
                    # differ from UniProt's and are what a RefSeq-indexed
                    # result would be looked up under.
                    "protein_names_refseq": item.get("protein_names_refseq") or [],
                    "gene_names_refseq": item.get("gene_names_refseq") or [],
                    # The protein's enzyme classification, which a search for
                    # glycoproteins by organism returned 51 of and showed none.
                    "ec_numbers": item.get("ec_number_list") or [],
                    "hit_score": item.get("hit_score"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": self._search_pagination_metadata(
                list_data,
                results,
                offset,
                limit,
                {"list_id": list_id, "query": query},
            ),
        }

    def _site_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get details about a specific glycosylation site."""
        site_id = arguments.get("site_id", "")
        if not site_id:
            return {
                "status": "error",
                "error": "site_id parameter is required (format: UniProtAC-isoform.start.end, e.g. P02724-1.52.52)",
            }

        url = f"{GLYGEN_BASE_URL}/site/detail/{site_id}/"
        response = requests.post(
            url,
            json={},
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        raw = response.json()

        result = {
            "site_id": raw.get("id"),
            "uniprot_ac": raw.get("uniprot_canonical_ac"),
            "start_pos": raw.get("start_pos"),
            "end_pos": raw.get("end_pos"),
            "site_seq": raw.get("site_seq"),
            "start_aa": raw.get("start_aa"),
            "upstream_seq": raw.get("up_seq"),
            "downstream_seq": raw.get("down_seq"),
            "glycosylation": raw.get("glycosylation", []),
            "phosphorylation": raw.get("phosphorylation", []),
            "snv": raw.get("snv", []),
            "mutagenesis": raw.get("mutagenesis", []),
            "species": raw.get("species"),
            "all_sites_count": len(raw.get("all_sites", [])),
            "categories": raw.get("categories", []),
        }

        # Which protein the site is in. The tool answered a UniProt accession
        # and left the caller to look up what it is, from a response that
        # names it: P02724-1.52.52 is a site in Glycophorin-A, gene GYPA.
        result["protein_name"] = raw.get("protein_name")
        result["gene_name"] = raw.get("gene_name")

        # Glycation is the same kind of site annotation as the phosphorylation
        # and mutagenesis the description promises, and it was the one of the
        # three that was never read.
        result["glycation"] = raw.get("glycation") or []

        # The annotated sites around this one, with how far and in which
        # direction, which is what "site-specific glycosylation and its
        # biological consequences" is read against: a glycosylation site 20
        # residues downstream of an SNV site is a different finding from an
        # isolated one.
        neighbors, neighbor_total, neighbors_cut = _capped(raw.get("neighbors"))
        result["neighbors"] = [
            {
                "id": n.get("id"),
                "distance": n.get("distance"),
                "direction": n.get("direction"),
                "categories": n.get("categories") or [],
            }
            for n in neighbors
        ]
        result["neighbor_count"] = neighbor_total
        result["neighbors_truncated"] = neighbors_cut

        publications, publication_total, publications_cut = _publications(
            raw.get("publication")
        )
        result["publications"] = publications
        result["publication_count"] = publication_total
        result["publications_truncated"] = publications_cut

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "GlyGen",
                "query": site_id,
                "endpoint": "site/detail",
            },
        }
