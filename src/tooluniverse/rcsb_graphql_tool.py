# rcsb_graphql_tool.py
"""
RCSB PDB GraphQL Data API tool for ToolUniverse.

The RCSB PDB Data API (GraphQL) provides rich, structured access to
PDB structure details, ligand/chemical component information, and
polymer entity data. Supports batch queries for multiple entries.

API: https://data.rcsb.org/graphql
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

RCSB_GRAPHQL_URL = "https://data.rcsb.org/graphql"


@register_tool("RCSBGraphQLTool")
class RCSBGraphQLTool(BaseTool):
    """
    Tool for querying the RCSB PDB Data API via GraphQL.

    Supports:
    - Structure summary (title, resolution, method, citation, etc.)
    - Chemical component / ligand details (formula, SMILES, targets)
    - Polymer entity details (sequence, annotations, descriptions)

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "structure_summary")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the RCSB GraphQL query."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"RCSB Data API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to RCSB Data API"}
        except Exception as e:
            return {"error": f"Unexpected error querying RCSB Data API: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate GraphQL query."""
        if self.endpoint == "structure_summary":
            return self._get_structure_summary(arguments)
        elif self.endpoint == "ligand_info":
            return self._get_ligand_info(arguments)
        elif self.endpoint == "polymer_entity":
            return self._get_polymer_entity(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _execute_graphql(self, query_str: str) -> Dict[str, Any]:
        """Execute a GraphQL query against the RCSB Data API."""
        response = requests.post(
            RCSB_GRAPHQL_URL,
            json={"query": query_str},
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            error_msgs = [e.get("message", "") for e in result["errors"]]
            return {"error": f"GraphQL errors: {'; '.join(error_msgs)}"}

        return result

    def _get_structure_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive structure summary for one or more PDB IDs."""
        pdb_ids = arguments.get("pdb_ids")
        pdb_id = arguments.get("pdb_id")

        if pdb_id and not pdb_ids:
            pdb_ids = [pdb_id]
        elif isinstance(pdb_ids, str):
            pdb_ids = [p.strip() for p in pdb_ids.split(",")]

        if not pdb_ids:
            return {
                "error": "pdb_id or pdb_ids parameter is required (e.g., '4HHB' or '4HHB,1TUP')"
            }

        # Uppercase PDB IDs
        pdb_ids = [p.upper().strip() for p in pdb_ids]

        ids_str = '", "'.join(pdb_ids)
        query_str = f'''{{
            entries(entry_ids: ["{ids_str}"]) {{
                rcsb_id
                struct {{
                    title
                }}
                rcsb_entry_info {{
                    resolution_combined
                    molecular_weight
                    deposited_atom_count
                    polymer_entity_count
                    nonpolymer_entity_count
                    experimental_method
                }}
                rcsb_accession_info {{
                    deposit_date
                    initial_release_date
                }}
                rcsb_primary_citation {{
                    pdbx_database_id_PubMed
                    title
                    journal_abbrev
                    year
                }}
                exptl {{
                    method
                }}
                cell {{
                    length_a
                    length_b
                    length_c
                }}
            }}
        }}'''

        result = self._execute_graphql(query_str)
        if "error" in result:
            return result

        entries = result.get("data", {}).get("entries", [])
        if not entries:
            return {
                "data": [],
                "metadata": {
                    "source": "RCSB PDB GraphQL Data API",
                    "requested_ids": pdb_ids,
                    "returned": 0,
                },
            }

        structures = []
        for entry in entries:
            if entry is None:
                continue
            info = entry.get("rcsb_entry_info") or {}
            accession = entry.get("rcsb_accession_info") or {}
            citation = entry.get("rcsb_primary_citation") or {}
            struct = entry.get("struct") or {}
            cell = entry.get("cell") or {}

            resolution = info.get("resolution_combined")
            if isinstance(resolution, list) and resolution:
                resolution = resolution[0]

            structures.append(
                {
                    "pdb_id": entry.get("rcsb_id"),
                    "title": struct.get("title"),
                    "resolution": resolution,
                    "molecular_weight_kda": info.get("molecular_weight"),
                    "atom_count": info.get("deposited_atom_count"),
                    "polymer_entity_count": info.get("polymer_entity_count"),
                    "nonpolymer_entity_count": info.get("nonpolymer_entity_count"),
                    "experimental_method": info.get("experimental_method"),
                    "deposit_date": accession.get("deposit_date"),
                    "release_date": accession.get("initial_release_date"),
                    "citation_pubmed_id": citation.get("pdbx_database_id_PubMed"),
                    "citation_title": citation.get("title"),
                    "citation_journal": citation.get("journal_abbrev"),
                    "citation_year": citation.get("year"),
                    "unit_cell_a": cell.get("length_a"),
                    "unit_cell_b": cell.get("length_b"),
                    "unit_cell_c": cell.get("length_c"),
                }
            )

        return {
            "data": structures,
            "metadata": {
                "source": "RCSB PDB GraphQL Data API",
                "requested_ids": pdb_ids,
                "returned": len(structures),
            },
        }

    def _get_ligand_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get chemical component (ligand) information from PDB."""
        comp_id = arguments.get("comp_id", "")
        if not comp_id:
            return {
                "error": "comp_id parameter is required (e.g., 'ATP', 'HEM', 'NAG')"
            }

        comp_id = comp_id.upper().strip()

        query_str = f'''{{
            chem_comp(comp_id: "{comp_id}") {{
                chem_comp {{
                    id
                    name
                    formula
                    formula_weight
                    type
                    mon_nstd_parent_comp_id
                }}
                rcsb_chem_comp_descriptor {{
                    InChIKey
                    SMILES
                }}
                rcsb_chem_comp_info {{
                    initial_release_date
                }}
                rcsb_chem_comp_target {{
                    target_actions
                    comp_id
                    name
                    provenance_source
                    reference_database_accession_code
                    reference_database_name
                }}
            }}
        }}'''

        result = self._execute_graphql(query_str)
        if "error" in result:
            return result

        comp = result.get("data", {}).get("chem_comp")
        if not comp:
            return {"error": f"Chemical component '{comp_id}' not found in PDB"}

        basic = comp.get("chem_comp") or {}
        descriptor = comp.get("rcsb_chem_comp_descriptor") or {}
        info = comp.get("rcsb_chem_comp_info") or {}
        targets_raw = comp.get("rcsb_chem_comp_target") or []

        targets = []
        for t in targets_raw:
            targets.append(
                {
                    "name": t.get("name"),
                    "actions": t.get("target_actions"),
                    "provenance": t.get("provenance_source"),
                    "accession": t.get("reference_database_accession_code"),
                    "database": t.get("reference_database_name"),
                }
            )

        return {
            "data": {
                "comp_id": basic.get("id"),
                "name": basic.get("name"),
                "formula": basic.get("formula"),
                "formula_weight": basic.get("formula_weight"),
                "type": basic.get("type"),
                "parent_comp_id": basic.get("mon_nstd_parent_comp_id"),
                "inchikey": descriptor.get("InChIKey"),
                "smiles": descriptor.get("SMILES"),
                "initial_release_date": info.get("initial_release_date"),
                "targets": targets,
            },
            "metadata": {
                "source": "RCSB PDB GraphQL Data API",
                "comp_id": comp_id,
                "target_count": len(targets),
            },
        }

    def _get_polymer_entity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get polymer entity details (sequence, annotations, etc.)."""
        entity_ids = arguments.get("entity_ids")
        pdb_id = arguments.get("pdb_id")
        entity_num = arguments.get("entity_num") or 1

        if pdb_id and not entity_ids:
            entity_ids = [f"{pdb_id.upper().strip()}_{entity_num}"]
        elif isinstance(entity_ids, str):
            entity_ids = [e.strip() for e in entity_ids.split(",")]

        if not entity_ids:
            return {
                "error": "pdb_id or entity_ids parameter is required (e.g., pdb_id='4HHB' or entity_ids='4HHB_1,4HHB_2')"
            }

        ids_str = '", "'.join(entity_ids)
        query_str = f'''{{
            polymer_entities(entity_ids: ["{ids_str}"]) {{
                rcsb_id
                rcsb_polymer_entity {{
                    pdbx_description
                }}
                entity_poly {{
                    pdbx_strand_id
                    rcsb_entity_polymer_type
                    type
                    pdbx_seq_one_letter_code_can
                }}
                rcsb_polymer_entity_annotation {{
                    annotation_id
                    type
                    description
                }}
                rcsb_entity_source_organism {{
                    scientific_name
                    ncbi_taxonomy_id
                }}
            }}
        }}'''

        result = self._execute_graphql(query_str)
        if "error" in result:
            return result

        entities = result.get("data", {}).get("polymer_entities", [])
        if not entities:
            return {
                "data": [],
                "metadata": {
                    "source": "RCSB PDB GraphQL Data API",
                    "requested_ids": entity_ids,
                    "returned": 0,
                },
            }

        polymer_list = []
        for entity in entities:
            if entity is None:
                continue
            desc_obj = entity.get("rcsb_polymer_entity") or {}
            poly = entity.get("entity_poly") or {}
            annotations_raw = entity.get("rcsb_polymer_entity_annotation") or []
            organisms_raw = entity.get("rcsb_entity_source_organism") or []

            annotations = []
            for a in annotations_raw:
                annotations.append(
                    {
                        "id": a.get("annotation_id"),
                        "type": a.get("type"),
                        "description": a.get("description"),
                    }
                )

            organisms = []
            for o in organisms_raw:
                organisms.append(
                    {
                        "scientific_name": o.get("scientific_name"),
                        "ncbi_taxonomy_id": o.get("ncbi_taxonomy_id"),
                    }
                )

            sequence = poly.get("pdbx_seq_one_letter_code_can", "")

            polymer_list.append(
                {
                    "entity_id": entity.get("rcsb_id"),
                    "description": desc_obj.get("pdbx_description"),
                    "chain_ids": poly.get("pdbx_strand_id"),
                    "polymer_type": poly.get("rcsb_entity_polymer_type"),
                    "entity_type": poly.get("type"),
                    "sequence": sequence,
                    "sequence_length": len(sequence) if sequence else 0,
                    "annotations": annotations,
                    "source_organisms": organisms,
                }
            )

        return {
            "data": polymer_list,
            "metadata": {
                "source": "RCSB PDB GraphQL Data API",
                "requested_ids": entity_ids,
                "returned": len(polymer_list),
            },
        }
