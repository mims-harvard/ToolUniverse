Examples & Code Samples
========================

**Comprehensive examples from basic queries to advanced scientific workflows.**

Learn ToolUniverse through practical, copy-paste examples that you can run immediately. This Tutorial progresses from simple 30-second tests to complex multi-database research pipelines.

🚀 Getting Started Examples
----------------------------

30-Second Test Drive
~~~~~~~~~~~~~~~~~~~~

Verify your installation and see ToolUniverse in action:

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize
   tu = ToolUniverse()
   tu.load_tools()

   # Check what's available
   print(f"✅ Loaded {len(tu.all_tools)} tools")

   # List first 5 tools
   for tool in tu.list_built_in_tools()[:5]:
       print(f"   • {tool}")

Your First Scientific Query
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse

   tu = ToolUniverse()
   tu.load_tools()

   # Search for drug adverse events
   query = {
       "name": "FAERS_count_reactions_by_drug_event",
       "arguments": {"medicinalproduct": "aspirin"}
   }

   try:
       result = tu.run(query)
       print(f"✅ Found {len(result.get('results', []))} adverse event reports")

       # Show first result
       if result.get('results'):
           first_event = result['results'][0]
           print(f"Example: {first_event.get('patient', {}).get('reaction', 'N/A')}")

   except Exception as e:
       print(f"❌ Error: {e}")

📊 Basic Scientific Queries
----------------------------

Gene Information
~~~~~~~~~~~~~~~~

Get comprehensive protein/gene information:

.. code-block:: python

   # Look up protein function by UniProt accession (BRCA1 → P38398)
   gene_query = {
       "name": "UniProt_get_function_by_accession",
       "arguments": {"accession": "P38398"}
   }

   protein_info = tu.run(gene_query)

   if protein_info:
       print(f"Gene: {protein_info.get('gene_symbol', 'Unknown')}")
       print(f"Function: {protein_info.get('function', 'No description available')}")
       print(f"Location: {protein_info.get('subcellular_location', 'Unknown')}")

Disease Information
~~~~~~~~~~~~~~~~~~~

Explore disease definitions and associations:

.. code-block:: python

   # Find disease information
   disease_query = {
       "name": "OpenTargets_get_disease_id_description_by_name",
       "arguments": {"diseaseName": "Alzheimer's disease"}
   }

   disease_info = tu.run(disease_query)

   if disease_info and 'data' in disease_info:
       disease_data = disease_info['data']
       print(f"Disease ID: {disease_data['id']}")
       print(f"Description: {disease_data['description']}")

       # Get associated targets
       targets_query = {
           "name": "OpenTargets_get_associated_targets_by_disease_efoId",
           "arguments": {"efoId": disease_data['id']}
       }

       targets = tu.run(targets_query)
       if targets and 'data' in targets:
           print(f"\nTop 3 associated targets:")
           for target in targets['data'][:3]:
               symbol = target.get('approvedSymbol', 'Unknown')
               score = target.get('associationScore', 0)
               print(f"   • {symbol}: {score:.3f}")

Drug Safety Analysis
~~~~~~~~~~~~~~~~~~~~

Check drug safety information:

.. code-block:: python

   # Get FDA drug warnings
   warnings_query = {
       "name": "openfda_get_warnings_by_drug_name",
       "arguments": {
           "drug_name": "warfarin",
           "limit": 3
       }
   }

   warnings = tu.run(warnings_query)

   if warnings and 'results' in warnings:
       print("⚠️  FDA warnings for warfarin:")
       for warning in warnings['results']:
           warning_text = warning.get('warnings', ['No warning text'])
           if isinstance(warning_text, list):
               warning_text = warning_text[0] if warning_text else 'No warning text'
           print(f"   • {warning_text[:100]}...")

Literature Search
~~~~~~~~~~~~~~~~~

Find relevant scientific papers:

.. code-block:: python

   # Search literature
   literature_query = {
       "name": "PubTator_search_publications",
       "arguments": {
           "query": "CRISPR cancer therapy",
           "limit": 5
       }
   }

   papers = tu.run(literature_query)

   if papers and 'results' in papers:
       print("📄 Recent papers on CRISPR cancer therapy:")
       for paper in papers['results']:
           title = paper.get('title', 'No title')
           authors = paper.get('authors', [])
           author_str = ', '.join(authors[:2]) + ('...' if len(authors) > 2 else '')
           print(f"   • {title}")
           print(f"     Authors: {author_str}")
           print()

