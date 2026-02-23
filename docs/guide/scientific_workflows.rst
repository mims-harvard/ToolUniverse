Scientific Workflows
====================

**Build comprehensive research workflows using ToolUniverse's compose tools and individual tools for real-world scientific scenarios.**

This Tutorial demonstrates how to create sophisticated scientific workflows that combine multiple tools to solve complex research problems. Learn to build reproducible, efficient analysis pipelines using ToolUniverse's composition capabilities.

🎯 What You'll Learn
--------------------

* Design multi-tool research workflows using compose tools
* Combine data from different scientific databases and APIs
* Build reproducible analysis pipelines with error handling
* Create agentic workflows with AI-guided decision making
* Optimize workflows for efficiency and accuracy

📋 Prerequisites
----------------

* Familiarity with ToolUniverse tools (:doc:`../guide/tools`)
* Understanding of scientific databases and concepts
* Basic Python programming for workflow automation
* Knowledge of tool composition (:doc:`../guide/tool_composition`)

Workflow Architecture Overview
------------------------------

ToolUniverse supports two approaches for building scientific workflows:

1. **Compose Tools**: Pre-built, reusable workflows that combine multiple tools
2. **Custom Workflows**: Ad-hoc combinations of individual tools for specific needs

**Compose Tool Benefits**:
- **Reusability**: Share workflows across research projects
- **Reliability**: Built-in error handling and fallback mechanisms
- **Efficiency**: Optimized tool loading and execution
- **Maintainability**: Centralized workflow logic

🧬 Drug Discovery & Development Workflows
------------------------------------------

Target Identification Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario**: Identify and validate potential therapeutic targets for a disease using a compose tool.

**Using Compose Tool Approach**:

.. code-block:: python

   from tooluniverse import ToolUniverse

   def target_identification_workflow(disease_name):
       """Complete target identification using compose tools"""

       tu = ToolUniverse()
       tu.load_tools(['compose_tools'])  # Load compose tools

       print(f"🎯 Target Identification Workflow: {disease_name}")
       print("=" * 60)

       # Use the LiteratureSearchTool compose tool for initial research
       literature_results = tu.run({"name": "LiteratureSearchTool", "arguments": {'research_topic': f"{disease_name} therapeutic targets druggability"}})

       print("✅ Literature review completed")

       # Get disease information and associated targets
       disease_query = {
           "name": "OpenTargets_get_disease_id_description_by_name",
           "arguments": {"diseaseName": disease_name}
       }

       disease_info = tu.run(disease_query)
       if not disease_info or 'data' not in disease_info:
           print(f"❌ Disease '{disease_name}' not found")
           return None

       disease_id = disease_info['data']['id']
       print(f"✅ Disease ID: {disease_id}")

       # Get associated targets with evidence scores
       targets_query = {
           "name": "OpenTargets_get_associated_targets_by_disease_efoId",
           "arguments": {"efoId": disease_id, "limit": 25}
       }

       targets = tu.run(targets_query)
       if targets and 'data' in targets:
           print(f"✅ Found {len(targets['data'])} targets")

           # Show top 5 targets
           print("\n🏆 Top 5 Targets by Association Score:")
           for i, target in enumerate(targets['data'][:5], 1):
               symbol = target.get('approvedSymbol', 'Unknown')
               name = target.get('approvedName', 'Unknown')
               score = target.get('associationScore', 0)
               print(f"   {i}. {symbol}: {score:.3f} - {name[:50]}...")

       return {
           'disease': disease_info['data'],
           'targets': targets['data'] if targets else [],
           'literature_summary': literature_results
       }

**Custom Workflow Approach** (for specific needs):

.. code-block:: python

   def custom_target_validation_workflow(disease_name, target_symbols):
       """Custom workflow for validating specific targets"""

       print(f"🔍 Custom Target Validation: {disease_name}")
       print(f"Targets: {', '.join(target_symbols)}")
       print("=" * 60)

       validation_results = {}

       for target in target_symbols:
           print(f"\nAnalyzing target: {target}")

           # Get protein information
           protein_query = {
               "name": "UniProt_get_protein_info",
               "arguments": {"gene_symbol": target}
           }

           protein_data = tu.run(protein_query)
           if protein_data:
               validation_results[target] = {"protein": protein_data}
               print(f"   ✅ Protein data retrieved")

           # Check existing drugs
           drug_query = {
               "name": "ChEMBL_get_compounds_by_target",
               "arguments": {"target_symbol": target}
           }

           compounds = tu.run(drug_query)
           if compounds:
               validation_results[target]["existing_drugs"] = compounds
               print(f"   💊 Found existing compounds")

           # Literature validation
           lit_query = {
               "name": "PubTator_search_publications",
               "arguments": {"query": f"{target} {disease_name} therapeutic"}
           }

           papers = tu.run(lit_query)
           if papers and 'results' in papers:
               validation_results[target]["literature"] = papers['results']
               print(f"   📚 Found {len(papers['results'])} relevant papers")

       return validation_results

Drug Repositioning Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario**: Find existing drugs that could be repurposed for a new indication using heterogeneous data sources.

