Tool Composition Tutorial
======================

**Chain ToolUniverse's 1000+ tools into powerful scientific workflows**

Overview
--------

Tool composition is the art of combining individual scientific tools into sophisticated research workflows. ToolUniverse's Tool Composer enables the integration of tools with heterogeneous backends to build end-to-end workflows. By leveraging the Tool Caller for direct in-code execution, Tool Composer generates a container function that exposes both the Tool Caller and ToolUniverse as in-line, executable primitives.

.. code-block:: text

   Individual Tools → Composed Workflows → Research Solutions

   Example: Literature Search & Summary Tool

   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │EuropePMC    │    │ Literature  │    │ Research    │
   │OpenAlex     │ →  │ Search &    │ →  │ Summary     │
   │PubTator     │    │ Summary     │    │ Generated   │
   │AI Reviewer  │    │ Tool        │    │             │
   └─────────────┘    └─────────────┘    └─────────────┘

**Benefits of Tool Composition**:
- **Complex Research**: Solve multi-step problems that no single tool can address
- **Workflow Reuse**: Create reusable research pipelines for common tasks
- **Automation**: Reduce manual coordination between different tools
- **Quality Control**: Build in validation and expert review at critical steps
- **Heterogeneous Integration**: Combine tools with different backends seamlessly
- **Agentic Loops**: Enable adaptive, multi-step experimental analysis

Tool Composer Architecture
---------------------------

The Tool Composer generates a container function that serves as the execution backbone for complex workflows. This container function, implemented as `compose(arguments, tooluniverse, call_tool)`, contains the logic for coordinating different types of tools so they work together in a single workflow.

**Container Function Components**:

1. **arguments**: Specifies the tool call arguments that follow the interaction protocol schema of ToolUniverse
2. **tooluniverse**: An instance of ToolUniverse that provides all available functions that ToolUniverse can support
3. **call_tool**: A callable interface of Tool Caller that abstracts the invocation of individual tools in ToolUniverse

**Execution Patterns**:
- **Chaining**: Chain the output of one tool into the input of the next
- **Broadcasting**: Call multiple tools with a single query
- **Agentic Loops**: Build agentic loops that use agentic tools to generate function calls, execute tools, and incorporate tool feedback for multi-step experimental analysis

How Tool Composition Works
---------------------------

ToolUniverse's ComposeTool system works through a configuration-driven approach:

1. **Configuration File**: Define compose tools in a JSON file like `compose_tools.json`
2. **Implementation Script**: Write Python scripts in the compose environment: `def compose(arguments, tooluniverse, call_tool): ...`
3. **Automatic Loading**: ComposeTool automatically loads dependencies and executes workflows

Creating Your First Compose Tool
---------------------------------

Let's create a literature search and summary tool as an example:

Step 1: Create the Implementation Script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file `src/tooluniverse/compose_scripts/literature_tool.py`:

.. code-block:: python

   """
   Literature Search & Summary Tool
   Minimal compose tool perfect for paper screenshots
   """

   def compose(arguments, tooluniverse, call_tool):
       """Search literature and generate summary"""
       topic = arguments['research_topic']

       literature = {}
       literature['pmc'] = call_tool('EuropePMC_search_articles', {'query': topic, 'limit': 5})
       literature['openalex'] = call_tool('openalex_literature_search', {'search_keywords': topic, 'max_results': 5})
       literature['pubtator'] = call_tool('PubTator3_LiteratureSearch', {'text': topic, 'page_size': 5})

       summary = call_tool('MedicalLiteratureReviewer', {
           'research_topic': topic, 'literature_content': str(literature),
           'focus_area': 'key findings', 'study_types': 'all studies',
           'quality_level': 'all evidence', 'review_scope': 'rapid review'
       })

       return summary

Step 2: Add Configuration to compose_tools.json
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add this configuration to `src/tooluniverse/data/compose_tools.json`:

.. code-block:: json

   {
     "type": "ComposeTool",
     "name": "LiteratureSearchTool",
     "description": "Comprehensive literature search and summary tool that searches multiple databases (EuropePMC, OpenAlex, PubTator) and generates AI-powered summaries of research findings",
     "parameter": {
       "type": "object",
       "properties": {
         "research_topic": {
           "type": "string",
           "description": "The research topic or query to search for in the literature"
         }
       },
       "required": ["research_topic"]
     },
     "auto_load_dependencies": true,
     "fail_on_missing_tools": false,
     "required_tools": [
       "EuropePMC_search_articles",
       "openalex_literature_search",
       "PubTator3_LiteratureSearch",
       "MedicalLiteratureReviewer"
     ],
     "composition_file": "literature_tool.py",
     "composition_function": "compose"
   }

Step 3: Use Your Compose Tool
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once configured, you can use your compose tool like any other ToolUniverse tool:

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()

   # Load compose tools
   tu.load_tools(['compose_tools'])

   # Use your literature search tool
   result = tu.call_tool('LiteratureSearchTool', {
       'research_topic': 'COVID-19 vaccine efficacy'
   })

   print(result)

Compose Tool Configuration Reference
------------------------------------

Required Fields
~~~~~~~~~~~~~~~

- **type**: Must be "ComposeTool"
- **name**: Unique name for your compose tool
- **description**: Human-readable description of what the tool does
- **parameter**: JSON schema defining input parameters
- **composition_file**: Python file in `compose_scripts/` directory
- **composition_function**: Function name to call (usually "compose")

Optional Fields
~~~~~~~~~~~~~~~

- **auto_load_dependencies**: Whether to automatically load required tools (default: true)
- **fail_on_missing_tools**: Whether to fail if required tools are missing (default: false)
- **required_tools**: List of tool names that must be available

Compose Function Signature
~~~~~~~~~~~~~~~~~~~~~~~~~~

Your compose function must follow this exact signature:

.. code-block:: python

   def compose(arguments, tooluniverse, call_tool):
       """
       Compose function signature

       Args:
           arguments (dict): Input parameters from the tool call
           tooluniverse (ToolUniverse): Reference to the ToolUniverse instance
           call_tool (function): Function to call other tools

       Returns:
           Any: The result of your composition
       """
       # Your composition logic here
       pass

Heterogeneous Workflow Construction
------------------------------------

As illustrated in the ToolUniverse paper, a composed tool can run several literature search tools concurrently and then invoke a summarization agent to synthesize the findings, demonstrating heterogeneous workflow construction in which each step is driven by tool execution. This approach enables:

- **Multi-backend Integration**: Combine tools from different scientific databases and APIs
- **Concurrent Execution**: Run multiple tools simultaneously for efficiency
- **Intelligent Synthesis**: Use AI agents to synthesize results from heterogeneous sources
- **Adaptive Analysis**: Build workflows that can adapt based on intermediate results

Core Composition Patterns
--------------------------

1. Sequential Chaining
~~~~~~~~~~~~~~~~~~~~~~

**Use Case**: Linear workflows where each step depends on the previous one

**Pattern**: Chain the output of one tool into the input of the next

.. code-block:: python

   def compose(arguments, tooluniverse, call_tool):
       """Sequential pipeline: Disease → Targets → Drugs → Safety Assessment"""

       disease_id = arguments['disease_efo_id']

       # Step 1: Find disease-associated targets
       targets_result = call_tool('OpenTargets_get_associated_targets_by_disease_efoId', {
           'efoId': disease_id
       })

       top_targets = targets_result["data"]["disease"]["associatedTargets"]["rows"][:5]

       # Step 2: Find known drugs for this disease
       drugs_result = call_tool('OpenTargets_get_associated_drugs_by_disease_efoId', {
           'efoId': disease_id,
           'size': 20
       })

       drug_rows = drugs_result["data"]["disease"]["knownDrugs"]["rows"]

       # Step 3: Extract SMILES and assess safety
       safety_assessments = []
       processed_drugs = set()

       for drug in drug_rows[:5]:  # Limit for demo
           drug_name = drug["drug"]["name"]
           if drug_name in processed_drugs:
               continue
           processed_drugs.add(drug_name)

           # Get SMILES from drug name
           cid_result = call_tool('PubChem_get_CID_by_compound_name', {
               'name': drug_name
           })

           if cid_result and 'IdentifierList' in cid_result:
               cids = cid_result['IdentifierList']['CID']
               if cids:
                   smiles_result = call_tool('PubChem_get_compound_properties_by_CID', {
                       'cid': cids[0]
                   })

                   if smiles_result and 'PropertyTable' in smiles_result:
                       properties = smiles_result['PropertyTable']['Properties'][0]
                       smiles = properties.get('CanonicalSMILES') or properties.get('ConnectivitySMILES')

                       if smiles:
                           # Assess safety properties
                           bbb_result = call_tool('ADMETAI_predict_BBB_penetrance', {
                               'smiles': [smiles]
                           })

                           safety_assessments.append({
                               'drug_name': drug_name,
                               'smiles': smiles,
                               'bbb_penetrance': bbb_result
                           })

       return {
           'disease': disease_id,
           'targets_found': len(top_targets),
           'drugs_analyzed': len(safety_assessments),
           'safety_results': safety_assessments
       }

