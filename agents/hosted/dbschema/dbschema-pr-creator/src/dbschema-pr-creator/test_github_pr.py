import base64
import json
import unittest

from github_pr import PublicationError, parse_request, publish


SCHEMA = {"database": {"name": "app", "engine": None}, "tables": [{"name": "orders"}], "types": []}


def payload():
    return {
        "repository": "target/catalogue",
        "schemas": [{
            "sourceUrl": "https://github.com/source/app/tree/main/src/Data",
            "schema": SCHEMA,
            "targetPath": "app/db-schema/database.schema.json",
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

    def test_rejects_invalid_schema(self):
        request = payload()
        request["schemas"][0]["schema"] = {"tables": []}
        with self.assertRaisesRegex(PublicationError, "database, tables, and types"):
            publish(request, FakeClient())

    def test_creates_one_commit_and_pull_request(self):
        client = FakeClient()
        result = publish(payload(), client, branch_factory=lambda: "dbschema/test")
        self.assertEqual("created", result["status"])
        self.assertEqual(7, result["pullRequestNumber"])
        self.assertEqual("app/db-schema/database.schema.json", result["filesWritten"][0]["path"])
        self.assertEqual(1, len([call for call in client.calls if call[1].endswith("/pulls")]))

    def test_unchanged_content_does_not_create_pull_request(self):
        existing = (json.dumps(SCHEMA, indent=2) + "\n").encode("utf-8")
        client = FakeClient(existing)
        result = publish(payload(), client)
        self.assertEqual("unchanged", result["status"])
        self.assertFalse(any(call[1].endswith("/pulls") for call in client.calls))

    def test_schema_and_manifest_share_one_tree(self):
        request = payload()
        request["manifestFile"] = {"path": "manifest.json", "content": []}
        client = FakeClient()
        result = publish(request, client, branch_factory=lambda: "dbschema/manifest")
        self.assertEqual(2, len(result["filesWritten"]))
        tree_call = next(call for call in client.calls if call[1].endswith("/git/trees"))
        self.assertEqual(2, len(tree_call[2]["tree"]))


if __name__ == "__main__":
    unittest.main()