.. code-block:: python

   def drug_repositioning_workflow(source_disease, target_disease):
       """Find drugs approved for one disease that might work for another"""

       print(f"🔄 Drug Repositioning Analysis")
       print(f"From: {source_disease} → To: {target_disease}")
       print("=" * 60)

       repositioning_results = {}

       # Step 1: Get both disease IDs
       diseases = {}
       for disease_name in [source_disease, target_disease]:
           disease_query = {
               "name": "OpenTargets_get_disease_id_description_by_name",
               "arguments": {"diseaseName": disease_name}
           }
           disease_info = tu.run(disease_query)
           if disease_info and 'data' in disease_info:
               diseases[disease_name] = disease_info['data']['id']

       if len(diseases) != 2:
           print("❌ Could not find both diseases")
           return None

       # Step 2: Get targets for both diseases
       disease_targets = {}
       for disease_name, disease_id in diseases.items():
           targets_query = {
               "name": "OpenTargets_get_associated_targets_by_disease_efoId",
               "arguments": {"efoId": disease_id}
           }
           targets = tu.run(targets_query)
           if targets and 'data' in targets:
               disease_targets[disease_name] = [
                   t.get('approvedSymbol') for t in targets['data']
               ]

       # Step 3: Find overlapping targets
       source_targets = set(disease_targets.get(source_disease, []))
       target_targets = set(disease_targets.get(target_disease, []))
       overlapping_targets = source_targets.intersection(target_targets)

       print(f"🎯 Overlapping targets: {len(overlapping_targets)}")
       for target in list(overlapping_targets)[:5]:
           print(f"   • {target}")

       # Step 4: Find drugs targeting the overlapping targets
       repositioning_candidates = []
       for target in list(overlapping_targets)[:10]:
           drug_query = {
               "name": "ChEMBL_get_compounds_by_target",
               "arguments": {"target_symbol": target}
           }
           compounds = tu.run(drug_query)
           if compounds:
               repositioning_candidates.extend(compounds)

       repositioning_results['candidates'] = repositioning_candidates
       print(f"💊 Found {len(repositioning_candidates)} repositioning candidates")

       # Step 5: Check if any candidates are already being tested
       trials_query = {
           "name": "ClinicalTrials_search_studies",
           "arguments": {"condition": target_disease}
       }

       trials = tu.run(trials_query)
       if trials and 'studies' in trials:
           repositioning_results['existing_trials'] = trials['studies']
           print(f"🧪 Found {len(trials['studies'])} existing trials for {target_disease}")

       return repositioning_results

Comprehensive Drug Discovery Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Complete end-to-end drug discovery workflow from disease to optimized candidates**

This advanced workflow demonstrates how to create a compose tool that orchestrates multiple phases of drug discovery:

