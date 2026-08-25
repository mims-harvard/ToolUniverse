import ast
import collections
import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTE_SOURCE_ROOT = REPO_ROOT / "src" / "tooluniverse" / "remote"
REMOTE_CONFIG_ROOT = REPO_ROOT / "src" / "tooluniverse" / "data" / "remote_tools"
SETUP_SKILLS_ROOT = REPO_ROOT / "skills"


def _without_descriptions(value):
    """Return schema structure while ignoring documentation-only wording."""
    if isinstance(value, dict):
        return {
            key: _without_descriptions(item)
            for key, item in value.items()
            if key != "description"
        }
    if isinstance(value, list):
        return [_without_descriptions(item) for item in value]
    return value


def _decorated_parameter_schemas():
    schemas = {}
    for source_path in REMOTE_SOURCE_ROOT.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path)
        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                name = decorator.func
                if not isinstance(name, ast.Name) or name.id != "register_mcp_tool":
                    continue
                arguments = {kw.arg: kw.value for kw in decorator.keywords if kw.arg}
                try:
                    tool_name = ast.literal_eval(arguments["tool_type_name"])
                    config = ast.literal_eval(arguments["config"])
                except (KeyError, ValueError, TypeError):
                    continue
                parameter_schema = config.get("parameter_schema")
                if parameter_schema is not None:
                    parameter_schema = dict(parameter_schema)
                    if parameter_schema.get("type") == "object":
                        parameter_schema.setdefault("additionalProperties", False)
                    schemas[tool_name] = parameter_schema
    return schemas


def _decorated_tool_sources():
    sources = {}
    for source_path in REMOTE_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source, source_path)
        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                name = decorator.func
                if not isinstance(name, ast.Name) or name.id != "register_mcp_tool":
                    continue
                arguments = {kw.arg: kw.value for kw in decorator.keywords if kw.arg}
                try:
                    tool_name = ast.literal_eval(arguments["tool_type_name"])
                except (KeyError, ValueError, TypeError):
                    continue
                sources[tool_name] = source
    return sources


def _published_parameter_schemas():
    schemas = {}
    for config_path in REMOTE_CONFIG_ROOT.glob("*.json"):
        for tool in json.loads(config_path.read_text(encoding="utf-8")):
            if "name" in tool and "parameter" in tool:
                schemas[tool["name"]] = tool["parameter"]
    return schemas


