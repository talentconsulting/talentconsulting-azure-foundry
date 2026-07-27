"""OpenAPI normalization and deterministic endpoint completion."""

from __future__ import annotations

import json
import re
from typing import Any

from github_scanner import Endpoint, SourceFile


def _service_name(path: str) -> str:
    stem = path.rsplit("/", 1)[-1].removesuffix(".cs")
    stem = stem[: -len("Controller")] if stem.lower().endswith("controller") else stem
    return re.sub(r"(?<!^)(?=[A-Z])", " ", stem).strip() + " API"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "api"


def _operation(endpoint: Endpoint) -> dict[str, Any]:
    value: dict[str, Any] = {
        "operationId": endpoint.operation_name,
        "responses": {"200": {"description": "Successful response"}},
    }
    parameters = [
        {
            "name": name,
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        }
        for name in re.findall(r"\{([^}]+)\}", endpoint.path)
    ]
    if parameters:
        value["parameters"] = parameters
    return value


def ensure_complete(document: dict[str, Any], source: SourceFile) -> dict[str, Any]:
    paths = document.setdefault("paths", {})
    if not isinstance(paths, dict):
        paths = {}
        document["paths"] = paths
    for endpoint in source.endpoints:
        item = paths.setdefault(endpoint.path, {})
        if not isinstance(item, dict):
            item = {}
            paths[endpoint.path] = item
        item.setdefault(endpoint.method, _operation(endpoint))
    return document


def fallback_document(source: SourceFile) -> dict[str, Any]:
    service_name = _service_name(source.path)
    return ensure_complete(
        {
            "openapi": "3.1.0",
            "info": {"title": service_name, "version": "1.0.0"},
            "paths": {},
            "components": {"securitySchemes": {}, "schemas": {}},
            "security": [],
        },
        source,
    )


def parse_json_object(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start, end = value.find("{"), value.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(value[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Model response must be a JSON object.")
    return parsed


def wrap_spec(source: SourceFile, document: dict[str, Any]) -> dict[str, Any]:
    service_name = _service_name(source.path)
    domain_api = _slug(service_name)
    normalized = ensure_complete(document, source)
    normalized["openapi"] = "3.1.0"
    normalized.setdefault("info", {"title": service_name, "version": "1.0.0"})
    components = normalized.setdefault("components", {})
    if not isinstance(components, dict):
        components = {}
        normalized["components"] = components
    components.setdefault("securitySchemes", {})
    components.setdefault("schemas", {})
    normalized.setdefault("security", [])
    return {
        "domain-api": domain_api,
        "open-api": normalized,
        "serviceName": service_name,
        "sourcePath": source.path,
        "fileName": f"{domain_api}.json",
        "contentType": "application/json",
    }