🔬 Intermediate Workflows
-------------------------

Drug-Target-Disease Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive analysis connecting drugs, targets, and diseases:

.. code-block:: python

   def analyze_drug_target_disease(drug_name, disease_name):
       """Complete drug-target-disease analysis workflow"""

       results = {}

       # 1. Get disease information
       disease_query = {
           "name": "OpenTargets_get_disease_id_description_by_name",
           "arguments": {"diseaseName": disease_name}
       }

       disease_info = tu.run(disease_query)
       if not disease_info or 'data' not in disease_info:
           print(f"❌ Could not find disease: {disease_name}")
           return None

       disease_id = disease_info['data']['id']
       results['disease'] = disease_info['data']
       print(f"🩺 Analyzing disease: {disease_name} ({disease_id})")

       # 2. Get disease-associated targets
       targets_query = {
           "name": "OpenTargets_get_associated_targets_by_disease_efoId",
           "arguments": {"efoId": disease_id, "limit": 10}
       }

       targets = tu.run(targets_query)
       if targets and 'data' in targets:
           results['targets'] = targets['data']
           print(f"🎯 Found {len(targets['data'])} associated targets")

           # Show top targets
           for target in targets['data'][:3]:
               symbol = target.get('approvedSymbol', 'Unknown')
               score = target.get('associationScore', 0)
               print(f"   • {symbol}: {score:.3f}")

       # 3. Get drug information
       drug_query = {
           "name": "PubChem_get_compound_info",
           "arguments": {"compound_name": drug_name}
       }

       drug_info = tu.run(drug_query)
       if drug_info:
           results['drug'] = drug_info
           print(f"💊 Drug information retrieved for: {drug_name}")

       # 4. Check for adverse events
       adverse_query = {
           "name": "FAERS_count_reactions_by_drug_event",
           "arguments": {"medicinalproduct": drug_name}
       }

       adverse_events = tu.run(adverse_query)
       if adverse_events and 'results' in adverse_events:
           results['adverse_events'] = adverse_events['results']
           print(f"⚠️  Found {len(adverse_events['results'])} adverse event reports")

       return results

   # Example usage
   analysis = analyze_drug_target_disease("aspirin", "cardiovascular disease")

Multi-Database Gene Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive gene analysis across multiple databases:

.. code-block:: python

   def comprehensive_gene_analysis(gene_symbol):
       """Analyze a gene across multiple databases"""

       print(f"🧬 Comprehensive analysis of {gene_symbol}")
       print("=" * 50)

       analysis_results = {}

       # 1. Basic protein function annotation by accession
       # Map your gene symbol to accession externally, then query by accession
       protein_query = {
           "name": "UniProt_get_function_by_accession",
           "arguments": {"accession": "P38398" if gene_symbol == "BRCA1" else "P04637"}
       }

       protein_info = tu.run(protein_query)
       if protein_info:
           analysis_results['protein'] = protein_info
           print(f"✅ Protein information: {protein_info.get('function', 'N/A')[:100]}...")

       # 2. Disease associations
       disease_query = {
           "name": "OpenTargets_get_associated_diseases_by_target",
           "arguments": {"target_symbol": gene_symbol, "limit": 5}
       }

       diseases = tu.run(disease_query)
       if diseases and 'data' in diseases:
           analysis_results['diseases'] = diseases['data']
           print(f"✅ Associated diseases ({len(diseases['data'])}):")
           for disease in diseases['data'][:3]:
               name = disease.get('name', 'Unknown')
               score = disease.get('associationScore', 0)
               print(f"   • {name}: {score:.3f}")

       # 3. Pathway analysis
       pathway_query = {
           "name": "Enrichr_analyze_gene_list",
           "arguments": {
               "gene_list": [gene_symbol],
               "library": "KEGG_2021_Human"
           }
       }

       pathways = tu.run(pathway_query)
       if pathways:
           analysis_results['pathways'] = pathways
           print(f"✅ Pathway analysis completed")

       # 4. Literature search
       literature_query = {
           "name": "PubTator_search_publications",
           "arguments": {
               "query": f"@GENE_{gene_symbol}",
               "limit": 10
           }
       }

       papers = tu.run(literature_query)
       if papers and 'results' in papers:
           analysis_results['literature'] = papers['results']
           print(f"✅ Found {len(papers['results'])} relevant papers")

       return analysis_results

   # Example usage
   brca1_analysis = comprehensive_gene_analysis("BRCA1")

