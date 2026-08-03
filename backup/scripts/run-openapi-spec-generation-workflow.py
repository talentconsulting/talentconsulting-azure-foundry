import argparse
import json
import os
import re
import urllib.parse
from pathlib import Path
from typing import Any

import yaml
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required YAML file not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML object.")
    return payload


def parse_json_response(text: str) -> dict[str, Any]:
    value = text.strip()
    fence = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```", value, re.DOTALL | re.IGNORECASE
    )
    if fence:
        value = fence.group(1).strip()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        start, end = value.find("{"), value.rfind("}")
        if start < 0 or end <= start:
            raise
        payload = json.loads(value[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("Agent response must be a JSON object.")
    return payload


def extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text:
        return output_text
    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if isinstance(text, str) and text:
                parts.append(text)
    if not parts:
        raise ValueError("Agent response did not contain text output.")
    return "\n".join(parts)


def invoke_agent(
    project: AIProjectClient,
    agent_name: str,
    model: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    print(f"Invoking {agent_name}.")
    client = project.get_openai_client(agent_name=agent_name)
    response = client.responses.create(
        model=model,
        input=json.dumps(payload, separators=(",", ":")),
    )
    return parse_json_response(extract_response_text(response))


def load_agent_models(agents_dir: Path) -> dict[str, str]:
    models: dict[str, str] = {}
    for manifest_path in sorted(agents_dir.glob("*/manifest.yaml")):
        manifest = read_yaml(manifest_path)
        name = manifest.get("name")
        model = manifest.get("agent", {}).get("model")
        if isinstance(name, str) and name and isinstance(model, str) and model:
            models[name] = model
    return models


def parse_source_directory_url(value: str) -> tuple[str, str, str, str]:
    parsed = urllib.parse.urlparse(value.strip())
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"github.com", "www.github.com"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("source-directory-url must be a clean HTTPS github.com URL.")
    parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) < 4 or parts[2] != "tree":
        raise ValueError(
            "source-directory-url must match "
            "https://github.com/<owner>/<repo>/tree/<ref>[/<path>]."
        )
    owner, repository, _, ref, *path_parts = parts
    return owner, repository.removesuffix(".git"), ref, "/".join(path_parts)


def validate_relative_path(path: Any, base_path: str, label: str) -> str:
    if not isinstance(path, str) or not path or path.startswith("/"):
        raise ValueError(f"{label} must be a repository-relative path.")
    if any(part in {"", ".", ".."} for part in path.split("/")):
        raise ValueError(f"{label} contains an invalid path segment.")
    if base_path and path != base_path and not path.startswith(f"{base_path}/"):
        raise ValueError(f"{label} is outside the supplied source directory.")
    return path


def validate_file_scan_output(
    payload: dict[str, Any],
    source_directory_url: str,
) -> list[dict[str, Any]]:
    if set(payload) != {"apiFiles"} or not isinstance(payload["apiFiles"], list):
        raise ValueError("File-scan output must contain only an apiFiles array.")
    _, _, _, base_path = parse_source_directory_url(source_directory_url)
    validated: list[dict[str, Any]] = []
    for index, item in enumerate(payload["apiFiles"]):
        if not isinstance(item, dict) or set(item) != {"apiFilePath", "payloadFiles"}:
            raise ValueError(f"apiFiles[{index}] does not match the file-scan contract.")
        api_path = validate_relative_path(
            item["apiFilePath"], base_path, f"apiFiles[{index}].apiFilePath"
        )
        payload_files = item["payloadFiles"]
        if not isinstance(payload_files, dict):
            raise ValueError(f"apiFiles[{index}].payloadFiles must be an object.")
        normalized: dict[str, list[str]] = {}
        for path, type_names in payload_files.items():
            payload_path = validate_relative_path(
                path, "", f"apiFiles[{index}].payloadFiles path"
            )
            if (
                not isinstance(type_names, list)
                or not type_names
                or not all(isinstance(name, str) and name for name in type_names)
                or type_names != sorted(set(type_names))
            ):
                raise ValueError("Payload DTO names must be sorted and unique strings.")
            normalized[payload_path] = type_names
        if list(payload_files) != sorted(payload_files):
            raise ValueError("Payload file paths must be sorted.")
        validated.append({"apiFilePath": api_path, "payloadFiles": normalized})
    paths = [item["apiFilePath"] for item in validated]
    if paths != sorted(set(paths)):
        raise ValueError("API file paths must be sorted and unique.")
    return validated


def source_file_url(source_directory_url: str, path: str) -> str:
    owner, repository, ref, _ = parse_source_directory_url(source_directory_url)
    return (
        f"https://github.com/{urllib.parse.quote(owner, safe='')}/"
        f"{urllib.parse.quote(repository, safe='')}/blob/"
        f"{urllib.parse.quote(ref, safe='')}/"
        f"{urllib.parse.quote(path, safe='/')}"
    )


def validate_generator_output(payload: dict[str, Any], source_url: str) -> None:
    required = {
        "domainApi",
        "openapi",
        "serviceName",
        "sourcePath",
        "fileName",
        "contentType",
    }
    if set(payload) != required:
        raise ValueError(f"Generator output must contain only {sorted(required)}.")
    if payload["contentType"] != "application/json":
        raise ValueError("Generator contentType must be application/json.")
    if not isinstance(payload["openapi"], dict):
        raise ValueError("Generator openapi must be an object.")
    if payload["openapi"].get("openapi") != "3.1.0":
        raise ValueError("Generated document must use OpenAPI 3.1.0.")
    if not isinstance(payload["openapi"].get("paths"), dict):
        raise ValueError("Generated document must contain a paths object.")
    expected_path = urllib.parse.unquote(
        urllib.parse.urlparse(source_url).path.split("/blob/", 1)[1].split("/", 1)[1]
    )
    if payload["sourcePath"] != expected_path:
        raise ValueError("Generator sourcePath does not match its sourceFileUrl.")


def safe_output_name(value: Any, source_url: str, index: int) -> str:
    fallback = Path(urllib.parse.urlparse(source_url).path).stem
    candidate = str(value or fallback)
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip(".-").lower()
    if not candidate:
        candidate = f"openapi-{index}"
    if not candidate.endswith(".json"):
        candidate += ".json"
    return candidate


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run talent-openapi-file-scan, then invoke openapi-spec-generator once "
            "for every returned API file object."
        )
    )
    parser.add_argument("--source-directory-url", required=True)
    parser.add_argument(
        "--project-endpoint",
        default=os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        or os.getenv("PROJECT_ENDPOINT"),
    )
    parser.add_argument(
        "--workflow-dir", default="workflows/openapi-spec-generation"
    )
    parser.add_argument("--agents-dir", default="agents/prompt")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    if not args.project_endpoint:
        raise ValueError("Set AZURE_AI_PROJECT_ENDPOINT or pass --project-endpoint.")
    parse_source_directory_url(args.source_directory_url)

    workflow = read_yaml(Path(args.workflow_dir) / "manifest.yaml")
    models = load_agent_models(Path(args.agents_dir))
    file_scan = workflow["agents"]["openapi_file_scan"]
    file_scan_name = file_scan["name"]
    generator_name = workflow["agents"]["openapi_spec_generator"]["name"]
    file_scan_model = file_scan.get("model", file_scan_name)
    generator_model = models.get(generator_name)
    if not file_scan_model or not generator_model:
        raise ValueError("File-scan and generator model declarations are required.")

    output_dir = Path(
        args.output_dir or workflow["outputs"]["directory"]
    )
    specs_dir = output_dir / next(
        step["output_dir"]
        for step in workflow["steps"]
        if step["id"] == "generate_openapi_specs"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    project = AIProjectClient(
        endpoint=args.project_endpoint,
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )
    file_scan_output = invoke_agent(
        project,
        file_scan_name,
        file_scan_model,
        {"sourceUrl": args.source_directory_url},
    )
    api_files = validate_file_scan_output(
        file_scan_output, args.source_directory_url
    )
    write_json(output_dir / "file-scan-output.json", file_scan_output)

    generated: list[dict[str, str]] = []
    used_names: set[str] = set()
    for index, api_file in enumerate(api_files, start=1):
        source_url = source_file_url(
            args.source_directory_url, api_file["apiFilePath"]
        )
        print(f"Generating specification {index}/{len(api_files)}: {source_url}")
        spec = invoke_agent(
            project,
            generator_name,
            generator_model,
            {
                "sourceFileUrl": source_url,
                "payloadFiles": api_file["payloadFiles"],
            },
        )
        validate_generator_output(spec, source_url)
        file_name = safe_output_name(spec["fileName"], source_url, index)
        if file_name in used_names:
            file_name = f"{index:03d}-{file_name}"
        used_names.add(file_name)
        write_json(specs_dir / file_name, spec)
        generated.append({"sourceFileUrl": source_url, "outputFile": file_name})

    summary = {
        "sourceDirectoryUrl": args.source_directory_url,
        "fileScanAgent": file_scan_name,
        "generatorAgent": generator_name,
        "apiFileCount": len(api_files),
        "generatedSpecCount": len(generated),
        "generated": generated,
    }
    write_json(output_dir / workflow["outputs"]["summary"], summary)
    print(
        f"Generated {len(generated)} specification(s) in {specs_dir}."
    )


if __name__ == "__main__":
    main()