2. Broadcasting (Parallel Execution)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Use Case**: Independent operations that can run simultaneously

**Pattern**: Call multiple tools with a single query (broadcasting)

.. code-block:: python

   def compose(arguments, tooluniverse, call_tool):
       """Parallel search across multiple literature databases"""

       research_topic = arguments['research_topic']

       # Execute searches in parallel
       literature = {}
       literature['pmc'] = call_tool('EuropePMC_search_articles', {
           'query': research_topic, 'limit': 50
       })
       literature['openalex'] = call_tool('openalex_literature_search', {
           'search_keywords': research_topic, 'max_results': 50
       })
       literature['pubtator'] = call_tool('PubTator3_LiteratureSearch', {
           'text': research_topic, 'page_size': 50
       })

       # Synthesize findings using AI agent
       synthesis = call_tool('MedicalLiteratureReviewer', {
           'research_topic': research_topic,
           'literature_content': str(literature),
           'focus_area': 'key findings',
           'study_types': 'all studies',
           'quality_level': 'all evidence',
           'review_scope': 'comprehensive review'
       })

       return {
           'topic': research_topic,
           'sources_searched': len(literature),
           'total_papers': sum(len(r.get('documents', r.get('papers', [])))
                              for r in literature.values()),
           'synthesis': synthesis,
           'detailed_results': literature
       }

3. Agentic Loops
~~~~~~~~~~~~~~~~

**Use Case**: Iterative optimization with AI guidance and tool feedback

**Pattern**: Build agentic loops that use agentic tools to generate function calls, execute tools, and incorporate tool feedback for multi-step experimental analysis

.. code-block:: python

   def compose(arguments, tooluniverse, call_tool):
       """Iterative compound optimization with AI-guided feedback loops"""

       initial_smiles = arguments['initial_smiles']
       target_protein = arguments['target_protein']

       current_compound = initial_smiles
       optimization_history = []
       max_iterations = 5
       target_affinity = -8.0  # Strong binding threshold

       for iteration in range(max_iterations):
           # Step 1: Predict binding affinity using molecular docking
           binding_result = call_tool('boltz2_docking', {
               'protein_id': target_protein,
               'ligand_smiles': current_compound
           })

           # Step 2: Predict ADMET properties
           bbb_result = call_tool('ADMETAI_predict_BBB_penetrance', {
               'smiles': [current_compound]
           })

           bio_result = call_tool('ADMETAI_predict_bioavailability', {
               'smiles': [current_compound]
           })

           tox_result = call_tool('ADMETAI_predict_toxicity', {
               'smiles': [current_compound]
           })

           # Step 3: Record iteration data
           iteration_data = {
               'iteration': iteration,
               'compound': current_compound,
               'binding_affinity': binding_result.get('binding_affinity'),
               'binding_probability': binding_result.get('binding_probability'),
               'bbb_penetrance': bbb_result,
               'bioavailability': bio_result,
               'toxicity': tox_result
           }
           optimization_history.append(iteration_data)

           # Step 4: Check if target achieved
           if binding_result.get('binding_affinity', 0) <= target_affinity:
               break

           # Step 5: AI-guided compound optimization
           # Use an agentic tool to analyze current results and suggest improvements
           optimization_suggestion = call_tool('ChemicalOptimizationAgent', {
               'current_compound': current_compound,
               'current_properties': iteration_data,
               'optimization_goals': ['binding_affinity', 'oral_bioavailability'],
               'target_protein': target_protein
           })

           # Step 6: Generate next compound based on AI feedback
           next_compound = call_tool('CompoundGenerator', {
               'base_compound': current_compound,
               'optimization_suggestions': optimization_suggestion,
               'modification_type': 'targeted_improvement'
           })

           current_compound = next_compound.get('new_compound', current_compound)

       return {
           'initial_compound': initial_smiles,
           'final_compound': current_compound,
           'iterations': len(optimization_history),
           'optimization_history': optimization_history,
           'target_achieved': binding_result.get('binding_affinity', 0) <= target_affinity
       }