Gene Enrichment Analysis
~~~~~~~~~~~~~~~~~~~~~~~~

Perform comprehensive gene enrichment analysis:

.. code-block:: python

   def gene_enrichment_analysis(gene_list, description="Gene set"):
       """Perform comprehensive gene enrichment analysis."""

       print(f"Analyzing {len(gene_list)} genes: {description}")

       # Define libraries for analysis
       libraries = [
           "GO_Biological_Process_2023",
           "GO_Molecular_Function_2023",
           "KEGG_2021_Human",
           "Reactome_2022",
           "WikiPathway_2023_Human",
           "HPO_2023"
       ]

       results = {}
       for library in libraries:
           print(f"\nAnalyzing against {library}...")

           enrichment_query = {
               "name": "enrichr_gene_enrichment_analysis",
               "arguments": {
                   "gene_lists": [gene_list],
                   "libraries": [library]
               }
           }
           enrichment = tu.run(enrichment_query)

           if library in enrichment and enrichment[library]:
               results[library] = enrichment[library]

               print(f"Top 5 enriched terms:")
               for i, term in enumerate(enrichment[library][:5], 1):
                   print(f"{i}. {term['term']}")
                   print(f"   P-value: {term['p_value']:.2e}")
                   print(f"   Adjusted P-value: {term['adjusted_p_value']:.2e}")
                   print(f"   Genes: {'/'.join(term['genes'])}")

       return results

   # Example: Analyze cancer-related genes
   cancer_genes = [
       "BRCA1", "BRCA2", "TP53", "PTEN", "ATM",
       "CHEK2", "PALB2", "MLH1", "MSH2", "MSH6"
   ]

   enrichment_results = gene_enrichment_analysis(
       cancer_genes,
       "Cancer susceptibility genes"
   )

🏭 Advanced Workflows
---------------------

Drug Discovery Pipeline
~~~~~~~~~~~~~~~~~~~~~~~

Complete drug discovery workflow:

.. code-block:: python

   def drug_discovery_pipeline(target_gene, disease_term):
       """Complete drug discovery workflow"""

       pipeline_results = {}

       print(f"🔬 Drug Discovery Pipeline")
       print(f"Target: {target_gene} | Disease: {disease_term}")
       print("=" * 60)

       # 1. Validate target-disease association
       disease_query = {
           "name": "OpenTargets_get_disease_id_description_by_name",
           "arguments": {"diseaseName": disease_term}
       }

       disease_info = tu.run(disease_query)
       if not disease_info or 'data' not in disease_info:
           print("❌ Disease not found")
           return None

       disease_id = disease_info['data']['id']

       # Check if target is associated with disease
       targets_query = {
           "name": "OpenTargets_get_associated_targets_by_disease_efoId",
           "arguments": {"efoId": disease_id, "limit": 50}
       }

       targets = tu.run(targets_query)
       target_found = False
       if targets and 'data' in targets:
           for target in targets['data']:
               if target.get('approvedSymbol', '').upper() == target_gene.upper():
                   target_found = True
                   score = target.get('associationScore', 0)
                   print(f"✅ Target validation: {target_gene} associated with {disease_term} (score: {score:.3f})")
                   break

       if not target_found:
           print(f"⚠️  Target {target_gene} not strongly associated with {disease_term}")

       # 2. Find existing drugs targeting this gene
       drug_target_query = {
           "name": "ChEMBL_get_compounds_by_target",
           "arguments": {"target_symbol": target_gene, "limit": 10}
       }

       compounds = tu.run(drug_target_query)
       if compounds:
           pipeline_results['existing_compounds'] = compounds
           print(f"✅ Found existing compounds targeting {target_gene}")

       # 3. Check clinical trials
       trials_query = {
           "name": "ClinicalTrials_search_studies",
           "arguments": {
               "condition": disease_term,
               "intervention": target_gene,
               "limit": 5
           }
       }

       trials = tu.run(trials_query)
       if trials and 'studies' in trials:
           pipeline_results['clinical_trials'] = trials['studies']
           print(f"✅ Found {len(trials['studies'])} relevant clinical trials")

       # 4. Safety analysis for target
       safety_query = {
           "name": "OpenTargets_get_target_safety",
           "arguments": {"target_symbol": target_gene}
       }

       safety_info = tu.run(safety_query)
       if safety_info:
           pipeline_results['safety'] = safety_info
           print(f"✅ Target safety analysis completed")

       # 5. Literature review
       literature_query = {
           "name": "PubTator_search_publications",
           "arguments": {
               "query": f"{target_gene} {disease_term} drug",
               "limit": 20
           }
       }

       papers = tu.run(literature_query)
       if papers and 'results' in papers:
           pipeline_results['literature'] = papers['results']
           print(f"✅ Literature review: {len(papers['results'])} relevant papers")

       return pipeline_results

   # Example usage
   discovery_results = drug_discovery_pipeline("EGFR", "lung cancer")

