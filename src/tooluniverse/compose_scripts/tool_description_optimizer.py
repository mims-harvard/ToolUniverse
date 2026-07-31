import json
import os
import re


def compose(arguments, tooluniverse, call_tool):
    tool_config = arguments["tool_config"]
    tool_name = tool_config.get("name", "unnamed_tool")
    save_to_file = arguments.get("save_to_file", False)
    output_file = arguments.get("output_file")
    max_iterations = arguments.get("max_iterations", 3)  # Maximum optimization rounds
    satisfaction_threshold = arguments.get(
        "satisfaction_threshold", 8
    )  # Quality score threshold (1-10)

    # 1. Generate test cases
    tc_result = call_tool("TestCaseGenerator", {"tool_config": tool_config})
    print("TestCaseGenerator result:", json.dumps(tc_result, indent=2))

    # Handle the result - it should be a list of test cases or a dict containing test cases
    test_cases = []
    if isinstance(tc_result, list):
        test_cases = tc_result
    elif isinstance(tc_result, dict):
        # Check if it has a 'result' key (from agentic tool)
        if "result" in tc_result:
            result_data = tc_result["result"]
            if isinstance(result_data, list):
                test_cases = result_data
            elif isinstance(result_data, str):
                # Try to parse JSON string with robust whitespace handling
                try:
                    # Multiple parsing strategies for robust handling
                    strategies = [
                        result_data.strip(),  # Simple strip
                        re.sub(r"\s+", " ", result_data.strip()),  # Collapse whitespace
                        re.sub(r"\s", "", result_data),  # Remove all whitespace
                    ]

                    for strategy in strategies:
                        try:
                            parsed_result = json.loads(strategy)
                            if isinstance(parsed_result, list):
                                test_cases = parsed_result
                                break
                            elif isinstance(parsed_result, dict):
                                test_cases = parsed_result.get("test_cases", [])
                                break
                        except json.JSONDecodeError:
                            continue

                    # If direct parsing fails, try pattern matching
                    if not test_cases:
                        json_patterns = [
                            r"\[.*?\]",  # Array pattern
                            r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",  # Single object
                        ]

                        for strategy in strategies:
                            for pattern in json_patterns:
                                matches = re.findall(pattern, strategy, re.DOTALL)
                                for match in matches:
                                    try:
                                        parsed_result = json.loads(match)
                                        if isinstance(parsed_result, list):
                                            test_cases = parsed_result
                                            break
                                        elif isinstance(parsed_result, dict):
                                            test_cases = [parsed_result]
                                            break
                                    except json.JSONDecodeError:
                                        continue
                                if test_cases:
                                    break
                            if test_cases:
                                break
                except Exception as e:
                    print(f"Failed to parse test cases from result: {e}")
                    test_cases = []
            else:
                test_cases = (
                    result_data.get("test_cases", [])
                    if isinstance(result_data, dict)
                    else []
                )
        else:
            test_cases = tc_result.get("test_cases", [])

    # If we still don't have test cases, generate some basic ones from the tool config
    if not test_cases:
        print("No valid test cases found, generating basic test cases from tool config")
        tool_params = tool_config.get("parameter", {}).get("properties", {})
        required_params = []

        # Extract required parameters correctly
        if "parameter" in tool_config and "properties" in tool_config["parameter"]:
            properties = tool_config["parameter"]["properties"]
            for param_name, param_info in properties.items():
                if param_info.get("required", False):
                    required_params.append(param_name)

            # If no explicitly required params found, check if there's a 'required' field at the parameter level
            if not required_params and "required" in tool_config["parameter"]:
                required_params = tool_config["parameter"]["required"]

        # Generate a basic test case with required parameters
        if required_params and tool_params:
            basic_case = {}
            for param in required_params:
                if param in tool_params:
                    param_type = tool_params[param].get("type", "string")
                    if param_type == "string":
                        basic_case[param] = f"test_{param}_value"
                    elif param_type == "integer":
                        basic_case[param] = 10
                    elif param_type == "boolean":
                        basic_case[param] = True
                    else:
                        basic_case[param] = "test_value"
            if basic_case:
                test_cases = [basic_case]

        # If still no test cases, create a minimal one with available params
        if not test_cases and tool_params:
            basic_case = {}
            for param_name, param_info in list(tool_params.items())[
                :1
            ]:  # Take first param
                param_type = param_info.get("type", "string")
                if param_type == "string":
                    basic_case[param_name] = f"test_{param_name}_value"
                elif param_type == "integer":
                    basic_case[param_name] = 10
                elif param_type == "boolean":
                    basic_case[param_name] = True
                else:
                    basic_case[param_name] = "test_value"
            if basic_case:
                test_cases = [basic_case]

    if not test_cases:
        return {
            "error": "No test cases generated and could not create basic test cases.",
            "raw_result": tc_result,
        }

    # 2. Run tool on each test case
    results = []
    for case in test_cases:
        try:
            # If case is a full tool call dict with 'name' and 'arguments', extract arguments
            if isinstance(case, dict) and "arguments" in case:
                arguments = case["arguments"]
            elif isinstance(case, dict):
                # If case is already just the arguments
                arguments = case
            else:
                arguments = case

            result = tooluniverse.run_one_function(
                {"name": tool_name, "arguments": arguments}
            )
        except Exception as e:
            result = {"error": str(e)}
        results.append({"input": arguments, "output": result})

    # 3. Multi-round optimization until satisfactory
    current_tool_config = tool_config.copy()
    original_description = tool_config.get("description", "")
    optimization_history = []
    previous_feedback = ""  # Track previous round feedback
    all_test_results = results.copy()  # Accumulate test results from all rounds

    for iteration in range(max_iterations):
        print(f"\n=== Optimization Round {iteration + 1}/{max_iterations} ===")

        current_description = current_tool_config.get("description", "")

        # 3a. Generate additional test cases based on previous feedback (after first round)
        current_round_results = []
        if iteration > 0 and previous_feedback:
            print("🧪 Generating additional test cases based on previous feedback...")
            try:
                # Create an enhanced TestCaseGenerator prompt that includes previous feedback
                enhanced_tool_config = current_tool_config.copy()
                enhanced_tool_config["_optimization_feedback"] = previous_feedback
                enhanced_tool_config["_iteration"] = iteration + 1

                new_tc_result = call_tool(
                    "TestCaseGenerator", {"tool_config": enhanced_tool_config}
                )
                print(
                    f"Additional TestCaseGenerator result: {json.dumps(new_tc_result, indent=2)}"
                )

                # Parse new test cases with robust whitespace handling
                new_test_cases = []
                if isinstance(new_tc_result, dict) and "result" in new_tc_result:
                    result_data = new_tc_result["result"]
                    if isinstance(result_data, str):
                        # Aggressive cleaning of whitespace and newlines
                        cleaned_result = re.sub(r"\s+", " ", result_data.strip())
                        # Remove all whitespace and newlines completely for pure JSON detection
                        minimal_result = re.sub(r"\s", "", result_data)

                        # Try multiple parsing strategies
                        parsing_strategies = [
                            cleaned_result,  # Whitespace-collapsed version
                            minimal_result,  # All whitespace removed
                            result_data.strip(),  # Simple strip
                        ]

                        # Look for JSON array patterns
                        json_patterns = [
                            r"\[.*?\]",  # Array pattern
                            r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",  # Single object
                        ]

                        for strategy in parsing_strategies:
                            # Try direct parsing first
                            try:
                                parsed_result = json.loads(strategy)
                                if isinstance(parsed_result, list):
                                    new_test_cases = parsed_result
                                    break
                                elif isinstance(parsed_result, dict):
                                    new_test_cases = [parsed_result]
                                    break
                            except json.JSONDecodeError:
                                pass

                            # Try pattern matching if direct parsing fails
                            if not new_test_cases:
                                for pattern in json_patterns:
                                    matches = re.findall(pattern, strategy, re.DOTALL)
                                    for match in matches:
                                        try:
                                            parsed_result = json.loads(match)
                                            if isinstance(parsed_result, list):
                                                new_test_cases = parsed_result
                                                break
                                            elif isinstance(parsed_result, dict):
                                                new_test_cases = [parsed_result]
                                                break
                                        except json.JSONDecodeError:
                                            continue
                                    if new_test_cases:
                                        break
                            if new_test_cases:
                                break

                        if not new_test_cases:
                            print(
                                f"Failed to parse new test cases from: {result_data[:200]}..."
                            )
                    elif isinstance(result_data, list):
                        new_test_cases = result_data

                # Run new test cases
                if new_test_cases:
                    print(f"📊 Running {len(new_test_cases)} additional test cases...")
                    for case in new_test_cases:
                        try:
                            if isinstance(case, dict) and "arguments" in case:
                                arguments = case["arguments"]
                            elif isinstance(case, dict):
                                arguments = case
                            else:
                                arguments = case

                            result = tooluniverse.run_one_function(
                                {"name": tool_name, "arguments": arguments}
                            )
                        except Exception as e:
                            result = {"error": str(e)}
                        current_round_results.append(
                            {"input": arguments, "output": result}
                        )

                    # Add new results to accumulated results
                    all_test_results.extend(current_round_results)
                    print(f"✅ Added {len(current_round_results)} new test results")
                else:
                    print("⚠️ No additional test cases generated")

            except Exception as e:
                print(f"❌ Failed to generate additional test cases: {str(e)}")

        # 3b. Analyze results and suggest optimized description using ALL accumulated test results
        # Include previous feedback for iterative improvement
        analysis_input = {
            "original_description": current_description,
            "test_results": json.dumps(
                all_test_results
            ),  # Use ALL accumulated test results
        }

        # Add previous feedback to help guide the next optimization
        if previous_feedback and iteration > 0:
            enhanced_description = f"{current_description}\n\nPrevious optimization feedback: {previous_feedback}"
            analysis_input["original_description"] = enhanced_description

        analysis = call_tool("DescriptionAnalyzer", analysis_input)

        # Handle the analysis result
        optimized_description = None
        rationale = None

        if isinstance(analysis, dict):
            if "result" in analysis:
                # If it's wrapped in a result key
                result_data = analysis["result"]
                if isinstance(result_data, str):
                    try:
                        parsed_analysis = json.loads(result_data)
                        optimized_description = parsed_analysis.get(
                            "optimized_description"
                        )
                        rationale = parsed_analysis.get("rationale")
                    except json.JSONDecodeError:
                        optimized_description = result_data
                        rationale = "Parsed from raw text result"
                elif isinstance(result_data, dict):
                    optimized_description = result_data.get("optimized_description")
                    rationale = result_data.get("rationale")
            else:
                # Direct dict result
                optimized_description = analysis.get("optimized_description")
                rationale = analysis.get("rationale")
        elif isinstance(analysis, str):
            optimized_description = analysis
            rationale = "Generated from string result"

        # Fallback if we still don't have an optimized description
        if not optimized_description:
            optimized_description = f"Enhanced description: {current_description} (Based on test results analysis)"
            rationale = (
                "Generated fallback description based on original and test results"
            )

        # 3c. Optimize argument descriptions using ALL accumulated test results
        optimized_parameters = {}
        argument_rationale = ""

        if (
            "parameter" in current_tool_config
            and "properties" in current_tool_config["parameter"]
        ):
            try:
                # Include previous feedback for parameter optimization too
                arg_analysis_input = {
                    "parameter_schema": json.dumps(current_tool_config["parameter"]),
                    "test_results": json.dumps(
                        all_test_results
                    ),  # Use ALL accumulated test results
                }

                # Add previous feedback to parameter optimization
                if previous_feedback and iteration > 0:
                    # Extract parameter-specific feedback from previous round
                    param_feedback = (
                        f"Previous feedback for improvement: {previous_feedback}"
                    )
                    enhanced_schema = current_tool_config["parameter"].copy()
                    enhanced_schema["_previous_feedback"] = param_feedback
                    arg_analysis_input["parameter_schema"] = json.dumps(enhanced_schema)

                arg_analysis = call_tool(
                    "ArgumentDescriptionOptimizer", arg_analysis_input
                )

                # Parse argument optimization results
                if isinstance(arg_analysis, dict):
                    if "result" in arg_analysis:
                        result_data = arg_analysis["result"]
                        if isinstance(result_data, str):
                            try:
                                parsed_arg_analysis = json.loads(result_data)
                                raw_params = parsed_arg_analysis.get(
                                    "optimized_parameters", {}
                                )
                                # Extract description strings from the result structure
                                optimized_parameters = {}
                                for param_name, param_data in raw_params.items():
                                    if (
                                        isinstance(param_data, dict)
                                        and "description" in param_data
                                    ):
                                        optimized_parameters[param_name] = param_data[
                                            "description"
                                        ]
                                    elif isinstance(param_data, str):
                                        optimized_parameters[param_name] = param_data
                                    else:
                                        optimized_parameters[param_name] = str(
                                            param_data
                                        )
                                argument_rationale = parsed_arg_analysis.get(
                                    "rationale", ""
                                )
                            except json.JSONDecodeError:
                                print("Failed to parse argument optimization result")
                        elif isinstance(result_data, dict):
                            raw_params = result_data.get("optimized_parameters", {})
                            # Extract description strings from the result structure
                            optimized_parameters = {}
                            for param_name, param_data in raw_params.items():
                                if (
                                    isinstance(param_data, dict)
                                    and "description" in param_data
                                ):
                                    optimized_parameters[param_name] = param_data[
                                        "description"
                                    ]
                                elif isinstance(param_data, str):
                                    optimized_parameters[param_name] = param_data
                                else:
                                    optimized_parameters[param_name] = str(param_data)
                            argument_rationale = result_data.get("rationale", "")
                    else:
                        raw_params = arg_analysis.get("optimized_parameters", {})
                        # Extract description strings from the result structure
                        optimized_parameters = {}
                        for param_name, param_data in raw_params.items():
                            if (
                                isinstance(param_data, dict)
                                and "description" in param_data
                            ):
                                optimized_parameters[param_name] = param_data[
                                    "description"
                                ]
                            elif isinstance(param_data, str):
                                optimized_parameters[param_name] = param_data
                            else:
                                optimized_parameters[param_name] = str(param_data)
                        argument_rationale = arg_analysis.get("rationale", "")

            except Exception as e:
                print(f"Failed to optimize argument descriptions: {str(e)}")
                argument_rationale = (
                    f"Failed to optimize argument descriptions: {str(e)}"
                )

        # 3d. Update current tool config with optimizations
        current_tool_config["description"] = optimized_description
        if (
            optimized_parameters
            and "parameter" in current_tool_config
            and "properties" in current_tool_config["parameter"]
        ):
            for param_name, new_description in optimized_parameters.items():
                if param_name in current_tool_config["parameter"]["properties"]:
                    current_tool_config["parameter"]["properties"][param_name][
                        "description"
                    ] = new_description

        # 3e. Evaluate quality of current optimization using ALL accumulated test results
        try:
            quality_evaluation = call_tool(
                "DescriptionQualityEvaluator",
                {
                    "tool_description": optimized_description,
                    "parameter_descriptions": json.dumps(optimized_parameters),
                    "test_results": json.dumps(
                        all_test_results
                    ),  # Use ALL accumulated test results
                },
            )

            # Parse quality evaluation result
            quality_score = 0
            is_satisfactory = False
            feedback = ""
            criteria_scores = {}

            if isinstance(quality_evaluation, dict):
                if "result" in quality_evaluation:
                    result_data = quality_evaluation["result"]
                    if isinstance(result_data, str):
                        try:
                            parsed_eval = json.loads(result_data)
                            quality_score = parsed_eval.get("overall_score", 0)
                            is_satisfactory = parsed_eval.get("is_satisfactory", False)
                            feedback = parsed_eval.get("feedback", "")
                            criteria_scores = parsed_eval.get("criteria_scores", {})
                        except json.JSONDecodeError:
                            quality_score = 5  # Default middle score
                            feedback = "Failed to parse evaluation result"
                    elif isinstance(result_data, dict):
                        quality_score = result_data.get("overall_score", 0)
                        is_satisfactory = result_data.get("is_satisfactory", False)
                        feedback = result_data.get("feedback", "")
                        criteria_scores = result_data.get("criteria_scores", {})
                else:
                    quality_score = quality_evaluation.get("overall_score", 0)
                    is_satisfactory = quality_evaluation.get("is_satisfactory", False)
                    feedback = quality_evaluation.get("feedback", "")
                    criteria_scores = quality_evaluation.get("criteria_scores", {})

        except Exception as e:
            print(f"Failed to evaluate quality: {str(e)}")
            quality_score = 5  # Default middle score
            is_satisfactory = quality_score >= satisfaction_threshold
            feedback = f"Quality evaluation failed: {str(e)}"
            criteria_scores = {}

        # Record this iteration
        iteration_record = {
            "iteration": iteration + 1,
            "description": optimized_description,
            "parameters": optimized_parameters.copy(),
            "description_rationale": rationale,
            "argument_rationale": argument_rationale,
            "quality_score": quality_score,
            "criteria_scores": criteria_scores,
            "feedback": feedback,
            "is_satisfactory": is_satisfactory,
        }
        optimization_history.append(iteration_record)

        print(f"Quality Score: {quality_score}/10")
        print(f"Satisfactory: {is_satisfactory}")
        print(f"Feedback: {feedback}")

        # Store current feedback for next iteration
        previous_feedback = str(
            feedback
        )  # Convert to string to ensure it's serializable

        # Check if we've reached satisfactory quality
        if is_satisfactory or quality_score >= satisfaction_threshold:
            print(f"✅ Reached satisfactory quality in round {iteration + 1}")
            break
        elif iteration < max_iterations - 1:
            print(f"🔄 Quality not satisfactory, continuing to round {iteration + 2}")
            feedback_preview = (
                previous_feedback[:100] + "..."
                if len(previous_feedback) > 100
                else previous_feedback
            )
            print(f"📝 Using feedback for next round: {feedback_preview}")
        else:
            print("⚠️ Reached maximum iterations without achieving satisfactory quality")

    # Use the final optimized configuration
    final_optimized_tool_config = current_tool_config
    final_description = current_tool_config.get("description", "")
    final_parameters = {}
    final_rationale = (
        optimization_history[-1]["description_rationale"]
        if optimization_history
        else "No optimization performed"
    )
    final_argument_rationale = (
        optimization_history[-1]["argument_rationale"] if optimization_history else ""
    )

    # Extract final parameter descriptions
    if (
        "parameter" in final_optimized_tool_config
        and "properties" in final_optimized_tool_config["parameter"]
    ):
        for param_name, param_info in final_optimized_tool_config["parameter"][
            "properties"
        ].items():
            final_parameters[param_name] = param_info.get("description", "")

    # Print final optimization results
    print("\n" + "=" * 80)
    print("🎉 OPTIMIZATION COMPLETED!")
    print("=" * 80)
    print("\n📊 Final Results Summary:")
    print(f"  • Total optimization rounds: {len(optimization_history)}")
    print(
        f"  • Final quality score: {optimization_history[-1]['quality_score'] if optimization_history else 0}/10"
    )
    print(
        f"  • Achieved satisfaction: {optimization_history[-1]['is_satisfactory'] if optimization_history else False}"
    )

    print("\n✨ Final Optimized Tool Configuration:")
    print(json.dumps(final_optimized_tool_config, indent=2, ensure_ascii=False))

    # 4. Save the optimized description to a file, if requested
    file_path = None
    if save_to_file and final_description:
        if not output_file:
            file_path = f"{tool_name}_optimized_description.txt"
        else:
            file_path = output_file

        # Create directory if it doesn't exist (only if there's a directory part)
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        # Do not overwrite if file exists
        if os.path.exists(file_path):
            base, ext = os.path.splitext(file_path)
            file_path = f"{base}_new{ext}"

        print(f"\n💾 Saving optimization report to: {file_path}")

        # Save comprehensive optimization report
        optimization_report = {
            "original_tool_config": tool_config,
            "final_optimized_tool_config": final_optimized_tool_config,
            "optimization_history": optimization_history,
            "optimization_summary": {
                "total_iterations": len(optimization_history),
                "final_description_changed": final_description != original_description,
                "final_parameters_optimized": (
                    list(final_parameters.keys()) if final_parameters else []
                ),
                "final_description_rationale": final_rationale,
                "final_argument_rationale": final_argument_rationale,
                "final_quality_score": (
                    optimization_history[-1]["quality_score"]
                    if optimization_history
                    else 0
                ),
                "achieved_satisfaction": (
                    optimization_history[-1]["is_satisfactory"]
                    if optimization_history
                    else False
                ),
            },
            "test_results": results,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# Multi-Round Tool Description Optimization Report\n\n")
            f.write(f"## Final Optimized Tool Description\n{final_description}\n\n")
            if final_parameters:
                f.write("## Final Optimized Parameter Descriptions\n")
                for param_name, new_desc in final_parameters.items():
                    f.write(f"- **{param_name}**: {new_desc}\n")
                f.write("\n")
            f.write(f"## Final Description Rationale\n{final_rationale}\n\n")
            if final_argument_rationale:
                f.write(
                    f"## Final Argument Optimization Rationale\n{final_argument_rationale}\n\n"
                )

            # Write optimization history
            f.write("## Optimization History\n")
            for _i, record in enumerate(optimization_history):
                f.write(f"### Round {record['iteration']}\n")
                f.write(f"- **Quality Score**: {record['quality_score']}/10\n")
                f.write(f"- **Satisfactory**: {record['is_satisfactory']}\n")
                f.write(f"- **Description**: {record['description']}\n")
                f.write(f"- **Feedback**: {record['feedback']}\n\n")

            f.write("## Complete Optimization Report\n")
            f.write("```json\n")
            f.write(json.dumps(optimization_report, indent=2))
            f.write("\n```\n")

        print(f"✅ Optimization report saved successfully to: {file_path}")
    elif not final_description:
        print("⚠️ No optimized description to save")

    return {
        "optimized_description": final_description,
        "optimized_parameters": final_parameters,
        "optimized_tool_config": final_optimized_tool_config,
        "rationale": final_rationale,
        "argument_rationale": final_argument_rationale,
        "optimization_history": optimization_history,
        "total_iterations": len(optimization_history),
        "final_quality_score": (
            optimization_history[-1]["quality_score"] if optimization_history else 0
        ),
        "achieved_satisfaction": (
            optimization_history[-1]["is_satisfactory"]
            if optimization_history
            else False
        ),
        "test_results": results,
        "saved_to": file_path,
    }