4. Error Handling and Fallbacks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Use Case**: Robust workflows that handle failures gracefully

**Pattern**: Implement fallback mechanisms and graceful degradation

.. code-block:: python

   def compose(arguments, tooluniverse, call_tool):
       """Workflow with comprehensive error handling and fallbacks"""

       results = {"status": "running", "completed_steps": []}

       try:
           # Step 1: Critical initial step
           step1_result = call_tool('critical_analysis_tool', arguments)
           results["step1"] = step1_result
           results["completed_steps"].append("step1")

       except Exception as e:
           results["status"] = "failed"
           results["error"] = f"Step 1 failed: {str(e)}"
           return results

       try:
           # Step 2: Optional enhancement step
           step2_result = call_tool('enhancement_tool', {"data": step1_result})
           results["step2"] = step2_result
           results["completed_steps"].append("step2")

       except Exception as e:
           # Continue without this step
           results["step2_warning"] = f"Enhancement step failed: {str(e)}"

       # Step 3: Alternative approaches with fallback
       try:
           step3_result = call_tool('primary_validation_tool', {"data": step1_result})
           results["validation"] = step3_result

       except Exception:
           # Fallback validation method
           try:
               fallback_result = call_tool('alternative_validation_tool', {"data": step1_result})
               results["validation"] = fallback_result
               results["validation_method"] = "fallback"

           except Exception as e:
               results["validation_error"] = str(e)

       results["status"] = "completed"
       return results

Real-World Composition Examples
-------------------------------

For comprehensive examples of compose tools in action, see the :doc:`scientific_workflows` Tutorial, which includes:

- **Comprehensive Drug Discovery Pipeline**: End-to-end workflow from target identification to safety assessment
- **Biomarker Discovery Workflow**: Multi-step biomarker validation using literature, expression data, and pathway analysis
- **Advanced Literature Review**: AI-powered systematic reviews with citation analysis
- **Agentic Research Workflows**: Adaptive workflows that use AI feedback for multi-step analysis

These examples demonstrate how compose tools can orchestrate complex scientific workflows, combining tools from different backends to solve real-world research problems.

Tool Caller Interface
-----------------------

The Tool Caller provides a callable interface that abstracts the invocation of individual tools in ToolUniverse. This abstraction enables:

- **Unified Tool Access**: All tools are accessed through the same `call_tool` interface
- **Protocol Compliance**: Tool calls follow the interaction protocol schema of ToolUniverse
- **Error Handling**: Consistent error handling across different tool types
- **Dependency Management**: Automatic loading and management of tool dependencies

**Tool Caller Usage Pattern**:

.. code-block:: python

   def compose(arguments, tooluniverse, call_tool):
       # Direct tool invocation through the Tool Caller interface
       result = call_tool('tool_name', {'param1': 'value1', 'param2': 'value2'})

       # The call_tool function handles:
       # - Tool loading and instantiation
       # - Parameter validation
       # - Execution and error handling
       # - Result formatting

       return result

Troubleshooting
---------------

Common Issues and Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Tool Not Found Error**
   - Check that the tool name is correct in your compose script
   - Ensure the tool is loaded in ToolUniverse
   - Verify the tool is in the `required_tools` list
   - Use `auto_load_dependencies: true` to automatically load missing tools