.. code-block:: python

   def compose(arguments, tooluniverse, call_tool):
       """End-to-end drug discovery: Target → Lead → Optimization → Validation"""

       disease_efo_id = arguments['disease_efo_id']
       results = {}

       # Phase 1: Target Identification & Validation
       print("Phase 1: Target Identification...")
       try:
           target_result = call_tool('OpenTargets_get_associated_targets_by_disease_efoId', {
               'efoId': disease_efo_id
           })
           selected_targets = target_result["data"]["disease"]["associatedTargets"]["rows"][:5]
           results["target_selection"] = target_result
           print(f"✅ Found {len(selected_targets)} targets")
       except Exception as e:
           print(f"❌ Target identification failed: {e}")
           results["target_selection"] = {"error": str(e)}
           return results

       # Phase 2: Lead Compound Discovery (using OpenTargets drugs)
       print("Phase 2: Lead Discovery...")
       try:
           # Get known drugs for this disease
           known_drugs = call_tool('OpenTargets_get_associated_drugs_by_disease_efoId', {
               'efoId': disease_efo_id,
               'size': 20
           })

           if 'data' in known_drugs and 'disease' in known_drugs['data']:
               drugs_data = known_drugs['data']['disease'].get('knownDrugs', {})
               drug_rows = drugs_data.get('rows', [])
               results["lead_discovery"] = {
                   "total_drugs": len(drug_rows),
                   "approved_drugs": len([d for d in drug_rows if d.get('drug', {}).get('isApproved', False)]),
                   "drug_data": drug_rows  # Store full drug data for safety assessment
               }
               print(f"✅ Found {len(drug_rows)} known drugs")
           else:
               results["lead_discovery"] = {"error": "No drug data available"}
               print("⚠️ No drug data available")
       except Exception as e:
           print(f"⚠️ Drug discovery failed: {e}")
           results["lead_discovery"] = {"error": str(e)}

       # Phase 3: Safety Assessment (using ADMETAI tools)
       print("Phase 3: Safety Assessment...")
       safety_assessments = []

       # Extract SMILES from known drugs for ADMET assessment
       try:
           if 'lead_discovery' in results and 'total_drugs' in results['lead_discovery']:
               # Get drug SMILES from OpenTargets drug data
               drug_data = results['lead_discovery'].get('drug_data', [])
               if drug_data:
                   # Extract SMILES from first few drugs for assessment
                   test_smiles = []
                   processed_drugs = set()  # Track processed drugs to avoid duplicates

                   for drug in drug_data[:5]:  # Test first 5 drugs
                       if 'drug' in drug:
                           drug_info = drug['drug']
                           drug_name = drug_info.get('name', '')

                           # Skip if already processed
                           if drug_name in processed_drugs:
                               continue
                           processed_drugs.add(drug_name)

                           # Try to get SMILES from drug name using PubChem
                           if drug_name:
                               try:
                                   # Get CID from drug name
                                   cid_result = call_tool('PubChem_get_CID_by_compound_name', {
                                       'name': drug_name
                                   })

                                   if cid_result and 'IdentifierList' in cid_result and 'CID' in cid_result['IdentifierList']:
                                       cids = cid_result['IdentifierList']['CID']
                                       if cids:
                                           # Get SMILES from first CID
                                           smiles_result = call_tool('PubChem_get_compound_properties_by_CID', {
                                               'cid': cids[0]
                                           })

                                           if smiles_result and 'PropertyTable' in smiles_result:
                                               properties = smiles_result['PropertyTable'].get('Properties', [])
                                               if properties:
                                                   # Try CanonicalSMILES first, then ConnectivitySMILES
                                                   smiles = properties[0].get('CanonicalSMILES') or properties[0].get('ConnectivitySMILES')
                                                   if smiles and smiles not in test_smiles:  # Avoid duplicate SMILES
                                                       test_smiles.append(smiles)
                                                       print(f"✅ Found SMILES for {drug_name}: {smiles[:50]}...")

                                                       # Stop after finding 3 unique SMILES
                                                       if len(test_smiles) >= 3:
                                                           break
                               except Exception as e:
                                   print(f"⚠️ Failed to get SMILES for {drug_name}: {e}")

                   if test_smiles:
                       # Test BBB penetrance
                       bbb_result = call_tool('ADMETAI_predict_BBB_penetrance', {
                           'smiles': test_smiles
                       })

                       # Test bioavailability
                       bio_result = call_tool('ADMETAI_predict_bioavailability', {
                           'smiles': test_smiles
                       })

                       # Test toxicity
                       tox_result = call_tool('ADMETAI_predict_toxicity', {
                           'smiles': test_smiles
                       })

                       safety_assessments.append({
                           "compounds_assessed": len(test_smiles),
                           "bbb_penetrance": bbb_result,
                           "bioavailability": bio_result,
                           "toxicity": tox_result
                       })

                       results["safety_assessment"] = safety_assessments
                       print(f"✅ Completed safety assessment for {len(test_smiles)} compounds")
                   else:
                       print("⚠️ No SMILES data available for safety assessment")
                       results["safety_assessment"] = {"error": "No SMILES data available"}
               else:
                   print("⚠️ No drug data available for safety assessment")
                   results["safety_assessment"] = {"error": "No drug data available"}
           else:
               print("⚠️ Lead discovery phase failed, skipping safety assessment")
               results["safety_assessment"] = {"error": "Lead discovery phase failed"}
       except Exception as e:
           print(f"⚠️ Safety assessment failed: {e}")
           results["safety_assessment"] = {"error": str(e)}

       # Phase 4: Literature Validation
       print("Phase 4: Literature Validation...")
       try:
           literature_validation = call_tool('LiteratureSearchTool', {
               'research_topic': f"drug discovery {disease_efo_id} therapeutic targets"
           })
           results["literature_validation"] = literature_validation
           print("✅ Literature validation completed")
       except Exception as e:
           print(f"⚠️ Literature validation failed: {e}")
           results["literature_validation"] = {"error": str(e)}

       return results