Pharmacovigilance Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~

Real-world safety monitoring workflow:

.. code-block:: python

   def pharmacovigilance_analysis(drug_name):
       """Comprehensive drug safety monitoring"""

       print(f"🛡️  Pharmacovigilance Analysis: {drug_name}")
       print("=" * 50)

       safety_report = {}

       # 1. FDA adverse events
       adverse_query = {
           "name": "FAERS_count_reactions_by_drug_event",
           "arguments": {"medicinalproduct": drug_name}
       }

       adverse_events = tu.run(adverse_query)
       if adverse_events and 'results' in adverse_events:
           safety_report['adverse_events'] = adverse_events['results']

           # Analyze event types
           event_types = {}
           for event in adverse_events['results']:
               reactions = event.get('patient', {}).get('reaction', [])
               for reaction in reactions:
                   reaction_name = reaction.get('reactionmeddrapt', 'Unknown')
                   event_types[reaction_name] = event_types.get(reaction_name, 0) + 1

           print(f"✅ Adverse events: {len(adverse_events['results'])} reports")
           print("Top adverse reactions:")
           for reaction, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True)[:5]:
               print(f"   • {reaction}: {count} reports")

       # 2. FDA drug labels and warnings
       label_query = {
           "name": "openfda_get_warnings_by_drug_name",
           "arguments": {"drug_name": drug_name, "limit": 10}
       }

       warnings = tu.run(label_query)
       if warnings and 'results' in warnings:
           safety_report['warnings'] = warnings['results']
           print(f"✅ FDA warnings: {len(warnings['results'])} found")

       # 3. Literature safety analysis
       safety_literature_query = {
           "name": "PubTator_search_publications",
           "arguments": {
               "query": f"{drug_name} safety adverse effects",
               "limit": 15
           }
       }

       safety_papers = tu.run(safety_literature_query)
       if safety_papers and 'results' in safety_papers:
           safety_report['safety_literature'] = safety_papers['results']
           print(f"✅ Safety literature: {len(safety_papers['results'])} papers")

       # 4. Clinical trial safety data
       trial_safety_query = {
           "name": "ClinicalTrials_search_studies",
           "arguments": {
               "intervention": drug_name,
               "study_type": "Interventional",
               "limit": 10
           }
       }

       trials = tu.run(trial_safety_query)
       if trials and 'studies' in trials:
           safety_report['clinical_trials'] = trials['studies']
           print(f"✅ Clinical trials: {len(trials['studies'])} found")

       return safety_report

   # Example usage
   safety_analysis = pharmacovigilance_analysis("metformin")

Clinical Trial Analysis
~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive clinical trial analysis:

