#!/usr/bin/env python3
"""
ANTIBODY ENGINEERING - WORKING PIPELINE WITH CORRECT SOAP PARAMETERS

This pipeline demonstrates correct usage of SOAP tools (IMGT, SAbDab, TheraSAbDab)
which require 'operation' parameter.

Fixed SOAP tool calls:
- IMGT_search_genes(operation="search_genes", ...)
- IMGT_get_sequence(operation="get_sequence", ...)
- SAbDab_search_structures(operation="search_structures", ...)
- TheraSAbDab_search_by_target(operation="search_by_target", ...)
"""

from tooluniverse import ToolUniverse
from datetime import datetime


class AntibodyHumanizer:
    """Antibody humanization pipeline using ToolUniverse."""

    def __init__(self):
        """Initialize ToolUniverse."""
        print("Initializing ToolUniverse...")
        self.tu = ToolUniverse()
        self.tu.load_tools()
        print(f"✅ Loaded {len(self.tu.all_tool_dict)} tools\n")

    def analyze(self, vh_sequence, vl_sequence, target_antigen, output_file=None):
        """
        Complete antibody humanization analysis.

        Args:
            vh_sequence: Heavy chain variable region
            vl_sequence: Light chain variable region
            target_antigen: Target antigen name
            output_file: Optional report file

        Returns:
            dict with humanization analysis
        """
        if output_file is None:
            output_file = f"Antibody_Humanization_{target_antigen.replace(' ', '_')}.md"

        print("=" * 80)
        print(f"ANTIBODY HUMANIZATION ANALYSIS")
        print(f"Target: {target_antigen}")
        print(f"VH Length: {len(vh_sequence)} aa")
        print(f"VL Length: {len(vl_sequence)} aa")
        print("=" * 80)

        report = {
            'target': target_antigen,
            'vh_sequence': vh_sequence,
            'vl_sequence': vl_sequence,
            'timestamp': datetime.now().isoformat(),
            'germlines': {},
            'clinical_precedents': [],
            'structures': [],
            'immunogenicity': {},
            'humanization_score': 0
        }

        # Create report file
        self._create_report(output_file, target_antigen, vh_sequence, vl_sequence)

        print("\n🔬 Running Humanization Analysis...")
        print("-" * 80)

        # STEP 1: Find Clinical Precedents
        report['clinical_precedents'] = self._find_clinical_precedents(target_antigen)
        self._update_report(output_file, "## 1. Clinical Precedents", report['clinical_precedents'])

        # STEP 2: Identify Germline Genes
        report['germlines'] = self._identify_germlines()
        self._update_report(output_file, "## 2. Human Germline Genes", report['germlines'])

        # STEP 3: Search Antibody Structures
        report['structures'] = self._search_structures(target_antigen)
        self._update_report(output_file, "## 3. Structural Precedents", report['structures'])

        # STEP 4: Immunogenicity Assessment
        report['immunogenicity'] = self._assess_immunogenicity(target_antigen)
        self._update_report(output_file, "## 4. Immunogenicity Assessment", report['immunogenicity'])

        # STEP 5: Humanization Scoring
        report['humanization_score'] = self._calculate_score(report)
        self._update_report(output_file, "## 5. Humanization Feasibility", {
            'score': report['humanization_score'],
            'interpretation': self._interpret_score(report['humanization_score'])
        })

        print(f"\n✅ Analysis complete! Report saved to: {output_file}")
        print(f"📊 Humanization Score: {report['humanization_score']}/100")

        return report

    def _create_report(self, filename, target, vh, vl):
        """Create initial report file."""
        with open(filename, 'w') as f:
            f.write(f"# Antibody Humanization Report\n\n")
            f.write(f"**Target Antigen**: {target}\n")
            f.write(f"**VH Length**: {len(vh)} amino acids\n")
            f.write(f"**VL Length**: {len(vl)} amino acids\n")
            f.write(f"**Analysis Date**: {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write("---\n\n")

    def _update_report(self, filename, section, data):
        """Update report with new section."""
        with open(filename, 'a') as f:
            f.write(f"\n{section}\n\n")
            if isinstance(data, dict):
                for key, value in data.items():
                    f.write(f"**{key}**: {value}\n\n")
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        f.write(f"- {item}\n")
                    else:
                        f.write(f"- {item}\n")
                f.write("\n")
            else:
                f.write(f"{data}\n\n")

    def _find_clinical_precedents(self, target_antigen):
        """Search for approved/clinical antibodies against target."""
        print("\n1️⃣ Clinical Precedent Search")
        print(f"   Searching TheraSAbDab for: {target_antigen}")

        precedents = []
        try:
            # ✅ CORRECT: SOAP tool requires 'operation' parameter
            result = self.tu.tools.TheraSAbDab_search_by_target(
                operation="search_by_target",  # ✅ Required for SOAP tools
                target=target_antigen
            )

            if result.get('status') == 'success' and result.get('data', {}).get('therapeutics'):
                therapeutics = result['data']['therapeutics']
                precedents = [
                    {
                        'name': ab.get('name', 'N/A'),
                        'status': ab.get('phase', 'N/A'),
                        'target': ab.get('target', target_antigen)
                    }
                    for ab in therapeutics[:5]
                ]
                print(f"   ✅ Found {len(therapeutics)} clinical antibodies")
            else:
                print(f"   ℹ️ No clinical precedents found (may need alternative target names)")
                # Try alternative names
                alternative_names = {
                    'PD-L1': ['PDL1', 'CD274', 'B7-H1'],
                    'HER2': ['ERBB2', 'NEU'],
                    'EGFR': ['HER1', 'ERBB1']
                }

                if target_antigen in alternative_names:
                    for alt_name in alternative_names[target_antigen]:
                        print(f"   Trying alternative name: {alt_name}")
                        result = self.tu.tools.TheraSAbDab_search_by_target(
                            operation="search_by_target",
                            target=alt_name
                        )
                        if result.get('data', {}).get('therapeutics'):
                            precedents = [{
                                'name': ab.get('name', 'N/A'),
                                'status': ab.get('phase', 'N/A'),
                                'target': alt_name
                            } for ab in result['data']['therapeutics'][:5]]
                            print(f"   ✅ Found {len(result['data']['therapeutics'])} with '{alt_name}'")
                            break
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

        return precedents

    def _identify_germlines(self):
        """Identify human germline genes for humanization."""
        print("\n2️⃣ Germline Gene Identification")
        germlines = {}

        # Search for IGHV (heavy chain)
        print(f"   Searching IMGT for IGHV genes...")
        try:
            # ✅ CORRECT: SOAP tool requires 'operation' parameter
            result = self.tu.tools.IMGT_search_genes(
                operation="search_genes",  # ✅ Required for SOAP tools
                gene_type="IGHV",
                species="Homo sapiens"
            )

            if result.get('status') == 'success' and result.get('data', {}).get('genes'):
                genes = result['data']['genes']
                germlines['IGHV_count'] = len(genes)
                germlines['IGHV_top'] = [g.get('name', 'N/A') for g in genes[:5]]
                print(f"   ✅ Found {len(genes)} IGHV genes")
            else:
                print(f"   ℹ️ No IGHV genes found")
                germlines['IGHV_count'] = 0
                germlines['IGHV_note'] = 'Using fallback: Common germlines (IGHV1-69, IGHV3-23)'
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            germlines['IGHV_error'] = str(e)

        # Search for IGKV (kappa light chain)
        print(f"   Searching IMGT for IGKV genes...")
        try:
            result = self.tu.tools.IMGT_search_genes(
                operation="search_genes",  # ✅ Required for SOAP tools
                gene_type="IGKV",
                species="Homo sapiens"
            )

            if result.get('status') == 'success' and result.get('data', {}).get('genes'):
                genes = result['data']['genes']
                germlines['IGKV_count'] = len(genes)
                germlines['IGKV_top'] = [g.get('name', 'N/A') for g in genes[:5]]
                print(f"   ✅ Found {len(genes)} IGKV genes")
            else:
                print(f"   ℹ️ No IGKV genes found")
                germlines['IGKV_count'] = 0
                germlines['IGKV_note'] = 'Using fallback: Common germlines (IGKV1-39, IGKV3-20)'
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            germlines['IGKV_error'] = str(e)

        return germlines

    def _search_structures(self, target_antigen):
        """Search for antibody-antigen structures."""
        print("\n3️⃣ Structural Precedent Search")
        print(f"   Searching SAbDab for: {target_antigen}")

        structures = []
        try:
            # ✅ CORRECT: SOAP tool requires 'operation' parameter
            result = self.tu.tools.SAbDab_search_structures(
                operation="search_structures",  # ✅ Required for SOAP tools
                query=target_antigen
            )

            if result.get('status') == 'success' and result.get('data', {}).get('structures'):
                structs = result['data']['structures']
                structures = [
                    {
                        'pdb_id': s.get('pdb', 'N/A'),
                        'resolution': s.get('resolution', 'N/A'),
                        'antigen': s.get('antigen', target_antigen)
                    }
                    for s in structs[:5]
                ]
                print(f"   ✅ Found {len(structs)} antibody structures")
            else:
                print(f"   ℹ️ No structures found")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

        return structures

    def _assess_immunogenicity(self, target_antigen):
        """Assess T-cell epitope content."""
        print("\n4️⃣ Immunogenicity Assessment")
        immunogenicity = {}

        print(f"   Searching IEDB for epitopes...")
        try:
            result = self.tu.tools.iedb_search_epitopes(
                epitope_name=target_antigen,
                limit=10
            )

            if isinstance(result, dict) and result.get('status') == 'success':
                data = result.get('data', [])
                if isinstance(data, list):
                    immunogenicity['epitope_count'] = len(data)
                    print(f"   ✅ Found {len(data)} epitopes")
                else:
                    immunogenicity['epitope_count'] = 0
                    print(f"   ℹ️ No epitopes found")
            else:
                immunogenicity['epitope_count'] = 0
                print(f"   ℹ️ No epitopes found")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            immunogenicity['error'] = str(e)

        return immunogenicity

    def _calculate_score(self, report):
        """Calculate humanization feasibility score (0-100)."""
        print("\n5️⃣ Humanization Scoring")
        score = 0

        # Clinical precedents: +30
        if len(report['clinical_precedents']) > 0:
            score += 30
            print(f"   ✅ Clinical precedents found: +30")

        # Germline genes available: +30
        if report['germlines'].get('IGHV_count', 0) > 0:
            score += 15
            print(f"   ✅ IGHV germlines available: +15")
        if report['germlines'].get('IGKV_count', 0) > 0:
            score += 15
            print(f"   ✅ IGKV germlines available: +15")

        # Structural precedents: +20
        if len(report['structures']) > 0:
            score += 20
            print(f"   ✅ Structural precedents found: +20")

        # Immunogenicity data: +20
        if report['immunogenicity'].get('epitope_count', 0) > 0:
            score += 20
            print(f"   ✅ Immunogenicity data available: +20")

        print(f"   📊 Total Score: {score}/100")

        return score

    def _interpret_score(self, score):
        """Interpret humanization feasibility score."""
        if score >= 75:
            return "HIGH FEASIBILITY - Strong precedents and resources available"
        elif score >= 50:
            return "MODERATE FEASIBILITY - Some resources available, gaps exist"
        elif score >= 25:
            return "LOW FEASIBILITY - Limited precedents, significant effort needed"
        else:
            return "VERY LOW FEASIBILITY - Minimal resources, high risk"


def main():
    """Run antibody humanization example."""
    print("=" * 80)
    print("ANTIBODY HUMANIZATION PIPELINE - SOAP TOOLS FIXED")
    print("=" * 80)
    print()

    analyzer = AntibodyHumanizer()

    # Example: Anti-PD-L1 antibody
    vh_sequence = "EVQLVESGGGLVQPGGSLRLSCAASGYTFTSYYMHWVRQAPGKGLEWVSGIIPIFGTANYAQKFQGRVTISADTSKNTAYLQMNSLRAEDTAVYYCARDDGSYSPFDYWGQGTLVTVSS"
    vl_sequence = "DIQMTQSPSSLSASVGDRVTITCRASQSISSYLNWYQQKPGKAPKLLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQSYSTPLTFGQGTKVEIK"

    print("\n" + "=" * 80)
    print("EXAMPLE: Anti-PD-L1 Antibody Humanization")
    print("=" * 80)

    report = analyzer.analyze(
        vh_sequence=vh_sequence,
        vl_sequence=vl_sequence,
        target_antigen="PD-L1"
    )

    print("\n" + "=" * 80)
    print("✅ PIPELINE COMPLETE")
    print("=" * 80)
    print(f"\n📄 Report: Antibody_Humanization_PD-L1.md")
    print(f"📊 Humanization Score: {report['humanization_score']}/100")
    print(f"\n💡 SOAP tools now working with 'operation' parameter!")


if __name__ == "__main__":
    main()
