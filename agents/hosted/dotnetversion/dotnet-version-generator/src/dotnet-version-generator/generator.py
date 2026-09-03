"""Deterministically parse .csproj and global.json files into a .NET version catalog."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Callable


MAX_SOURCE_FILES = 100
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024


class GenerationError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SourceLocation:
    owner: str
    repository: str
    ref: str
    base_path: str


def parse_source_url(value: object) -> SourceLocation:
    if not isinstance(value, str) or not value.strip():
        raise GenerationError("invalid_input", "sourceUrl must be a GitHub tree URL.")
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
        raise GenerationError("invalid_input", "sourceUrl must match https://github.com/owner/repository/tree/ref[/path].")
    owner, repository, _, ref, *path = parts
    return SourceLocation(owner, repository.removesuffix(".git"), ref, "/".join(path))


def _validate_blob_url(value: object, location: SourceLocation) -> str:
    if not isinstance(value, str):
        raise GenerationError("invalid_input", "sourceFiles must contain GitHub blob URLs.")
    parsed = urllib.parse.urlparse(value)
    parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"github.com", "www.github.com"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or len(parts) < 5
        or parts[2] != "blob"
        or any(part in {".", ".."} or "/" in part or "\\" in part for part in parts)
    ):
        raise GenerationError("invalid_input", "sourceFiles must contain GitHub blob URLs.")
    owner, repository, _, ref, *path_parts = parts
    if (owner, repository.removesuffix(".git"), ref) != (location.owner, location.repository, location.ref):
        raise GenerationError("invalid_input", "sourceFiles must belong to the same repository and ref as sourceUrl.")
    return "/".join(path_parts)


def parse_input(user_input: str) -> dict[str, Any]:
    try:
        payload = json.loads(user_input)
    except json.JSONDecodeError as error:
        raise GenerationError("invalid_input", "Input must be one JSON object.") from error
    if not isinstance(payload, dict) or set(payload) != {"sourceUrl", "sourceFiles"}:
        raise GenerationError("invalid_input", "Input must contain exactly sourceUrl and sourceFiles.")
    location = parse_source_url(payload["sourceUrl"])
    files = payload["sourceFiles"]
    if not isinstance(files, list) or not files or len(files) > MAX_SOURCE_FILES:
        raise GenerationError("invalid_input", f"sourceFiles must contain 1-{MAX_SOURCE_FILES} blob URLs.")
    paths: list[str] = []
    seen: set[str] = set()
    for item in files:
        path = _validate_blob_url(item, location)
        if path in seen:
            raise GenerationError("invalid_input", "sourceFiles must not contain duplicates.")
        seen.add(path)
        paths.append(path)
    return {"location": location, "paths": paths}


def _download_selected_sources(location: SourceLocation, paths: list[str]) -> dict[str, str]:
    sources: dict[str, str] = {}
    total_bytes = 0
    for path in paths:
        url = (
            f"https://raw.githubusercontent.com/{urllib.parse.quote(location.owner, safe='')}/"
            f"{urllib.parse.quote(location.repository, safe='')}/{urllib.parse.quote(location.ref, safe='')}/"
            f"{urllib.parse.quote(path, safe='/')}"
        )
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "dotnet-version-generator"})
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read(MAX_FILE_BYTES + 1)
        except urllib.error.HTTPError as error:
            raise GenerationError("source_download_failed", f"GitHub returned HTTP {error.code} for {path}.") from error
        except urllib.error.URLError as error:
            raise GenerationError("source_download_failed", f"Unable to download {path}.") from error
        if len(body) > MAX_FILE_BYTES:
            raise GenerationError("source_too_large", f"{path} exceeds the 512 KiB per-file limit.")
        total_bytes += len(body)
        if total_bytes > MAX_TOTAL_BYTES:
            raise GenerationError("source_too_large", "Selected source files exceed the 2 MiB combined limit.")
        try:
            sources[path] = body.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise GenerationError("source_not_utf8", f"{path} is not UTF-8 text.") from error
    return sources


def _local_tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _find_all_local(root: ET.Element, tag: str) -> list[ET.Element]:
    return [element for element in root.iter() if _local_tag(element) == tag]


def _parse_csproj(content: str) -> list[str]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []
    frameworks: list[str] = []
    for element in _find_all_local(root, "TargetFrameworks"):
        if element.text:
            frameworks.extend(part.strip() for part in element.text.split(";") if part.strip())
    if not frameworks:
        for element in _find_all_local(root, "TargetFramework"):
            if element.text and element.text.strip():
                frameworks.append(element.text.strip())
    if not frameworks:
        # Legacy (non-SDK-style) .NET Framework projects declare a single moniker this way instead.
        for element in _find_all_local(root, "TargetFrameworkVersion"):
            if element.text and element.text.strip():
                frameworks.append(element.text.strip())
    seen: set[str] = set()
    deduped: list[str] = []
    for framework in frameworks:
        if framework not in seen:
            seen.add(framework)
            deduped.append(framework)
    return deduped


def _parse_global_json(content: str) -> dict[str, str] | None:
    try:
        document = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(document, dict):
        return None
    sdk = document.get("sdk")
    if not isinstance(sdk, dict):
        return None
    version = sdk.get("version")
    if not isinstance(version, str) or not version.strip():
        return None
    result = {"version": version.strip()}
    roll_forward = sdk.get("rollForward")
    if isinstance(roll_forward, str) and roll_forward.strip():
        result["rollForward"] = roll_forward.strip()
    return result


def _build_catalog(location: SourceLocation, sources: dict[str, str]) -> dict[str, Any]:
    projects: list[dict[str, Any]] = []
    sdks: list[dict[str, Any]] = []
    for path in sorted(sources):
        content = sources[path]
        if path.lower().endswith(".csproj"):
            projects.append({"path": path, "targetFrameworks": _parse_csproj(content)})
        elif path.lower().rsplit("/", 1)[-1] == "global.json":
            sdk = _parse_global_json(content)
            if sdk is not None:
                sdks.append({"path": path, **sdk})
    return {
        "repository": f"{location.owner}/{location.repository}",
        "ref": location.ref,
        "path": location.base_path,
        "projects": projects,
        "sdks": sdks,
    }


def validate_catalog(
    document: dict[str, Any],
    location: SourceLocation | None = None,
    source_paths: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(document, dict) or set(document) != {"repository", "ref", "path", "projects", "sdks"}:
        raise GenerationError("invalid_catalog", "Catalog must contain repository, ref, path, projects, and sdks.")
    if not all(isinstance(document[field], str) for field in ("repository", "ref", "path")):
        raise GenerationError("invalid_catalog", "Catalog repository, ref, and path must be strings.")
    if location is not None and (document["repository"], document["ref"], document["path"]) != (
        f"{location.owner}/{location.repository}",
        location.ref,
        location.base_path,
    ):
        raise GenerationError("invalid_catalog", "Catalog source identity does not match sourceUrl.")

    projects = document["projects"]
    if not isinstance(projects, list):
        raise GenerationError("invalid_catalog", "projects must be a list.")
    seen_project_paths: set[str] = set()
    for item in projects:
        if (
            not isinstance(item, dict)
            or set(item) != {"path", "targetFrameworks"}
            or not isinstance(item["path"], str)
            or not item["path"]
            or not isinstance(item["targetFrameworks"], list)
            or not all(isinstance(framework, str) and framework for framework in item["targetFrameworks"])
        ):
            raise GenerationError("invalid_catalog", "Each project must contain path and targetFrameworks.")
        if source_paths is not None and item["path"] not in source_paths:
            raise GenerationError("invalid_catalog", f"project path {item['path']} was not one of the supplied source files.")
        if item["path"] in seen_project_paths:
            raise GenerationError("invalid_catalog", f"Duplicate project path {item['path']}.")
        seen_project_paths.add(item["path"])

    sdks = document["sdks"]
    if not isinstance(sdks, list):
        raise GenerationError("invalid_catalog", "sdks must be a list.")
    seen_sdk_paths: set[str] = set()
    for item in sdks:
        if (
            not isinstance(item, dict)
            or not set(item).issubset({"path", "version", "rollForward"})
            or not isinstance(item.get("path"), str)
            or not item.get("path")
            or not isinstance(item.get("version"), str)
            or not item.get("version")
            or ("rollForward" in item and (not isinstance(item["rollForward"], str) or not item["rollForward"]))
        ):
            raise GenerationError("invalid_catalog", "Each sdk entry must contain path and version, with an optional rollForward.")
        if source_paths is not None and item["path"] not in source_paths:
            raise GenerationError("invalid_catalog", f"sdk path {item['path']} was not one of the supplied source files.")
        if item["path"] in seen_sdk_paths:
            raise GenerationError("invalid_catalog", f"Duplicate sdk path {item['path']}.")
        seen_sdk_paths.add(item["path"])

    return {
        "repository": document["repository"],
        "ref": document["ref"],
        "path": document["path"],
        "projects": sorted(projects, key=lambda item: item["path"].lower()),
        "sdks": sorted(sdks, key=lambda item: item["path"].lower()),
    }


def generate_from_text(
    user_input: str,
    source_loader: Callable[[SourceLocation, list[str]], dict[str, str]] = _download_selected_sources,
) -> dict[str, Any]:
    parsed = parse_input(user_input)
    location: SourceLocation = parsed["location"]
    sources = source_loader(location, parsed["paths"])
    catalog = _build_catalog(location, sources)
    return validate_catalog(catalog, location=location, source_paths=set(sources))
