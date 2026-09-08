"""Deterministically parse .csproj, global.json, Bicep, and Terraform files into a repo-metadata catalog."""

from __future__ import annotations

import json
import os
import re
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
            request = urllib.request.Request(url, headers={"User-Agent": "repo-metadata-generator"})
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


def _fetch_last_commit_date(location: SourceLocation) -> str:
    url = (
        f"https://api.github.com/repos/{urllib.parse.quote(location.owner, safe='')}/"
        f"{urllib.parse.quote(location.repository, safe='')}/commits/{urllib.parse.quote(location.ref, safe='')}"
    )
    failure = GenerationError(
        "commit_lookup_failed",
        f"Unable to determine the last commit date for {location.owner}/{location.repository}@{location.ref}.",
    )
    headers = {"User-Agent": "repo-metadata-generator"}
    token = os.environ.get("GITHUB_READ_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        raise failure from error
    except urllib.error.URLError as error:
        raise failure from error
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise failure from error
    if not isinstance(payload, dict):
        raise failure
    commit = payload.get("commit")
    committer = commit.get("committer") if isinstance(commit, dict) else None
    author = commit.get("author") if isinstance(commit, dict) else None
    date = committer.get("date") if isinstance(committer, dict) else None
    if not isinstance(date, str) or not date:
        date = author.get("date") if isinstance(author, dict) else None
    if not isinstance(date, str) or not date:
        raise failure
    return date


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


_BICEP_RESOURCE_PATTERN = re.compile(
    r"\bresource\b\s+[A-Za-z_][A-Za-z0-9_]*\s+'([^'@]+)@[^']*'\s*(?:existing\s+)?=\s*\{"
)
_BICEP_NAME_PATTERN = re.compile(r"name\s*:\s*'([^']*)'")
_TERRAFORM_RESOURCE_PATTERN = re.compile(r'\bresource\b\s+"([^"]+)"\s+"[^"]*"\s*\{')
_TERRAFORM_NAME_PATTERN = re.compile(r'name\s*=\s*"([^"]*)"')


def _matching_brace_index(content: str, open_brace_index: int) -> int:
    """Return the index of the '}' that closes the '{' at open_brace_index, by depth counting.

    This is a plain character-level brace counter, not a string-literal-aware tokenizer: a
    '{' or '}' that happens to appear inside a nested string literal (for example Bicep string
    interpolation like '${...}' containing its own braces, or a plain string value containing a
    literal brace character) is counted the same as a real block delimiter. In every case
    exercised by this pipeline's own resource declarations that has not been an issue -- Bicep's
    own '${...}' interpolation braces are still balanced pairs, so depth counting still finds the
    correct end -- but a resource block whose string content contained a genuinely unbalanced
    brace character would throw this off. If no matching '}' is found (unbalanced/truncated
    content), the end of the string is returned so the caller still gets a bounded slice instead
    of raising.
    """
    depth = 1
    index = open_brace_index + 1
    length = len(content)
    while index < length:
        char = content[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return length


def _first_literal_name(block: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(block)
    if not match:
        return None
    value = match.group(1)
    # A quoted value containing '${' is a string interpolation/expression, not a plain literal
    # (e.g. Bicep '${var}-thing' or Terraform "${var.prefix}-thing") -- treat it as unresolved.
    if "${" in value:
        return None
    return value


def _parse_bicep(content: str) -> list[dict[str, Any]]:
    """Extract {type, name} pairs from top-level Bicep `resource` declarations.

    Only literal single-quoted `name: '...'` values are resolved; anything else (a variable
    reference, an expression, or a string interpolation like '${var}-thing') yields name: None.
    `existing` resource references are included, since they still describe a dependency of this
    application even though Bicep will not deploy them. Out of scope for this pass: .bicepparam
    files and ARM JSON templates are not parsed at all (the source-discovery scanner never
    selects them), and Bicep modules (`module` blocks) are not treated as resources.
    """
    resources: list[dict[str, Any]] = []
    try:
        for match in _BICEP_RESOURCE_PATTERN.finditer(content):
            resource_type = match.group(1)
            open_brace_index = match.end() - 1
            close_brace_index = _matching_brace_index(content, open_brace_index)
            block = content[open_brace_index + 1 : close_brace_index]
            resources.append({"type": resource_type, "name": _first_literal_name(block, _BICEP_NAME_PATTERN)})
    except Exception:
        return []
    return resources


def _parse_terraform(content: str) -> list[dict[str, Any]]:
    """Extract {type, name} pairs from top-level Terraform `resource "azurerm_..." "..." {}` blocks.

    Only resource types starting with `azurerm_` are included -- other providers (aws_*,
    google_*, etc.) are skipped, since this pipeline is specifically extracting Azure
    infrastructure. Only literal double-quoted `name = "..."` values are resolved; anything else
    (a variable reference, an expression, or a string interpolation like "${var.prefix}-thing")
    yields name: None. Terraform `data` blocks are out of scope for this pass and are never
    matched, since the pattern only matches the `resource` keyword.
    """
    resources: list[dict[str, Any]] = []
    try:
        for match in _TERRAFORM_RESOURCE_PATTERN.finditer(content):
            resource_type = match.group(1)
            if not resource_type.startswith("azurerm_"):
                continue
            open_brace_index = match.end() - 1
            close_brace_index = _matching_brace_index(content, open_brace_index)
            block = content[open_brace_index + 1 : close_brace_index]
            resources.append({"type": resource_type, "name": _first_literal_name(block, _TERRAFORM_NAME_PATTERN)})
    except Exception:
        return []
    return resources


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


def _build_catalog(location: SourceLocation, sources: dict[str, str], last_commit_date: str) -> dict[str, Any]:
    projects: list[dict[str, Any]] = []
    sdks: list[dict[str, Any]] = []
    azure_resources: list[dict[str, Any]] = []
    for path in sorted(sources):
        content = sources[path]
        lower_path = path.lower()
        if lower_path.endswith(".csproj"):
            projects.append({"path": path, "targetFrameworks": _parse_csproj(content)})
        elif lower_path.rsplit("/", 1)[-1] == "global.json":
            sdk = _parse_global_json(content)
            if sdk is not None:
                sdks.append({"path": path, **sdk})
        elif lower_path.endswith(".bicep"):
            for resource in _parse_bicep(content):
                azure_resources.append({"path": path, **resource})
        elif lower_path.endswith(".tf"):
            for resource in _parse_terraform(content):
                azure_resources.append({"path": path, **resource})
    return {
        "repository": f"{location.owner}/{location.repository}",
        "ref": location.ref,
        "path": location.base_path,
        "lastCommitDate": last_commit_date,
        "projects": projects,
        "sdks": sdks,
        "azureResources": azure_resources,
    }


def validate_catalog(
    document: dict[str, Any],
    location: SourceLocation | None = None,
    source_paths: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(document, dict) or set(document) != {
        "repository", "ref", "path", "lastCommitDate", "projects", "sdks", "azureResources",
    }:
        raise GenerationError(
            "invalid_catalog",
            "Catalog must contain repository, ref, path, lastCommitDate, projects, sdks, and azureResources.",
        )
    if not all(isinstance(document[field], str) for field in ("repository", "ref", "path", "lastCommitDate")):
        raise GenerationError("invalid_catalog", "Catalog repository, ref, path, and lastCommitDate must be strings.")
    if not document["lastCommitDate"]:
        raise GenerationError("invalid_catalog", "Catalog lastCommitDate must be a non-empty string.")
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

    azure_resources = document["azureResources"]
    if not isinstance(azure_resources, list):
        raise GenerationError("invalid_catalog", "azureResources must be a list.")
    for item in azure_resources:
        if (
            not isinstance(item, dict)
            or set(item) != {"path", "type", "name"}
            or not isinstance(item["path"], str)
            or not item["path"]
            or not isinstance(item["type"], str)
            or not item["type"]
            or not (item["name"] is None or (isinstance(item["name"], str) and item["name"]))
        ):
            raise GenerationError(
                "invalid_catalog",
                "Each azureResources entry must contain path, type, and name (name may be null).",
            )
        if source_paths is not None and item["path"] not in source_paths:
            raise GenerationError(
                "invalid_catalog", f"azureResources path {item['path']} was not one of the supplied source files."
            )
        # Unlike projects/sdks, a single Bicep/Terraform file can legitimately declare many
        # resources, so many azureResources entries are expected to share the same path -- no
        # path-uniqueness check here.

    return {
        "repository": document["repository"],
        "ref": document["ref"],
        "path": document["path"],
        "lastCommitDate": document["lastCommitDate"],
        "projects": sorted(projects, key=lambda item: item["path"].lower()),
        "sdks": sorted(sdks, key=lambda item: item["path"].lower()),
        "azureResources": sorted(
            azure_resources, key=lambda item: (item["path"].lower(), item["type"], item["name"] or "")
        ),
    }


def generate_from_text(
    user_input: str,
    source_loader: Callable[[SourceLocation, list[str]], dict[str, str]] = _download_selected_sources,
    commit_date_loader: Callable[[SourceLocation], str] = _fetch_last_commit_date,
) -> dict[str, Any]:
    parsed = parse_input(user_input)
    location: SourceLocation = parsed["location"]
    sources = source_loader(location, parsed["paths"])
    last_commit_date = commit_date_loader(location)
    catalog = _build_catalog(location, sources, last_commit_date)
    return validate_catalog(catalog, location=location, source_paths=set(sources))
