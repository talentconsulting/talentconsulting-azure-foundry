"""Deterministic GitHub traversal and ASP.NET endpoint discovery."""

from __future__ import annotations

import json
import io
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from typing import Any


class ScanError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceLocation:
    owner: str
    repository: str
    ref: str
    base_path: str

    @property
    def repository_ref(self) -> str:
        return f"{self.owner}/{self.repository}"


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    operation_name: str


@dataclass(frozen=True)
class SourceFile:
    path: str
    content: str
    endpoints: tuple[Endpoint, ...]


IGNORED_PARTS = {
    ".git", ".github", ".vs", ".vscode", "bin", "build", "dist",
    "node_modules", "obj", "packages", "test", "tests",
}
HTTP_ATTRIBUTE_RE = re.compile(
    r"\bHttp(?P<method>Get|Post|Put|Patch|Delete|Head|Options)"
    r"(?:\s*\(\s*\"(?P<route>[^\"]*)\"[^)]*\))?",
    re.IGNORECASE,
)
ATTRIBUTE_METHOD_RE = re.compile(
    r"(?P<attributes>(?:\s*\[[^\]]+\]\s*)+)"
    r"(?:public|protected|internal)\s+(?:async\s+)?"
    r"(?:[\w<>,?\[\].]+\s+)+(?P<name>\w+)\s*\(",
    re.MULTILINE,
)
CLASS_RE = re.compile(r"\bclass\s+(?P<name>\w+Controller)\b", re.IGNORECASE)
CLASS_ROUTE_RE = re.compile(r"\[\s*Route\s*\(\s*\"(?P<route>[^\"]+)\"", re.IGNORECASE)
ROUTE_CONSTRAINT_RE = re.compile(r"\{(?P<name>[^}:]+)(?::[^}]+)?\}")


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
        raise ScanError("sourceUrl must be a credential-free HTTPS github.com tree URL.")
    segments = [urllib.parse.unquote(value) for value in parsed.path.split("/") if value]
    if len(segments) < 4 or segments[2] != "tree":
        raise ScanError(
            "sourceUrl must match https://github.com/<owner>/<repo>/tree/<ref>/<path>."
        )
    owner, repository, _, ref, *path_parts = segments
    if any(part in {".", ".."} for part in path_parts):
        raise ScanError("sourceUrl path must not contain traversal segments.")
    return SourceLocation(
        owner, repository.removesuffix(".git"), ref, "/".join(path_parts).strip("/")
    )


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.getenv("SOURCE_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")

    def get(self, api_path: str) -> dict[str, Any]:
        request = urllib.request.Request(
            f"https://api.github.com{api_path}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "talent-agent-openAI-generator",
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise ScanError(f"GitHub returned HTTP {error.code} for {api_path}.") from error
        except urllib.error.URLError as error:
            raise ScanError(f"GitHub request failed for {api_path}.") from error
        if not isinstance(payload, dict):
            raise ScanError(f"GitHub returned an invalid object for {api_path}.")
        return payload

    def tree(self, location: SourceLocation) -> list[dict[str, Any]]:
        repo = urllib.parse.quote(location.repository_ref, safe="/")
        ref = urllib.parse.quote(location.ref, safe="")
        payload = self.get(f"/repos/{repo}/git/trees/{ref}?recursive=1")
        if payload.get("truncated"):
            raise ScanError("GitHub tree is truncated; use a narrower sourceUrl.")
        tree = payload.get("tree")
        if not isinstance(tree, list):
            raise ScanError("GitHub response does not contain a tree.")
        return [item for item in tree if isinstance(item, dict)]

    def raw_file(self, location: SourceLocation, path: str) -> str:
        owner = urllib.parse.quote(location.owner, safe="")
        repository = urllib.parse.quote(location.repository, safe="")
        ref = urllib.parse.quote(location.ref, safe="")
        encoded_path = urllib.parse.quote(path, safe="/")
        request = urllib.request.Request(
            f"https://raw.githubusercontent.com/{owner}/{repository}/{ref}/{encoded_path}",
            headers={"User-Agent": "talent-agent-openAI-generator"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            raise ScanError(f"GitHub raw content returned HTTP {error.code} for {path}.") from error
        except (urllib.error.URLError, UnicodeDecodeError) as error:
            raise ScanError(f"Unable to read GitHub raw content for {path}.") from error

    def archive_sources(self, location: SourceLocation) -> list[tuple[str, str]]:
        owner = urllib.parse.quote(location.owner, safe="")
        repository = urllib.parse.quote(location.repository, safe="")
        ref = urllib.parse.quote(location.ref, safe="")
        request = urllib.request.Request(
            f"https://codeload.github.com/{owner}/{repository}/zip/{ref}",
            headers={"User-Agent": "talent-agent-openAI-generator"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                content_length = int(response.headers.get("Content-Length", "0") or "0")
                if content_length > 100 * 1024 * 1024:
                    raise ScanError("GitHub archive exceeds the 100 MiB download limit.")
                archive_bytes = response.read(100 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as error:
            raise ScanError(f"GitHub codeload returned HTTP {error.code}.") from error
        except urllib.error.URLError as error:
            raise ScanError("Unable to download the GitHub source archive.") from error
        if len(archive_bytes) > 100 * 1024 * 1024:
            raise ScanError("GitHub archive exceeds the 100 MiB download limit.")

        sources: list[tuple[str, str]] = []
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
                    if (
                        separator
                        and _is_under_base(relative_path, location.base_path)
                        and is_controller(relative_path)
                    ):
                        sources.append(
                            (
                                relative_path,
                                archive.read(member).decode("utf-8"),
                            )
                        )
        except (zipfile.BadZipFile, UnicodeDecodeError) as error:
            raise ScanError("GitHub returned an invalid source archive.") from error
        return sorted(sources, key=lambda item: item[0])


def _is_under_base(path: str, base_path: str) -> bool:
    return not base_path or path == base_path or path.startswith(f"{base_path}/")


def is_controller(path: str) -> bool:
    lowered = path.lower()
    ignored = {part.lower() for part in path.split("/")} & IGNORED_PARTS
    return (
        lowered.endswith(".cs")
        and not ignored
        and (lowered.endswith("controller.cs") or "/controllers/" in lowered)
    )


def is_infrastructure_controller(source: SourceFile) -> bool:
    lowered = source.path.lower()
    return (
        lowered.endswith("/healthcontroller.cs")
        or "/health/" in lowered
        or all(endpoint.path.rstrip("/").lower() == "/health" for endpoint in source.endpoints)
    )


def _normalize_route(route: str, controller_name: str) -> str:
    value = route.strip().replace("[controller]", controller_name)
    value = ROUTE_CONSTRAINT_RE.sub(lambda match: "{" + match.group("name") + "}", value)
    value = re.sub(r"/+", "/", value)
    return "/" + value.strip("/") if value.strip("/") else "/"


def _join_routes(prefix: str, suffix: str, controller_name: str) -> str:
    if suffix.startswith("~/"):
        return _normalize_route(suffix[2:], controller_name)
    if suffix.startswith("/"):
        return _normalize_route(suffix, controller_name)
    return _normalize_route(f"{prefix.strip('/')}/{suffix.strip('/')}", controller_name)


def discover_aspnet_endpoints(content: str) -> tuple[Endpoint, ...]:
    class_match = CLASS_RE.search(content)
    controller_name = (
        class_match.group("name")[: -len("Controller")].lower() if class_match else ""
    )
    class_prefix = ""
    if class_match:
        routes = list(CLASS_ROUTE_RE.finditer(content[: class_match.start()]))
        if routes:
            class_prefix = routes[-1].group("route")

    endpoints: set[Endpoint] = set()
    for method_match in ATTRIBUTE_METHOD_RE.finditer(content):
        for http_match in HTTP_ATTRIBUTE_RE.finditer(method_match.group("attributes")):
            endpoints.add(
                Endpoint(
                    http_match.group("method").lower(),
                    _join_routes(
                        class_prefix, http_match.group("route") or "", controller_name
                    ),
                    method_match.group("name"),
                )
            )
    return tuple(
        sorted(endpoints, key=lambda item: (item.path, item.method, item.operation_name))
    )


def scan_source_url(source_url: str, client: GitHubClient | None = None) -> list[SourceFile]:
    location = parse_source_url(source_url)
    github = client or GitHubClient()
    files = []
    for path, content in github.archive_sources(location):
        endpoints = discover_aspnet_endpoints(content)
        if endpoints:
            files.append(SourceFile(path, content, endpoints))
    if any(not is_infrastructure_controller(source) for source in files):
        files = [source for source in files if not is_infrastructure_controller(source)]
    return files