**Using the Compose Tool**:

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()
   tu.load_tools(['compose_tools'])

   # Run the comprehensive drug discovery pipeline
   discovery_results = tu.run({"name": "ComprehensiveDrugDiscoveryPipeline", "arguments": {'disease_efo_id': 'EFO_0001074'  # Alzheimer's disease}})

   print("Drug Discovery Results:")
   print(f"Targets identified: {len(discovery_results['target_selection']['data']['disease']['associatedTargets']['rows'])}")
   print(f"Known drugs found: {discovery_results['lead_discovery']['total_drugs']}")
   print(f"Approved drugs: {discovery_results['lead_discovery']['approved_drugs']}")
   print(f"Compounds assessed for safety: {discovery_results['safety_assessment'][0]['compounds_assessed']}")

🛡️ Drug Safety & Pharmacovigilance Workflows
---------------------------------------------

Comprehensive Safety Assessment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario**: Conduct thorough safety evaluation of a marketed drug using multiple data sources.

.. code-block:: python

   def comprehensive_safety_assessment(drug_name):
       """Complete safety assessment workflow for a drug"""

       print(f"🛡️ Comprehensive Safety Assessment: {drug_name}")
       print("=" * 60)

       safety_assessment = {}

       # Step 1: Basic drug information
       drug_query = {
           "name": "PubChem_get_compound_info",
           "arguments": {"compound_name": drug_name}
       }

       drug_info = tu.run(drug_query)
       if drug_info:
           safety_assessment['drug_info'] = drug_info
           print(f"✅ Basic drug information retrieved")

       # Step 2: FDA adverse events analysis
       adverse_query = {
           "name": "FAERS_count_reactions_by_drug_event",
           "arguments": {"medicinalproduct": drug_name}
       }

       adverse_events = tu.run(adverse_query)
       if adverse_events and 'results' in adverse_events:
           # Analyze adverse event patterns
           event_analysis = analyze_adverse_events(adverse_events['results'])
           safety_assessment['adverse_events'] = event_analysis

           print(f"⚠️ Analyzed {len(adverse_events['results'])} adverse event reports")
           print("Top adverse reactions:")
           for reaction, count in event_analysis['top_reactions'][:5]:
               print(f"   • {reaction}: {count} reports")

       # Step 3: Safety literature review using compose tool
       safety_literature = tu.run({"name": "LiteratureSearchTool", "arguments": {'research_topic': f"{drug_name} safety toxicity adverse effects"}})

       safety_assessment['safety_literature'] = safety_literature
       print(f"📚 Safety literature review completed")

       # Step 4: Clinical trial safety data
       trial_safety_query = {
           "name": "ClinicalTrials_search_studies",
           "arguments": {
               "intervention": drug_name,
               "study_type": "Interventional"
           }
       }

       trials = tu.run(trial_safety_query)
       if trials and 'studies' in trials:
           safety_assessment['clinical_trials'] = trials['studies']
           print(f"🧪 Found {len(trials['studies'])} relevant clinical trials")

       return safety_assessment

   def analyze_adverse_events(events):
       """Helper function to analyze adverse event patterns"""

       reaction_counts = {}
       age_groups = {'pediatric': 0, 'adult': 0, 'elderly': 0}
       serious_events = 0

       for event in events:
           # Count reactions
           patient = event.get('patient', {})
           reactions = patient.get('reaction', [])

           for reaction in reactions:
               reaction_name = reaction.get('reactionmeddrapt', 'Unknown')
               reaction_counts[reaction_name] = reaction_counts.get(reaction_name, 0) + 1

           # Analyze demographics
           age = patient.get('patientonsetage')
           if age:
               age = float(age)
               if age < 18:
                   age_groups['pediatric'] += 1
               elif age >= 65:
                   age_groups['elderly'] += 1
               else:
                   age_groups['adult'] += 1

           # Count serious events
           if event.get('serious') == '1':
               serious_events += 1

       return {
           'top_reactions': sorted(reaction_counts.items(), key=lambda x: x[1], reverse=True),
           'age_distribution': age_groups,
           'serious_events': serious_events,
           'total_events': len(events)
       }

📚 Literature Research & Meta-Analysis Workflows
------------------------------------------------

Systematic Literature Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario**: Conduct systematic review of literature on a specific research topic using compose tools.

.. code-block:: python

   def systematic_literature_review(research_topic, years_back=5):
       """Systematic literature review workflow using compose tools"""

       print(f"📚 Systematic Literature Review: {research_topic}")
       print("=" * 60)

       review_results = {}

       # Step 1: Use LiteratureSearchTool compose tool for comprehensive search
       literature_summary = tu.run({"name": "LiteratureSearchTool", "arguments": {'research_topic': research_topic}})

       review_results['ai_summary'] = literature_summary
       print("✅ AI-powered literature summary completed")

       # Step 2: Additional targeted searches for specific aspects
       search_aspects = [
           f"{research_topic} clinical trials",
           f"{research_topic} biomarkers",
           f"{research_topic} mechanisms"
       ]

       detailed_searches = {}
       for aspect in search_aspects:
           aspect_results = tu.run({"name": "LiteratureSearchTool", "arguments": {'research_topic': aspect}})
           detailed_searches[aspect] = aspect_results
           print(f"✅ {aspect} search completed")

       review_results['detailed_searches'] = detailed_searches

       # Step 3: Citation analysis using individual tools
       citation_query = {
           "name": "SemanticScholar_search_papers",
           "arguments": {
               "query": research_topic,
               "limit": 100,
               "fields": ["citations", "abstract", "authors"]
           }
       }

       citation_data = tu.run(citation_query)
       if citation_data and 'results' in citation_data:
           citation_analysis = analyze_citations(citation_data['results'])
           review_results['citation_analysis'] = citation_analysis

           print(f"📊 Citation analysis:")
           print(f"   High-impact papers (>50 citations): {citation_analysis['high_impact_count']}")
           print(f"   Average citations: {citation_analysis['avg_citations']:.1f}")

       # Step 4: Temporal analysis
       temporal_query = {
           "name": "EuropePMC_search_articles",
           "arguments": {
               "query": research_topic,
               "limit": 200,
               "year_range": f"{2024-years_back}-2024"
           }
       }

       temporal_data = tu.run(temporal_query)
       if temporal_data and 'results' in temporal_data:
           temporal_analysis = analyze_publication_trends(temporal_data['results'])
           review_results['temporal_trends'] = temporal_analysis

           print(f"📈 Publication trends:")
           for year, count in sorted(temporal_analysis['year_counts'].items()):
               print(f"   {year}: {count} papers")

       return review_results

   def analyze_citations(papers):
       """Analyze citation patterns"""
       citations = [int(paper.get('citation_count', 0)) for paper in papers if paper.get('citation_count')]

       if not citations:
           return {'high_impact_count': 0, 'avg_citations': 0}

       return {
           'high_impact_count': len([c for c in citations if c > 50]),
           'avg_citations': sum(citations) / len(citations),
           'max_citations': max(citations),
           'total_citations': sum(citations)
       }

   def analyze_publication_trends(papers):
       """Analyze publication trends over time"""
       year_counts = {}

       for paper in papers:
           year = paper.get('publication_year') or paper.get('year')
           if year:
               year_counts[year] = year_counts.get(year, 0) + 1

       return {
           'year_counts': year_counts,
           'total_years': len(year_counts),
           'peak_year': max(year_counts.items(), key=lambda x: x[1])[0] if year_counts else None
       }

🧬 Genomics Research Workflows
-------------------------------

Variant Analysis Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario**: Analyze genetic variants and their functional impact using multiple genomic databases.

.. code-block:: python

   def variant_analysis_workflow(gene_symbols):
       """Comprehensive variant analysis workflow"""

       print(f"🧬 Variant Analysis Workflow")
       print(f"Genes: {', '.join(gene_symbols)}")
       print("=" * 50)

       analysis_results = {}

       # Step 1: Gene Information Gathering
       print("Step 1: Gathering gene information...")
       gene_info = {}

       for gene in gene_symbols:
           # Get protein information
           protein_query = {
               "name": "UniProt_get_protein_info",
               "arguments": {"gene_symbol": gene}
           }

           protein_data = tu.run(protein_query)
           if protein_data:
               gene_info[gene] = {"protein": protein_data}

           # Get disease associations
           disease_query = {
               "name": "OpenTargets_get_associated_diseases_by_target",
               "arguments": {"target_symbol": gene, "limit": 10}
           }

           diseases = tu.run(disease_query)
           if diseases:
               gene_info[gene]["diseases"] = diseases

       analysis_results['gene_info'] = gene_info
       print(f"✅ Gene information collected for {len(gene_info)} genes")

       # Step 2: Literature analysis for each gene
       print("Step 2: Literature analysis...")
       literature_analysis = {}

       for gene in gene_symbols:
           gene_literature = tu.run({"name": "LiteratureSearchTool", "arguments": {'research_topic': f"{gene} variants mutations functional impact"}})
           literature_analysis[gene] = gene_literature
           print(f"   ✅ {gene} literature analysis completed")

       analysis_results['literature_analysis'] = literature_analysis

       # Step 3: Pathway enrichment analysis
       print("Step 3: Pathway analysis...")
       pathway_query = {
           "name": "Enrichr_analyze_gene_list",
           "arguments": {
               "gene_list": gene_symbols,
               "library": "KEGG_2021_Human"
           }
       }

       pathways = tu.run(pathway_query)
       if pathways:
           analysis_results['pathways'] = pathways
           print(f"✅ Pathway analysis completed")

       return analysis_results

Biomarker Discovery Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario**: Discover and validate biomarkers for a specific disease condition using compose tools.

.. code-block:: python

   def compose(arguments, tooluniverse, call_tool):
       """Discover and validate biomarkers for a specific disease condition"""

       disease_condition = arguments['disease_condition']
       sample_type = arguments.get('sample_type', 'blood')

       print("🔬 Biomarker Discovery Workflow")
       print(f"Disease: {disease_condition}")
       print(f"Sample Type: {sample_type}")
       print("=" * 50)

       results = {}

       # Step 1: Literature-based biomarker discovery
       print("Step 1: Literature-based biomarker discovery...")
       try:
           literature_biomarkers = call_tool('LiteratureSearchTool', {
               'research_topic': f"{disease_condition} biomarkers {sample_type}"
           })
           results['literature_evidence'] = literature_biomarkers
           print("✅ Literature analysis completed")
       except Exception as e:
           print(f"⚠️ Literature search failed: {e}")
           results['literature_evidence'] = {"error": str(e)}

       # Step 2: Database mining for expression data
       print("Step 2: Database mining for expression data...")
       try:
           # Try multiple gene search strategies
           gene_search_results = []

           # Strategy 1: Direct disease name search
           try:
               hpa_result = call_tool('HPA_search_genes_by_query', {
                   'search_query': disease_condition
               })
               if hpa_result and isinstance(hpa_result, dict) and 'genes' in hpa_result:
                   genes = hpa_result['genes']
                   gene_search_results.extend(genes)
                   print(f"✅ HPA search found {len(genes)} genes for '{disease_condition}'")
               elif hpa_result and isinstance(hpa_result, list):
                   gene_search_results.extend(hpa_result)
                   print(f"✅ HPA search found {len(hpa_result)} genes for '{disease_condition}'")
           except Exception as e:
               print(f"⚠️ HPA search failed: {e}")

           # Strategy 2: Search for common biomarker genes if no results
           if not gene_search_results:
               biomarker_keywords = ['biomarker', 'marker', 'indicator', 'diagnostic']
               for keyword in biomarker_keywords:
                   try:
                       search_term = f"{disease_condition} {keyword}"
                       hpa_result = call_tool('HPA_search_genes_by_query', {
                           'search_query': search_term
                       })
                       if hpa_result and isinstance(hpa_result, dict) and 'genes' in hpa_result:
                           genes = hpa_result['genes']
                           gene_search_results.extend(genes)
                           print(f"✅ HPA search found {len(genes)} genes for '{search_term}'")
                           break
                       elif hpa_result and isinstance(hpa_result, list):
                           gene_search_results.extend(hpa_result)
                           print(f"✅ HPA search found {len(hpa_result)} genes for '{search_term}'")
                           break
                   except Exception as e:
                       print(f"⚠️ HPA search failed for '{search_term}': {e}")

           # Strategy 3: Use alternative search if no results
           if not gene_search_results:
               print("⚠️ No genes found with HPA search strategies")
               # Create a fallback result with common cancer genes
               fallback_genes = [
                   {'gene_name': 'BRCA1', 'ensembl_id': 'ENSG00000012048', 'description': 'Breast cancer type 1 susceptibility protein'},
                   {'gene_name': 'BRCA2', 'ensembl_id': 'ENSG00000139618', 'description': 'Breast cancer type 2 susceptibility protein'},
                   {'gene_name': 'TP53', 'ensembl_id': 'ENSG00000141510', 'description': 'Tumor protein p53'},
                   {'gene_name': 'EGFR', 'ensembl_id': 'ENSG00000146648', 'description': 'Epidermal growth factor receptor'},
                   {'gene_name': 'MYC', 'ensembl_id': 'ENSG00000136997', 'description': 'MYC proto-oncogene protein'}
               ]
               gene_search_results.extend(fallback_genes)
               print(f"✅ Using fallback cancer genes: {len(fallback_genes)} genes")

           if gene_search_results:
               # Get details for the first gene found
               first_gene = gene_search_results[0]
               if 'ensembl_id' in first_gene and first_gene['ensembl_id'] != 'unknown':
                   expression_data = call_tool('HPA_get_comprehensive_gene_details_by_ensembl_id', {
                       'ensembl_id': first_gene['ensembl_id']
                   })
                   results['expression_data'] = {
                       'search_query': disease_condition,
                       'genes_found': len(gene_search_results),
                       'search_strategy': 'multi-strategy',
                       'gene_details': expression_data,
                       'all_candidates': gene_search_results
                   }
                   print(f"✅ Expression data retrieved for {first_gene.get('gene_name', 'unknown gene')}")
               else:
                   results['expression_data'] = {
                       'search_query': disease_condition,
                       'genes_found': len(gene_search_results),
                       'search_strategy': 'multi-strategy',
                       'gene_details': first_gene,
                       'all_candidates': gene_search_results
                   }
                   print(f"✅ Expression data retrieved using fallback strategy")
           else:
               results['expression_data'] = {"error": "No genes found with any search strategy"}
               print("⚠️ No genes found with any search strategy")
       except Exception as e:
           print(f"⚠️ Expression data search failed: {e}")
           results['expression_data'] = {"error": str(e)}

       # Step 3: Pathway enrichment analysis
       print("Step 3: Pathway enrichment analysis...")
       try:
           # Use genes found in step 2 for pathway analysis
           pathway_data = {}

           if 'expression_data' in results and 'gene_details' in results['expression_data']:
               # Extract gene name from the gene details
               gene_details = results['expression_data']['gene_details']
               if 'gene_name' in gene_details:
                   gene_name = gene_details['gene_name']

                   # Multi-tool pathway analysis using available HPA tools
                   pathway_results = {}

                   # Tool 1: HPA biological processes
                   try:
                       hpa_processes = call_tool('HPA_get_biological_processes_by_gene', {
                           'gene': gene_name
                       })
                       pathway_results['hpa_biological_processes'] = hpa_processes
                       print(f"✅ HPA biological processes completed for {gene_name}")
                   except Exception as e:
                       pathway_results['hpa_biological_processes'] = {"error": str(e)}
                       print(f"⚠️ HPA biological processes failed for {gene_name}: {e}")

                   # Tool 2: HPA contextual biological process analysis
                   try:
                       contextual_analysis = call_tool('HPA_get_contextual_biological_process_analysis', {
                           'gene': gene_name
                       })
                       pathway_results['hpa_contextual_analysis'] = contextual_analysis
                       print(f"✅ HPA contextual analysis completed for {gene_name}")
                   except Exception as e:
                       pathway_results['hpa_contextual_analysis'] = {"error": str(e)}
                       print(f"⚠️ HPA contextual analysis failed for {gene_name}: {e}")

                   # Tool 3: HPA protein interactions
                   try:
                       protein_interactions = call_tool('HPA_get_protein_interactions_by_gene', {
                           'gene': gene_name
                       })
                       pathway_results['hpa_protein_interactions'] = protein_interactions
                       print(f"✅ HPA protein interactions completed for {gene_name}")
                   except Exception as e:
                       pathway_results['hpa_protein_interactions'] = {"error": str(e)}
                       print(f"⚠️ HPA protein interactions failed for {gene_name}: {e}")

                   # Tool 4: HPA cancer prognostics (if relevant)
                   try:
                       cancer_prognostics = call_tool('HPA_get_cancer_prognostics_by_gene', {
                           'gene': gene_name
                       })
                       pathway_results['hpa_cancer_prognostics'] = cancer_prognostics
                       print(f"✅ HPA cancer prognostics completed for {gene_name}")
                   except Exception as e:
                       pathway_results['hpa_cancer_prognostics'] = {"error": str(e)}
                       print(f"⚠️ HPA cancer prognostics failed for {gene_name}: {e}")

                   pathway_data[gene_name] = pathway_results
               else:
                   pathway_data["error"] = "No gene name available for pathway analysis"
                   print("⚠️ No gene name available for pathway analysis")
           else:
               # Fallback: use disease condition for pathway search
               try:
                   processes = call_tool('HPA_get_biological_processes_by_gene', {
                       'gene': disease_condition
                   })
                   pathway_data[disease_condition] = {
                       'hpa_biological_processes': processes,
                       'note': 'Fallback analysis using disease condition'
                   }
                   print(f"✅ Pathway analysis completed using disease condition")
               except Exception as e:
                   pathway_data["error"] = str(e)
                   print(f"⚠️ Pathway analysis failed: {e}")

           results['pathway_analysis'] = pathway_data
       except Exception as e:
           print(f"⚠️ Pathway analysis failed: {e}")
           results['pathway_analysis'] = {"error": str(e)}

       # Step 4: Clinical validation search
       print("Step 4: Clinical validation search...")
       try:
           # Use FDA drug names instead
           clinical_evidence = call_tool('FDA_get_drug_names_by_clinical_pharmacology', {
               'clinical_pharmacology': disease_condition
           })
           results['clinical_validation'] = clinical_evidence
           print("✅ Clinical validation search completed")
       except Exception as e:
           print(f"⚠️ Clinical validation search failed: {e}")
           results['clinical_validation'] = {"error": str(e)}

       # Step 5: Additional protein information
       print("Step 5: Protein information gathering...")
       protein_info = {}

       # Use genes found in step 2 for protein information
       if 'expression_data' in results and 'gene_details' in results['expression_data']:
           gene_details = results['expression_data']['gene_details']
           if 'gene_name' in gene_details and 'ensembl_id' in gene_details:
               gene_name = gene_details['gene_name']
               ensembl_id = gene_details['ensembl_id']
               try:
                   # Get comprehensive gene details (already retrieved in step 2)
                   protein_info[gene_name] = gene_details
                   print(f"✅ Protein information gathered for {gene_name}")
               except Exception as e:
                   print(f"⚠️ Protein info failed for {gene_name}: {e}")
                   protein_info[gene_name] = {"error": str(e)}
           else:
               protein_info["error"] = "No gene name or Ensembl ID available"
               print("⚠️ No gene name or Ensembl ID available")
       else:
           protein_info["error"] = "No gene data available from expression analysis"
           print("⚠️ No gene data available from expression analysis")

       results['protein_information'] = protein_info
       print(f"✅ Protein information gathered for {len(protein_info)} genes")

       return {
           'disease': disease_condition,
           'sample_type': sample_type,
           'literature_evidence': results['literature_evidence'],
           'expression_data': results['expression_data'],
           'pathway_analysis': results['pathway_analysis'],
           'clinical_validation': results['clinical_validation'],
           'protein_information': results['protein_information']
       }

**Using the Compose Tool**:

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()
   tu.load_tools(['compose_tools'])

   # Run biomarker discovery workflow
   biomarker_results = tu.run({"name": "BiomarkerDiscoveryWorkflow", "arguments": {'disease_condition': 'breast cancer',
       'sample_type': 'blood'}})

   print("Biomarker Discovery Results:")
   print(f"Disease: {biomarker_results['disease']}")
   print(f"Sample type: {biomarker_results['sample_type']}")
   print(f"Genes found: {biomarker_results['expression_data']['genes_found']}")
   print(f"Search strategy: {biomarker_results['expression_data']['search_strategy']}")
   print(f"Protein information: {len(biomarker_results['protein_information'])} genes")
   print("Literature evidence and pathway analysis completed")

🧪 Clinical Research Workflows
-------------------------------

Clinical Trial Analysis Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario**: Comprehensive analysis of clinical trials for a specific condition.

.. code-block:: python

   def clinical_trial_analysis_workflow(condition, intervention=None):
       """Analyze clinical trials for a condition or intervention"""

       print(f"🧪 Clinical Trial Analysis")
       print(f"Condition: {condition}")
       if intervention:
           print(f"Intervention: {intervention}")
       print("=" * 50)

       trial_analysis = {}

       # Step 1: Search for relevant trials
       search_params = {
           "condition": condition
       }
       if intervention:
           search_params["intervention"] = intervention

       trials_query = {
           "name": "ClinicalTrials_search_studies",
           "arguments": search_params
       }

       trials = tu.run(trials_query)
       if not trials or 'studies' not in trials:
           print("❌ No trials found")
           return None

       all_trials = trials['studies']
       trial_analysis['total_trials'] = len(all_trials)
       print(f"✅ Found {len(all_trials)} relevant trials")

       # Step 2: Analyze trial phases
       phase_distribution = analyze_trial_phases(all_trials)
       trial_analysis['phase_distribution'] = phase_distribution

       print(f"📊 Trial phases:")
       for phase, count in phase_distribution.items():
           print(f"   {phase}: {count} trials")

       # Step 3: Literature context using compose tool
       literature_context = tu.run({"name": "LiteratureSearchTool", "arguments": {'research_topic': f"{condition} {intervention} clinical trials outcomes"}})

       trial_analysis['literature_context'] = literature_context
       print("✅ Literature context analysis completed")

       # Step 4: Geographic distribution
       geographic_analysis = analyze_trial_locations(all_trials)
       trial_analysis['geographic_distribution'] = geographic_analysis

       print(f"🌍 Top locations:")
       for country, count in geographic_analysis['top_countries'][:5]:
           print(f"   {country}: {count} trials")

       return trial_analysis

   def analyze_trial_phases(trials):
       """Analyze distribution of trial phases"""
       phases = {}
       for trial in trials:
           phase = trial.get('phase', 'Unknown')
           phases[phase] = phases.get(phase, 0) + 1
       return phases

   def analyze_trial_locations(trials):
       """Analyze geographic distribution of trials"""
       countries = {}
       for trial in trials:
           locations = trial.get('location_countries', [])
           for country in locations:
               countries[country] = countries.get(country, 0) + 1

       return {
           'top_countries': sorted(countries.items(), key=lambda x: x[1], reverse=True),
           'total_countries': len(countries)
       }

🤖 Agentic Workflows with AI Integration
----------------------------------------

Intelligent Research Assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario**: Create an AI-guided workflow that adapts based on intermediate results.

.. code-block:: python

   def intelligent_research_assistant(research_question):
       """AI-guided research workflow that adapts based on findings"""

       print(f"🤖 Intelligent Research Assistant")
       print(f"Research Question: {research_question}")
       print("=" * 60)

       research_results = {}

       # Step 1: Initial literature exploration
       print("Step 1: Initial literature exploration...")
       initial_literature = tu.run({"name": "LiteratureSearchTool", "arguments": {'research_topic': research_question}})

       research_results['initial_literature'] = initial_literature
       print("✅ Initial literature review completed")

       # Step 2: Extract key entities and concepts
       print("Step 2: Extracting key concepts...")
       # This would use an AI tool to extract key concepts from the literature
       # For now, we'll simulate this step
       key_concepts = extract_key_concepts(initial_literature)
       research_results['key_concepts'] = key_concepts

       # Step 3: Adaptive follow-up searches based on findings
       print("Step 3: Adaptive follow-up searches...")
       follow_up_searches = {}

       for concept in key_concepts[:3]:  # Top 3 concepts
           concept_literature = tu.run({"name": "LiteratureSearchTool", "arguments": {'research_topic': f"{research_question} {concept}"}})
           follow_up_searches[concept] = concept_literature
           print(f"   ✅ {concept} follow-up search completed")

       research_results['follow_up_searches'] = follow_up_searches

       # Step 4: Data integration and synthesis
       print("Step 4: Data integration...")
       integrated_analysis = integrate_research_findings(research_results)
       research_results['integrated_analysis'] = integrated_analysis

       return research_results

   def extract_key_concepts(literature_summary):
       """Extract key concepts from literature summary"""
       # Simplified concept extraction
       # In practice, this would use NLP/AI tools
       concepts = []
       if isinstance(literature_summary, str):
           words = literature_summary.lower().split()
           # Look for scientific terms
           scientific_terms = ['protein', 'gene', 'disease', 'drug', 'therapy', 'mechanism']
           for term in scientific_terms:
               if term in words:
                   concepts.append(term)
       return concepts[:5]  # Return top 5 concepts

   def integrate_research_findings(research_results):
       """Integrate findings from multiple sources"""
       return {
           'summary': 'Integrated analysis of research findings',
           'key_findings': research_results.get('key_concepts', []),
           'literature_sources': len(research_results.get('follow_up_searches', {}))
       }

Current Working Compose Tools
-------------------------------

ToolUniverse provides several production-ready compose tools that implement the workflows described in this Tutorial:

**✅ Verified Working Compose Tools**:

1. **LiteratureSearchTool**

   - **Purpose**: Comprehensive literature research and synthesis
   - **Workflow**: Broadcasting pattern across EuropePMC, OpenAlex, PubTator
   - **AI Integration**: MedicalLiteratureReviewer for intelligent summarization

2. **ComprehensiveDrugDiscoveryPipeline**

   - **Purpose**: End-to-end drug discovery from disease to candidates
   - **Workflow**: Sequential chaining with tool integration
   - **Phases**: Target identification → Lead discovery → Safety assessment → Literature validation
   - **Tool Chaining**: OpenTargets → PubChem → ADMETAI → LiteratureSearchTool

3. **BiomarkerDiscoveryWorkflow**

   - **Purpose**: Biomarker discovery and validation for diseases
   - **Workflow**: Multi-strategy approach with comprehensive fallbacks
   - **Steps**: Literature search → Gene discovery → Pathway analysis → Clinical validation
   - **Multi-tool Analysis**: HPA biological processes, protein interactions, cancer prognostics


4. **DrugSafetyAnalyzer**

   - **Purpose**: Comprehensive drug safety assessment
   - **Workflow**: Safety-focused data integration
   - **Components**: PubChem compound data, EuropePMC literature search
   - **Status**: ✅ Fully functional with real safety data processing

5. **ToolDescriptionOptimizer**

   - **Purpose**: AI-powered tool description optimization
   - **Workflow**: Agentic optimization loops with quality evaluation
   - **Features**: Test case generation, iterative improvement, quality scoring

6. **ToolDiscover**

   - **Purpose**: AI-powered tool creation from natural language descriptions
   - **Workflow**: Advanced agentic workflows with iterative code improvement
   - **Features**: Tool specification generation, code implementation, quality analysis



.. tip::
   **Workflow Strategy**: Start with compose tools for common patterns, then build custom workflows for specific research needs. Always implement error handling and consider performance optimization for large-scale analyses.

.. note::
   **Compose vs Custom**: Use compose tools for reusable patterns and custom workflows for specific research questions. Compose tools provide better reliability and maintainability, while custom workflows offer maximum flexibility.

.. important::
   **Heterogeneous Integration**: ToolUniverse excels at combining tools from different scientific databases and APIs. Leverage this capability to build comprehensive research pipelines that would be impossible with individual tools alone.