.. code-block:: python

   def analyze_clinical_trials(condition, intervention=None):
       """Comprehensive clinical trial analysis."""

       print(f"Clinical Trial Analysis")
       print(f"Condition: {condition}")
       if intervention:
           print(f"Intervention: {intervention}")
       print("=" * 50)

       # Search for trials
       trials_query = {
           "name": "ClinicalTrials_search_studies",
           "arguments": {
               "condition": condition,
               "intervention": intervention or "",
               "pageSize": 20
           }
       }
       trials = tu.run(trials_query)

       if not trials or 'studies' not in trials:
           print("No trials found")
           return

       studies = trials['studies']
       print(f"Found {len(studies)} clinical trials")

       # Analyze trial phases
       phases = {}
       statuses = {}

       # Get detailed information
       for i, study in enumerate(studies[:10]):  # Analyze first 10 trials
           nct_id = study['protocolSection']['identificationModule']['nctId']

           # Extract basic info
           design = study['protocolSection'].get('designModule', {})
           status_module = study['protocolSection'].get('statusModule', {})

           phase = design.get('phases', ['N/A'])[0] if design.get('phases') else 'N/A'
           status = status_module.get('overallStatus', 'Unknown')

           phases[phase] = phases.get(phase, 0) + 1
           statuses[status] = statuses.get(status, 0) + 1

           print(f"\n{i+1}. NCT ID: {nct_id}")
           print(f"   Title: {study['protocolSection']['identificationModule'].get('briefTitle', 'N/A')}")
           print(f"   Phase: {phase}")
           print(f"   Status: {status}")

       # Summary statistics
       print(f"\n\nSummary Statistics:")
       print(f"Trial Phases:")
       for phase, count in sorted(phases.items()):
           print(f"  - {phase}: {count} trials")

       print(f"\nTrial Statuses:")
       for status, count in sorted(statuses.items()):
           print(f"  - {status}: {count} trials")

       return {
           'total_trials': len(studies),
           'phases': phases,
           'statuses': statuses
       }

   # Example usage
   trial_analysis = analyze_clinical_trials("cancer", "immunotherapy")

Multi-Modal Analysis
~~~~~~~~~~~~~~~~~~~~

Comprehensive analysis combining multiple data sources:

.. code-block:: python

   def comprehensive_scientific_analysis(gene_of_interest):
       """Multi-modal analysis combining multiple data sources."""

       print(f"Comprehensive Analysis: {gene_of_interest}")
       print("=" * 60)

       results = {}

       # 1. Gene/Target Information
       print("1. Gene/Target Information")
       print("-" * 30)

       target_query = {
           "name": "OpenTargets_get_target_id_description_by_name",
           "arguments": {"target_name": gene_of_interest}
       }
       target_info = tu.run(target_query)

       if target_info:
           ensembl_id = target_info['id']
           results['target_info'] = target_info

           print(f"Ensembl ID: {ensembl_id}")
           print(f"Description: {target_info.get('description', 'N/A')}")

       # 2. Disease Associations
       print(f"\n2. Disease Associations")
       print("-" * 30)

       if 'target_info' in results:
           diseases_query = {
               "name": "OpenTargets_get_diseases_phenotypes_by_target_ensembl",
               "arguments": {"ensembl_id": ensembl_id}
           }
           diseases = tu.run(diseases_query)
           results['diseases'] = diseases

           print(f"Associated diseases: {len(diseases)}")
           for disease in diseases[:5]:
               print(f"- {disease['name']}: Score {disease.get('score', 'N/A')}")

       # 3. Drug Associations
       print(f"\n3. Drug Associations")
       print("-" * 30)

       if 'target_info' in results:
           drugs_query = {
               "name": "OpenTargets_get_associated_drugs_by_target_ensemblID",
               "arguments": {
                   "target_ensembl_id": ensembl_id,
                   "size": 10,
                   "cursor": ""
               }
           }
           drugs = tu.run(drugs_query)
           results['drugs'] = drugs

           print(f"Associated drugs: {len(drugs)}")
           for drug in drugs[:5]:
               print(f"- {drug['name']}: Phase {drug.get('maxClinicalTrialPhase', 'N/A')}")

       # 4. Literature Analysis
       print(f"\n4. Literature Analysis")
       print("-" * 30)

       lit_query = {
           "name": "PubTator_search_publications",
           "arguments": {
               "query": f"@GENE_{gene_of_interest}",
               "page": 0,
               "page_size": 10
           }
       }
       papers = tu.run(lit_query)
       results['literature'] = papers

       if papers and 'results' in papers:
           print(f"Related papers: {len(papers['results'])}")
           for paper in papers['results'][:3]:
               print(f"- PMID {paper['pmid']}: {paper['title'][:80]}...")

       # 5. Functional Analysis
       print(f"\n5. Functional Analysis")
       print("-" * 30)

       enrichment_query = {
           "name": "enrichr_gene_enrichment_analysis",
           "arguments": {
               "gene_lists": [gene_of_interest],
               "libraries": ["GO_Biological_Process_2023"]
           }
       }
       enrichment = tu.run(enrichment_query)
       results['enrichment'] = enrichment

       if enrichment and "GO_Biological_Process_2023" in enrichment:
           go_results = enrichment["GO_Biological_Process_2023"]
           print(f"GO enrichment terms: {len(go_results)}")
           for term in go_results[:3]:
               print(f"- {term['term']}: p={term['p_value']:.2e}")

       return results

   # Example usage
   analysis = comprehensive_scientific_analysis("BRCA1")

