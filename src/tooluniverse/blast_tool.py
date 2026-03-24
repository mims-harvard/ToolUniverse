from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool

# Optional dependency - Biopython
try:
    from Bio.Blast import NCBIWWW, NCBIXML
    from Bio.Seq import Seq

    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False


@register_tool("NCBIBlastTool")
class NCBIBlastTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.timeout = 300  # BLAST can take a long time
        self.max_wait_time = 600  # Maximum wait time for results

    def _parse_blast_results(self, blast_xml: str) -> Dict[str, Any]:
        """Parse BLAST XML results into structured data"""
        try:
            from io import StringIO

            blast_record = NCBIXML.read(StringIO(blast_xml))

            results = {
                "query_id": blast_record.query_id,
                "query_length": blast_record.query_length,
                "database": blast_record.database,
                "algorithm": blast_record.application,
                "alignments": [],
            }

            for alignment in blast_record.alignments:
                alignment_data = {
                    "hit_id": getattr(alignment, "hit_id", "unknown"),
                    "hit_def": getattr(alignment, "hit_def", "unknown"),
                    "hit_length": getattr(alignment, "length", 0),
                    "hsps": [],
                }

                for hsp in alignment.hsps:
                    hsp_data = {
                        "score": getattr(hsp, "score", 0),
                        "bits": getattr(hsp, "bits", 0),
                        "expect": getattr(hsp, "expect", 0),
                        "identities": getattr(hsp, "identities", 0),
                        "positives": getattr(hsp, "positives", 0),
                        "gaps": getattr(hsp, "gaps", 0),
                        "align_length": getattr(hsp, "align_length", 0),
                        "query_start": getattr(hsp, "query_start", 0),
                        "query_end": getattr(hsp, "query_end", 0),
                        "hit_start": getattr(hsp, "sbjct_start", 0),
                        "hit_end": getattr(hsp, "sbjct_end", 0),
                        "query": getattr(hsp, "query", ""),
                        "match": getattr(hsp, "match", ""),
                        "sbjct": getattr(hsp, "sbjct", ""),
                    }
                    alignment_data["hsps"].append(hsp_data)

                results["alignments"].append(alignment_data)

            return results

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to parse BLAST results: {str(e)}",
                "raw_xml": (
                    blast_xml[:1000] + "..." if len(blast_xml) > 1000 else blast_xml
                ),
            }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute BLAST search using NCBI Web service"""
        # Check if Biopython is available
        if not BIOPYTHON_AVAILABLE:
            return {
                "status": "error",
                "error": "Biopython is required for BLAST tools. Install with: pip install biopython",
            }

        try:
            sequence = arguments.get("sequence", "")

            # Determine blast_type from tool name or arguments
            tool_name = self.tool_config.get("name", "")
            if "protein" in tool_name.lower():
                default_blast_type = "blastp"
                default_database = "nr"
            else:
                default_blast_type = "blastn"
                default_database = "nt"

            blast_type = arguments.get("blast_type", default_blast_type)
            database = arguments.get("database", default_database)
            expect = arguments.get("expect", 10.0)
            hitlist_size = arguments.get("hitlist_size", 50)

            if not sequence:
                return {
                    "status": "error",
                    "error": "Missing required parameter: sequence",
                }

            # Validate sequence
            try:
                seq_obj = Seq(sequence)
                if len(seq_obj) < 10:
                    return {
                        "status": "error",
                        "error": "Sequence too short (minimum 10 residues)",
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Invalid sequence format: {str(e)}",
                }

            # Perform BLAST search
            result_handle = NCBIWWW.qblast(
                blast_type,
                database,
                sequence,
                expect=expect,
                hitlist_size=hitlist_size,
                format_type="XML",
            )

            # Read results
            blast_xml = result_handle.read()
            result_handle.close()

            # Parse results
            parsed_results = self._parse_blast_results(blast_xml)

            if "error" in parsed_results:
                return {
                    "status": "error",
                    "error": parsed_results["error"],
                    "raw_data": parsed_results.get("raw_xml", ""),
                }

            return {
                "status": "success",
                "data": parsed_results,
                "query_sequence": sequence,
                "blast_type": blast_type,
                "database": database,
                "hit_count": len(parsed_results["alignments"]),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"BLAST search failed: {str(e)}",
            }
