import base64
import json
import unittest

from github_pr import PublicationError, parse_request, publish


SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "Bids API", "version": "1.0.0"},
    "paths": {},
    "components": {"schemas": {}},
}


def request_payload():
    return {
        "repository": "target/specs",
        "specifications": [
            {
                "apiFile": "https://github.com/source/app/blob/main/src/Api/BidsController.cs",
                "specification": SPEC,
            }
        ],
        "targetDirectory": "openapi",
    }


class FakeClient:
    def __init__(self, existing=None):
        self.existing = existing
        self.calls = []

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET" and path == "/repos/target/specs":
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
            return {"html_url": "https://github.com/target/specs/pull/7", "number": 7}
        raise AssertionError((method, path, payload))


class GitHubPrTests(unittest.TestCase):
    def test_parse_requires_json_object(self):
        with self.assertRaisesRegex(PublicationError, "one JSON object"):
            parse_request("[]")

    def test_rejects_non_openapi_specification(self):
        payload = request_payload()
        payload["specifications"][0]["specification"] = {"openapi": "3.0.0"}
        with self.assertRaisesRegex(PublicationError, "OpenAPI 3.1.0"):
            publish(payload, FakeClient())

    def test_rejects_invalid_branch_name(self):
        payload = request_payload()
        payload["branchName"] = "../main"
        with self.assertRaisesRegex(PublicationError, "valid Git branch"):
            publish(payload, FakeClient())

    def test_creates_single_commit_and_pull_request(self):
        client = FakeClient()
        result = publish(request_payload(), client, branch_factory=lambda: "openapi-specs/test")
        self.assertEqual("created", result["status"])
        self.assertEqual(7, result["pullRequestNumber"])
        self.assertEqual(
            "openapi/BidsController.openapi.json", result["filesWritten"][0]["path"]
        )
        self.assertEqual("created", result["filesWritten"][0]["action"])
        ref_call = next(call for call in client.calls if call[1].endswith("/git/refs"))
        self.assertEqual("refs/heads/openapi-specs/test", ref_call[2]["ref"])

    def test_does_not_create_branch_when_content_is_unchanged(self):
        content = (json.dumps(SPEC, indent=2) + "\n").encode("utf-8")
        client = FakeClient(existing=content)
        result = publish(request_payload(), client)
        self.assertEqual("unchanged", result["status"])
        self.assertFalse(any(call[1].endswith("/git/refs") for call in client.calls))
        self.assertFalse(any(call[1].endswith("/pulls") for call in client.calls))

    def test_writes_explicit_target_path_and_manifest_in_same_commit(self):
        payload = request_payload()
        payload["specifications"][0]["targetPath"] = "openapi/source/app/Bids.openapi.json"
        payload["manifestFile"] = {
            "path": "repoManifest.json",
            "content": [{"github-repo": "https://github.com/source/app"}],
        }
        client = FakeClient()

        result = publish(payload, client, branch_factory=lambda: "openapi-specs/manifest")

        self.assertEqual(
            ["openapi/source/app/Bids.openapi.json", "repoManifest.json"],
            [item["path"] for item in result["filesWritten"]],
        )
        tree_call = next(call for call in client.calls if call[1].endswith("/git/trees"))
        self.assertEqual(2, len(tree_call[2]["tree"]))


if __name__ == "__main__":
    unittest.main()
