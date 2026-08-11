"""Database-schema generation and publication orchestration."""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Callable


class WorkflowError(ValueError):
    """A stable workflow validation or execution error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def parse_json_value(text: str) -> Any:
    value = text.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", value, re.DOTALL | re.IGNORECASE)
    if fence:
        value = fence.group(1).strip()
    try:
        return json.loads(value)
    except json.JSONDecodeError as original_error:
        starts = [position for position in (value.find("["), value.find("{")) if position >= 0]
        if not starts:
            raise WorkflowError("invalid_agent_response", "Agent response was not JSON.") from original_error
        try:
            result, _ = json.JSONDecoder().raw_decode(value[min(starts) :])
            return result
        except json.JSONDecodeError as error:
            raise WorkflowError("invalid_agent_response", "Agent response was not JSON.") from error


def parse_source_url(value: object) -> tuple[str, str, str]:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowError("invalid_source_url", "sourceUrl must be a GitHub tree URL.")
    parsed = urllib.parse.urlparse(value.strip())
    parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"github.com", "www.github.com"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or len(parts) < 4
        or parts[2] != "tree"
        or any(part in {".", ".."} or "/" in part or "\\" in part for part in parts)
    ):
        raise WorkflowError(
            "invalid_source_url",
            "sourceUrl must match https://github.com/owner/repository/tree/ref[/path].",
        )
    return parts[0], parts[1].removesuffix(".git"), parts[3]


def parse_workflow_request(input_text: str) -> dict[str, Any]:
    try:
        payload = json.loads(input_text)
    except json.JSONDecodeError as error:
        raise WorkflowError("invalid_json", "Input must be one JSON object.") from error
    if not isinstance(payload, dict):
        raise WorkflowError("invalid_input", "Input must be one JSON object.")
    allowed = {
        "sourceUrl",
        "targetRepository",
        "targetDirectory",
        "targetBaseBranch",
        "branchName",
        "pullRequestTitle",
        "pullRequestBody",
        "deferPublication",
    }
    if not set(payload).issubset(allowed):
        raise WorkflowError("invalid_input", "Input contains unsupported properties.")
    parse_source_url(payload.get("sourceUrl"))
    deferred = payload.get("deferPublication", False)
    if not isinstance(deferred, bool):
        raise WorkflowError("invalid_input", "deferPublication must be a boolean.")
    target = payload.get("targetRepository")
    if not deferred and (not isinstance(target, str) or not target.strip()):
        raise WorkflowError("invalid_input", "targetRepository is required.")
    if target is not None and (not isinstance(target, str) or not target.strip()):
        raise WorkflowError("invalid_input", "targetRepository must be a non-empty string.")
    for field in allowed - {"sourceUrl", "targetRepository", "deferPublication"}:
        value = payload.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise WorkflowError("invalid_input", f"{field} must be a non-empty string.")
    return payload


def validate_schema(value: Any) -> dict[str, Any]:
    if isinstance(value, dict) and isinstance(value.get("error"), dict):
        error = value["error"]
        raise WorkflowError(
            str(error.get("code", "schema_generation_failed")),
            str(error.get("message", "Database schema generation failed.")),
        )
    if not isinstance(value, dict) or set(value) != {"database", "tables", "types"}:
        raise WorkflowError("invalid_generator_output", "Generator response must contain database, tables, and types.")
    if not isinstance(value["database"], dict) or set(value["database"]) != {"name", "engine"}:
        raise WorkflowError("invalid_generator_output", "Generator response contains an invalid database object.")
    if not isinstance(value["tables"], list) or not isinstance(value["types"], list):
        raise WorkflowError("invalid_generator_output", "Generator response contains an incomplete database schema.")
    return value


def _validate_blob_url(value: object, source: tuple[str, str, str]) -> str:
    if not isinstance(value, str):
        raise WorkflowError("invalid_discovery_output", "Discovered file URLs must be strings.")
    parsed = urllib.parse.urlparse(value)
    parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if (
        parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}
        or parsed.username or parsed.password or parsed.query or parsed.fragment
        or len(parts) < 5 or parts[2] != "blob"
        or (parts[0], parts[1].removesuffix(".git"), parts[3]) != source
        or any(part in {".", ".."} or "/" in part or "\\" in part for part in parts)
    ):
        raise WorkflowError("invalid_discovery_output", "Discovered files must be GitHub blob URLs from the source repository and ref.")
    return value


def validate_discovery_output(value: Any, source_url: str, max_files: int) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schemaFiles", "excludedFiles"}:
        raise WorkflowError("invalid_discovery_output", "Discovery must contain exactly schemaFiles and excludedFiles.")
    files = value["schemaFiles"]
    excluded = value["excludedFiles"]
    if not isinstance(files, list) or not files or len(files) > max_files:
        raise WorkflowError("invalid_discovery_output", f"schemaFiles must contain between 1 and {max_files} files.")
    source = parse_source_url(source_url)
    validated = [_validate_blob_url(item, source) for item in files]
    if len(validated) != len(set(validated)):
        raise WorkflowError("invalid_discovery_output", "schemaFiles must be unique.")
    if not isinstance(excluded, list) or any(not isinstance(item, dict) or set(item) != {"path", "reason"} or not all(isinstance(item[key], str) and item[key] for key in item) for item in excluded):
        raise WorkflowError("invalid_discovery_output", "excludedFiles has an invalid shape.")
    return {"schemaFiles": validated, "excludedFiles": excluded}


def invoke_agent(project: Any, agent_name: str, model: str, payload: dict[str, Any], max_attempts: int = 2) -> Any:
    last_error: Exception | None = None
    for _ in range(max(1, max_attempts)):
        try:
            client = project.get_openai_client(agent_name=agent_name)
            response = client.responses.create(
                model=model,
                input=json.dumps(payload, separators=(",", ":")),
                timeout=600,
            )
            return parse_json_value(response.output_text)
        except Exception as error:
            last_error = error
    assert last_error is not None
    raise last_error


def merge_schemas(schemas: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    database_name: str | None = None
    database_engine: str | None = None
    tables: list[dict[str, Any]] = []
    table_identities: set[tuple[Any, Any]] = set()
    types: list[dict[str, Any]] = []
    type_names: set[str] = set()
    warnings: list[dict[str, Any]] = []
    for schema in schemas:
        database_name = database_name or schema["database"]["name"]
        database_engine = database_engine or schema["database"]["engine"]
        for table in schema["tables"]:
            identity = (table["schema"], table["name"])
            if identity in table_identities:
                warnings.append(
                    {
                        "errorType": "DuplicateTable",
                        "message": (
                            f"Generator produced table {table['name']!r} more than once; "
                            "kept the first occurrence and discarded the duplicate."
                        ),
                    }
                )
                continue
            table_identities.add(identity)
            tables.append(table)
        for named_type in schema["types"]:
            if named_type["name"] not in type_names:
                type_names.add(named_type["name"])
                types.append(named_type)
    return {"database": {"name": database_name, "engine": database_engine}, "tables": tables, "types": types}, warnings


def _generate_batch(
    project: Any,
    generator_name: str,
    model: str,
    source_url: str,
    batch: list[str],
    invoker: Callable[..., Any],
    max_attempts: int = 3,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for _ in range(max(1, max_attempts)):
        try:
            return validate_schema(
                invoker(project, generator_name, model, {"sourceUrl": source_url, "sourceFiles": batch}, max_attempts=1)
            )
        except Exception as error:
            last_error = error
    assert last_error is not None
    raise last_error


def _publisher_payload(request: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    _, source_repository, _ = parse_source_url(request["sourceUrl"])
    target_directory = request.get("targetDirectory", f"{source_repository}/db-schema")
    payload: dict[str, Any] = {
        "repository": request["targetRepository"],
        "schemas": [
            {
                "sourceUrl": request["sourceUrl"],
                "schema": schema,
                "targetPath": f"{target_directory.strip('/')}/database.schema.json",
            }
        ],
    }
    for source, destination in {
        "targetBaseBranch": "baseBranch",
        "branchName": "branchName",
        "pullRequestTitle": "pullRequestTitle",
        "pullRequestBody": "pullRequestBody",
    }.items():
        if source in request:
            payload[destination] = request[source]
    return payload


def run_workflow(
    project: Any,
    request: dict[str, Any],
    discovery_name: str,
    generator_name: str,
    publisher_name: str,
    model: str,
    max_files: int = 100,
    generator_batch_size: int = 5,
    invoker: Callable[..., Any] = invoke_agent,
) -> dict[str, Any]:
    request = parse_workflow_request(json.dumps(request))
    source_url = request["sourceUrl"]
    batch_errors: list[dict[str, Any]] = []
    try:
        discovery = invoker(project, discovery_name, model, {"sourceUrl": source_url})
        discovered = validate_discovery_output(discovery, source_url, max_files)
        schema_files = discovered["schemaFiles"]
        batches = [
            schema_files[index : index + generator_batch_size]
            for index in range(0, len(schema_files), generator_batch_size)
        ]
        batch_schemas = []
        for batch in batches:
            try:
                batch_schemas.append(_generate_batch(project, generator_name, model, source_url, batch, invoker))
            except Exception as error:
                batch_errors.append(
                    {
                        "sourceUrl": source_url,
                        "files": batch,
                        "errorType": type(error).__name__,
                        "message": str(error)[:300],
                    }
                )
        if not batch_schemas:
            raise WorkflowError("generation_failed", "No batch of source files produced a valid schema.")
        schema, merge_warnings = merge_schemas(batch_schemas)
        batch_errors.extend(merge_warnings)
    except Exception as error:
        return {
            "success": False,
            "sourceUrl": source_url,
            "generatedSchemaCount": 0,
            "discoveredFileCount": 0,
            "excludedFileCount": 0,
            "generationErrors": batch_errors
            or [{"sourceUrl": source_url, "errorType": type(error).__name__, "message": str(error)[:300]}],
            "schemas": [],
            "pullRequest": None,
            "errors": [{"code": "generation_failed", "message": "The database schema was not generated."}],
        }

    schemas = [{"sourceUrl": source_url, "schema": schema}]
    if request.get("deferPublication", False):
        return {
            "success": True,
            "sourceUrl": source_url,
            "generatedSchemaCount": 1,
            "discoveredFileCount": len(discovered["schemaFiles"]),
            "excludedFileCount": len(discovered["excludedFiles"]),
            "generationErrors": batch_errors,
            "schemas": schemas,
            "pullRequest": None,
            "errors": [],
        }

    publication = invoker(
        project,
        publisher_name,
        model,
        _publisher_payload(request, schema),
        max_attempts=1,
    )
    if not isinstance(publication, dict) or not isinstance(publication.get("success"), bool):
        raise WorkflowError("invalid_publisher_output", "PR creator response does not match its JSON contract.")
    return {
        "success": publication["success"],
        "sourceUrl": source_url,
        "generatedSchemaCount": 1,
        "discoveredFileCount": len(discovered["schemaFiles"]),
        "excludedFileCount": len(discovered["excludedFiles"]),
        "generationErrors": batch_errors,
        "schemas": schemas,
        "pullRequest": publication,
        "errors": [],
    }
