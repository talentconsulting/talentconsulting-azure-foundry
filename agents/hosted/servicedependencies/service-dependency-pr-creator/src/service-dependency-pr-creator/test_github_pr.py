import base64
import json
import unittest

from github_pr import PublicationError, parse_request, publish


CATALOG = {
    "repository": "source/app", "ref": "main", "path": "src",
    "systemName": "App", "containers": [], "dependencies": [],
}


def payload():
    return {
        "repository": "target/catalogue",
        "catalogs": [{
            "sourceUrl": "https://github.com/source/app/tree/main/src",
            "catalog": CATALOG,
            "targetPath": "app/service-dependencies/service-dependencies.json",
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
    def test_rejects_invalid_catalog(self):
        request = payload()
        request["catalogs"][0]["catalog"] = {"dependencies": []}
        with self.assertRaisesRegex(PublicationError, "repository, ref, path"):
            publish(request, FakeClient())

    def test_creates_one_commit_and_pull_request(self):
        client = FakeClient()
        result = publish(payload(), client, branch_factory=lambda: "service-dependencies/test")
        self.assertEqual("created", result["status"])
        self.assertEqual("app/service-dependencies/service-dependencies.json", result["filesWritten"][0]["path"])
        self.assertEqual(1, len([call for call in client.calls if call[1].endswith("/pulls")]))

    def test_unchanged_content_does_not_create_pull_request(self):
        client = FakeClient((json.dumps(CATALOG, indent=2) + "\n").encode("utf-8"))
        result = publish(payload(), client)
        self.assertEqual("unchanged", result["status"])
        self.assertFalse(any(call[1].endswith("/pulls") for call in client.calls))

    def test_catalog_and_manifest_share_one_tree(self):
        request = payload()
        request["manifestFile"] = {"path": "manifest.json", "content": []}
        result = publish(request, FakeClient(), branch_factory=lambda: "service-dependencies/manifest")
        self.assertEqual(2, len(result["filesWritten"]))

    def test_puml_is_written_alongside_the_catalog_at_a_derived_path(self):
        request = payload()
        request["catalogs"][0]["puml"] = "@startuml\n@enduml"
        result = publish(request, FakeClient(), branch_factory=lambda: "service-dependencies/puml")
        paths = [item["path"] for item in result["filesWritten"]]
        self.assertEqual(
            ["app/service-dependencies/service-dependencies.json", "app/service-dependencies/service-dependencies.puml"],
            paths,
        )

    def test_puml_is_optional(self):
        result = publish(payload(), FakeClient(), branch_factory=lambda: "service-dependencies/no-puml")
        self.assertEqual(1, len(result["filesWritten"]))

    def test_rejects_a_non_string_puml(self):
        request = payload()
        request["catalogs"][0]["puml"] = 12345
        with self.assertRaisesRegex(PublicationError, "puml must be a string"):
            publish(request, FakeClient())

    def test_parse_requires_json_object(self):
        with self.assertRaisesRegex(PublicationError, "one JSON object"):
            parse_request("[]")


if __name__ == "__main__":
    unittest.main()
