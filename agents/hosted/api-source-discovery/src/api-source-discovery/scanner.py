"""Deterministic GitHub API and payload-file discovery."""

from __future__ import annotations

import io
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass


class ScanError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceLocation:
    owner: str
    repository: str
    ref: str
    base_path: str


IGNORED_PARTS = {
    ".git", ".github", ".vs", ".vscode", "bin", "build", "dist",
    "node_modules", "obj", "packages", "test", "tests",
}
HTTP_ATTRIBUTE_RE = re.compile(
    r"\bHttp(?:Get|Post|Put|Patch|Delete|Head|Options)\b", re.IGNORECASE
)
MAPPED_ROUTE_RE = re.compile(
    r"\.Map(?:Get|Post|Put|Patch|Delete|Methods|Fallback)\s*\(", re.IGNORECASE
)
ACTION_SIGNATURE_RE = re.compile(
    r"(?P<attributes>(?:\s*\[[^\]]+\]\s*)+)"
    r"(?:public|protected|internal)\s+(?:async\s+)?"
    r"(?P<return_type>[\w<>,?\[\].\s]+?)\s+"
    r"(?P<name>\w+)\s*\((?P<parameters>[^)]*)\)",
    re.MULTILINE,
)
TYPE_DECLARATION_RE = re.compile(
    r"\b(?:class|struct|enum|interface|record(?:\s+(?:class|struct))?)\s+"
    r"(?P<name>[A-Za-z_]\w*)\b"
)


def parse_source_url(source_url: str) -> SourceLocation:
    parsed = urllib.parse.urlparse(source_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"github.com", "www.github.com"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ScanError("sourceUrl must be a credential-free HTTPS github.com URL.")
    parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) < 4 or parts[2] != "tree":
        raise ScanError(
            "sourceUrl must match "
            "https://github.com/<owner>/<repository>/tree/<ref>[/<path>]."
        )
    owner, repository, _, ref, *path_parts = parts
    if any(part in {".", ".."} for part in path_parts):
        raise ScanError("sourceUrl path contains an invalid traversal segment.")
    return SourceLocation(
        owner=owner,
        repository=repository.removesuffix(".git"),
        ref=ref,
        base_path="/".join(path_parts).strip("/"),
    )


def _is_ignored(path: str) -> bool:
    return bool({part.lower() for part in path.split("/")} & IGNORED_PARTS)


def _is_under_base(path: str, base_path: str) -> bool:
    return not base_path or path == base_path or path.startswith(f"{base_path}/")


def _is_source_file(path: str) -> bool:
    return path.lower().endswith(".cs") and not _is_ignored(path)


def _is_api_file(path: str, content: str) -> bool:
    if not _is_source_file(path):
        return False
    lowered = path.lower()
    controller_candidate = (
        lowered.endswith("controller.cs") or "/controllers/" in lowered
    )
    return (
        controller_candidate and bool(HTTP_ATTRIBUTE_RE.search(content))
    ) or bool(MAPPED_ROUTE_RE.search(content))


def _download_sources(location: SourceLocation) -> dict[str, str]:
    owner = urllib.parse.quote(location.owner, safe="")
    repository = urllib.parse.quote(location.repository, safe="")
    ref = urllib.parse.quote(location.ref, safe="")
    request = urllib.request.Request(
        f"https://codeload.github.com/{owner}/{repository}/zip/{ref}",
        headers={"User-Agent": "api-source-discovery"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            content_length = int(response.headers.get("Content-Length", "0") or "0")
            if content_length > 100 * 1024 * 1024:
                raise ScanError("GitHub archive exceeds the 100 MiB limit.")
            archive_bytes = response.read(100 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as error:
        raise ScanError(f"GitHub returned HTTP {error.code}.") from error
    except urllib.error.URLError as error:
        raise ScanError("Unable to download the GitHub repository archive.") from error
    if len(archive_bytes) > 100 * 1024 * 1024:
        raise ScanError("GitHub archive exceeds the 100 MiB limit.")

    sources: dict[str, str] = {}
    total_uncompressed = 0
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                total_uncompressed += member.file_size
                if total_uncompressed > 250 * 1024 * 1024:
                    raise ScanError("GitHub archive exceeds the uncompressed size limit.")
                _, separator, relative_path = member.filename.partition("/")
                if separator and _is_source_file(relative_path):
                    sources[relative_path] = archive.read(member).decode("utf-8")
    except (zipfile.BadZipFile, UnicodeDecodeError) as error:
        raise ScanError("GitHub returned an invalid source archive.") from error
    return dict(sorted(sources.items()))


def _action_type_names(content: str) -> set[str]:
    names: set[str] = set()
    for match in ACTION_SIGNATURE_RE.finditer(content):
        if not HTTP_ATTRIBUTE_RE.search(match.group("attributes")):
            continue
        signature = " ".join(
            (
                match.group("attributes"),
                match.group("return_type"),
                match.group("parameters"),
            )
        )
        names.update(re.findall(r"\b[A-Za-z_]\w*\b", signature))

    # Minimal API declarations often keep handler types on the same statement.
    for line in content.splitlines():
        if MAPPED_ROUTE_RE.search(line):
            names.update(re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", line))
    return names


def _supporting_paths(api_path: str, content: str, sources: dict[str, str]) -> list[str]:
    declarations: dict[str, list[str]] = {}
    for path, source in sources.items():
        if path == api_path:
            continue
        for match in TYPE_DECLARATION_RE.finditer(source):
            declarations.setdefault(match.group("name"), []).append(path)

    pending = list(_action_type_names(content))
    visited_types: set[str] = set()
    visited_paths: set[str] = set()
    while pending:
        type_name = pending.pop()
        if type_name in visited_types:
            continue
        visited_types.add(type_name)
        for path in declarations.get(type_name, []):
            if path in visited_paths:
                continue
            visited_paths.add(path)
            source = sources[path]
            pending.extend(
                name
                for name in declarations
                if name not in visited_types
                and re.search(rf"\b{re.escape(name)}\b", source)
            )
    return sorted(visited_paths)


def _blob_url(location: SourceLocation, path: str) -> str:
    return (
        f"https://github.com/{urllib.parse.quote(location.owner, safe='')}/"
        f"{urllib.parse.quote(location.repository, safe='')}/blob/"
        f"{urllib.parse.quote(location.ref, safe='')}/"
        f"{urllib.parse.quote(path, safe='/')}"
    )


def scan(source_url: str, sources: dict[str, str] | None = None) -> list[dict[str, object]]:
    location = parse_source_url(source_url)
    repository_sources = sources if sources is not None else _download_sources(location)
    results: list[dict[str, object]] = []
    for path, content in sorted(repository_sources.items()):
        if not _is_under_base(path, location.base_path) or not _is_api_file(path, content):
            continue
        results.append(
            {
                "apiFile": _blob_url(location, path),
                "supportingFiles": [
                    _blob_url(location, supporting_path)
                    for supporting_path in _supporting_paths(
                        path, content, repository_sources
                    )
                ],
            }
        )
    return results