class RemoteSchemaParityTests(unittest.TestCase):
    def test_remote_manifests_have_unique_keys_and_valid_return_schemas(self):
        from jsonschema import Draft202012Validator

        manifest_paths = list(REMOTE_CONFIG_ROOT.glob("*.json"))
        manifest_paths.extend(REMOTE_SOURCE_ROOT.rglob("*_tools.json"))
        problems = []
        for config_path in sorted(set(manifest_paths)):
            duplicate_keys = []

            def reject_duplicates(pairs):
                counts = collections.Counter(key for key, _value in pairs)
                duplicate_keys.extend(key for key, count in counts.items() if count > 1)
                return dict(pairs)

            tools = json.loads(
                config_path.read_text(encoding="utf-8"),
                object_pairs_hook=reject_duplicates,
            )
            if duplicate_keys:
                problems.append(
                    f"{config_path}: duplicate keys {sorted(duplicate_keys)}"
                )
            for tool in tools:
                schema = tool.get("return_schema")
                if schema is None:
                    continue
                try:
                    Draft202012Validator.check_schema(schema)
                except Exception as exc:
                    problems.append(f"{tool.get('name')}: invalid return schema: {exc}")

        self.assertEqual(problems, [])

    def test_all_published_remote_inputs_are_closed_and_examples_validate(self):
        from jsonschema import Draft202012Validator

        problems = []
        for config_path in sorted(REMOTE_CONFIG_ROOT.glob("*.json")):
            for tool in json.loads(config_path.read_text(encoding="utf-8")):
                schema = tool.get("parameter")
                if schema is None:
                    continue
                if schema.get("type") != "object":
                    problems.append(f"{tool['name']}: input schema is not an object")
                    continue
                if schema.get("additionalProperties") is not False:
                    problems.append(
                        f"{tool['name']}: unknown input fields are not rejected"
                    )
                try:
                    Draft202012Validator.check_schema(schema)
                except Exception as exc:
                    problems.append(f"{tool['name']}: invalid input schema: {exc}")
                    continue
                validator = Draft202012Validator(schema)
                for index, example in enumerate(tool.get("test_examples", [])):
                    errors = sorted(
                        validator.iter_errors(example), key=lambda item: list(item.path)
                    )
                    problems.extend(
                        f"{tool['name']}: example {index}: {error.message}"
                        for error in errors
                    )

        self.assertEqual(problems, [])

    def test_standalone_retrieval_endpoints_offload_and_serialize_shared_state(self):
        cases = {
            "depmap_24q2/depmap_24q2_mcp_tool.py": "_DEPMAP_REQUEST_LOCK",
            "pinnacle/pinnacle_tool.py": "_PINNACLE_REQUEST_LOCK",
            "transcriptformer/transcriptformer_tool.py": (
                "_TRANSCRIPTFORMER_REQUEST_LOCK"
            ),
        }
        problems = []
        for relative, lock_name in cases.items():
            source = (REMOTE_SOURCE_ROOT / relative).read_text(encoding="utf-8")
            if "return await asyncio.to_thread(execute)" not in source:
                problems.append(f"{relative}: blocks the MCP event loop")
            if f"with {lock_name}:" not in source:
                problems.append(f"{relative}: shared provider state is not serialized")
        self.assertEqual(problems, [])

    def test_artifact_retrieval_requirements_are_service_scoped(self):
        expected = {
            "depmap_24q2": {"fastmcp>=3.4.5,<4", "numpy>=2.0,<3", "h5py>=3.11,<4"},
            "pinnacle": {"fastmcp>=3.4.5,<4", "torch>=2.6,<3"},
            "transcriptformer": {"fastmcp>=3.4.5,<4", "numpy>=2.0,<3"},
        }
        problems = []
        for implementation, wanted in expected.items():
            lines = {
                line.strip()
                for line in (REMOTE_SOURCE_ROOT / implementation / "requirements.txt")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            }
            if lines != wanted:
                problems.append(
                    f"{implementation}: unexpected dependency surface {lines}"
                )
        self.assertEqual(problems, [])

    def test_standalone_internal_and_published_input_contracts_match(self):
        pairs = {
            "boltz/boltz_client_tools.json": "boltz_tools.json",
            "uspto_downloader/uspto_downloader_client_tools.json": (
                "uspto_downloader_tools.json"
            ),
            "expert_feedback/human_expert_client_tools.json": (
                "expert_feedback_tools.json"
            ),
        }
        problems = []
        for internal_relative, published_name in pairs.items():
            internal = {
                item["name"]: item
                for item in json.loads(
                    (REMOTE_SOURCE_ROOT / internal_relative).read_text(encoding="utf-8")
                )
            }
            published = {
                item["name"]: item
                for item in json.loads(
                    (REMOTE_CONFIG_ROOT / published_name).read_text(encoding="utf-8")
                )
            }
            if set(internal) != set(published):
                problems.append(f"{internal_relative}: operation names differ")
                continue
            for name in internal:
                if internal[name].get("parameter") != published[name].get("parameter"):
                    problems.append(
                        f"{name}: internal and published input schemas differ"
                    )
        self.assertEqual(problems, [])

    def test_setup_skill_entrypoints_and_ports_match_sources(self):
        skill_paths = sorted(SETUP_SKILLS_ROOT.glob("setup-*-remote-tool/SKILL.md"))
        self.assertEqual(len(skill_paths), 30)
        problems = []
        for skill_path in skill_paths:
            text = skill_path.read_text(encoding="utf-8")
            module_match = re.search(
                r"^python -m (tooluniverse\.remote\.\S+)", text, re.MULTILINE
            )
            port_match = re.search(r"endpoint is http://127\.0\.0\.1:(\d+)/mcp", text)
            if module_match is None or port_match is None:
                problems.append(f"{skill_path.parent.name}: entrypoint/port absent")
                continue
            module = module_match.group(1)
            source_path = (
                REPO_ROOT / "src" / Path(*module.split(".")).with_suffix(".py")
            )
            if not source_path.is_file():
                problems.append(
                    f"{skill_path.parent.name}: source module {module} is absent"
                )
                continue
            port = port_match.group(1)
            source = source_path.read_text(encoding="utf-8")
            literal_port = re.search(rf"port[\"']?\s*[:=]\s*{port}\b", source)
            environment_default = re.search(
                rf"TOOLUNIVERSE_MCP_PORT[\"'],\s*[\"']{port}[\"']", source
            )
            if literal_port is None and environment_default is None:
                problems.append(
                    f"{skill_path.parent.name}: port {port} differs from source"
                )

        self.assertEqual(problems, [])

    def test_setup_skill_examples_match_selected_operation_schemas(self):
        schemas = _published_parameter_schemas()
        schemas.update(_decorated_parameter_schemas())
        skill_paths = sorted(SETUP_SKILLS_ROOT.glob("setup-*-remote-tool/SKILL.md"))
        self.assertEqual(len(skill_paths), 30)

        problems = []
        for skill_path in skill_paths:
            text = skill_path.read_text(encoding="utf-8")
            operation_match = re.search(r"^Operation: (\S+)", text, re.MULTILINE)
            example_match = re.search(r"~~~json\n(.*?)\n~~~", text, re.DOTALL)
            if operation_match is None or example_match is None:
                problems.append(f"{skill_path.parent.name}: operation/example absent")
                continue
            operation = operation_match.group(1)
            schema = schemas.get(operation)
            if schema is None:
                problems.append(
                    f"{skill_path.parent.name}: unknown operation {operation}"
                )
                continue
            try:
                example = json.loads(example_match.group(1))
            except json.JSONDecodeError:
                problems.append(f"{skill_path.parent.name}: invalid example JSON")
                continue
            properties = set(schema.get("properties", {}))
            required = set(schema.get("required", []))
            unknown = set(example) - properties
            missing = required - set(example)
            if unknown:
                problems.append(
                    f"{skill_path.parent.name}: unknown fields {sorted(unknown)}"
                )
            if missing:
                problems.append(
                    f"{skill_path.parent.name}: missing fields {sorted(missing)}"
                )

        self.assertEqual(problems, [])

    def test_readmes_match_setup_skill_tou_contract(self):
        skill_paths = sorted(SETUP_SKILLS_ROOT.glob("setup-*-remote-tool/SKILL.md"))
        self.assertEqual(len(skill_paths), 30)

        problems = []
        readme_paths = set()
        for skill_path in skill_paths:
            skill_text = skill_path.read_text(encoding="utf-8")
            module_match = re.search(
                r"^python -m (tooluniverse\.remote\.\S+)",
                skill_text,
                re.MULTILINE,
            )
            port_match = re.search(
                r"endpoint is http://127\.0\.0\.1:(\d+)/mcp", skill_text
            )
            operation_match = re.search(r"^Operation: (\S+)", skill_text, re.MULTILINE)
            status_match = re.search(
                r"^> Validation status(?: \(\d{4}-\d{2}-\d{2}\))?: (.+)$",
                skill_text,
                re.MULTILINE,
            )
            doctor_match = re.search(
                r"^(tu doctor --forward \S+ --json)$", skill_text, re.MULTILINE
            )
            relay_match = re.search(
                r"^(tu serve --share --forward \S+ --name \S+ --workers ([12]))$",
                skill_text,
                re.MULTILINE,
            )
            share_match = re.search(
                r"^(tu remote share (\S+))$",
                skill_text,
                re.MULTILINE,
            )
            share_options_match = re.search(
                r"^(tu remote share (\S+) --name \S+ --workers ([12]))$",
                skill_text,
                re.MULTILINE,
            )
            if any(
                match is None
                for match in (
                    module_match,
                    port_match,
                    operation_match,
                    status_match,
                    doctor_match,
                    relay_match,
                    share_match,
                    share_options_match,
                )
            ):
                problems.append(
                    f"{skill_path.parent.name}: incomplete documented contract"
                )
                continue
            if "authenticated 2026-08-16 Platform matrix" not in skill_text:
                problems.append(
                    f"{skill_path.parent.name}: authenticated Platform evidence is absent"
                )
            if "unpublished owner drafts" not in skill_text:
                problems.append(
                    f"{skill_path.parent.name}: private-draft boundary is absent"
                )
            if "tu remote login" not in skill_text:
                problems.append(
                    f"{skill_path.parent.name}: one-time remote login is absent"
                )
            if "tu remote logout" not in skill_text:
                problems.append(
                    f"{skill_path.parent.name}: remote logout recovery is absent"
                )
            if "expired, or revoked" not in skill_text:
                problems.append(
                    f"{skill_path.parent.name}: invalid-key recovery is absent"
                )
            expected_workers = (
                "2"
                if skill_path.parent.name == "setup-expert-feedback-remote-tool"
                else "1"
            )
            if relay_match.group(2) != expected_workers:
                problems.append(
                    f"{skill_path.parent.name}: relay worker count is unsafe"
                )
            expected_slug = skill_path.parent.name.removeprefix("setup-").removesuffix(
                "-remote-tool"
            )
            if share_match.group(2) != expected_slug:
                problems.append(
                    f"{skill_path.parent.name}: short-share implementation differs"
                )
            if share_options_match.group(2) != expected_slug:
                problems.append(
                    f"{skill_path.parent.name}: configured-share implementation differs"
                )
            if share_options_match.group(3) != expected_workers:
                problems.append(
                    f"{skill_path.parent.name}: configured-share worker count is unsafe"
                )

            module = module_match.group(1)
            port = port_match.group(1)
            operation = operation_match.group(1)
            endpoint = f"http://127.0.0.1:{port}/mcp"
            source_path = (
                REPO_ROOT / "src" / Path(*module.split(".")).with_suffix(".py")
            )
            readme_path = source_path.parent / "README.md"
            readme_paths.add(readme_path)
            if not readme_path.is_file():
                problems.append(f"{skill_path.parent.name}: README is absent")
                continue

            readme_text = readme_path.read_text(encoding="utf-8")
            guide_link = f"../../../../skills/{skill_path.parent.name}/SKILL.md"
            readme_status_match = re.search(
                r"^## TOU validation and deployment status \(2026-08-16\)"
                r"\n\n> (.+?)(?:\n\n)",
                readme_text,
                re.MULTILINE | re.DOTALL,
            )
            if readme_status_match is None:
                problems.append(
                    f"{readme_path.relative_to(REPO_ROOT)}: missing status paragraph"
                )
            else:
                normalized_status = " ".join(
                    line.removeprefix("> ").strip()
                    for line in readme_status_match.group(1).splitlines()
                ).lower()
                limitation_terms = (
                    "incomplete",
                    "blocked",
                    "unmeasured",
                    "unvalidated",
                    "not a ",
                    "not an ",
                )
                if not any(term in normalized_status for term in limitation_terms):
                    problems.append(
                        f"{readme_path.relative_to(REPO_ROOT)}: "
                        "status lacks an explicit evidence limitation"
                    )
                forbidden_claims = (
                    "all working",
                    "fully validated",
                    "fully production-ready",
                )
                if any(term in normalized_status for term in forbidden_claims):
                    problems.append(
                        f"{readme_path.relative_to(REPO_ROOT)}: "
                        "status contains an unsupported blanket claim"
                    )
            required_fragments = {
                "dated validation status": (
                    "## TOU validation and deployment status (2026-08-16)"
                ),
                "primary operation": f"`{operation}`",
                "start module": f"`python -m {module}",
                "loopback endpoint": f"`{endpoint}`",
                "TOU discovery check": f"`{doctor_match.group(1)}`",
                "private relay command": f"`{relay_match.group(1)}`",
                "one-time remote login": "tu remote login",
                "remote logout recovery": "tu remote logout",
                "invalid-key recovery": "expired, or revoked",
                "short share command": share_match.group(1),
                "configured share command": share_options_match.group(1),
                "non-loopback bearer requirement": "`TOOLUNIVERSE_API_TOKEN`",
                "Connect relay credential": "`TOOLUNIVERSE_SERVICE_KEY`",
                "authenticated Platform evidence": (
                    "authenticated 2026-08-16 Platform matrix"
                ),
                "private-draft boundary": "unpublished owner draft",
                "owner test route": "`/expert-sessions/{id}/test`",
                "independent-caller limitation": "independent-caller",
                "setup skill link": guide_link,
            }
            for label, fragment in required_fragments.items():
                if fragment not in readme_text:
                    problems.append(
                        f"{readme_path.relative_to(REPO_ROOT)}: missing {label}"
                    )

        self.assertFalse(problems, "\n".join(problems))
        self.assertEqual(len(readme_paths), 30)

    def test_decorator_and_published_schemas_have_identical_structure(self):
        decorated = _decorated_parameter_schemas()
        published = _published_parameter_schemas()
        shared = sorted(decorated.keys() & published.keys())
        self.assertGreater(len(shared), 0)
        self.assertIn("consult_human_expert", shared)
        self.assertIn("run_macs3_callpeak", shared)

        mismatches = []
        for tool_name in shared:
            if _without_descriptions(decorated[tool_name]) != _without_descriptions(
                published[tool_name]
            ):
                mismatches.append(tool_name)

        self.assertEqual(
            mismatches,
            [],
            "Live @register_mcp_tool schemas differ from published JSON schemas",
        )

    def test_published_h5ad_operations_use_the_provider_root_resolver(self):
        decorated_sources = _decorated_tool_sources()
        published = _published_parameter_schemas()
        h5ad_tools = []
        for tool_name, schema in published.items():
            properties = schema.get("properties", {})
            if (
                any(
                    ".h5ad" in str(prop.get("description", "")).lower()
                    for prop in properties.values()
                    if isinstance(prop, dict)
                )
                and tool_name in decorated_sources
            ):
                h5ad_tools.append(tool_name)

        self.assertGreater(len(h5ad_tools), 0)
        missing = []
        for tool_name in h5ad_tools:
            source = decorated_sources[tool_name]
            for property_name, prop in (
                published[tool_name].get("properties", {}).items()
            ):
                if ".h5ad" not in str(prop.get("description", "")).lower():
                    continue
                resolution_call = rf"(?:load_remote_h5ad|resolve_remote_data_path)\(\s*{re.escape(property_name)}\b"
                if not re.search(resolution_call, source):
                    missing.append(f"{tool_name}.{property_name}")
        self.assertEqual(
            missing,
            [],
            "Published .h5ad operations must reject URLs and paths outside the provider root",
        )
        unsafe_descriptions = []
        for tool_name in h5ad_tools:
            for property_name, prop in (
                published[tool_name].get("properties", {}).items()
            ):
                description = str(prop.get("description", "")).lower()
                if ".h5ad" in description and (
                    "url" in description or "server-accessible path" in description
                ):
                    unsafe_descriptions.append(f"{tool_name}.{property_name}")
        self.assertEqual(
            unsafe_descriptions,
            [],
            "Published .h5ad descriptions must state the provider-root boundary",
        )

    def test_compass_uses_provider_safe_artifact_without_public_model_selection(self):
        source_path = REMOTE_SOURCE_ROOT / "immune_compass" / "compass_tool.py"
        source = source_path.read_text(encoding="utf-8")
        published = _published_parameter_schemas()["run_compass_prediction"]
        properties = published.get("properties", {})

        problems = []
        if "read_pickle" in source:
            problems.append("runtime loads caller-selected pickle data")
        if "torch.load" in source or "loadcompass(" in source:
            problems.append("COMPASS live runtime permits pickle checkpoint loading")
        if "root_path" in properties:
            problems.append("published operation exposes the model checkpoint root")
        if "resolve_remote_data_path" not in source:
            problems.append("expression input does not use the provider-root resolver")
        if set(published.get("required", [])) != {"gene_expression_data_path"}:
            problems.append("defaulted parameters are incorrectly required")
        if "COMPASS_SAFE_MODEL_DIR" not in source:
            problems.append("COMPASS lacks a provider-controlled safe artifact setting")
        if "load_file(weights_path" not in source or "allow_pickle=False" not in source:
            problems.append("COMPASS does not use data-only weights and preprocessing")
        if "model.load_state_dict(state, strict=True)" not in source:
            problems.append(
                "COMPASS does not strictly reconstruct the reviewed factory"
            )

        self.assertEqual(problems, [])

    def test_large_provider_artifacts_are_single_flight_cached(self):
        cases = {
            "pinnacle/pinnacle_tool.py": (
                "_PINNACLE_TOOL_LOCK",
                "pinnacle_tool = _get_pinnacle_tool()",
            ),
            "transcriptformer/transcriptformer_tool.py": (
                "_TRANSCRIPTFORMER_TOOL_LOCK",
                "transcriptformer_tool = _get_transcriptformer_tool()",
            ),
            "depmap_24q2/depmap_24q2_mcp_tool.py": (
                "_DEPMAP_TOOL_LOCK",
                "depmap_tool = _get_depmap_tool()",
            ),
        }
        problems = []
        for relative, required_fragments in cases.items():
            source = (REMOTE_SOURCE_ROOT / relative).read_text(encoding="utf-8")
            for fragment in required_fragments:
                if fragment not in source:
                    problems.append(f"{relative}: missing {fragment}")
        self.assertEqual(problems, [])

    def test_shared_gpu_models_serialize_initialization_and_inference(self):
        cases = {
            "borzoi/borzoi_tool.py": ("_MODEL_INIT_LOCK", "_INFERENCE_LOCK"),
            "enformer/enformer_tool.py": ("_MODEL_INIT_LOCK", "_INFERENCE_LOCK"),
            "esm/esm_tool.py": ("_ESM_INIT_LOCK", "_ESM_INFERENCE_LOCK"),
            "chrombpnet/chrombpnet_tool.py": (
                "_MODEL_INIT_LOCK",
                "_INFERENCE_LOCK",
            ),
            "boltz/boltz_mcp_server.py": ("_BOLTZ_REQUEST_LOCK",),
        }
        problems = []
        for relative, lock_names in cases.items():
            source = (REMOTE_SOURCE_ROOT / relative).read_text(encoding="utf-8")
            for lock_name in lock_names:
                if f"with {lock_name}:" not in source:
                    problems.append(f"{relative}: {lock_name} is not applied")
        self.assertEqual(problems, [])

    def test_pinnacle_and_depmap_artifacts_are_provider_owned_and_safe_loaded(self):
        published = _published_parameter_schemas()
        pinnacle_source = (
            REMOTE_SOURCE_ROOT / "pinnacle" / "pinnacle_tool.py"
        ).read_text(encoding="utf-8")
        depmap_source = (
            REMOTE_SOURCE_ROOT / "depmap_24q2" / "depmap_24q2_mcp_tool.py"
        ).read_text(encoding="utf-8")
        problems = []
        if "embed_path" in published["run_pinnacle_ppi_retrieval"].get(
            "properties", {}
        ):
            problems.append("PINNACLE exposes its embedding checkpoint path")
        if "weights_only=False" in pinnacle_source:
            problems.append("PINNACLE permits arbitrary pickle objects")
        if "data_dir" in published["compute_depmap24q2_gene_correlations"].get(
            "properties", {}
        ):
            problems.append("DepMap exposes its provider dataset directory")
        if "allow_pickle=True" in depmap_source:
            problems.append("DepMap permits pickle-backed numpy arrays")

        transcriptformer_path = (
            REMOTE_SOURCE_ROOT / "transcriptformer" / "transcriptformer_tool.py"
        )
        transcriptformer_tree = ast.parse(
            transcriptformer_path.read_text(encoding="utf-8"), transcriptformer_path
        )
        transcriptformer_fn = next(
            node
            for node in ast.walk(transcriptformer_tree)
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "run_transcriptformer_embedding_retrieval"
        )
        transcriptformer_args = {arg.arg for arg in transcriptformer_fn.args.args}
        if "data_dir" in transcriptformer_args:
            problems.append("Transcriptformer exposes its provider dataset directory")
        genes_schema = published["run_transcriptformer_embedding_retrieval"][
            "properties"
        ]["gene_names"]
        if genes_schema.get("minItems") != 1 or genes_schema.get("maxItems") != 250:
            problems.append("Transcriptformer embedding output is not input-bounded")
        transcriptformer_source = transcriptformer_path.read_text(encoding="utf-8")
        if 'allow_pickle=False, mmap_mode="r"' not in transcriptformer_source:
            problems.append(
                "Transcriptformer matrix loading is not safely memory mapped"
            )

        compass_path = REMOTE_SOURCE_ROOT / "immune_compass" / "compass_tool.py"
        compass_tree = ast.parse(compass_path.read_text(encoding="utf-8"), compass_path)
        torch_load_calls = [
            node
            for node in ast.walk(compass_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "load"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "torch"
        ]
        if torch_load_calls:
            problems.append("COMPASS live runtime still calls torch.load")
        if "from safetensors.torch import load_file" not in compass_path.read_text(
            encoding="utf-8"
        ):
            problems.append("COMPASS live runtime does not use safetensors")

        self.assertEqual(problems, [])

    def test_r_backed_remote_tools_do_not_return_raw_process_output(self):
        unsafe = []
        for implementation, filename in (
            ("singler", "singler_tool.py"),
            ("slingshot", "slingshot_tool.py"),
            ("monocle3", "monocle3_tool.py"),
        ):
            source = (REMOTE_SOURCE_ROOT / implementation / filename).read_text(
                encoding="utf-8"
            )
            if "proc.stderr" in source or "proc.stdout" in source:
                unsafe.append(implementation)
        self.assertEqual(unsafe, [])

    def test_standalone_fastmcp_servers_use_fail_closed_shared_security(self):
        fastmcp_sources = []
        for source_path in REMOTE_SOURCE_ROOT.rglob("*.py"):
            source = source_path.read_text(encoding="utf-8")
            if "from fastmcp import FastMCP" in source:
                fastmcp_sources.append((source_path, source))

        self.assertEqual(len(fastmcp_sources), 6)
        problems = []
        for source_path, source in fastmcp_sources:
            relative = source_path.relative_to(REMOTE_SOURCE_ROOT)
            if "auth=get_fastmcp_token_auth()" not in source:
                problems.append(f"{relative}: missing shared bearer authentication")
            if "run_fastmcp_server(" not in source:
                problems.append(f"{relative}: missing shared bind guard")
            if 'host="0.0.0.0"' in source:
                problems.append(f"{relative}: unsafe default network bind")
            if "_optional_token_auth" in source:
                problems.append(f"{relative}: legacy fail-open authentication helper")
        self.assertEqual(problems, [])

    def test_fastmcp_manifest_names_and_provider_owned_uspto_key(self):
        published = {}
        for config_path in REMOTE_CONFIG_ROOT.glob("*.json"):
            for tool in json.loads(config_path.read_text(encoding="utf-8")):
                published[tool["name"]] = tool

        cases = {
            "boltz2_docking": REMOTE_SOURCE_ROOT / "boltz" / "boltz_mcp_server.py",
            "get_abstract_from_patent_app_number": REMOTE_SOURCE_ROOT
            / "uspto_downloader"
            / "uspto_downloader_mcp_server.py",
            "get_claims_from_patent_app_number": REMOTE_SOURCE_ROOT
            / "uspto_downloader"
            / "uspto_downloader_mcp_server.py",
            "get_full_text_from_patent_app_number": REMOTE_SOURCE_ROOT
            / "uspto_downloader"
            / "uspto_downloader_mcp_server.py",
        }
        problems = []
        for operation, source_path in cases.items():
            source = source_path.read_text(encoding="utf-8")
            tree = ast.parse(source, source_path)
            fastmcp_functions = {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and any(
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "tool"
                    for decorator in node.decorator_list
                )
            }
            configured = (
                published[operation].get("remote_info", {}).get("mcp_tool_name")
            )
            if configured != operation:
                problems.append(f"{operation}: published MCP name is {configured!r}")
            if operation not in fastmcp_functions:
                problems.append(f"{operation}: FastMCP function name is absent")

        for operation in (
            "get_abstract_from_patent_app_number",
            "get_claims_from_patent_app_number",
            "get_full_text_from_patent_app_number",
        ):
            if "USPTO_API_KEY" in published[operation].get("required_api_keys", []):
                problems.append(f"{operation}: provider API key required from caller")
            schema = published[operation]["parameter"]["properties"][
                "applicationNumberText"
            ]
            if schema.get("pattern") != "^[0-9]{8,16}$":
                problems.append(f"{operation}: application number is not bounded")

        self.assertEqual(problems, [])

    def test_sequence_models_have_reproducible_installs_and_bounded_inputs(self):
        published = _published_parameter_schemas()
        problems = []
        for implementation, operations in {
            "borzoi": ("run_borzoi_predict", "run_borzoi_variant_effect"),
            "enformer": ("run_enformer_predict", "run_enformer_variant_effect"),
        }.items():
            source = (
                REMOTE_SOURCE_ROOT / implementation / f"{implementation}_tool.py"
            ).read_text(encoding="utf-8")
            if (
                "validate_sequence" not in source
                or "validate_track_selection" not in source
            ):
                problems.append(f"{implementation}: shared input bounds are absent")
            for operation in operations:
                schema = published[operation]
                sequence_fields = [
                    prop
                    for name, prop in schema["properties"].items()
                    if "sequence" in name
                ]
                if not sequence_fields or any(
                    not prop.get("maxLength") or not prop.get("pattern")
                    for prop in sequence_fields
                ):
                    problems.append(f"{operation}: sequence payload is unbounded")
                tracks = schema["properties"].get("track_indices", {})
                if tracks.get("maxItems") != 1000 or not tracks.get("uniqueItems"):
                    problems.append(f"{operation}: explicit track output is unbounded")
                top_n = schema["properties"].get("top_n", {})
                if top_n.get("minimum") != 1 or top_n.get("maximum") != 1000:
                    problems.append(f"{operation}: top-N output is unbounded")

        esm_source = (REMOTE_SOURCE_ROOT / "esm" / "esm_tool.py").read_text(
            encoding="utf-8"
        )
        if (
            "validate_sequence" not in esm_source
            or "embedding_tensor[1:-1]" not in esm_source
        ):
            problems.append("ESM-C input bounds or residue-only pooling are absent")

        borzoi_requirements = (
            REMOTE_SOURCE_ROOT / "borzoi" / "requirements.txt"
        ).read_text(encoding="utf-8")
        if "borzoi-pytorch>=0.4.4,<0.5" not in borzoi_requirements:
            problems.append("Borzoi requirement does not select a released version")
        if "transformers>=4.46,<4.51" not in borzoi_requirements:
            problems.append(
                "Borzoi requirement violates borzoi-pytorch's Transformers bound"
            )
        esm_requirements = (REMOTE_SOURCE_ROOT / "esm" / "requirements.txt").read_text(
            encoding="utf-8"
        )
        if "Biohub/esm.git@c94ed8d" not in esm_requirements:
            problems.append(
                "ESM dependency is not pinned to the reviewed official source"
            )

        self.assertEqual(problems, [])

    def test_chrombpnet_and_celltypist_use_safe_model_boundaries(self):
        published = _published_parameter_schemas()
        chrom_source = (
            REMOTE_SOURCE_ROOT / "chrombpnet" / "chrombpnet_tool.py"
        ).read_text(encoding="utf-8")
        celltypist_source = (
            REMOTE_SOURCE_ROOT / "celltypist" / "celltypist_tool.py"
        ).read_text(encoding="utf-8")
        problems = []

        for operation in ("run_chrombpnet_predict", "run_chrombpnet_variant_effect"):
            properties = published[operation].get("properties", {})
            if "model_path" in properties:
                problems.append(f"{operation}: caller can select a model artifact")
            for name, prop in properties.items():
                if "sequence" in name and (
                    prop.get("maxLength") != 10_000 or not prop.get("pattern")
                ):
                    problems.append(f"{operation}.{name}: sequence is not bounded")
        if "CHROMBPNET_MODEL_PATH" not in chrom_source:
            problems.append("ChromBPNet lacks an administrator model setting")
        if (
            "safe_mode=True" not in chrom_source
            or 'suffix.lower() != ".keras"' not in chrom_source
        ):
            problems.append("ChromBPNet does not require safe Keras v3 loading")
        if (
            "validate_sequence" not in chrom_source
            or "validate_variant_sequences" not in chrom_source
        ):
            problems.append("ChromBPNet does not use shared sequence validation")

        if (
            "models.download_models(" in celltypist_source
            or "Model.load(" in celltypist_source
        ):
            problems.append("CellTypist live runtime loads or downloads pickle models")
        if "CELLTYPIST_SAFE_MODEL_DIR" not in celltypist_source:
            problems.append(
                "CellTypist lacks a provider-controlled safe artifact setting"
            )
        if "np.load(path, allow_pickle=False)" not in celltypist_source:
            problems.append(
                "CellTypist safe artifact is not loaded with pickle disabled"
            )
        if (
            "LogisticRegression()" not in celltypist_source
            or "StandardScaler(" not in celltypist_source
        ):
            problems.append(
                "CellTypist does not reconstruct its reviewed model factory"
            )

        self.assertEqual(problems, [])

    def test_expert_companion_http_surfaces_install_shared_auth(self):
        source = (
            REMOTE_SOURCE_ROOT / "expert_feedback" / "human_expert_mcp_tools.py"
        ).read_text(encoding="utf-8")
        problems = []
        if (
            "def _install_flask_token_auth" not in source
            or "@app.before_request" not in source
        ):
            problems.append("shared Flask bearer middleware is absent")
        if source.count("_install_flask_token_auth(") < 3:
            problems.append("API and web companion surfaces are not both protected")
        if 'headers["Authorization"] = f"Bearer {token}"' not in source:
            problems.append(
                "internal web-to-API requests do not forward authentication"
            )
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