🛠️ Utility Functions
---------------------

Error Handling Best Practices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Robust error handling for production use:

.. code-block:: python

   def safe_query_execution(query, max_retries=3, timeout=30):
       """Execute query with comprehensive error handling"""

       for attempt in range(max_retries):
           try:
               # Set timeout for this attempt
               tu_local = ToolUniverse(timeout=timeout)
               tu_local.load_tools()

               result = tu_local.run(query)

               # Validate result structure
               if not isinstance(result, dict):
                   raise ValueError("Invalid result format")

               return {
                   "success": True,
                   "data": result,
                   "attempt": attempt + 1,
                   "error": None
               }

           except ConnectionError as e:
               print(f"🔄 Connection error on attempt {attempt + 1}: {e}")
               if attempt == max_retries - 1:
                   return {"success": False, "error": f"Connection failed: {e}", "data": None}

           except TimeoutError as e:
               print(f"⏱️  Timeout on attempt {attempt + 1}: {e}")
               if attempt == max_retries - 1:
                   return {"success": False, "error": f"Timeout: {e}", "data": None}

           except KeyError as e:
               print(f"🔑 Key error on attempt {attempt + 1}: {e}")
               return {"success": False, "error": f"Invalid query structure: {e}", "data": None}

           except Exception as e:
               print(f"❌ Unexpected error on attempt {attempt + 1}: {e}")
               if attempt == max_retries - 1:
                   return {"success": False, "error": f"Unexpected error: {e}", "data": None}

       return {"success": False, "error": "Max retries exceeded", "data": None}

   # Example usage
   test_query = {
       "name": "FAERS_count_reactions_by_drug_event",
       "arguments": {"medicinalproduct": "aspirin"}
   }

   result = safe_query_execution(test_query)
   if result["success"]:
       print(f"✅ Query succeeded after {result['attempt']} attempts")
       data = result["data"]
   else:
       print(f"❌ Query failed: {result['error']}")

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

Optimize for speed and efficiency:

.. code-block:: python

   import time
   from concurrent.futures import ThreadPoolExecutor, as_completed

   def batch_query_processor(queries, max_workers=5):
       """Process multiple queries in parallel"""

       def execute_single_query(query_data):
           query, query_id = query_data
           start_time = time.time()

           try:
               result = tu.run(query)
               execution_time = time.time() - start_time

               return {
                   "id": query_id,
                   "success": True,
                   "result": result,
                   "execution_time": execution_time,
                   "error": None
               }

           except Exception as e:
               execution_time = time.time() - start_time
               return {
                   "id": query_id,
                   "success": False,
                   "result": None,
                   "execution_time": execution_time,
                   "error": str(e)
               }

       # Prepare query data with IDs
       query_data = [(query, i) for i, query in enumerate(queries)]
       results = []

       # Execute queries in parallel
       with ThreadPoolExecutor(max_workers=max_workers) as executor:
           future_to_query = {
               executor.submit(execute_single_query, qd): qd[1]
               for qd in query_data
           }

           for future in as_completed(future_to_query):
               try:
                   result = future.result()
                   results.append(result)
               except Exception as e:
                   query_id = future_to_query[future]
                   results.append({
                       "id": query_id,
                       "success": False,
                       "result": None,
                       "execution_time": 0,
                       "error": f"Future execution failed: {e}"
                   })

       # Sort results by original order
       results.sort(key=lambda x: x["id"])
       return results

   # Example usage
   batch_queries = [
       {"name": "FAERS_count_reactions_by_drug_event", "arguments": {"medicinalproduct": "aspirin"}},
       {"name": "UniProt_get_function_by_accession", "arguments": {"accession": "P38398"}},
       {"name": "PubTator_search_publications", "arguments": {"query": "cancer", "limit": 3}}
   ]

   batch_results = batch_query_processor(batch_queries)

   for result in batch_results:
       status = "✅" if result["success"] else "❌"
       time_str = f"{result['execution_time']:.2f}s"
       print(f"{status} Query {result['id']}: {time_str}")

