#!/usr/bin/env python3
"""
CLINICAL TRIAL DESIGN FEASIBILITY - COMPLETE WORKING PIPELINE

Fixed version using correct ToolUniverse tools.
Assesses trial feasibility across 6 research dimensions.
"""

from tooluniverse import ToolUniverse
from datetime import datetime


class TrialFeasibilityAnalyzer:
    """Complete trial design feasibility pipeline."""

    def __init__(self):
        """Initialize ToolUniverse."""
        print("Initializing ToolUniverse...")
        self.tu = ToolUniverse()
        self.tu.load_tools()
        print(f"✅ Loaded {len(self.tu.all_tool_dict)} tools\n")

    def analyze(self, indication, drug_name, phase="Phase 2", output_file=None):
        """
        Complete trial feasibility analysis.

        Args:
            indication: Disease/indication (e.g., "EGFR-mutant NSCLC")
            drug_name: Drug/intervention name
            phase: Trial phase
            output_file: Optional report file

        Returns:
            dict with feasibility analysis
        """
        if output_file is None:
            output_file = f"Trial_Feasibility_{drug_name.replace(' ', '_')}.md"

        print("=" * 80)
        print(f"TRIAL FEASIBILITY ANALYSIS")
        print(f"Indication: {indication}")
        print(f"Drug: {drug_name}")
        print(f"Phase: {phase}")
        print("=" * 80)

        report = {
            'indication': indication,
            'drug': drug_name,
            'phase': phase,
            'timestamp': datetime.now().isoformat(),
            'disease_info': {},
            'drug_info': {},
            'precedent_trials': [],
            'safety_data': {},
            'feasibility_score': 0
        }

        # Create report file
        self._create_report(output_file, indication, drug_name, phase)

        print("\n🔬 Running Feasibility Analysis...")
        print("-" * 80)

        # PATH 1: Patient Population Sizing
        report['disease_info'] = self._analyze_patient_population(indication)
        self._update_report(output_file, "## 1. Patient Population", report['disease_info'])

        # PATH 2: Drug/Intervention Profile
        report['drug_info'] = self._analyze_drug(drug_name)
        self._update_report(output_file, "## 2. Drug Profile", report['drug_info'])

        # PATH 3: Precedent Trials
        report['precedent_trials'] = self._find_precedent_trials(indication, drug_name)
        self._update_report(output_file, "## 3. Precedent Trials", report['precedent_trials'])

        # PATH 4: Safety Assessment
        report['safety_data'] = self._assess_safety(drug_name)
        self._update_report(output_file, "## 4. Safety Profile", report['safety_data'])

        # PATH 5: Literature Evidence
        literature = self._search_literature(indication, drug_name)
        self._update_report(output_file, "## 5. Literature Evidence", literature)

        # PATH 6: Feasibility Scoring
        report['feasibility_score'] = self._calculate_feasibility(report)
        self._update_report(output_file, "## 6. Feasibility Assessment", {
            'score': report['feasibility_score'],
            'interpretation': self._interpret_feasibility(report['feasibility_score'])
        })

        print(f"\n✅ Analysis complete! Report saved to: {output_file}")
        print(f"📊 Feasibility Score: {report['feasibility_score']}/100")

        return report

    def _create_report(self, filename, indication, drug, phase):
        """Create initial report file."""
        with open(filename, 'w') as f:
            f.write(f"# Clinical Trial Feasibility Report\n\n")
            f.write(f"**Indication**: {indication}\n")
            f.write(f"**Drug/Intervention**: {drug}\n")
            f.write(f"**Phase**: {phase}\n")
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

    def _analyze_patient_population(self, indication):
        """Analyze patient population size and characteristics."""
        print("\n1️⃣ Patient Population Analysis")
        population = {}

        # Search for disease information (Open Targets)
        print(f"   Searching disease database for: {indication}")
        try:
            result = self.tu.tools.OpenTargets_get_disease_id_description_by_name(
                disease_name=indication
            )

            if result.get('data', {}).get('diseases'):
                diseases = result['data']['diseases']
                if diseases:
                    disease = diseases[0]
                    population['disease_id'] = disease.get('id', 'N/A')
                    population['disease_name'] = disease.get('name', indication)
                    population['description'] = disease.get('description', 'N/A')[:200]
                    print(f"   ✅ Found disease: {disease.get('name')}")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            population['disease_name'] = indication
            population['description'] = 'Could not retrieve disease information'

        # Estimate prevalence (using literature search as proxy)
        print(f"   Estimating prevalence...")
        try:
            result = self.tu.tools.PubMed_search_articles(
                query=f'"{indication}"[Title/Abstract] AND "prevalence"[Title/Abstract]',
                max_results=5
            )

            if isinstance(result, dict) and result.get('data', {}).get('articles'):
                articles = result['data']['articles']
                population['prevalence_literature'] = len(articles)
                print(f"   ✅ Found {len(articles)} prevalence articles")
            else:
                population['prevalence_literature'] = 0
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            population['prevalence_literature'] = 0

        return population

    def _analyze_drug(self, drug_name):
        """Get drug information from DrugBank."""
        print("\n2️⃣ Drug Profile Analysis")
        drug_info = {}

        print(f"   Querying DrugBank for: {drug_name}")
        try:
            result = self.tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
                query=drug_name,  # ✅ CORRECT parameter
                case_sensitive=False,
                exact_match=False,
                limit=1
            )

            if result.get('data', {}).get('drugs'):
                drug = result['data']['drugs'][0]
                drug_info['drugbank_id'] = drug.get('drugbank_id', 'N/A')
                drug_info['name'] = drug.get('drug_name', drug_name)
                drug_info['description'] = drug.get('description', 'N/A')[:200]
                drug_info['approval_groups'] = drug.get('approval_groups', [])
                print(f"   ✅ Found: {drug.get('drug_name')}")
            else:
                print(f"   ℹ️ Not found in DrugBank (may be novel compound)")
                drug_info['name'] = drug_name
                drug_info['status'] = 'Novel or not in database'
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            drug_info['name'] = drug_name
            drug_info['error'] = str(e)

        # Get pharmacology
        print(f"   Getting pharmacology...")
        try:
            result = self.tu.tools.drugbank_get_pharmacology_by_drug_name_or_drugbank_id(
                query=drug_name,  # ✅ CORRECT
                case_sensitive=False,
                exact_match=False,
                limit=1
            )

            if result.get('data', {}).get('drugs'):
                pharm = result['data']['drugs'][0]
                drug_info['mechanism'] = pharm.get('mechanism_of_action', 'N/A')[:150]
                print(f"   ✅ Retrieved mechanism")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

        return drug_info

    def _find_precedent_trials(self, indication, drug_name):
        """Search ClinicalTrials.gov for precedent trials."""
        print("\n3️⃣ Precedent Trial Search")
        precedents = []

        print(f"   Searching ClinicalTrials.gov...")
        try:
            result = self.tu.tools.search_clinical_trials(
                condition=indication,
                intervention=drug_name,
                max_results=10
            )

            if result.get('data', {}).get('trials'):
                trials = result['data']['trials']
                precedents = [
                    {
                        'nct_id': trial.get('nct_id', 'N/A'),
                        'title': trial.get('title', 'N/A')[:80],
                        'status': trial.get('status', 'N/A'),
                        'phase': trial.get('phase', 'N/A')
                    }
                    for trial in trials[:5]
                ]
                print(f"   ✅ Found {len(trials)} precedent trials")
            else:
                print(f"   ℹ️ No precedent trials found")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

        return precedents

    def _assess_safety(self, drug_name):
        """Assess drug safety profile."""
        print("\n4️⃣ Safety Assessment")
        safety = {}

        # Check DrugBank safety data
        print(f"   Checking safety data...")
        try:
            result = self.tu.tools.drugbank_get_safety_by_drug_name_or_drugbank_id(
                query=drug_name,  # ✅ CORRECT
                case_sensitive=False,
                exact_match=False,
                limit=1
            )

            if result.get('data', {}).get('drugs'):
                safety_data = result['data']['drugs'][0]
                safety['toxicity'] = safety_data.get('toxicity', 'N/A')[:150]
                print(f"   ✅ Retrieved safety data")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

        # Check FDA warnings
        print(f"   Checking FDA warnings...")
        try:
            result = self.tu.tools.FDA_get_warnings_and_cautions_by_drug_name(
                drug_name=drug_name
            )

            if result.get('data'):
                warnings = result['data'].get('warnings', [])
                safety['fda_warnings_count'] = len(warnings)
                print(f"   ✅ Found {len(warnings)} FDA warnings")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            safety['fda_warnings_count'] = 0

        return safety

    def _search_literature(self, indication, drug_name):
        """Search PubMed for evidence."""
        print("\n5️⃣ Literature Evidence")
        literature = {}

        query = f'"{indication}"[Title/Abstract] AND "{drug_name}"[Title/Abstract]'
        print(f"   PubMed search: {query[:60]}...")

        try:
            result = self.tu.tools.PubMed_search_articles(
                query=query,
                max_results=20
            )

            if isinstance(result, dict) and result.get('data', {}).get('articles'):
                articles = result['data']['articles']
                literature['article_count'] = len(articles)
                literature['top_articles'] = [
                    {
                        'title': art.get('title', 'N/A')[:80],
                        'pmid': art.get('pmid', 'N/A')
                    }
                    for art in articles[:3]
                ]
                print(f"   ✅ Found {len(articles)} articles")
            else:
                literature['article_count'] = 0
                print(f"   ℹ️ No articles found")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            literature['article_count'] = 0

        return literature

    def _calculate_feasibility(self, report):
        """Calculate feasibility score (0-100)."""
        print("\n6️⃣ Feasibility Scoring")
        score = 0

        # Disease information available: +20
        if report['disease_info'].get('disease_id'):
            score += 20
            print(f"   ✅ Disease identified: +20")

        # Drug information available: +20
        if report['drug_info'].get('drugbank_id'):
            score += 20
            print(f"   ✅ Drug in database: +20")

        # Precedent trials exist: +30
        if len(report['precedent_trials']) > 0:
            score += 30
            print(f"   ✅ Precedent trials found: +30")

        # Safety data available: +15
        if report['safety_data']:
            score += 15
            print(f"   ✅ Safety data available: +15")

        # Literature evidence: +15
        if report.get('literature', {}).get('article_count', 0) > 5:
            score += 15
            print(f"   ✅ Strong literature: +15")

        print(f"   📊 Total Score: {score}/100")

        return score

    def _interpret_feasibility(self, score):
        """Interpret feasibility score."""
        if score >= 75:
            return "HIGH FEASIBILITY - Strong precedent and data available"
        elif score >= 50:
            return "MODERATE FEASIBILITY - Some gaps but viable"
        elif score >= 25:
            return "LOW FEASIBILITY - Significant challenges"
        else:
            return "VERY LOW FEASIBILITY - Major gaps in data/precedent"


def main():
    """Run trial feasibility examples."""
    print("=" * 80)
    print("CLINICAL TRIAL FEASIBILITY PIPELINE - FIXED VERSION")
    print("=" * 80)
    print()

    analyzer = TrialFeasibilityAnalyzer()

    # Example 1: EGFR inhibitor in NSCLC
    print("\n" + "=" * 80)
    print("EXAMPLE: EGFR Inhibitor for EGFR-mutant NSCLC")
    print("=" * 80)
    report = analyzer.analyze(
        indication="EGFR-mutant non-small cell lung cancer",
        drug_name="osimertinib",
        phase="Phase 2"
    )

    print("\n" + "=" * 80)
    print("✅ PIPELINE COMPLETE")
    print("=" * 80)
    print(f"\n📄 Report: Trial_Feasibility_osimertinib.md")
    print(f"📊 Feasibility Score: {report['feasibility_score']}/100")
    print(f"\n💡 Trial design skill is now functional!")


if __name__ == "__main__":
    main()
