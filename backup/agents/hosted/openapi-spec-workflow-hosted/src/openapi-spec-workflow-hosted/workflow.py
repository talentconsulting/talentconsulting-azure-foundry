"""File-inventory-to-generator orchestration for the hosted OpenAPI workflow."""

from __future__ import annotations

import concurrent.futures
import json
import re
import urllib.parse
from typing import Any


class WorkflowInputError(ValueError):
    pass


def parse_json_object(text: str) -> dict[str, Any]:
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


def parse_source_directory_url(value: str) -> tuple[str, str, str, str]:
    parsed = urllib.parse.urlparse(value.strip())
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"github.com", "www.github.com"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise WorkflowInputError(
            "sourceDirectoryUrl must be a credential-free HTTPS github.com URL."
        )
    parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) < 4 or parts[2] != "tree":
        raise WorkflowInputError(
            "sourceDirectoryUrl must match "
            "https://github.com/<owner>/<repo>/tree/<ref>[/<path>]."
        )
    owner, repository, _, ref, *path_parts = parts
    if any(part in {".", ".."} for part in path_parts):
        raise WorkflowInputError("sourceDirectoryUrl contains an invalid path.")
    return owner, repository.removesuffix(".git"), ref, "/".join(path_parts)


def _validate_relative_path(path: Any, base_path: str, label: str) -> str:
    if not isinstance(path, str) or not path or path.startswith("/"):
        raise ValueError(f"{label} must be a non-empty repository-relative path.")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{label} contains an invalid path segment.")
    if base_path and path != base_path and not path.startswith(f"{base_path}/"):
        raise ValueError(f"{label} is outside the supplied source directory.")
    return path


def validate_file_scan_output(
    payload: dict[str, Any],
    source_directory_url: str,
    max_files: int,
) -> list[dict[str, Any]]:
    if set(payload) != {"apiFiles"} or not isinstance(payload["apiFiles"], list):
        raise ValueError("File-scan response must contain only apiFiles.")
    _, _, _, base_path = parse_source_directory_url(source_directory_url)
    api_files = payload["apiFiles"]
    if len(api_files) > max_files:
        raise ValueError(f"File scan returned more than the {max_files}-file limit.")

    validated: list[dict[str, Any]] = []
    for index, item in enumerate(api_files):
        if not isinstance(item, dict) or set(item) != {"apiFilePath", "payloadFiles"}:
            raise ValueError(f"apiFiles[{index}] does not match the file-scan contract.")
        api_path = _validate_relative_path(
            item["apiFilePath"], base_path, f"apiFiles[{index}].apiFilePath"
        )
        payload_files = item["payloadFiles"]
        if not isinstance(payload_files, dict):
            raise ValueError(f"apiFiles[{index}].payloadFiles must be an object.")
        normalized_payload_files: dict[str, list[str]] = {}
        for path, type_names in payload_files.items():
            payload_path = _validate_relative_path(
                path, "", f"apiFiles[{index}].payloadFiles path"
            )
            if (
                not isinstance(type_names, list)
                or not type_names
                or not all(isinstance(name, str) and name for name in type_names)
                or type_names != sorted(set(type_names))
            ):
                raise ValueError(
                    f"apiFiles[{index}].payloadFiles type names must be sorted, "
                    "unique, non-empty strings."
                )
            normalized_payload_files[payload_path] = type_names
        if list(payload_files) != sorted(payload_files):
            raise ValueError(f"apiFiles[{index}].payloadFiles paths must be sorted.")
        validated.append(
            {"apiFilePath": api_path, "payloadFiles": normalized_payload_files}
        )

    api_paths = [item["apiFilePath"] for item in validated]
    if api_paths != sorted(set(api_paths)):
        raise ValueError("File-scan API paths must be sorted and unique.")
    return validated


def source_file_url(source_directory_url: str, path: str) -> str:
    owner, repository, ref, _ = parse_source_directory_url(source_directory_url)
    return (
        f"https://github.com/{urllib.parse.quote(owner, safe='')}/"
        f"{urllib.parse.quote(repository, safe='')}/blob/"
        f"{urllib.parse.quote(ref, safe='')}/"
        f"{urllib.parse.quote(path, safe='/')}"
    )


def validate_generator_output(
    payload: dict[str, Any],
    source_file_url: str,
) -> dict[str, Any]:
    required = {
        "domainApi",
        "openapi",
        "serviceName",
        "sourcePath",
        "fileName",
        "contentType",
    }
    if set(payload) != required:
        raise ValueError("Generator response does not match its output contract.")
    document = payload.get("openapi")
    if not isinstance(document, dict) or document.get("openapi") != "3.1.0":
        raise ValueError("Generator response is not an OpenAPI 3.1 document.")
    if not isinstance(document.get("paths"), dict):
        raise ValueError("Generator response does not contain a paths object.")
    if payload.get("contentType") != "application/json":
        raise ValueError("Generator response contentType is invalid.")
    expected_path = urllib.parse.unquote(
        urllib.parse.urlparse(source_file_url).path.split("/blob/", 1)[1].split(
            "/", 1
        )[1]
    )
    if payload.get("sourcePath") != expected_path:
        raise ValueError("Generator sourcePath does not match sourceFileUrl.")
    return payload


def invoke_agent(
    project: Any,
    agent_name: str,
    model: str,
    payload: dict[str, Any],
    max_attempts: int = 2,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for _ in range(max(1, max_attempts)):
        try:
            client = project.get_openai_client(agent_name=agent_name)
            response = client.responses.create(
                model=model,
                input=json.dumps(payload, separators=(",", ":")),
                timeout=180,
            )
            return parse_json_object(response.output_text)
        except Exception as error:
            last_error = error
    assert last_error is not None
    raise last_error


def run_workflow(
    project: Any,
    source_directory_url: str,
    file_scan_name: str,
    file_scan_model: str,
    generator_name: str,
    generator_model: str,
    max_concurrency: int = 4,
    max_files: int = 100,
) -> dict[str, Any]:
    parse_source_directory_url(source_directory_url)
    file_scan_output = invoke_agent(
        project,
        file_scan_name,
        file_scan_model,
        {"sourceUrl": source_directory_url},
    )
    api_files = validate_file_scan_output(
        file_scan_output, source_directory_url, max_files
    )
    ordered_specs: list[dict[str, Any] | None] = [None] * len(api_files)
    errors: list[dict[str, str]] = []

    def generate(index: int, api_file: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        file_url = source_file_url(source_directory_url, api_file["apiFilePath"])
        response = invoke_agent(
            project,
            generator_name,
            generator_model,
            {
                "sourceFileUrl": file_url,
                "payloadFiles": api_file["payloadFiles"],
            },
        )
        return index, validate_generator_output(response, file_url)

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, min(max_concurrency, 8))
    ) as executor:
        futures = {
            executor.submit(generate, index, api_file): (index, api_file)
            for index, api_file in enumerate(api_files)
        }
        for future in concurrent.futures.as_completed(futures):
            index, api_file = futures[future]
            file_url = source_file_url(
                source_directory_url, api_file["apiFilePath"]
            )
            try:
                result_index, spec = future.result()
                ordered_specs[result_index] = spec
            except Exception as error:
                errors.append(
                    {
                        "sourceFileUrl": file_url,
                        "errorType": type(error).__name__,
                    }
                )

    specs = [spec for spec in ordered_specs if spec is not None]
    errors.sort(key=lambda item: item["sourceFileUrl"])
    return {
        "success": not errors and len(specs) == len(api_files),
        "sourceDirectoryUrl": source_directory_url,
        "apiFiles": api_files,
        "specs": specs,
        "errors": errors,
    }