Interactive Tool Discovery
~~~~~~~~~~~~~~~~~~~~~~~~~~

Find tools for your research area:

.. code-block:: python

   def find_tools_for_research(research_area):
       """Helper function to find relevant tools"""

       # Keywords for different research areas
       keywords_map = {
           "drug_discovery": ["drug", "compound", "chemical", "pharmaco"],
           "genomics": ["gene", "genome", "dna", "sequence"],
           "disease": ["disease", "disorder", "syndrome", "pathology"],
           "protein": ["protein", "enzyme", "peptide"],
           "clinical": ["clinical", "trial", "patient", "treatment"]
       }

       keywords = keywords_map.get(research_area, [research_area])

       relevant_tools = []
       for tool in tu.all_tools:
           tool_text = f"{tool.get('name', '')} {tool.get('description', '')}".lower()
           if any(keyword in tool_text for keyword in keywords):
               relevant_tools.append(tool)

       return relevant_tools

   # Example usage
   print("🔬 Drug discovery tools:")
   drug_tools = find_tools_for_research("drug_discovery")
   for tool in drug_tools[:3]:
       print(f"   • {tool['name']}")

   print("\n🧬 Genomics tools:")
   gene_tools = find_tools_for_research("genomics")
   for tool in gene_tools[:3]:
       print(f"   • {tool['name']}")

Troubleshooting Examples
~~~~~~~~~~~~~~~~~~~~~~~~

Common issues and solutions:

.. code-block:: python

   def diagnose_tooluniverse():
       """Comprehensive diagnostic function"""

       print("🔍 ToolUniverse Diagnostic Report")
       print("=" * 40)

       # Test 1: Import check
       try:
           tu = ToolUniverse()
           print("✅ Import successful")
       except ImportError as e:
           print(f"❌ Import failed: {e}")
           return

       # Test 2: Tool loading
       try:
           tu.load_tools()
           print(f"✅ Loaded {len(tu.all_tools)} tools")
       except Exception as e:
           print(f"❌ Tool loading failed: {e}")
           return

       # Test 3: Basic functionality
       try:
           available_tools = tu.list_built_in_tools()
           print(f"✅ Found {len(available_tools)} available tools")
       except Exception as e:
           print(f"❌ Tool listing failed: {e}")

       # Test 4: Sample execution
       try:
           # Try a simple query
           result = tu.run("help")  # Simple test query
           print("✅ Basic execution test passed")
       except Exception as e:
           print(f"⚠️  Execution test failed: {e}")
           print("   This might be normal if no 'help' tool exists")

       print("\n📋 Diagnostic complete!")

   # Run diagnostic
   diagnose_tooluniverse()

🎯 Next Steps
-------------

You've now seen ToolUniverse in action! Here's what to explore next:

* **🔬 Scientific Workflows** → :doc:`scientific_workflows` - Ready for real research? See domain-specific workflows for drug discovery, literature review, and more
* **🛠️ All Available Tools** → :doc:`../tools/tools_config_index` - Explore the complete catalog of 1000+ scientific tools and their capabilities
* **🎯 Custom Development** → :doc:`finding_tools` - Want to create your own tools or integrate with AI assistants? Check out our tutorials

.. tip::
   **Practice tip**: Try modifying the examples above with your own research interests. Change gene names, diseases, or drug names to explore data relevant to your work!
