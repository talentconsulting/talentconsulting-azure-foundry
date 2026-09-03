import base64
import json
import unittest

from github_pr import PublicationError, parse_request, publish, validate_request


CATALOG = {
    "repository": "source/app",
    "ref": "main",
    "path": "src",
    "projects": [{"path": "src/App/App.csproj", "targetFrameworks": ["net8.0"]}],
    "sdks": [{"path": "src/global.json", "version": "8.0.100"}],
}


def payload():
    return {
        "repository": "target/catalogue",
        "catalogs": [{
            "sourceUrl": "https://github.com/source/app/tree/main/src",
            "catalog": CATALOG,
            "targetPath": "app/dotnet-version/dotnet-version.json",
        }],
    }


class FakeClient:
    def __init__(self, existing=None):
        self.existing = existing
        self.calls = []

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        if method == "GET" and path == "/repos/target/catalogue":
            return {"default_branch": "main"}
        if method == "GET" and "/contents/" in path:
            if self.existing is None:
                raise PublicationError("github_api_error", "GitHub API returned HTTP 404. Not Found")
            return {"type": "file", "content": base64.b64encode(self.existing).decode("ascii")}
        if method == "GET" and "/git/ref/heads/" in path:
            return {"object": {"sha": "base-sha"}}
        if method == "GET" and "/git/commits/base-sha" in path:
            return {"tree": {"sha": "base-tree"}}
        if method == "POST" and path.endswith("/git/blobs"):
            return {"sha": "blob-sha"}
        if method == "POST" and path.endswith("/git/trees"):
            return {"sha": "tree-sha"}
        if method == "POST" and path.endswith("/git/commits"):
            return {"sha": "commit-sha"}
        if method == "POST" and path.endswith("/git/refs"):
            return {}
        if method == "POST" and path.endswith("/pulls"):
            return {"html_url": "https://github.com/target/catalogue/pull/7", "number": 7}
        raise AssertionError((method, path, body))


class PublisherTests(unittest.TestCase):
    def test_parse_requires_json_object(self):
        with self.assertRaisesRegex(PublicationError, "one JSON object"):
            parse_request("[]")

    def test_validate_request_rejects_invalid_catalog_shape(self):
        request = payload()
        request["catalogs"][0]["catalog"] = {"repository": "source/app"}
        with self.assertRaisesRegex(PublicationError, "repository, ref, path, projects, and sdks"):
            validate_request(request)

    def test_validate_request_defaults_target_path_to_repo_first_convention(self):
        request = {
            "repository": "target/catalogue",
            "catalogs": [{
                "sourceUrl": "https://github.com/source/app/tree/main/src",
                "catalog": CATALOG,
            }],
        }
        result = validate_request(request)
        self.assertEqual(
            "app/dotnet-version/dotnet-version.json",
            result["catalogs"][0]["path"],
        )

    def test_validate_request_honors_target_directory_override(self):
        request = {
            "repository": "target/catalogue",
            "targetDirectory": "custom-dir",
            "catalogs": [{
                "sourceUrl": "https://github.com/source/app/tree/main/src",
                "catalog": CATALOG,
            }],
        }
        result = validate_request(request)
        self.assertEqual(
            "app/custom-dir/dotnet-version.json",
            result["catalogs"][0]["path"],
        )

    def test_validate_request_rejects_duplicate_target_paths(self):
        request = payload()
        request["catalogs"].append(dict(request["catalogs"][0]))
        with self.assertRaisesRegex(PublicationError, "Multiple catalogs map to"):
            validate_request(request)

    def test_publish_returns_unchanged_when_nothing_differs(self):
        existing = (json.dumps(CATALOG, indent=2) + "\n").encode("utf-8")
        client = FakeClient(existing)
        result = publish(payload(), client)
        self.assertEqual("unchanged", result["status"])
        self.assertEqual("", result["branchName"])
        self.assertEqual("", result["commitSha"])
        self.assertEqual("", result["pullRequestUrl"])
        self.assertEqual(0, result["pullRequestNumber"])
        self.assertFalse(any(call[0] == "POST" for call in client.calls))

    def test_publish_creates_one_commit_and_one_pull_request_when_content_differs(self):
        client = FakeClient()
        result = publish(payload(), client, branch_factory=lambda: "dotnet-version/test")
        self.assertEqual("created", result["status"])
        self.assertEqual(7, result["pullRequestNumber"])
        self.assertEqual("commit-sha", result["commitSha"])
        self.assertEqual("app/dotnet-version/dotnet-version.json", result["filesWritten"][0]["path"])
        self.assertEqual(1, len([call for call in client.calls if call[1].endswith("/pulls")]))
        self.assertEqual(1, len([call for call in client.calls if call[1].endswith("/git/commits") and call[0] == "POST"]))

    def test_publish_includes_manifest_file_in_the_same_tree_as_catalogs(self):
        request = payload()
        request["manifestFile"] = {"path": "manifest.json", "content": []}
        client = FakeClient()
        result = publish(request, client, branch_factory=lambda: "dotnet-version/manifest")
        self.assertEqual(2, len(result["filesWritten"]))
        tree_call = next(call for call in client.calls if call[1].endswith("/git/trees"))
        self.assertEqual(2, len(tree_call[2]["tree"]))


if __name__ == "__main__":
    unittest.main()