2. **Import Errors**
   - Make sure your compose script is in the `compose_scripts/` directory
   - Check that the function name matches `composition_function`
   - Verify the function signature is correct: `def compose(arguments, tooluniverse, call_tool):`

3. **Parameter Errors**
   - Validate your parameter schema in the JSON configuration
   - Check that required parameters are provided
   - Ensure parameter types match the schema
   - Follow the interaction protocol schema of ToolUniverse

4. **Performance Issues**
   - Limit the number of tools called in sequence
   - Use `auto_load_dependencies: true` for automatic loading
   - Consider caching results for repeated calls
   - Implement proper error handling to avoid cascading failures

5. **Heterogeneous Backend Issues**
   - Ensure all required tools are available across different backends
   - Use `fail_on_missing_tools: false` for graceful degradation
   - Implement fallback mechanisms for critical workflow steps

Available Compose Tools
------------------------

ToolUniverse currently provides several pre-built compose tools that demonstrate different workflow patterns:

**✅ Working Compose Tools**:

1. **LiteratureSearchTool** - Literature research and synthesis
   - Searches EuropePMC, OpenAlex, and PubTator databases
   - Uses AI agent for literature summarization
   - Demonstrates broadcasting pattern

2. **ComprehensiveDrugDiscoveryPipeline** - End-to-end drug discovery
   - Target identification using OpenTargets
   - Lead discovery from known drugs
   - Safety assessment using ADMETAI tools
   - Literature validation
   - Demonstrates sequential chaining with tool integration

3. **BiomarkerDiscoveryWorkflow** - Biomarker discovery and validation
   - Literature-based biomarker discovery
   - Multi-strategy gene search using HPA
   - Comprehensive pathway analysis using HPA tools
   - Clinical validation using FDA data
   - Demonstrates multi-strategy fallbacks and error handling

4. **DrugSafetyAnalyzer** - Drug safety assessment
   - PubChem compound information retrieval
   - EuropePMC literature search
   - Demonstrates safety-focused workflows

5. **ToolDescriptionOptimizer** - Tool optimization
   - AI-powered tool description improvement
   - Test case generation and quality evaluation
   - Demonstrates agentic optimization loops

6. **ToolDiscover** - Tool discovery and generation
   - AI-powered tool creation from descriptions
   - Iterative code improvement
   - Demonstrates advanced agentic workflows

**Key Features**:
- **All tools tested and working** with real data processing
- **Comprehensive error handling** with graceful fallbacks
- **Tool chaining** for complex multi-step workflows
- **Dynamic data extraction** (e.g., SMILES from drug names)
- **Multi-strategy approaches** for robust data retrieval

Summary
-------

ToolUniverse's Tool Composer enables the creation of sophisticated scientific workflows by combining individual tools with heterogeneous backends. The container function `compose(arguments, tooluniverse, call_tool)` serves as the execution backbone, providing:

- **Flexible Multi-tool Execution**: Support for chaining, broadcasting, and agentic loops
- **Heterogeneous Integration**: Seamless combination of tools from different scientific databases and APIs
- **Adaptive Analysis**: Multi-step experimental analysis with tool feedback incorporation
- **Protocol Compliance**: Consistent interaction with tools through the ToolUniverse schema

The Tool Caller interface abstracts tool invocation, enabling developers to focus on workflow logic rather than tool management details. This architecture supports complex research patterns while maintaining simplicity and reliability.

Next Steps
----------

- **Learn Components**: :doc:`../expand_tooluniverse/architecture` - Understand ToolUniverse architecture
- **Platform Setup**: :doc:`building_ai_scientists/index` - Connect to AI agents
- **Case Studies**: :doc:`scientific_workflows` - Real composition examples

.. tip::
   **Start simple**: Begin with sequential workflows like the LiteratureSearchTool example, then progress to more complex patterns as you become comfortable with tool composition.

.. note::
   **Compose Tool Location**: All compose scripts must be placed in `src/tooluniverse/compose_scripts/` directory and registered in `src/tooluniverse/data/compose_tools.json`.

.. important::
   **Tool Composer Architecture**: The Tool Composer generates container functions that expose ToolUniverse and Tool Caller as in-line, executable primitives, enabling flexible multi-tool execution patterns for complex scientific workflows.
